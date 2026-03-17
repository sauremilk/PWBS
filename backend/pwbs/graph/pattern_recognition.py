"""Mustererkennung ueber Knowledge Graph (TASK-139).

Detects patterns in the Neo4j knowledge graph:
1. Recurring themes: Topics appearing in >N distinct contexts within M days
2. Changing assumptions: Hypotheses contradicted or re-evaluated over time
3. Unresolved patterns: Open questions mentioned repeatedly without resolution

All queries use parametrized Cypher with owner_id filter for tenant isolation.
D3 Kernfunktion 2, D1 Section 3.3.3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

logger = logging.getLogger(__name__)

__all__ = [
    "DetectedPattern",
    "NullPatternGraphService",
    "PatternRecognitionConfig",
    "PatternRecognitionService",
    "PatternSourceRef",
    "PatternType",
]


# ------------------------------------------------------------------
# Enums & data types
# ------------------------------------------------------------------


class PatternType(str, Enum):
    """Types of detectable patterns."""

    RECURRING_THEME = "recurring_theme"
    CHANGING_ASSUMPTION = "changing_assumption"
    UNRESOLVED_QUESTION = "unresolved_question"


@dataclass(frozen=True, slots=True)
class PatternSourceRef:
    """Reference to a source document backing a detected pattern."""

    document_id: str
    title: str
    source_type: str
    date: str


@dataclass(frozen=True, slots=True)
class DetectedPattern:
    """A single detected pattern with source references."""

    pattern_type: PatternType
    entity_id: str
    entity_name: str
    summary: str
    context_count: int
    first_seen: str
    last_seen: str
    sources: list[PatternSourceRef] = field(default_factory=list)


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PatternRecognitionConfig:
    """Configuration for pattern detection thresholds.

    Attributes
    ----------
    recurring_theme_days:
        Time window (days) for recurring theme detection.
    recurring_theme_min_contexts:
        Minimum distinct document contexts for a topic to count as recurring.
    unresolved_min_mentions:
        Minimum mention count for an open question to be flagged.
    max_results_per_type:
        Maximum patterns returned per type.
    """

    recurring_theme_days: int = 30
    recurring_theme_min_contexts: int = 3
    unresolved_min_mentions: int = 2
    max_results_per_type: int = 10


# ------------------------------------------------------------------
# Neo4j Session Protocol
# ------------------------------------------------------------------


@runtime_checkable
class PatternGraphSession(Protocol):
    """Protocol for async Neo4j session/transaction."""

    async def run(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> Any: ...


# ------------------------------------------------------------------
# Cypher queries (parametrized, no string concatenation)
# ------------------------------------------------------------------

_RECURRING_THEMES_QUERY = """
MATCH (t:Topic {userId: $userId})-[r]-(d:Document {userId: $userId})
WHERE d.createdAt >= $since
WITH t, collect(DISTINCT d) AS docs
WHERE size(docs) >= $minContexts
RETURN t.id AS entityId, t.name AS entityName,
       size(docs) AS contextCount,
       t.firstSeen AS firstSeen, t.lastSeen AS lastSeen,
       [doc IN docs | {id: doc.id, title: doc.title,
        sourceType: coalesce(doc.sourceType, 'unknown'),
        date: coalesce(doc.createdAt, '')}] AS sources
ORDER BY contextCount DESC
LIMIT $limit
"""

_CHANGING_ASSUMPTIONS_QUERY = """
MATCH (h:Hypothesis {userId: $userId})
WHERE h.firstSeen IS NOT NULL AND h.lastSeen IS NOT NULL
  AND h.lastSeen > h.firstSeen
OPTIONAL MATCH (h)-[r]-(d:Document {userId: $userId})
WITH h, collect(DISTINCT d) AS docs
WHERE size(docs) >= 2
RETURN h.id AS entityId, h.statement AS entityName,
       size(docs) AS contextCount,
       h.firstSeen AS firstSeen, h.lastSeen AS lastSeen,
       [doc IN docs | {id: doc.id, title: doc.title,
        sourceType: coalesce(doc.sourceType, 'unknown'),
        date: coalesce(doc.createdAt, '')}] AS sources
ORDER BY h.lastSeen DESC
LIMIT $limit
"""

_UNRESOLVED_QUESTIONS_QUERY = """
MATCH (q:OpenQuestion {userId: $userId})
OPTIONAL MATCH (q)-[r]-(d:Document {userId: $userId})
WITH q, collect(DISTINCT d) AS docs
WHERE size(docs) >= $minMentions
RETURN q.id AS entityId, q.text AS entityName,
       size(docs) AS contextCount,
       q.firstSeen AS firstSeen, q.lastSeen AS lastSeen,
       [doc IN docs | {id: doc.id, title: doc.title,
        sourceType: coalesce(doc.sourceType, 'unknown'),
        date: coalesce(doc.createdAt, '')}] AS sources
