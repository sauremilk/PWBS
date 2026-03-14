"""Meeting-Vorbereitung Kontextassemblierung (TASK-077).

Assembles context for meeting preparation briefings:
1. Load the target meeting event (title, time, participants)
2. Per participant: Neo4j query for history (last meetings, shared projects, open items)
3. Flag unknown participants as 'Neu im System'
4. Semantic search: relevant documents (last 14 days, meeting-topic-filtered)
5. Token-budget check (6000 tokens) with prioritisation

Triggered 30 minutes before a meeting with >= 2 participants, or on-demand.

D1 Section 3.5, D4 F-018, D4 US-3.2.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, runtime_checkable

import tiktoken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.search.service import SemanticSearchResult, SemanticSearchService

logger = logging.getLogger(__name__)

__all__ = [
    "MeetingContextAssembler",
    "MeetingContextConfig",
    "MeetingPrepContext",
    "MeetingGraphService",
    "NullMeetingGraphService",
    "ParticipantContext",
]

_ENCODING = tiktoken.get_encoding("cl100k_base")

_DEFAULT_TOKEN_BUDGET = 6000
_DEFAULT_LOOKBACK_DAYS = 14
_DEFAULT_MAX_DOCUMENTS = 15
_DEFAULT_MIN_PARTICIPANTS = 2


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParticipantContext:
    """Context for a single meeting participant."""

    name: str
    known: bool = True
    last_meetings: list[str] = field(default_factory=list)
    shared_projects: list[str] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MeetingContextConfig:
    """Configuration for meeting context assembly."""

    token_budget: int = _DEFAULT_TOKEN_BUDGET
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS
    max_documents: int = _DEFAULT_MAX_DOCUMENTS
    min_participants: int = _DEFAULT_MIN_PARTICIPANTS


@dataclass(slots=True)
class MeetingPrepContext:
    """Assembled context for the meeting preparation prompt template.

    Maps to Jinja2 template variables.
    """

    meeting_title: str
    meeting_time: str
    meeting_location: str | None
    participants: list[dict[str, Any]]
    relevant_documents: list[dict[str, Any]]
    open_items_summary: list[str]
    token_count: int = 0
    truncated: bool = False


# ------------------------------------------------------------------
# Graph Query Protocol
# ------------------------------------------------------------------


@runtime_checkable
class MeetingGraphService(Protocol):
    """Protocol for Neo4j graph queries for meeting prep."""

    async def get_participant_context(
        self,
        participant_name: str,
        owner_id: uuid.UUID,
        limit: int = 5,
    ) -> ParticipantContext:
        """Get interaction history for a single participant."""
        ...


class NullMeetingGraphService:
    """No-op fallback when Neo4j is unavailable."""

    async def get_participant_context(
        self,
        participant_name: str,
        owner_id: uuid.UUID,
        limit: int = 5,
    ) -> ParticipantContext:
        return ParticipantContext(name=participant_name, known=False)


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class MeetingContextAssembler:
    """Assembles context for meeting preparation briefings.

    Orchestrates participant history retrieval via Neo4j,
    semantic search for relevant documents, and token budget
    enforcement.

    Parameters
    ----------
    session:
        SQLAlchemy async session for event queries.
    search_service:
        Semantic search for relevant documents.
    graph_service:
        Neo4j graph service (or NullMeetingGraphService fallback).
    config:
        Assembly configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        search_service: SemanticSearchService,
        graph_service: MeetingGraphService | None = None,
        config: MeetingContextConfig | None = None,
    ) -> None:
        self._session = session
        self._search = search_service
        self._graph = graph_service or NullMeetingGraphService()
        self._config = config or MeetingContextConfig()

    @property
    def config(self) -> MeetingContextConfig:
        return self._config

    async def assemble(
        self,
        user_id: uuid.UUID,
        event_id: str,
    ) -> MeetingPrepContext:
        """Assemble meeting preparation context.

        Parameters
        ----------
        user_id:
            Owner for tenant isolation.
        event_id:
            The calendar event to prepare for.

        Returns
        -------
        MeetingPrepContext
            Assembled context ready for prompt template rendering.
        """
        # Step 1: Load meeting event
        event = await self._load_event(user_id, event_id)
        if event is None:
            return MeetingPrepContext(
                meeting_title="Unbekannter Termin",
                meeting_time="",
                meeting_location=None,
                participants=[],
                relevant_documents=[],
                open_items_summary=[],
            )

        title = event.get("title", "Termin")
        start_time = event.get("start_time", "")
        location = event.get("location")
        participants = event.get("participants", [])

        # Step 2: Get participant contexts
        participant_contexts = await self._get_participant_contexts(
            participants, user_id,
        )

        # Step 3: Semantic search for relevant documents
        relevant_docs = await self._search_relevant_documents(
            title, participants, user_id,
        )

        # Step 4: Collect open items across participants
        open_items: list[str] = []
        for pc in participant_contexts:
            for item in pc.get("open_items", []):
                if item not in open_items:
                    open_items.append(item)

        # Step 5: Build and enforce token budget
        context = MeetingPrepContext(
            meeting_title=title,
            meeting_time=str(start_time),
            meeting_location=location,
            participants=participant_contexts,
            relevant_documents=relevant_docs,
            open_items_summary=open_items,
        )

        return self._enforce_token_budget(context)

    # ------------------------------------------------------------------
    # Step 1: Load event
    # ------------------------------------------------------------------

    async def _load_event(
        self,
        user_id: uuid.UUID,
        event_id: str,
    ) -> dict[str, Any] | None:
        """Load a calendar event from stored documents.

        Queries documents of source_type 'google_calendar' with
        matching source_id.
        """
        query = text(
            "SELECT title, content, metadata "
            "FROM documents "
            "WHERE user_id = :user_id AND source_id = :event_id "
            "AND source_type = 'google_calendar' "
            "LIMIT 1"
        )
        result = await self._session.execute(
            query, {"user_id": str(user_id), "event_id": event_id},
        )
        row = result.mappings().first()
        if row is None:
            return None

        metadata = row.get("metadata", {}) or {}
        return {
            "title": row.get("title", "Termin"),
            "start_time": metadata.get("start_time", ""),
            "location": metadata.get("location"),
            "participants": self._extract_participant_names(metadata),
        }

    @staticmethod
    def _extract_participant_names(metadata: dict[str, Any]) -> list[str]:
        """Extract participant names from event metadata."""
        participants = metadata.get("participants", [])
        names: list[str] = []
        for p in participants:
            if isinstance(p, dict):
                name = p.get("name", "").strip()
                if name:
                    names.append(name)
            elif isinstance(p, str) and p.strip():
                names.append(p.strip())
        return names

    # ------------------------------------------------------------------
    # Step 2: Participant contexts
    # ------------------------------------------------------------------

    async def _get_participant_contexts(
        self,
        participant_names: list[str],
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Get context for each participant via graph service."""
        contexts: list[dict[str, Any]] = []

        for name in participant_names:
            pc = await self._graph.get_participant_context(
                name, user_id,
            )

            context_dict: dict[str, Any] = {
                "name": pc.name,
                "known": pc.known,
                "last_meetings": pc.last_meetings,
                "shared_projects": pc.shared_projects,
                "open_items": pc.open_items,
            }

            if not pc.known:
                context_dict["note"] = "Neu im System - keine vorherigen Interaktionen gespeichert"

            contexts.append(context_dict)

        return contexts

    # ------------------------------------------------------------------
    # Step 3: Semantic search
    # ------------------------------------------------------------------

    async def _search_relevant_documents(
        self,
        meeting_title: str,
        participant_names: list[str],
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Search for documents relevant to the meeting topic and participants."""
        query_parts = [meeting_title]
        query_parts.extend(participant_names[:3])
        query = " ".join(query_parts)

        try:
            results: list[SemanticSearchResult] = await self._search.search(
                query=query,
                user_id=user_id,
                top_k=self._config.max_documents,
            )
        except Exception as exc:
            logger.warning("Semantic search failed for meeting prep: %s", exc)
            return []

        return [
            {
                "title": r.title,
                "content": r.content[:500],
                "source": r.source_type,
                "score": round(r.score, 3),
                "chunk_id": str(r.chunk_id),
            }
            for r in results
        ]

    # ------------------------------------------------------------------
    # Step 5: Token budget
    # ------------------------------------------------------------------

    def _enforce_token_budget(
        self,
        context: MeetingPrepContext,
    ) -> MeetingPrepContext:
        """Trim context to fit within the token budget.

        Priority: participants > open items > documents.
        """
        total = self._count_tokens(context)
        context.token_count = total

        if total <= self._config.token_budget:
            return context

        # Trim documents first
        while context.relevant_documents and self._count_tokens(context) > self._config.token_budget:
            context.relevant_documents.pop()
            context.truncated = True

        # Trim open items if still over
        while context.open_items_summary and self._count_tokens(context) > self._config.token_budget:
            context.open_items_summary.pop()
            context.truncated = True

        context.token_count = self._count_tokens(context)
        return context

    @staticmethod
    def _count_tokens(context: MeetingPrepContext) -> int:
        """Estimate token count for the assembled context."""
        parts: list[str] = [
            context.meeting_title,
            context.meeting_time,
            context.meeting_location or "",
        ]

        for p in context.participants:
            parts.append(str(p))

        for doc in context.relevant_documents:
            parts.append(str(doc))

        for item in context.open_items_summary:
            parts.append(item)

        text = " ".join(parts)
        return len(_ENCODING.encode(text))
