"""Morgenbriefing Kontextassemblierung (TASK-076).

Implements the 5-step context assembly process for morning briefings:
1. Fetch today's calendar events from stored documents
2. Per event: Neo4j query for participant history, shared projects, open items
3. Semantic search: relevant documents from last 7 days
4. Pending decisions from Neo4j
5. Token-budget check (8000 tokens) with prioritisation

D1 Section 3.5, D4 F-017.  Context priority:
  Calendar events > Pending decisions > Background documents.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

import tiktoken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.search.service import SemanticSearchResult, SemanticSearchService

logger = logging.getLogger(__name__)

__all__ = [
    "CalendarEvent",
    "GraphQueryService",
    "MorningBriefingConfig",
    "MorningBriefingContext",
    "MorningContextAssembler",
    "ParticipantHistory",
    "PendingDecision",
]

# Token counting via tiktoken (cl100k_base covers Claude/GPT-4)
_ENCODING = tiktoken.get_encoding("cl100k_base")

_DEFAULT_TOKEN_BUDGET = 8000
_DEFAULT_LOOKBACK_DAYS = 7
_DEFAULT_MAX_EVENTS = 20
_DEFAULT_MAX_DECISIONS = 10
_DEFAULT_MAX_DOCUMENTS = 20


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    """A calendar event for today."""

    event_id: str
    title: str
    start_time: datetime
    end_time: datetime | None = None
    participants: list[str] = field(default_factory=list)
    notes: str | None = None
    location: str | None = None


@dataclass(frozen=True, slots=True)
class ParticipantHistory:
    """History of interactions with a participant from Neo4j."""

    name: str
    last_meetings: list[str] = field(default_factory=list)
    shared_projects: list[str] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PendingDecision:
    """A pending decision from Neo4j."""

    title: str
    project: str | None = None
    created_date: str | None = None
    context: str | None = None


@dataclass(frozen=True, slots=True)
class MorningBriefingConfig:
    """Configuration for morning briefing context assembly."""

    token_budget: int = _DEFAULT_TOKEN_BUDGET
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS
    max_events: int = _DEFAULT_MAX_EVENTS
    max_decisions: int = _DEFAULT_MAX_DECISIONS
    max_documents: int = _DEFAULT_MAX_DOCUMENTS


@dataclass(slots=True)
class MorningBriefingContext:
    """Assembled context for the morning briefing prompt template.

    Maps directly to the Jinja2 template variables:
    - date, calendar_events, recent_documents
    - participant_histories, pending_decisions
    """

    date: str
    calendar_events: list[dict]
    participant_histories: dict[str, list[ParticipantHistory]]
    recent_documents: list[dict]
    pending_decisions: list[dict]
    token_count: int = 0
    truncated: bool = False


# ------------------------------------------------------------------
# Graph Query Protocol
# ------------------------------------------------------------------


@runtime_checkable
class GraphQueryService(Protocol):
    """Protocol for Neo4j graph queries used by the briefing engine.

    Implementations will query Neo4j for participant history and
    pending decisions.  All queries must filter by owner_id.
    """

    async def get_participant_history(
        self,
        participant_names: list[str],
        owner_id: uuid.UUID,
    ) -> list[ParticipantHistory]:
        """Get interaction history for participants from Neo4j."""
        ...

    async def get_pending_decisions(
        self,
        owner_id: uuid.UUID,
        limit: int = 10,
    ) -> list[PendingDecision]:
        """Get pending decisions sorted by age and relevance."""
        ...


class NullGraphService:
    """No-op graph service for when Neo4j is not available.

    Returns empty results so the briefing can still be generated
    based on calendar events and semantic search alone.
    """

    async def get_participant_history(
        self,
        participant_names: list[str],
        owner_id: uuid.UUID,
    ) -> list[ParticipantHistory]:
        return []

    async def get_pending_decisions(
        self,
        owner_id: uuid.UUID,
        limit: int = 10,
    ) -> list[PendingDecision]:
        return []


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class MorningContextAssembler:
    """Assembles context for the morning briefing.

    Orchestrates calendar event retrieval, graph queries for
    participant history and pending decisions, and semantic search
    for recent relevant documents.  All results are merged and
    trimmed to the token budget.

    Parameters
    ----------
    session:
        SQLAlchemy async session for calendar event queries.
    search_service:
        Semantic search service for recent document retrieval.
    graph_service:
        Neo4j graph query service (or NullGraphService fallback).
    config:
        Briefing configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        search_service: SemanticSearchService,
        graph_service: GraphQueryService | None = None,
        config: MorningBriefingConfig | None = None,
    ) -> None:
        self._session = session
        self._search = search_service
        self._graph = graph_service or NullGraphService()
        self._config = config or MorningBriefingConfig()

    async def assemble(
        self,
        user_id: uuid.UUID,
        target_date: date | None = None,
    ) -> MorningBriefingContext:
        """Assemble the morning briefing context.

        Parameters
        ----------
        user_id:
            Owner ID for data access.
        target_date:
            The date for the briefing (default: today).

        Returns
        -------
        MorningBriefingContext
            Assembled context ready for prompt template rendering.
        """
        today = target_date or date.today()

        # Step 1: Fetch today's calendar events
        events = await self._fetch_calendar_events(user_id, today)

        # Step 2: For each event, query participant history from graph
        all_participants = []
        for ev in events:
            all_participants.extend(ev.participants)
        unique_participants = list(set(all_participants))

        histories: list[ParticipantHistory] = []
        if unique_participants:
            histories = await self._graph.get_participant_history(
                unique_participants, user_id
            )

        # Build participant history lookup per event
        history_map: dict[str, ParticipantHistory] = {
            h.name: h for h in histories
        }
        event_histories: dict[str, list[ParticipantHistory]] = {}
        for ev in events:
            event_histories[ev.event_id] = [
                history_map[p] for p in ev.participants if p in history_map
            ]

        # Step 3: Semantic search for recent relevant docs
        search_query = self._build_search_query(events, today)
        recent_docs: list[SemanticSearchResult] = []
        if search_query:
            recent_docs = await self._search.search(
                query=search_query,
                user_id=user_id,
                top_k=self._config.max_documents,
            )

        # Step 4: Pending decisions from graph
        decisions = await self._graph.get_pending_decisions(
            user_id, limit=self._config.max_decisions
        )

        # Step 5: Assemble and check token budget
        context = self._build_context(
            today=today,
            events=events,
            event_histories=event_histories,
            recent_docs=recent_docs,
            decisions=decisions,
        )

        return self._enforce_token_budget(context)

    # ------------------------------------------------------------------
    # Step 1: Calendar events
    # ------------------------------------------------------------------

    async def _fetch_calendar_events(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> list[CalendarEvent]:
        """Fetch calendar events for the given date from documents table.

        Calendar events are stored as documents with source_type='google_calendar'.
        Event metadata (start, end, participants) is in the document content
        and parsed from the normalised format.
        """
        day_start = datetime(
            target_date.year, target_date.month, target_date.day,
            tzinfo=timezone.utc,
        )
        day_end = day_start + timedelta(days=1)

        sql = text("""
            SELECT
                d.source_id   AS event_id,
                d.title       AS title,
                d.created_at  AS created_at,
                c.content_preview AS content
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id AND c.chunk_index = 0
            WHERE d.user_id = :user_id
              AND d.source_type = 'google_calendar'
              AND d.created_at >= :day_start
              AND d.created_at < :day_end
            ORDER BY d.created_at ASC
            LIMIT :max_events
        """)

        result = await self._session.execute(
            sql,
            {
                "user_id": str(user_id),
                "day_start": day_start,
                "day_end": day_end,
                "max_events": self._config.max_events,
            },
        )

        events: list[CalendarEvent] = []
        for row in result.fetchall():
            participants = self._extract_participants(row.content or "")
            events.append(
                CalendarEvent(
                    event_id=row.event_id,
                    title=row.title or "Untitled Event",
                    start_time=row.created_at,
                    participants=participants,
                    notes=row.content,
                )
            )
        return events

    @staticmethod
    def _extract_participants(content: str) -> list[str]:
        """Extract participant names from event content.

        Looks for lines like 'Teilnehmer: Name1, Name2' or
        'Participants: Name1, Name2' in the content.
        """
        import re
        for line in content.split("\n"):
            match = re.match(
                r"(?:Teilnehmer|Participants)\s*:\s*(.+)",
                line.strip(),
                re.IGNORECASE,
            )
            if match:
                names = [n.strip() for n in match.group(1).split(",")]
                return [n for n in names if n]
        return []

    # ------------------------------------------------------------------
    # Step 3: Search query construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_search_query(events: list[CalendarEvent], today: date) -> str:
        """Build a semantic search query from today's events.

        Combines event titles and participant names into a query string
        for retrieving relevant background documents.
        """
        parts: list[str] = []
        for ev in events:
            parts.append(ev.title)
        if not parts:
            parts.append(f"Relevante Themen {today.isoformat()}")
        return " ".join(parts[:10])  # Cap to avoid overly long queries

    # ------------------------------------------------------------------
    # Step 5: Context building and token budget
    # ------------------------------------------------------------------

    def _build_context(
        self,
        today: date,
        events: list[CalendarEvent],
        event_histories: dict[str, list[ParticipantHistory]],
        recent_docs: list[SemanticSearchResult],
        decisions: list[PendingDecision],
    ) -> MorningBriefingContext:
        """Build the structured context for the prompt template."""
        calendar_dicts = []
        for ev in events:
            ev_dict: dict = {
                "title": ev.title,
                "time": ev.start_time.strftime("%H:%M") if ev.start_time else "",
                "participants": ev.participants,
            }
            if ev.notes:
                ev_dict["notes"] = ev.notes[:200]  # Truncate long notes
            if ev.location:
                ev_dict["location"] = ev.location
            calendar_dicts.append(ev_dict)

        doc_dicts = [
            {
                "title": doc.title,
                "source": doc.source_type,
                "date": doc.created_at,
                "content": doc.content[:300],  # Preview
                "score": doc.score,
            }
            for doc in recent_docs
        ]

        decision_dicts = [
            {
                "title": d.title,
                "project": d.project or "Kein Projekt",
                "created": d.created_date or "unbekannt",
                "context": d.context[:200] if d.context else "",
            }
            for d in decisions
        ]

        return MorningBriefingContext(
            date=today.isoformat(),
            calendar_events=calendar_dicts,
            participant_histories=event_histories,
            recent_documents=doc_dicts,
            pending_decisions=decision_dicts,
        )

    def _enforce_token_budget(
        self,
        context: MorningBriefingContext,
    ) -> MorningBriefingContext:
        """Check token count and trim context if over budget.

        Priority order for trimming (lowest priority trimmed first):
        1. Background documents (trim from end)
        2. Pending decisions (trim from end)
        3. Calendar events (never trimmed  always included)
        """
        context.token_count = self._count_tokens(context)

        if context.token_count <= self._config.token_budget:
            return context

        logger.info(
            "Token count %d exceeds budget %d, trimming context",
            context.token_count,
            self._config.token_budget,
        )

        # Trim background documents first
        while (
            context.recent_documents
            and self._count_tokens(context) > self._config.token_budget
        ):
            context.recent_documents.pop()
            context.truncated = True

        # Trim decisions if still over
        while (
            context.pending_decisions
            and self._count_tokens(context) > self._config.token_budget
        ):
            context.pending_decisions.pop()
            context.truncated = True

        context.token_count = self._count_tokens(context)
        return context

    @staticmethod
    def _count_tokens(context: MorningBriefingContext) -> int:
        """Count approximate tokens in the assembled context."""
        text_parts: list[str] = [context.date]

        for ev in context.calendar_events:
            text_parts.append(ev.get("title", ""))
            text_parts.append(ev.get("time", ""))
            text_parts.extend(ev.get("participants", []))
            if ev.get("notes"):
                text_parts.append(ev["notes"])

        for doc in context.recent_documents:
            text_parts.append(doc.get("title", ""))
            text_parts.append(doc.get("content", ""))

        for dec in context.pending_decisions:
            text_parts.append(dec.get("title", ""))
            text_parts.append(dec.get("context", ""))

        combined = " ".join(text_parts)
        return len(_ENCODING.encode(combined))
