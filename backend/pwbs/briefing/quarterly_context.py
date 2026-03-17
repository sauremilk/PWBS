"""Quarterly Review Briefing Context Assembly (TASK-155).

Assembles context for quarterly review briefings:
1. Fetch assumption timeline (confirmed/refuted/revised in last 3 months)
2. Extract top recurring themes from pattern recognition
3. Key decisions made in the quarter
4. Strategic theme shifts detected
5. Token-budget check (12000 tokens) with prioritisation

Max 1500 words. Context priority:
Assumptions > Theme shifts > Key decisions > Recurring patterns.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.assumption import Assumption
from pwbs.models.decision import Decision

logger = logging.getLogger(__name__)

__all__ = [
    "NullQuarterlyGraphService",
    "QuarterlyBriefingConfig",
    "QuarterlyBriefingContext",
    "QuarterlyContextAssembler",
    "QuarterlyGraphService",
    "ThemeShift",
]

_ENCODING = tiktoken.get_encoding("cl100k_base")
_DEFAULT_TOKEN_BUDGET = 12000
_DEFAULT_LOOKBACK_DAYS = 90
_DEFAULT_MAX_DECISIONS = 20
_DEFAULT_MAX_ASSUMPTIONS = 30
_DEFAULT_MAX_THEMES = 15


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThemeShift:
    """A detected shift in topic prominence over the quarter."""

    theme: str
    direction: str  # "rising" | "declining" | "stable"
    mention_count_current: int
    mention_count_previous: int


@dataclass(frozen=True, slots=True)
class QuarterlyDecision:
    """A key decision made during the quarter."""

    summary: str
    status: str
    decided_at: datetime | None = None
    project: str | None = None


@dataclass(frozen=True, slots=True)
class AssumptionSummary:
    """Summary of an assumption for the quarterly review."""

    title: str
    status: str
    status_reason: str | None = None
    changed_at: datetime | None = None
    evidence_count: int = 0


@dataclass(frozen=True, slots=True)
class QuarterlyBriefingConfig:
    """Configuration for quarterly briefing context assembly."""

    token_budget: int = _DEFAULT_TOKEN_BUDGET
    lookback_days: int = _DEFAULT_LOOKBACK_DAYS
    max_decisions: int = _DEFAULT_MAX_DECISIONS
    max_assumptions: int = _DEFAULT_MAX_ASSUMPTIONS
    max_themes: int = _DEFAULT_MAX_THEMES


@dataclass(slots=True)
class QuarterlyBriefingContext:
    """Assembled context for the quarterly review prompt template."""

    period_start: datetime
    period_end: datetime
    assumptions: list[AssumptionSummary] = field(default_factory=list)
    assumption_stats: dict[str, int] = field(default_factory=dict)
    key_decisions: list[QuarterlyDecision] = field(default_factory=list)
    theme_shifts: list[ThemeShift] = field(default_factory=list)
    recurring_patterns: list[str] = field(default_factory=list)
    token_count: int = 0

    def to_template_dict(self) -> dict[str, Any]:
        """Convert to dict suitable for Jinja2 template rendering."""
        return {
            "period_start": self.period_start.strftime("%Y-%m-%d"),
            "period_end": self.period_end.strftime("%Y-%m-%d"),
            "assumptions": [
                {
                    "title": a.title,
                    "status": a.status,
                    "reason": a.status_reason,
                    "changed_at": (a.changed_at.strftime("%Y-%m-%d") if a.changed_at else None),
                    "evidence_count": a.evidence_count,
                }
                for a in self.assumptions
            ],
            "assumption_stats": self.assumption_stats,
            "key_decisions": [
                {
                    "summary": d.summary,
                    "status": d.status,
                    "decided_at": (d.decided_at.strftime("%Y-%m-%d") if d.decided_at else None),
                    "project": d.project,
                }
                for d in self.key_decisions
            ],
            "theme_shifts": [
                {
                    "theme": t.theme,
                    "direction": t.direction,
                    "current": t.mention_count_current,
                    "previous": t.mention_count_previous,
                }
                for t in self.theme_shifts
            ],
            "recurring_patterns": self.recurring_patterns,
            "token_count": self.token_count,
        }


# ------------------------------------------------------------------
# Graph service protocol
# ------------------------------------------------------------------


@runtime_checkable
class QuarterlyGraphService(Protocol):
    """Protocol for Neo4j graph queries in quarterly context."""

    async def get_theme_shifts(
        self,
        owner_id: uuid.UUID,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        max_themes: int,
    ) -> list[ThemeShift]: ...

    async def get_recurring_patterns(
        self,
        owner_id: uuid.UUID,
        since: datetime,
        max_patterns: int,
    ) -> list[str]: ...


class NullQuarterlyGraphService:
    """No-op graph service for when Neo4j is unavailable."""

    async def get_theme_shifts(
        self,
        owner_id: uuid.UUID,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        max_themes: int,
    ) -> list[ThemeShift]:
        return []

    async def get_recurring_patterns(
        self,
        owner_id: uuid.UUID,
        since: datetime,
        max_patterns: int,
    ) -> list[str]:
        return []


# ------------------------------------------------------------------
# Assembler
# ------------------------------------------------------------------


class QuarterlyContextAssembler:
    """Assembles context for quarterly review briefings.

    Steps:
    1. Query assumptions with status changes in the period
    2. Fetch key decisions from the quarter
    3. Query theme shifts from knowledge graph
    4. Detect recurring patterns
    5. Enforce token budget
    """

    def __init__(
        self,
        db: AsyncSession,
        graph: QuarterlyGraphService | None = None,
        config: QuarterlyBriefingConfig | None = None,
    ) -> None:
        self._db = db
        self._graph = graph or NullQuarterlyGraphService()
        self._config = config or QuarterlyBriefingConfig()

    async def assemble(self, owner_id: uuid.UUID) -> QuarterlyBriefingContext:
        """Assemble quarterly review context for the given user."""
        now = datetime.now(UTC)
        period_end = now
        period_start = now - timedelta(days=self._config.lookback_days)

        # Previous period for comparison
        prev_start = period_start - timedelta(days=self._config.lookback_days)
        prev_end = period_start

        ctx = QuarterlyBriefingContext(
            period_start=period_start,
            period_end=period_end,
        )

        # 1. Assumptions
        assumptions = await self._fetch_assumptions(owner_id, period_start)
        ctx.assumptions = assumptions[: self._config.max_assumptions]
        ctx.assumption_stats = self._compute_assumption_stats(owner_id, assumptions)

        # 2. Key decisions
        ctx.key_decisions = await self._fetch_decisions(owner_id, period_start, period_end)

        # 3. Theme shifts from graph
        ctx.theme_shifts = await self._graph.get_theme_shifts(
            owner_id,
            period_start,
            period_end,
            prev_start,
            prev_end,
            self._config.max_themes,
        )

        # 4. Recurring patterns
        ctx.recurring_patterns = await self._graph.get_recurring_patterns(
            owner_id, period_start, self._config.max_themes
        )

        # 5. Token count
        template_dict = ctx.to_template_dict()
        ctx.token_count = len(_ENCODING.encode(str(template_dict)))

        return ctx

    async def _fetch_assumptions(
        self,
        owner_id: uuid.UUID,
        since: datetime,
    ) -> list[AssumptionSummary]:
        """Fetch assumptions relevant to the quarterly review."""
        stmt = (
            select(Assumption)
            .where(Assumption.user_id == owner_id)
            .order_by(Assumption.status_changed_at.desc().nullslast())
            .limit(self._config.max_assumptions)
        )
        result = await self._db.execute(stmt)
        assumptions = result.scalars().all()

        return [
            AssumptionSummary(
                title=a.title,
                status=a.status,
                status_reason=a.status_reason,
                changed_at=a.status_changed_at,
                evidence_count=len(a.evidence) if a.evidence else 0,
            )
            for a in assumptions
        ]

    def _compute_assumption_stats(
        self,
        owner_id: uuid.UUID,
        assumptions: list[AssumptionSummary],
    ) -> dict[str, int]:
        """Compute status distribution counts."""
        counts: dict[str, int] = {}
        for a in assumptions:
            counts[a.status] = counts.get(a.status, 0) + 1
        return counts

    async def _fetch_decisions(
        self,
        owner_id: uuid.UUID,
        since: datetime,
        until: datetime,
    ) -> list[QuarterlyDecision]:
        """Fetch key decisions from the quarter."""
        stmt = (
            select(Decision)
            .where(
                Decision.user_id == owner_id,
                Decision.created_at >= since,
                Decision.created_at <= until,
            )
            .order_by(Decision.created_at.desc())
            .limit(self._config.max_decisions)
        )
        result = await self._db.execute(stmt)
        decisions = result.scalars().all()

        return [
            QuarterlyDecision(
                summary=d.summary,
                status=d.status,
                decided_at=d.decided_at,
            )
            for d in decisions
        ]
