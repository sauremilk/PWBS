"""Weekly Briefing Kontextassemblierung (TASK-143).

Assembles context for weekly briefings (Fridays 17:00):
1. Fetch all documents from the past 7 days
2. Extract top topics via frequency/recency weighting
3. Pending and resolved decisions from Neo4j
4. Project progress: group documents by project entities
5. Open items from graph
6. Token-budget check (8000 tokens) with prioritisation

D1 Section 3.5, D4 F-019: Weekly Briefing max 600 Wörter.
Context priority: Decisions > Top topics > Project progress > Background documents.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

import tiktoken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.search.service import SemanticSearchService

logger = logging.getLogger(__name__)

__all__ = [
    "NullWeeklyGraphService",
    "ProjectProgress",
    "TopicSummary",
    "WeeklyBriefingConfig",
    "WeeklyBriefingContext",
    "WeeklyContextAssembler",
    "WeeklyDecision",
    "WeeklyGraphService",
]

_ENCODING = tiktoken.get_encoding("cl100k_base")

_DEFAULT_TOKEN_BUDGET = 8000
_DEFAULT_LOOKBACK_DAYS = 7
_DEFAULT_MAX_DOCUMENTS = 30
_DEFAULT_MAX_DECISIONS = 15
_DEFAULT_MAX_TOPICS = 10


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TopicSummary:
    """A topic that appeared frequently during the week."""

    name: str
    mention_count: int
    source_types: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WeeklyDecision:
    """A decision made or pending during the week."""

    title: str
    project: str | None = None
    status: str = "pending"  # "pending" | "resolved"
    context: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectProgress:
    """Aggregated progress for a project during the week."""

    name: str
    document_count: int
    decision_count: int
    open_items: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WeeklyBriefingConfig:
    """Configuration for weekly briefing context assembly."""

    token_budget: int = _DEFAULT_TOKEN_BUDGET
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS
    max_documents: int = _DEFAULT_MAX_DOCUMENTS
    max_decisions: int = _DEFAULT_MAX_DECISIONS
    max_topics: int = _DEFAULT_MAX_TOPICS


@dataclass(slots=True)
class WeeklyBriefingContext:
    """Assembled context for the weekly briefing prompt template.

    Maps directly to the Jinja2 template variables:
    - week_start, week_end, top_topics, decisions,
      project_progress, open_items, recent_documents
    """

    week_start: str
    week_end: str
    top_topics: list[dict]
    decisions: list[dict]
    project_progress: list[dict]
    open_items: list[str]
    recent_documents: list[dict]
    document_count: int = 0
    token_count: int = 0
    truncated: bool = False


# ------------------------------------------------------------------
# Graph Query Protocol
# ------------------------------------------------------------------


@runtime_checkable
class WeeklyGraphService(Protocol):
    """Protocol for Neo4j graph queries used by the weekly briefing."""

    async def get_week_decisions(
        self,
        owner_id: uuid.UUID,
        since: datetime,
        limit: int = 15,
    ) -> list[WeeklyDecision]:
        """Get decisions made or pending during the week."""
        ...

    async def get_project_entities(
        self,
        owner_id: uuid.UUID,
        since: datetime,
    ) -> list[dict]:
        """Get project entities with document counts from the week."""
        ...

    async def get_open_items(
        self,
        owner_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        """Get open items across all projects."""
        ...


class NullWeeklyGraphService:
    """No-op graph service for when Neo4j is not available."""

    async def get_week_decisions(
        self,
        owner_id: uuid.UUID,
        since: datetime,
        limit: int = 15,
    ) -> list[WeeklyDecision]:
        return []

    async def get_project_entities(
        self,
        owner_id: uuid.UUID,
        since: datetime,
    ) -> list[dict]:
        return []

    async def get_open_items(
        self,
        owner_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        return []


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class WeeklyContextAssembler:
    """Assembles context for the weekly briefing.

    Orchestrates document retrieval, graph queries for decisions
    and project progress, topic extraction, and open items.
    All results are merged and trimmed to the token budget.

    Parameters
    ----------
    session:
        SQLAlchemy async session for document queries.
    search_service:
        Semantic search service for document retrieval.
    graph_service:
        Neo4j graph query service (or NullWeeklyGraphService fallback).
    config:
        Weekly briefing configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        search_service: SemanticSearchService,
        graph_service: WeeklyGraphService | None = None,
        config: WeeklyBriefingConfig | None = None,
    ) -> None:
        self._session = session
        self._search = search_service
        self._graph = graph_service or NullWeeklyGraphService()
        self._config = config or WeeklyBriefingConfig()

    async def assemble(
        self,
        user_id: uuid.UUID,
        target_date: date | None = None,
    ) -> WeeklyBriefingContext:
        """Assemble the weekly briefing context.

        Parameters
        ----------
        user_id:
            Owner ID for data access.
        target_date:
            The end date for the week (default: today).

        Returns
        -------
        WeeklyBriefingContext
            Assembled context ready for prompt template rendering.
        """
        today = target_date or date.today()
        week_start = today - timedelta(days=self._config.lookback_days)
        since = datetime(
            week_start.year, week_start.month, week_start.day,
            tzinfo=timezone.utc,
        )

        # Step 1: Fetch documents from the past week
        documents = await self._fetch_week_documents(user_id, since)

        # Step 2: Extract top topics from document titles/content
        topics = self._extract_topics(documents)

        # Step 3: Decisions from graph
        decisions = await self._graph.get_week_decisions(
            user_id, since, limit=self._config.max_decisions,
        )

        # Step 4: Project progress from graph
        project_entities = await self._graph.get_project_entities(user_id, since)
        project_progress = self._build_project_progress(project_entities, decisions)

        # Step 5: Open items from graph
        open_items = await self._graph.get_open_items(user_id)

        # Step 6: Assemble context and enforce token budget
        context = self._build_context(
            week_start=week_start,
            week_end=today,
            documents=documents,
            topics=topics,
            decisions=decisions,
            project_progress=project_progress,
            open_items=open_items,
        )

        return self._enforce_token_budget(context)

    # ------------------------------------------------------------------
    # Step 1: Fetch week documents
    # ------------------------------------------------------------------

    async def _fetch_week_documents(
        self,
        user_id: uuid.UUID,
        since: datetime,
    ) -> list[dict]:
        """Fetch documents from the past week from the documents table."""
        sql = text("""
            SELECT
                d.id          AS doc_id,
                d.title       AS title,
                d.source_type AS source_type,
                d.created_at  AS created_at
            FROM documents d
            WHERE d.user_id = :user_id
              AND d.created_at >= :since
            ORDER BY d.created_at DESC
            LIMIT :max_docs
        """)

        result = await self._session.execute(
            sql,
            {
                "user_id": str(user_id),
                "since": since,
                "max_docs": self._config.max_documents,
            },
        )

        documents: list[dict] = []
        for row in result.fetchall():
            documents.append({
                "doc_id": str(row.doc_id),
                "title": row.title or "Untitled",
                "source": row.source_type,
                "date": row.created_at.strftime("%d.%m.%Y"),
            })
        return documents

    # ------------------------------------------------------------------
    # Step 2: Extract top topics
    # ------------------------------------------------------------------

    def _extract_topics(self, documents: list[dict]) -> list[TopicSummary]:
        """Extract top topics from document titles via word frequency.

        Filters common stop words and returns most frequent meaningful terms.
        """
        stop_words = {
            "der", "die", "das", "und", "in", "von", "zu", "mit", "für",
            "auf", "ist", "im", "den", "des", "ein", "eine", "an", "als",
            "am", "aus", "bei", "nach", "über", "the", "and", "for", "with",
            "from", "this", "that", "are", "was", "has", "have", "not",
            "but", "all", "can", "will", "new", "re", "untitled",
        }

        word_counts: Counter[str] = Counter()
        word_sources: dict[str, set[str]] = {}

        for doc in documents:
            title = doc.get("title", "")
            source = doc.get("source", "")
            words = [
                w.lower().strip(".,;:!?()[]{}\"'")
                for w in title.split()
                if len(w) > 2
            ]
            for word in words:
                if word not in stop_words:
                    word_counts[word] += 1
                    if word not in word_sources:
                        word_sources[word] = set()
                    word_sources[word].add(source)

        topics: list[TopicSummary] = []
        for word, count in word_counts.most_common(self._config.max_topics):
            if count >= 2:  # Only topics mentioned at least twice
                topics.append(TopicSummary(
                    name=word,
                    mention_count=count,
                    source_types=sorted(word_sources.get(word, set())),
                ))

        return topics

    # ------------------------------------------------------------------
    # Step 4: Project progress
    # ------------------------------------------------------------------

    def _build_project_progress(
        self,
        project_entities: list[dict],
        decisions: list[WeeklyDecision],
    ) -> list[ProjectProgress]:
        """Build project progress from graph entities and decisions."""
        decision_by_project: Counter[str] = Counter()
        open_by_project: dict[str, list[str]] = {}

        for d in decisions:
            project = d.project or "Unbekannt"
            decision_by_project[project] += 1
            if d.status == "pending":
                open_by_project.setdefault(project, []).append(d.title)

        progress: list[ProjectProgress] = []
        for entity in project_entities:
            name = entity.get("name", "Unbekannt")
            doc_count = entity.get("document_count", 0)
            progress.append(ProjectProgress(
                name=name,
                document_count=doc_count,
                decision_count=decision_by_project.get(name, 0),
                open_items=open_by_project.get(name, []),
            ))

        return sorted(progress, key=lambda p: p.document_count, reverse=True)

    # ------------------------------------------------------------------
    # Step 6: Build context
    # ------------------------------------------------------------------

    def _build_context(
        self,
        week_start: date,
        week_end: date,
        documents: list[dict],
        topics: list[TopicSummary],
        decisions: list[WeeklyDecision],
        project_progress: list[ProjectProgress],
        open_items: list[str],
    ) -> WeeklyBriefingContext:
        """Build the WeeklyBriefingContext from assembled data."""
        return WeeklyBriefingContext(
            week_start=week_start.strftime("%d.%m.%Y"),
            week_end=week_end.strftime("%d.%m.%Y"),
            top_topics=[
                {
                    "name": t.name,
                    "mentions": t.mention_count,
                    "sources": ", ".join(t.source_types),
                }
                for t in topics
            ],
            decisions=[
                {
                    "title": d.title,
                    "project": d.project or "—",
                    "status": d.status,
                    "context": d.context or "",
                }
                for d in decisions
            ],
            project_progress=[
                {
                    "name": p.name,
                    "documents": p.document_count,
                    "decisions": p.decision_count,
                    "open_items": p.open_items,
                }
                for p in project_progress
            ],
            open_items=open_items,
            recent_documents=documents[:15],  # Top 15 for template
            document_count=len(documents),
        )

    # ------------------------------------------------------------------
    # Token budget enforcement
    # ------------------------------------------------------------------

    def _enforce_token_budget(
        self,
        context: WeeklyBriefingContext,
    ) -> WeeklyBriefingContext:
        """Enforce token budget on the assembled context.

        Prioritisation order (highest first):
        1. Decisions
        2. Top topics
        3. Project progress
        4. Recent documents
        """
        serialised = self._serialise_context(context)
        token_count = len(_ENCODING.encode(serialised))
        context.token_count = token_count

        if token_count <= self._config.token_budget:
            return context

        # Truncate documents first (lowest priority)
        while (
            context.recent_documents
            and self._count_tokens(context) > self._config.token_budget
        ):
            context.recent_documents.pop()
            context.truncated = True

        # Then project progress
        while (
            context.project_progress
            and self._count_tokens(context) > self._config.token_budget
        ):
            context.project_progress.pop()
            context.truncated = True

        context.token_count = self._count_tokens(context)
        return context

    def _count_tokens(self, context: WeeklyBriefingContext) -> int:
        """Count tokens in the serialised context."""
        return len(_ENCODING.encode(self._serialise_context(context)))

    @staticmethod
    def _serialise_context(context: WeeklyBriefingContext) -> str:
        """Serialise the context to a string for token counting."""
        parts = [
            f"Woche: {context.week_start} – {context.week_end}",
            f"Dokumente gesamt: {context.document_count}",
        ]

        if context.top_topics:
            parts.append("Top-Themen:")
            for t in context.top_topics:
                parts.append(f"  - {t['name']} ({t['mentions']}x, {t['sources']})")

        if context.decisions:
            parts.append("Entscheidungen:")
            for d in context.decisions:
                parts.append(f"  - {d['title']} [{d['status']}] ({d['project']})")

        if context.project_progress:
            parts.append("Projekt-Fortschritt:")
            for p in context.project_progress:
                parts.append(
                    f"  - {p['name']}: {p['documents']} Dokumente, "
                    f"{p['decisions']} Entscheidungen"
                )

        if context.open_items:
            parts.append("Offene Punkte:")
            for item in context.open_items:
                parts.append(f"  - {item}")

        if context.recent_documents:
            parts.append("Dokumente:")
            for doc in context.recent_documents:
                parts.append(f"  - {doc['title']} ({doc['source']}, {doc['date']})")

        return "\n".join(parts)
