"""Tests for QuarterlyContextAssembler (TASK-155)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.quarterly_context import (
    AssumptionSummary,
    NullQuarterlyGraphService,
    QuarterlyBriefingConfig,
    QuarterlyBriefingContext,
    QuarterlyContextAssembler,
    QuarterlyDecision,
    ThemeShift,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

OWNER_ID = uuid.uuid4()
NOW = datetime.now(UTC)


def _make_assumption_row(
    *,
    title: str = "Test assumption",
    status: str = "open",
    status_changed_at: datetime | None = None,
    status_reason: str | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock Assumption ORM row."""
    row = MagicMock()
    row.title = title
    row.status = status
    row.status_changed_at = status_changed_at
    row.status_reason = status_reason
    row.evidence = evidence or []
    return row


def _make_decision_row(
    *,
    summary: str = "Decided to use PostgreSQL",
    status: str = "made",
    decided_at: datetime | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    row = MagicMock()
    row.summary = summary
    row.status = status
    row.decided_at = decided_at
    row.created_at = created_at or NOW
    return row


def _make_db(
    *,
    assumption_rows: list[Any] | None = None,
    decision_rows: list[Any] | None = None,
) -> AsyncMock:
    """Mock AsyncSession that returns assumptions first, then decisions."""
    db = AsyncMock()
    call_count = 0

    async def mock_execute(stmt: Any) -> MagicMock:
        nonlocal call_count
        result = MagicMock()
        scalars = MagicMock()
        if call_count == 0:
            scalars.all.return_value = assumption_rows or []
        else:
            scalars.all.return_value = decision_rows or []
        result.scalars.return_value = scalars
        call_count += 1
        return result

    db.execute = mock_execute
    return db


def _make_graph(
    *,
    theme_shifts: list[ThemeShift] | None = None,
    recurring_patterns: list[str] | None = None,
) -> AsyncMock:
    graph = AsyncMock()
    graph.get_theme_shifts.return_value = theme_shifts or []
    graph.get_recurring_patterns.return_value = recurring_patterns or []
    return graph


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


class TestThemeShift:
    def test_create(self) -> None:
        shift = ThemeShift(
            theme="ML Ops",
            direction="rising",
            mention_count_current=15,
            mention_count_previous=3,
        )
        assert shift.theme == "ML Ops"
        assert shift.direction == "rising"
        assert shift.mention_count_current == 15
        assert shift.mention_count_previous == 3


class TestQuarterlyDecision:
    def test_create(self) -> None:
        d = QuarterlyDecision(
            summary="Migrate to k8s",
            status="made",
            decided_at=NOW,
            project="Infra",
        )
        assert d.summary == "Migrate to k8s"
        assert d.project == "Infra"


class TestAssumptionSummary:
    def test_create(self) -> None:
        a = AssumptionSummary(
            title="Users prefer daily briefings",
            status="confirmed",
            status_reason="Survey results",
            changed_at=NOW,
            evidence_count=3,
        )
        assert a.title == "Users prefer daily briefings"
        assert a.evidence_count == 3

    def test_defaults(self) -> None:
        a = AssumptionSummary(title="Test", status="open")
        assert a.status_reason is None
        assert a.changed_at is None
        assert a.evidence_count == 0


# ------------------------------------------------------------------
# QuarterlyBriefingConfig
# ------------------------------------------------------------------


class TestQuarterlyBriefingConfig:
    def test_defaults(self) -> None:
        config = QuarterlyBriefingConfig()
        assert config.token_budget == 12000
        assert config.lookback_days == 90
        assert config.max_decisions == 20
        assert config.max_assumptions == 30
        assert config.max_themes == 15

    def test_custom(self) -> None:
        config = QuarterlyBriefingConfig(lookback_days=180, max_decisions=10)
        assert config.lookback_days == 180
        assert config.max_decisions == 10


# ------------------------------------------------------------------
# QuarterlyBriefingContext
# ------------------------------------------------------------------


class TestQuarterlyBriefingContext:
    def test_to_template_dict_empty(self) -> None:
        ctx = QuarterlyBriefingContext(
            period_start=NOW - timedelta(days=90),
            period_end=NOW,
        )
        d = ctx.to_template_dict()
        assert "period_start" in d
        assert "period_end" in d
        assert d["assumptions"] == []
        assert d["key_decisions"] == []
        assert d["theme_shifts"] == []
        assert d["recurring_patterns"] == []

    def test_to_template_dict_with_data(self) -> None:
        ctx = QuarterlyBriefingContext(
            period_start=NOW - timedelta(days=90),
            period_end=NOW,
            assumptions=[
                AssumptionSummary(
                    title="Test",
                    status="confirmed",
                    status_reason="Proven",
                    changed_at=NOW,
                    evidence_count=2,
                )
            ],
            assumption_stats={"confirmed": 1},
            key_decisions=[
                QuarterlyDecision(
                    summary="Use PostgreSQL",
                    status="made",
                    decided_at=NOW,
                    project="DB",
                )
            ],
            theme_shifts=[
                ThemeShift(
                    theme="AI",
                    direction="rising",
                    mention_count_current=10,
                    mention_count_previous=2,
                )
            ],
            recurring_patterns=["Security comes up in every sprint"],
        )
        d = ctx.to_template_dict()
        assert len(d["assumptions"]) == 1
        assert d["assumptions"][0]["title"] == "Test"
        assert d["assumptions"][0]["status"] == "confirmed"
        assert d["assumptions"][0]["reason"] == "Proven"
        assert d["assumptions"][0]["evidence_count"] == 2
        assert len(d["key_decisions"]) == 1
        assert d["key_decisions"][0]["summary"] == "Use PostgreSQL"
        assert d["key_decisions"][0]["project"] == "DB"
        assert len(d["theme_shifts"]) == 1
        assert d["theme_shifts"][0]["theme"] == "AI"
        assert d["theme_shifts"][0]["direction"] == "rising"
        assert d["theme_shifts"][0]["current"] == 10
        assert d["theme_shifts"][0]["previous"] == 2
        assert d["recurring_patterns"] == ["Security comes up in every sprint"]

    def test_dates_formatted_as_strings(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        end = datetime(2026, 3, 31, tzinfo=UTC)
        ctx = QuarterlyBriefingContext(period_start=start, period_end=end)
        d = ctx.to_template_dict()
        assert d["period_start"] == "2026-01-01"
        assert d["period_end"] == "2026-03-31"


# ------------------------------------------------------------------
# NullQuarterlyGraphService
# ------------------------------------------------------------------


class TestNullQuarterlyGraphService:
    @pytest.mark.asyncio
    async def test_theme_shifts_empty(self) -> None:
        svc = NullQuarterlyGraphService()
        result = await svc.get_theme_shifts(OWNER_ID, NOW, NOW, NOW, NOW, 10)
        assert result == []

    @pytest.mark.asyncio
    async def test_recurring_patterns_empty(self) -> None:
        svc = NullQuarterlyGraphService()
        result = await svc.get_recurring_patterns(OWNER_ID, NOW, 10)
        assert result == []


# ------------------------------------------------------------------
# QuarterlyContextAssembler
# ------------------------------------------------------------------


class TestQuarterlyContextAssembler:
    @pytest.mark.asyncio
    async def test_assemble_returns_context(self) -> None:
        db = _make_db()
        graph = _make_graph()
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert isinstance(ctx, QuarterlyBriefingContext)
        assert ctx.period_start < ctx.period_end

    @pytest.mark.asyncio
    async def test_assemble_with_assumptions(self) -> None:
        rows = [
            _make_assumption_row(
                title="Hyp A",
                status="confirmed",
                status_reason="Proven by data",
                status_changed_at=NOW - timedelta(days=10),
                evidence=[{"note": "e1"}, {"note": "e2"}],
            ),
            _make_assumption_row(title="Hyp B", status="open"),
        ]
        db = _make_db(assumption_rows=rows)
        graph = _make_graph()
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert len(ctx.assumptions) == 2
        assert ctx.assumptions[0].title == "Hyp A"
        assert ctx.assumptions[0].status == "confirmed"
        assert ctx.assumptions[0].evidence_count == 2
        assert ctx.assumptions[1].title == "Hyp B"
        assert ctx.assumptions[1].evidence_count == 0

    @pytest.mark.asyncio
    async def test_assemble_with_decisions(self) -> None:
        decisions = [
            _make_decision_row(
                summary="Adopt Weaviate",
                status="made",
                decided_at=NOW - timedelta(days=30),
            ),
        ]
        db = _make_db(decision_rows=decisions)
        graph = _make_graph()
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert len(ctx.key_decisions) == 1
        assert ctx.key_decisions[0].summary == "Adopt Weaviate"

    @pytest.mark.asyncio
    async def test_assemble_with_theme_shifts(self) -> None:
        shifts = [
            ThemeShift(
                theme="AI Ethics",
                direction="rising",
                mention_count_current=12,
                mention_count_previous=2,
            )
        ]
        db = _make_db()
        graph = _make_graph(theme_shifts=shifts)
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert len(ctx.theme_shifts) == 1
        assert ctx.theme_shifts[0].theme == "AI Ethics"

    @pytest.mark.asyncio
    async def test_assemble_with_recurring_patterns(self) -> None:
        patterns = ["Security keeps coming up", "Architecture debt"]
        db = _make_db()
        graph = _make_graph(recurring_patterns=patterns)
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert len(ctx.recurring_patterns) == 2

    @pytest.mark.asyncio
    async def test_assumption_stats_computed(self) -> None:
        rows = [
            _make_assumption_row(status="open"),
            _make_assumption_row(status="open"),
            _make_assumption_row(status="confirmed"),
            _make_assumption_row(status="refuted"),
        ]
        db = _make_db(assumption_rows=rows)
        graph = _make_graph()
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert ctx.assumption_stats["open"] == 2
        assert ctx.assumption_stats["confirmed"] == 1
        assert ctx.assumption_stats["refuted"] == 1

    @pytest.mark.asyncio
    async def test_token_count_set(self) -> None:
        db = _make_db()
        graph = _make_graph()
        assembler = QuarterlyContextAssembler(db, graph)

        ctx = await assembler.assemble(OWNER_ID)

        assert ctx.token_count >= 0

    @pytest.mark.asyncio
    async def test_uses_null_graph_when_none(self) -> None:
        db = _make_db()
        assembler = QuarterlyContextAssembler(db)

        ctx = await assembler.assemble(OWNER_ID)

        assert ctx.theme_shifts == []
        assert ctx.recurring_patterns == []

    @pytest.mark.asyncio
    async def test_custom_config(self) -> None:
        db = _make_db()
        config = QuarterlyBriefingConfig(lookback_days=180)
        assembler = QuarterlyContextAssembler(db, config=config)

        ctx = await assembler.assemble(OWNER_ID)

        # Lookback should be 180 days
        diff = (ctx.period_end - ctx.period_start).days
        assert 179 <= diff <= 181  # Allow for time precision

    @pytest.mark.asyncio
    async def test_max_assumptions_limit(self) -> None:
        rows = [_make_assumption_row(title=f"Hyp {i}") for i in range(50)]
        db = _make_db(assumption_rows=rows)
        graph = _make_graph()
        config = QuarterlyBriefingConfig(max_assumptions=10)
        assembler = QuarterlyContextAssembler(db, graph, config)

        ctx = await assembler.assemble(OWNER_ID)

        assert len(ctx.assumptions) <= 10
