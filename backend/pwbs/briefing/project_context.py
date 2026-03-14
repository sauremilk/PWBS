"""Projektbriefing Kontextassemblierung (TASK-133).

Assembles context for on-demand project briefings (max 1200 words):
1. Fetch project-related documents from PostgreSQL
2. Neo4j: project history (decisions, timeline, participants)
3. Semantic search: relevant chunks via Weaviate
4. Open items and relationships from knowledge graph
5. Token-budget check (8000 tokens) with prioritisation

D1 Section 3.5, D4 F-020: Project Briefing max 1200 Wörter.
Context priority: Decisions > Timeline > Participants > Background documents.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

import tiktoken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.search.service import SemanticSearchResult, SemanticSearchService

logger = logging.getLogger(__name__)

__all__ = [
    "NullProjectGraphService",
    "ProjectBriefingConfig",
    "ProjectBriefingContext",
    "ProjectContextAssembler",
    "ProjectDecision",
    "ProjectGraphService",
    "ProjectMilestone",
    "ProjectParticipant",
]

_ENCODING = tiktoken.get_encoding("cl100k_base")

_DEFAULT_TOKEN_BUDGET = 8000
_DEFAULT_LOOKBACK_DAYS = 90
_DEFAULT_MAX_DOCUMENTS = 30
_DEFAULT_MAX_DECISIONS = 20
_DEFAULT_MAX_PARTICIPANTS = 15


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectDecision:
    """A decision related to the project."""

    title: str
    status: str = "pending"  # "pending" | "resolved"
    context: str | None = None
    date: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectParticipant:
    """A person involved in the project."""

    name: str
    role: str | None = None
    last_activity: str | None = None
    contribution_count: int = 0


@dataclass(frozen=True, slots=True)
class ProjectMilestone:
    """A milestone or key event in the project timeline."""

    title: str
    date: str
    event_type: str = "milestone"  # "milestone" | "decision" | "document"


@dataclass(frozen=True, slots=True)
class ProjectBriefingConfig:
    """Configuration for project briefing context assembly."""

    token_budget: int = _DEFAULT_TOKEN_BUDGET
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS
    max_documents: int = _DEFAULT_MAX_DOCUMENTS
    max_decisions: int = _DEFAULT_MAX_DECISIONS
    max_participants: int = _DEFAULT_MAX_PARTICIPANTS


@dataclass(slots=True)
class ProjectBriefingContext:
    """Assembled context for the project briefing prompt template.

    Maps directly to the Jinja2 template variables.
    """

    project_name: str
    project_id: str
    timeline: list[dict]
    decisions: list[dict]
    participants: list[dict]
    open_items: list[str]
    recent_documents: list[dict]
    summary_stats: dict
    document_count: int = 0
    token_count: int = 0
    truncated: bool = False


# ------------------------------------------------------------------
# Graph Query Protocol
# ------------------------------------------------------------------


@runtime_checkable
class ProjectGraphService(Protocol):
    """Protocol for Neo4j graph queries used by project briefings."""

    async def get_project_decisions(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[ProjectDecision]:
        """Get decisions associated with a project."""
        ...

    async def get_project_participants(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 15,
    ) -> list[ProjectParticipant]:
        """Get people involved in the project."""
        ...

    async def get_project_timeline(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[ProjectMilestone]:
        """Get project timeline events."""
        ...

    async def get_project_open_items(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 10,
    ) -> list[str]:
        """Get open items for the project."""
        ...


class NullProjectGraphService:
    """No-op graph service for when Neo4j is not available."""

    async def get_project_decisions(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[ProjectDecision]:
        return []

    async def get_project_participants(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 15,
    ) -> list[ProjectParticipant]:
        return []

    async def get_project_timeline(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[ProjectMilestone]:
        return []

    async def get_project_open_items(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 10,
    ) -> list[str]:
        return []


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class ProjectContextAssembler:
    """Assembles context for project briefings.

    Orchestrates document retrieval, graph queries for decisions,
    participants, timeline, and open items.
    All results are merged and trimmed to the token budget.

    Parameters
    ----------
    session:
        SQLAlchemy async session for document queries.
    search_service:
        Semantic search service for document retrieval.
    graph_service:
        Neo4j graph query service (or NullProjectGraphService fallback).
    config:
        Project briefing configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        search_service: SemanticSearchService,
        graph_service: ProjectGraphService | None = None,
        config: ProjectBriefingConfig | None = None,
    ) -> None:
        self._session = session
        self._search = search_service
        self._graph = graph_service or NullProjectGraphService()
        self._config = config or ProjectBriefingConfig()

    async def assemble(
        self,
        user_id: uuid.UUID,
        project_name: str,
        project_id: str | None = None,
    ) -> ProjectBriefingContext:
        """Assemble the project briefing context.

        Parameters
        ----------
        user_id:
            Owner ID for data access.
        project_name:
            Name of the project.
        project_id:
            Optional entity ID for graph lookups.

        Returns
        -------
        ProjectBriefingContext
            Assembled context ready for prompt template rendering.
        """
        since = datetime.now(timezone.utc) - timedelta(
            days=self._config.lookback_days,
        )

        # Step 1: Fetch project-related documents from PostgreSQL
        documents = await self._fetch_project_documents(
            user_id, project_name, since,
        )

        # Step 2: Decisions from graph
        decisions = await self._graph.get_project_decisions(
            user_id,
            project_name,
            limit=self._config.max_decisions,
        )

        # Step 3: Participants from graph
        participants = await self._graph.get_project_participants(
            user_id,
            project_name,
            limit=self._config.max_participants,
        )

        # Step 4: Timeline from graph
        timeline = await self._graph.get_project_timeline(
            user_id,
            project_name,
        )

        # Step 5: Open items from graph
        open_items = await self._graph.get_project_open_items(
            user_id,
            project_name,
        )

        # Step 6: Assemble context and enforce token budget
        summary_stats = {
            "document_count": len(documents),
            "decision_count": len(decisions),
            "participant_count": len(participants),
            "open_item_count": len(open_items),
            "lookback_days": self._config.lookback_days,
        }

        context = ProjectBriefingContext(
            project_name=project_name,
            project_id=project_id or "",
            timeline=[
                {
                    "title": m.title,
                    "date": m.date,
                    "type": m.event_type,
                }
                for m in timeline
            ],
            decisions=[
                {
                    "title": d.title,
                    "status": d.status,
                    "context": d.context or "",
                    "date": d.date or "",
                }
                for d in decisions
            ],
            participants=[
                {
                    "name": p.name,
                    "role": p.role or "Beteiligt",
                    "last_activity": p.last_activity or "",
                    "contributions": p.contribution_count,
                }
                for p in participants
            ],
            open_items=open_items,
            recent_documents=[
                {
                    "title": doc["title"],
                    "source": doc["source"],
                    "date": doc["date"],
                }
                for doc in documents
            ],
            summary_stats=summary_stats,
            document_count=len(documents),
        )

        return self._enforce_token_budget(context)

    # ------------------------------------------------------------------
    # Step 1: Fetch project documents
    # ------------------------------------------------------------------

    async def _fetch_project_documents(
        self,
        user_id: uuid.UUID,
        project_name: str,
        since: datetime,
    ) -> list[dict]:
        """Fetch documents related to the project from the documents table.

        Uses a LIKE search on title and content for project-name matching.
        """
        sql = text("""
            SELECT
                d.id          AS doc_id,
                d.title       AS title,
                d.source_type AS source_type,
                d.created_at  AS created_at
            FROM documents d
            WHERE d.user_id = :user_id
              AND d.created_at >= :since
              AND (
                  d.title ILIKE :pattern
                  OR d.content ILIKE :pattern
              )
            ORDER BY d.created_at DESC
            LIMIT :max_docs
        """)

        result = await self._session.execute(
            sql,
            {
                "user_id": str(user_id),
                "since": since,
                "pattern": f"%{project_name}%",
                "max_docs": self._config.max_documents,
            },
        )

        documents: list[dict] = []
        for row in result.fetchall():
            documents.append(
                {
                    "doc_id": str(row.doc_id),
                    "title": row.title or "Untitled",
                    "source": row.source_type,
                    "date": row.created_at.strftime("%d.%m.%Y"),
                }
            )
        return documents

    # ------------------------------------------------------------------
    # Token budget enforcement
    # ------------------------------------------------------------------

    def _enforce_token_budget(
        self,
        context: ProjectBriefingContext,
    ) -> ProjectBriefingContext:
        """Trim context to fit within the token budget.

        Priority (highest first):
        1. Decisions
        2. Timeline
        3. Participants
        4. Open items
        5. Recent documents

        Lower-priority sections are truncated first.
        """
        budget = self._config.token_budget
        total = self._count_context_tokens(context)

        if total <= budget:
            context.token_count = total
            return context

        # Truncate documents first (lowest priority)
        while total > budget and context.recent_documents:
            context.recent_documents.pop()
            total = self._count_context_tokens(context)

        # Truncate open items next
        while total > budget and context.open_items:
            context.open_items.pop()
            total = self._count_context_tokens(context)

        # Truncate participants
        while total > budget and context.participants:
            context.participants.pop()
            total = self._count_context_tokens(context)

        # Truncate timeline
        while total > budget and context.timeline:
            context.timeline.pop()
            total = self._count_context_tokens(context)

        context.token_count = total
        context.truncated = True
        return context

    @staticmethod
    def _count_context_tokens(context: ProjectBriefingContext) -> int:
        """Count approximate tokens in the context."""
        parts: list[str] = [
            f"Projekt: {context.project_name}",
        ]

        for d in context.decisions:
            parts.append(
                f"Entscheidung: {d['title']} ({d['status']}) {d.get('context', '')}",
            )

        for t in context.timeline:
            parts.append(f"Timeline: {t['title']} ({t['date']}, {t['type']})")

        for p in context.participants:
            parts.append(f"Beteiligt: {p['name']} ({p['role']})")

        for item in context.open_items:
            parts.append(f"Offen: {item}")

        for doc in context.recent_documents:
            parts.append(f"Dokument: {doc['title']} ({doc['source']}, {doc['date']})")

        combined = " ".join(parts)
        return len(_ENCODING.encode(combined))
