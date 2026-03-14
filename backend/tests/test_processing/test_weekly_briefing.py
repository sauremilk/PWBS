"""Tests for Weekly Briefing (TASK-143).

Tests covering:
- WeeklyContextAssembler (context building, topic extraction, token budget)
- BriefingGenerator with WEEKLY type
- BriefingPersistenceService with WEEKLY expiry
- BriefingType.WEEKLY in schemas
- Celery beat schedule for weekly-briefing
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.generator import (
    BriefingGenerator,
    BriefingGeneratorConfig,
    BriefingLLMResult,
)
from pwbs.briefing.generator import BriefingType as GenBriefingType
from pwbs.briefing.persistence import (
    BriefingPersistenceService,
    PersistenceConfig,
)
from pwbs.briefing.weekly_context import (
    NullWeeklyGraphService,
    ProjectProgress,
    TopicSummary,
    WeeklyBriefingConfig,
    WeeklyBriefingContext,
    WeeklyContextAssembler,
    WeeklyDecision,
)
from pwbs.core.llm_gateway import LLMProvider, LLMResponse, LLMUsage
from pwbs.schemas.enums import BriefingType

USER_ID = uuid.uuid4()

MOCK_USAGE = LLMUsage(
    provider=LLMProvider.CLAUDE,
    model="claude-sonnet-4-20250514",
    input_tokens=500,
    output_tokens=300,
    duration_ms=1200.0,
    estimated_cost_usd=0.005,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _mock_session_with_documents(
    documents: list[dict] | None = None,
) -> AsyncMock:
    """Create a mock async session that returns documents."""
    docs = documents if documents is not None else [
        {
            "doc_id": str(uuid.uuid4()),
            "title": "Sprint Planning Notes",
            "source_type": "notion",
            "created_at": datetime(2025, 6, 13, 10, 0, tzinfo=timezone.utc),
        },
        {
            "doc_id": str(uuid.uuid4()),
            "title": "Sprint Review Meeting",
            "source_type": "zoom",
            "created_at": datetime(2025, 6, 12, 14, 0, tzinfo=timezone.utc),
        },
        {
            "doc_id": str(uuid.uuid4()),
            "title": "Sprint Retrospective Notes",
            "source_type": "notion",
            "created_at": datetime(2025, 6, 11, 16, 0, tzinfo=timezone.utc),
        },
    ]

    # Build mock rows
    mock_rows = []
    for d in docs:
        row = MagicMock()
        row.doc_id = d["doc_id"]
        row.title = d["title"]
        row.source_type = d["source_type"]
        row.created_at = d["created_at"]
        mock_rows.append(row)

    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows
    session.execute = AsyncMock(return_value=mock_result)
    session.add = MagicMock()
    session.flush = AsyncMock()

    return session


def _mock_search_service() -> MagicMock:
    """Create a mock SemanticSearchService."""
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[])
    return svc


def _make_template() -> MagicMock:
    tpl = MagicMock()
    tpl.id = "briefing_weekly.v1"
    tpl.system_prompt = "Du bist ein Briefing-Assistent."
    tpl.template = "## Wochenbriefing\n{{ week_start }} – {{ week_end }}"
    tpl.required_context = [
        "week_start", "week_end", "top_topics", "decisions",
        "project_progress", "open_items", "recent_documents",
    ]
    tpl.temperature = 0.3
    tpl.max_output_tokens = 1500
    return tpl


def _make_registry(template: MagicMock | None = None) -> MagicMock:
    tpl = template or _make_template()
    registry = MagicMock()
    registry.get.return_value = tpl
    registry.render.return_value = "## Wochenbriefing\n09.06.2025 – 15.06.2025"
    return registry


def _make_gateway(
    content: str = "# Wochenzusammenfassung\n\nDie Woche war produktiv. [Quelle: Sprint Notes, 13.06.2025]",
) -> AsyncMock:
    gw = AsyncMock()
    gw.generate = AsyncMock(return_value=LLMResponse(
        content=content,
        usage=MOCK_USAGE,
        provider=LLMProvider.CLAUDE,
        model="claude-sonnet-4-20250514",
    ))
    return gw


# ------------------------------------------------------------------
# BriefingType enum
# ------------------------------------------------------------------


class TestWeeklyBriefingType:
    """Verify WEEKLY exists in both BriefingType enums."""

    def test_schema_enum_has_weekly(self) -> None:
        assert BriefingType.WEEKLY.value == "weekly"

    def test_generator_enum_has_weekly(self) -> None:
        assert GenBriefingType.WEEKLY.value == "weekly"

    def test_schema_weekly_roundtrip(self) -> None:
        assert BriefingType("weekly") == BriefingType.WEEKLY

    def test_generator_weekly_roundtrip(self) -> None:
        assert GenBriefingType("weekly") == GenBriefingType.WEEKLY


# ------------------------------------------------------------------
# WeeklyContextAssembler
# ------------------------------------------------------------------


class TestWeeklyContextAssembler:
    """Tests for the weekly context assembler."""

    @pytest.mark.asyncio
    async def test_assemble_returns_context(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        assembler = WeeklyContextAssembler(
            session=session,
            search_service=search,
            graph_service=NullWeeklyGraphService(),
        )

        ctx = await assembler.assemble(user_id=USER_ID)

        assert isinstance(ctx, WeeklyBriefingContext)
        assert ctx.week_start != ""
        assert ctx.week_end != ""
        assert isinstance(ctx.recent_documents, list)

    @pytest.mark.asyncio
    async def test_assemble_fetches_documents(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        assembler = WeeklyContextAssembler(
            session=session,
            search_service=search,
        )

        ctx = await assembler.assemble(user_id=USER_ID)

        session.execute.assert_called_once()
        assert len(ctx.recent_documents) == 3

    @pytest.mark.asyncio
    async def test_assemble_with_target_date(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        assembler = WeeklyContextAssembler(
            session=session,
            search_service=search,
        )

        target = date(2025, 6, 15)
        ctx = await assembler.assemble(user_id=USER_ID, target_date=target)

        assert ctx.week_end == "15.06.2025"
        assert ctx.week_start == "08.06.2025"

    @pytest.mark.asyncio
    async def test_assemble_empty_documents(self) -> None:
        session = _mock_session_with_documents(documents=[])
        search = _mock_search_service()
        assembler = WeeklyContextAssembler(
            session=session,
            search_service=search,
        )

        ctx = await assembler.assemble(user_id=USER_ID)

        assert ctx.recent_documents == []
        assert ctx.top_topics == []
        assert ctx.document_count == 0


class TestTopicExtraction:
    """Tests for topic extraction from document titles."""

    def test_extracts_common_words(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
        )

        documents = [
            {"title": "Sprint Planning Notes", "source": "notion"},
            {"title": "Sprint Review", "source": "zoom"},
            {"title": "Sprint Retrospective", "source": "notion"},
        ]

        topics = assembler._extract_topics(documents)

        topic_names = [t.name for t in topics]
        assert "sprint" in topic_names

    def test_filters_stop_words(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
        )

        documents = [
            {"title": "Die neue Strategie", "source": "notion"},
            {"title": "Die alte Strategie", "source": "notion"},
        ]

        topics = assembler._extract_topics(documents)

        topic_names = [t.name for t in topics]
        assert "die" not in topic_names
        assert "strategie" in topic_names

    def test_requires_minimum_mentions(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
        )

        documents = [
            {"title": "UniqueWord1 document", "source": "notion"},
        ]

        topics = assembler._extract_topics(documents)

        # Single mention shouldn't appear (minimum is 2)
        assert len(topics) == 0

    def test_tracks_source_types(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
        )

        documents = [
            {"title": "Sprint Notes", "source": "notion"},
            {"title": "Sprint Recording", "source": "zoom"},
        ]

        topics = assembler._extract_topics(documents)

        sprint_topic = next((t for t in topics if t.name == "sprint"), None)
        assert sprint_topic is not None
        assert "notion" in sprint_topic.source_types
        assert "zoom" in sprint_topic.source_types


class TestProjectProgress:
    """Tests for project progress building."""

    def test_builds_from_entities_and_decisions(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
        )

        entities = [
            {"name": "PWBS", "document_count": 5},
            {"name": "Website Relaunch", "document_count": 3},
        ]
        decisions = [
            WeeklyDecision(title="Use FastAPI", project="PWBS", status="resolved"),
            WeeklyDecision(title="Choose CMS", project="Website Relaunch", status="pending"),
        ]

        progress = assembler._build_project_progress(entities, decisions)

        assert len(progress) == 2
        pwbs = next(p for p in progress if p.name == "PWBS")
        assert pwbs.document_count == 5
        assert pwbs.decision_count == 1

    def test_sorted_by_document_count(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
        )

        entities = [
            {"name": "Small", "document_count": 1},
            {"name": "Large", "document_count": 10},
        ]

        progress = assembler._build_project_progress(entities, [])

        assert progress[0].name == "Large"
        assert progress[1].name == "Small"


class TestTokenBudget:
    """Tests for token budget enforcement."""

    def test_within_budget_no_truncation(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
            config=WeeklyBriefingConfig(token_budget=10000),
        )

        ctx = WeeklyBriefingContext(
            week_start="08.06.2025",
            week_end="15.06.2025",
            top_topics=[],
            decisions=[],
            project_progress=[],
            open_items=[],
            recent_documents=[{"title": "Doc1", "source": "notion", "date": "13.06.2025"}],
            document_count=1,
        )

        result = assembler._enforce_token_budget(ctx)

        assert not result.truncated
        assert len(result.recent_documents) == 1

    def test_truncates_documents_first(self) -> None:
        assembler = WeeklyContextAssembler(
            session=AsyncMock(),
            search_service=MagicMock(),
            config=WeeklyBriefingConfig(token_budget=50),
        )

        ctx = WeeklyBriefingContext(
            week_start="08.06.2025",
            week_end="15.06.2025",
            top_topics=[{"name": "sprint", "mentions": 5, "sources": "notion"}],
            decisions=[{"title": "Use FastAPI", "project": "PWBS", "status": "resolved", "context": ""}],
            project_progress=[],
            open_items=[],
            recent_documents=[
                {"title": f"Document {i}", "source": "notion", "date": "13.06.2025"}
                for i in range(10)
            ],
            document_count=10,
        )

        result = assembler._enforce_token_budget(ctx)

        assert result.truncated
        assert len(result.recent_documents) < 10


# ------------------------------------------------------------------
# NullWeeklyGraphService
# ------------------------------------------------------------------


class TestNullWeeklyGraphService:
    """Verify null graph service returns empty results."""

    @pytest.mark.asyncio
    async def test_returns_empty_decisions(self) -> None:
        svc = NullWeeklyGraphService()
        result = await svc.get_week_decisions(
            USER_ID, datetime.now(timezone.utc),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_project_entities(self) -> None:
        svc = NullWeeklyGraphService()
        result = await svc.get_project_entities(
            USER_ID, datetime.now(timezone.utc),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_open_items(self) -> None:
        svc = NullWeeklyGraphService()
        result = await svc.get_open_items(USER_ID)
        assert result == []


# ------------------------------------------------------------------
# Generator: Weekly Briefing
# ------------------------------------------------------------------


class TestWeeklyBriefingGenerator:
    """Tests for BriefingGenerator with WEEKLY type."""

    @pytest.mark.asyncio
    async def test_generates_weekly_briefing(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            GenBriefingType.WEEKLY,
            {
                "week_start": "09.06.2025",
                "week_end": "15.06.2025",
                "top_topics": [],
                "decisions": [],
                "project_progress": [],
                "open_items": [],
                "recent_documents": [],
            },
            USER_ID,
        )

        assert isinstance(result, BriefingLLMResult)
        assert result.briefing_type == GenBriefingType.WEEKLY

    @pytest.mark.asyncio
    async def test_weekly_uses_correct_template(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            GenBriefingType.WEEKLY,
            {"week_start": "09.06.2025", "week_end": "15.06.2025"},
            USER_ID,
        )

        registry.get.assert_called_once_with("briefing_weekly")

    @pytest.mark.asyncio
    async def test_weekly_word_limit_in_system_prompt(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            GenBriefingType.WEEKLY,
            {"week_start": "09.06.2025", "week_end": "15.06.2025"},
            USER_ID,
        )

        request = gateway.generate.call_args[0][0]
        assert "600" in request.system_prompt

    @pytest.mark.asyncio
    async def test_weekly_max_output_tokens_from_config(self) -> None:
        tpl = _make_template()
        tpl.max_output_tokens = 0  # No template override
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        config = BriefingGeneratorConfig(weekly_max_output_tokens=1500)
        gen = BriefingGenerator(gateway, registry, config)

        await gen.generate(
            GenBriefingType.WEEKLY,
            {"week_start": "09.06.2025", "week_end": "15.06.2025"},
            USER_ID,
        )

        request = gateway.generate.call_args[0][0]
        assert request.max_tokens == 1500


# ------------------------------------------------------------------
# Persistence: Weekly Briefing
# ------------------------------------------------------------------


class TestWeeklyBriefingPersistence:
    """Tests for BriefingPersistenceService with WEEKLY type."""

    def test_weekly_expiry_7_days(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        svc = BriefingPersistenceService(session)
        now = datetime(2025, 6, 15, 17, 0, tzinfo=timezone.utc)

        exp = svc._calculate_expiry(BriefingType.WEEKLY, now)

        assert exp == now + timedelta(hours=168)  # 7 days

    def test_weekly_custom_expiry(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        config = PersistenceConfig(weekly_expiry_hours=72)
        svc = BriefingPersistenceService(session, config)
        now = datetime(2025, 6, 15, 17, 0, tzinfo=timezone.utc)

        exp = svc._calculate_expiry(BriefingType.WEEKLY, now)

        assert exp == now + timedelta(hours=72)

    @pytest.mark.asyncio
    async def test_save_weekly_briefing(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        svc = BriefingPersistenceService(session)

        result = await svc.save(
            user_id=USER_ID,
            briefing_type=BriefingType.WEEKLY,
            title="Weekly Briefing",
            content="# Wochenzusammenfassung",
            source_chunks=[uuid.uuid4()],
        )

        assert result.briefing_type == BriefingType.WEEKLY
        assert result.user_id == USER_ID
        assert result.is_new is True
        assert result.expires_at is not None
        # Verify 7-day expiry
        delta = result.expires_at - result.generated_at
        assert abs(delta.total_seconds() - 168 * 3600) < 2  # 7 days ± 2s


# ------------------------------------------------------------------
# Celery beat schedule
# ------------------------------------------------------------------


class TestCeleryBeatSchedule:
    """Tests that weekly-briefing is in the Celery beat schedule."""

    def test_weekly_briefing_in_beat_schedule(self) -> None:
        from pwbs.queue.celery_app import app

        assert "weekly-briefing" in app.conf.beat_schedule

    def test_weekly_schedule_friday_17(self) -> None:
        from pwbs.queue.celery_app import app

        schedule = app.conf.beat_schedule["weekly-briefing"]
        assert schedule["schedule"]["hour"] == "17"
        assert schedule["schedule"]["minute"] == "0"
        assert schedule["schedule"]["day_of_week"] == "5"

    def test_weekly_task_name(self) -> None:
        from pwbs.queue.celery_app import app

        schedule = app.conf.beat_schedule["weekly-briefing"]
        assert schedule["task"] == "pwbs.queue.tasks.briefing.generate_weekly_briefings"

    def test_weekly_queue(self) -> None:
        from pwbs.queue.celery_app import app

        schedule = app.conf.beat_schedule["weekly-briefing"]
        assert schedule["options"]["queue"] == "briefing.generate"


# ------------------------------------------------------------------
# WeeklyBriefingConfig
# ------------------------------------------------------------------


class TestWeeklyBriefingConfig:
    """Tests for WeeklyBriefingConfig defaults."""

    def test_default_values(self) -> None:
        cfg = WeeklyBriefingConfig()
        assert cfg.token_budget == 8000
        assert cfg.lookback_days == 7
        assert cfg.max_documents == 30
        assert cfg.max_decisions == 15
        assert cfg.max_topics == 10

    def test_custom_values(self) -> None:
        cfg = WeeklyBriefingConfig(
            token_budget=5000,
            lookback_days=14,
            max_topics=5,
        )
        assert cfg.token_budget == 5000
        assert cfg.lookback_days == 14
        assert cfg.max_topics == 5