ORDER BY contextCount DESC
LIMIT $limit
"""


# ------------------------------------------------------------------
# Null service for when Neo4j is not available
# ------------------------------------------------------------------


class NullPatternGraphService:
    """No-op fallback when Neo4j is unavailable."""

    async def run(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> Any:
        return _EmptyResult()


class _EmptyResult:
    """Mimics an empty Neo4j result set."""

    async def data(self) -> list[dict[str, Any]]:
        return []


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class PatternRecognitionService:
    """Detects patterns in the Neo4j knowledge graph.

    All queries are parametrized and filtered by userId (owner_id)
    for tenant isolation.

    Parameters
    ----------
    session:
        An async Neo4j session/transaction (or NullPatternGraphService).
    config:
        Detection thresholds.
    """

    def __init__(
        self,
        session: PatternGraphSession,
        config: PatternRecognitionConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or PatternRecognitionConfig()

    @property
    def config(self) -> PatternRecognitionConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def find_recurring_themes(
        self,
        owner_id: UUID,
    ) -> list[DetectedPattern]:
        """Find topics appearing in many distinct contexts recently."""
        since = datetime.now(tz=timezone.utc)
        since_iso = since.replace(
            day=max(1, since.day),
        )
        from datetime import timedelta

        since_iso = (since - timedelta(days=self._config.recurring_theme_days)).isoformat()

        result = await self._session.run(
            _RECURRING_THEMES_QUERY,
            {
                "userId": str(owner_id),
                "since": since_iso,
                "minContexts": self._config.recurring_theme_min_contexts,
                "limit": self._config.max_results_per_type,
            },
        )
        records = await result.data()
        return [self._to_pattern(r, PatternType.RECURRING_THEME) for r in records]

    async def find_changing_assumptions(
        self,
        owner_id: UUID,
    ) -> list[DetectedPattern]:
        """Find hypotheses that appear in multiple documents over time."""
        result = await self._session.run(
            _CHANGING_ASSUMPTIONS_QUERY,
            {
                "userId": str(owner_id),
                "limit": self._config.max_results_per_type,
            },
        )
        records = await result.data()
        return [
            self._to_pattern(r, PatternType.CHANGING_ASSUMPTION)
            for r in records
        ]

    async def find_unresolved_questions(
        self,
        owner_id: UUID,
    ) -> list[DetectedPattern]:
        """Find open questions mentioned repeatedly."""
        result = await self._session.run(
            _UNRESOLVED_QUESTIONS_QUERY,
            {
                "userId": str(owner_id),
                "minMentions": self._config.unresolved_min_mentions,
                "limit": self._config.max_results_per_type,
            },
        )
        records = await result.data()
        return [
            self._to_pattern(r, PatternType.UNRESOLVED_QUESTION)
            for r in records
        ]

    async def detect_all_patterns(
        self,
        owner_id: UUID,
    ) -> list[DetectedPattern]:
        """Run all detectors and return a unified, sorted list."""
        themes = await self.find_recurring_themes(owner_id)
        assumptions = await self.find_changing_assumptions(owner_id)
        questions = await self.find_unresolved_questions(owner_id)

        all_patterns = themes + assumptions + questions
        all_patterns.sort(key=lambda p: p.context_count, reverse=True)
        return all_patterns

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_pattern(
        record: dict[str, Any],
        pattern_type: PatternType,
    ) -> DetectedPattern:
        """Convert a Neo4j record to a DetectedPattern."""
        sources: list[PatternSourceRef] = []
        for src in record.get("sources") or []:
            if src and src.get("id"):
                sources.append(
                    PatternSourceRef(
                        document_id=str(src["id"]),
                        title=src.get("title") or "Untitled",
                        source_type=src.get("sourceType") or "unknown",
                        date=str(src.get("date") or ""),
                    )
                )

        first_seen = str(record.get("firstSeen") or "")
        last_seen = str(record.get("lastSeen") or "")

        summaries = {
            PatternType.RECURRING_THEME: (
                f"Thema '{record.get('entityName', '')}' taucht in "
                f"{record.get('contextCount', 0)} verschiedenen Kontexten auf"
            ),
            PatternType.CHANGING_ASSUMPTION: (
                f"Hypothese '{record.get('entityName', '')}' wurde in "
                f"{record.get('contextCount', 0)} Dokumenten ueber Zeit "
                f"neu bewertet"
            ),
            PatternType.UNRESOLVED_QUESTION: (
                f"Offene Frage '{record.get('entityName', '')}' bleibt in "
                f"{record.get('contextCount', 0)} Kontexten unbeantwortet"
            ),
        }

        return DetectedPattern(
            pattern_type=pattern_type,
            entity_id=str(record.get("entityId", "")),
            entity_name=str(record.get("entityName", "")),
            summary=summaries[pattern_type],
            context_count=record.get("contextCount", 0),
            first_seen=first_seen,
            last_seen=last_seen,
            sources=sources,
        )
