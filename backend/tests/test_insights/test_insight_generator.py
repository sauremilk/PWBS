"""Tests for the Proactive Insight Generator (TASK-158).

Covers:
- AC1: Insight generation from graph patterns (max 3/day)
- AC2: Category + frequency preference filtering
- AC3: Source references on every insight
- AC4: Feedback loop (negative feedback suppresses entities)
- Generator internals: filtering, LLM prompt building, response parsing
- Persistence: upsert preferences, persist insights, submit feedback
- Celery task structure
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.graph.pattern_recognition import (
    DetectedPattern,
    PatternSourceRef,
    PatternType,
)
from pwbs.insights.generator import (
    PATTERN_TO_CATEGORY,
    VALID_CATEGORIES,
    InsightCategory,
    InsightGeneratorConfig,
    InsightResult,
    ProactiveInsightGenerator,
    SourceRef,
)

# ── Fixtures ──────────────────────────────────────────────────────────

USER_ID = uuid.uuid4()


def _make_source(idx: int = 1) -> PatternSourceRef:
    return PatternSourceRef(
        document_id=f"doc-{idx}",
        title=f"Dokument {idx}",
        source_type="notion",
        date="2026-01-15",
    )


def _make_pattern(
    ptype: PatternType = PatternType.RECURRING_THEME,
    entity_id: str = "ent-1",
    entity_name: str = "KI-Strategie",
    context_count: int = 5,
    sources: list[PatternSourceRef] | None = None,
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=ptype,
        entity_id=entity_id,
        entity_name=entity_name,
        summary=f"Pattern {entity_name}",
        context_count=context_count,
        first_seen="2026-01-01",
        last_seen="2026-03-01",
        sources=sources if sources is not None else [_make_source()],
    )


def _make_pattern_service(
    patterns: list[DetectedPattern] | None = None,
) -> AsyncMock:
    svc = AsyncMock()
    svc.detect_all_patterns = AsyncMock(return_value=patterns or [])
    return svc


def _make_llm_gateway(
    response_content: str = '[{"title": "Test Insight", "content": "Test body."}]',
) -> AsyncMock:
    gateway = AsyncMock()
    resp = MagicMock()
    resp.content = response_content
    gateway.generate = AsyncMock(return_value=resp)
    return gateway


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1: InsightGeneratorConfig
# ═══════════════════════════════════════════════════════════════════════


class TestInsightGeneratorConfig:
    def test_defaults(self) -> None:
        cfg = InsightGeneratorConfig()
        assert cfg.max_insights_per_run == 3
        assert cfg.llm_temperature == 0.3
        assert cfg.llm_max_tokens == 512
        assert cfg.min_pattern_context_count == 2
        assert cfg.exclude_recently_rated_days == 30

    def test_custom_values(self) -> None:
        cfg = InsightGeneratorConfig(
            max_insights_per_run=5,
            llm_temperature=0.5,
        )
        assert cfg.max_insights_per_run == 5
        assert cfg.llm_temperature == 0.5


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2: Category Mapping
# ═══════════════════════════════════════════════════════════════════════


class TestCategoryMapping:
    def test_all_pattern_types_mapped(self) -> None:
        for pt in PatternType:
            assert pt in PATTERN_TO_CATEGORY

    def test_valid_categories_complete(self) -> None:
        assert {"contradictions", "forgotten_topics", "trends"} == VALID_CATEGORIES

    def test_category_constants(self) -> None:
        assert InsightCategory.CONTRADICTIONS == "contradictions"
        assert InsightCategory.FORGOTTEN_TOPICS == "forgotten_topics"
        assert InsightCategory.TRENDS == "trends"


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3: Pattern Filtering
# ═══════════════════════════════════════════════════════════════════════


class TestPatternFiltering:
    def _make_generator(
        self,
        config: InsightGeneratorConfig | None = None,
    ) -> ProactiveInsightGenerator:
        return ProactiveInsightGenerator(
            _make_pattern_service(),
            _make_llm_gateway(),
            config,
        )

    def test_filters_by_category(self) -> None:
        gen = self._make_generator()
        patterns = [
            _make_pattern(PatternType.CHANGING_ASSUMPTION),
            _make_pattern(PatternType.RECURRING_THEME),
        ]
        # Only allow contradictions
        result = gen._filter_patterns(patterns, {"contradictions"}, frozenset())
        assert len(result) == 1
        assert result[0].pattern_type == PatternType.CHANGING_ASSUMPTION

    def test_filters_by_min_context(self) -> None:
        gen = self._make_generator(InsightGeneratorConfig(min_pattern_context_count=3))
        patterns = [
            _make_pattern(context_count=2),
            _make_pattern(context_count=5, entity_id="ent-2"),
        ]
        result = gen._filter_patterns(patterns, set(VALID_CATEGORIES), frozenset())
        assert len(result) == 1
        assert result[0].entity_id == "ent-2"

    def test_filters_negative_feedback_entities(self) -> None:
        gen = self._make_generator()
        patterns = [
            _make_pattern(entity_id="ent-bad"),
            _make_pattern(entity_id="ent-good"),
        ]
        result = gen._filter_patterns(patterns, set(VALID_CATEGORIES), frozenset({"ent-bad"}))
        assert len(result) == 1
        assert result[0].entity_id == "ent-good"

    def test_empty_patterns_returns_empty(self) -> None:
        gen = self._make_generator()
        result = gen._filter_patterns([], set(VALID_CATEGORIES), frozenset())
        assert result == []


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 4: LLM Prompt Building
# ═══════════════════════════════════════════════════════════════════════


class TestPromptBuilding:
    def test_builds_user_prompt(self) -> None:
        patterns = [
            _make_pattern(
                PatternType.CHANGING_ASSUMPTION,
                entity_name="Datenschutz",
                context_count=4,
                sources=[_make_source(1), _make_source(2)],
            )
        ]
        prompt = ProactiveInsightGenerator._build_user_prompt(patterns)
        assert "Muster 1 [contradictions]" in prompt
        assert "Datenschutz" in prompt
        assert "Kontexte: 4" in prompt
        assert "Dokument 1" in prompt
        assert "Dokument 2" in prompt

    def test_no_sources_shows_placeholder(self) -> None:
        patterns = [_make_pattern(sources=[])]
        prompt = ProactiveInsightGenerator._build_user_prompt(patterns)
        assert "(keine Quellen)" in prompt


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 5: Response Parsing
# ═══════════════════════════════════════════════════════════════════════


class TestResponseParsing:
    def test_parses_valid_json_array(self) -> None:
        patterns = [_make_pattern()]
        content = json.dumps(
            [
                {"title": "Insight A", "content": "Body A"},
            ]
        )
        results = ProactiveInsightGenerator._parse_response(content, patterns)
        assert len(results) == 1
        assert results[0].title == "Insight A"
        assert results[0].content == "Body A"

    def test_parses_single_object(self) -> None:
        patterns = [_make_pattern()]
        content = json.dumps({"title": "Single", "content": "Body"})
        results = ProactiveInsightGenerator._parse_response(content, patterns)
        assert len(results) == 1
        assert results[0].title == "Single"

    def test_invalid_json_returns_empty(self) -> None:
        results = ProactiveInsightGenerator._parse_response("not json", [_make_pattern()])
        assert results == []

    def test_empty_title_skipped(self) -> None:
        content = json.dumps([{"title": "", "content": "Body"}])
        results = ProactiveInsightGenerator._parse_response(content, [_make_pattern()])
        assert results == []

    def test_sources_mapped_from_pattern(self) -> None:
        src = _make_source(42)
        patterns = [_make_pattern(sources=[src])]
        content = json.dumps([{"title": "T", "content": "C"}])
        results = ProactiveInsightGenerator._parse_response(content, patterns)
        assert len(results[0].sources) == 1
        assert results[0].sources[0].document_id == "doc-42"

    def test_category_mapped_from_pattern_type(self) -> None:
        patterns = [_make_pattern(PatternType.CHANGING_ASSUMPTION)]
        content = json.dumps([{"title": "T", "content": "C"}])
        results = ProactiveInsightGenerator._parse_response(content, patterns)
        assert results[0].category == "contradictions"

    def test_pattern_data_stored(self) -> None:
        patterns = [
            _make_pattern(
                entity_id="ent-x",
                entity_name="Test",
                context_count=7,
            )
        ]
        content = json.dumps([{"title": "T", "content": "C"}])
        results = ProactiveInsightGenerator._parse_response(content, patterns)
        assert results[0].pattern_data["entity_id"] == "ent-x"
        assert results[0].pattern_data["context_count"] == 7

    def test_extra_items_beyond_patterns_get_defaults(self) -> None:
        patterns = [_make_pattern()]
        content = json.dumps(
            [
                {"title": "A", "content": "X"},
                {"title": "B", "content": "Y"},
            ]
        )
        results = ProactiveInsightGenerator._parse_response(content, patterns)
        assert len(results) == 2
        # Second item has no matching pattern → defaults to 'trends'
        assert results[1].category == "trends"
        assert results[1].sources == []


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 6: Full Generation Flow (AC1 + AC3)
# ═══════════════════════════════════════════════════════════════════════


class TestGenerateFlow:
    @pytest.mark.asyncio
    async def test_generates_insights_from_patterns(self) -> None:
        """AC1: Scheduled job generates proactive insights."""
        patterns = [
            _make_pattern(PatternType.RECURRING_THEME, entity_id="e1"),
            _make_pattern(PatternType.CHANGING_ASSUMPTION, entity_id="e2"),
        ]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway(
            json.dumps(
                [
                    {"title": "T1", "content": "C1"},
                    {"title": "T2", "content": "C2"},
                ]
            )
        )
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        results = await gen.generate(USER_ID)

        assert len(results) == 2
        pattern_svc.detect_all_patterns.assert_awaited_once_with(USER_ID)
        llm.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_max_insights_cap(self) -> None:
        """AC1: Max 3 per day."""
        patterns = [_make_pattern(entity_id=f"e{i}", context_count=10 - i) for i in range(5)]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway(
            json.dumps([{"title": f"T{i}", "content": f"C{i}"} for i in range(3)])
        )
        gen = ProactiveInsightGenerator(
            pattern_svc, llm, InsightGeneratorConfig(max_insights_per_run=3)
        )

        results = await gen.generate(USER_ID)

        # LLM should only receive 3 patterns
        call_args = llm.generate.call_args[0][0]
        prompt_text = call_args.user_prompt
        assert "Muster 3" in prompt_text
        assert "Muster 4" not in prompt_text

    @pytest.mark.asyncio
    async def test_each_insight_has_sources(self) -> None:
        """AC3: Each insight contains sources with at least one reference."""
        patterns = [_make_pattern(sources=[_make_source(1), _make_source(2)])]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway(json.dumps([{"title": "T", "content": "C"}]))
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        results = await gen.generate(USER_ID)

        assert len(results) == 1
        assert len(results[0].sources) >= 1
        assert results[0].sources[0].document_id == "doc-1"

    @pytest.mark.asyncio
    async def test_no_patterns_returns_empty(self) -> None:
        pattern_svc = _make_pattern_service([])
        llm = _make_llm_gateway()
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        results = await gen.generate(USER_ID)

        assert results == []
        llm.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_temperature_is_0_3(self) -> None:
        """Technische Hinweise: LLM-Temperatur 0.3."""
        patterns = [_make_pattern()]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway()
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        await gen.generate(USER_ID)

        request = llm.generate.call_args[0][0]
        assert request.temperature == 0.3

    @pytest.mark.asyncio
    async def test_json_mode_enabled(self) -> None:
        patterns = [_make_pattern()]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway()
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        await gen.generate(USER_ID)

        request = llm.generate.call_args[0][0]
        assert request.json_mode is True


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 7: Category Filtering (AC2)
# ═══════════════════════════════════════════════════════════════════════


class TestCategoryPreferences:
    @pytest.mark.asyncio
    async def test_only_enabled_categories_generated(self) -> None:
        """AC2: User configures which categories to receive."""
        patterns = [
            _make_pattern(PatternType.CHANGING_ASSUMPTION, entity_id="e1"),
            _make_pattern(PatternType.RECURRING_THEME, entity_id="e2"),
            _make_pattern(PatternType.UNRESOLVED_QUESTION, entity_id="e3"),
        ]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway(json.dumps([{"title": "T", "content": "C"}]))
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        results = await gen.generate(USER_ID, enabled_categories=["contradictions"])

        # LLM prompt should only have the contradiction pattern
        prompt = llm.generate.call_args[0][0].user_prompt
        assert "[contradictions]" in prompt
        assert "[forgotten_topics]" not in prompt
        assert "[trends]" not in prompt

    @pytest.mark.asyncio
    async def test_invalid_category_ignored(self) -> None:
        patterns = [_make_pattern()]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway()
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        results = await gen.generate(USER_ID, enabled_categories=["invalid_cat"])

        assert results == []


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 8: Feedback Suppression (AC4)
# ═══════════════════════════════════════════════════════════════════════


class TestFeedbackSuppression:
    @pytest.mark.asyncio
    async def test_negative_feedback_suppresses_entity(self) -> None:
        """AC4: Negative feedback suppresses future insights for that entity."""
        patterns = [
            _make_pattern(entity_id="bad-ent"),
            _make_pattern(entity_id="good-ent", context_count=3),
        ]
        pattern_svc = _make_pattern_service(patterns)
        llm = _make_llm_gateway(json.dumps([{"title": "T", "content": "C"}]))
        gen = ProactiveInsightGenerator(pattern_svc, llm)

        results = await gen.generate(
            USER_ID,
            negative_entity_ids=frozenset({"bad-ent"}),
        )

        # Should only have insights for good-ent
        prompt = llm.generate.call_args[0][0].user_prompt
        assert "good-ent" not in prompt  # entity_id not in prompt
        # But the entity_name IS in the prompt
        assert "Muster 1" in prompt
        assert "Muster 2" not in prompt


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 9: Data Types
# ═══════════════════════════════════════════════════════════════════════


class TestDataTypes:
    def test_source_ref_is_frozen(self) -> None:
        ref = SourceRef(
            document_id="d1",
            title="T",
            source_type="notion",
            date="2026-01-01",
        )
        with pytest.raises(AttributeError):
            ref.title = "changed"  # type: ignore[misc]

    def test_insight_result_is_frozen(self) -> None:
        result = InsightResult(
            category="trends",
            title="T",
            content="C",
            sources=[],
            pattern_data={},
        )
        with pytest.raises(AttributeError):
            result.title = "changed"  # type: ignore[misc]

    def test_insight_result_fields(self) -> None:
        src = SourceRef("d1", "T", "notion", "2026-01-01")
        result = InsightResult(
            category="contradictions",
            title="Title",
            content="Content",
            sources=[src],
            pattern_data={"key": "value"},
        )
        assert result.category == "contradictions"
        assert len(result.sources) == 1
        assert result.pattern_data["key"] == "value"


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 10: ORM Model Structure
# ═══════════════════════════════════════════════════════════════════════


class TestOrmModels:
    def test_proactive_insight_table_name(self) -> None:
        from pwbs.models.proactive_insight import ProactiveInsight

        assert ProactiveInsight.__tablename__ == "proactive_insights"

    def test_proactive_insight_has_required_columns(self) -> None:
        from pwbs.models.proactive_insight import ProactiveInsight

        cols = {c.name for c in ProactiveInsight.__table__.columns}
        assert "owner_id" in cols
        assert "category" in cols
        assert "title" in cols
        assert "content" in cols
        assert "sources" in cols
        assert "feedback_rating" in cols
        assert "expires_at" in cols

    def test_insight_preferences_table_name(self) -> None:
        from pwbs.models.proactive_insight import InsightPreferences

        assert InsightPreferences.__tablename__ == "insight_preferences"

    def test_insight_preferences_has_required_columns(self) -> None:
        from pwbs.models.proactive_insight import InsightPreferences

        cols = {c.name for c in InsightPreferences.__table__.columns}
        assert "owner_id" in cols
        assert "frequency" in cols
        assert "enabled_categories" in cols
        assert "max_insights_per_run" in cols


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 11: Celery Task Registration
# ═══════════════════════════════════════════════════════════════════════


class TestCeleryTask:
    def test_task_is_registered(self) -> None:
        # Import triggers task registration
        import pwbs.queue.tasks.insights  # noqa: F401
        from pwbs.queue.celery_app import app

        task_name = "pwbs.queue.tasks.insights.generate_proactive_insights"
        assert task_name in app.tasks

    def test_task_config(self) -> None:
        from pwbs.queue.tasks.insights import generate_proactive_insights

        assert generate_proactive_insights.max_retries == 3
        assert generate_proactive_insights.queue == "briefing.generate"

    def test_beat_schedule_has_insight_entry(self) -> None:
        from pwbs.queue.celery_app import app

        assert "proactive-insights" in app.conf.beat_schedule
        entry = app.conf.beat_schedule["proactive-insights"]
        assert entry["task"] == "pwbs.queue.tasks.insights.generate_proactive_insights"
        assert entry["schedule"]["hour"] == "8"
