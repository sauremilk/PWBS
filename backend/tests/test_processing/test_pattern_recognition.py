"""Tests for Pattern Recognition Service (TASK-139)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.graph.pattern_recognition import (
    DetectedPattern,
    NullPatternGraphService,
    PatternRecognitionConfig,
    PatternRecognitionService,
    PatternSourceRef,
    PatternType,
    _EmptyResult,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()


def _mock_result(records: list[dict]) -> AsyncMock:
    """Create a mock Neo4j result that returns the given records."""
    result = AsyncMock()
    result.data = AsyncMock(return_value=records)
    return result


def _mock_session(results_by_query: dict[str, list[dict]] | None = None) -> AsyncMock:
    """Create a mock Neo4j session.

    Parameters
    ----------
    results_by_query:
        Mapping of query-substring to records.  If None, returns empty
        results for every query.
    """
    session = AsyncMock()

    if results_by_query is None:
        session.run = AsyncMock(return_value=_mock_result([]))
        return session

    async def _run(query: str, parameters: dict | None = None) -> AsyncMock:
        for substring, records in results_by_query.items():
            if substring in query:
                return _mock_result(records)
        return _mock_result([])

    session.run = AsyncMock(side_effect=_run)
    return session


def _topic_record(
    entity_id: str = "topic-1",
    entity_name: str = "Architektur",
    context_count: int = 5,
    first_seen: str = "2026-01-01T00:00:00",
    last_seen: str = "2026-03-14T00:00:00",
    sources: list[dict] | None = None,
) -> dict:
    return {
        "entityId": entity_id,
        "entityName": entity_name,
        "contextCount": context_count,
        "firstSeen": first_seen,
        "lastSeen": last_seen,
        "sources": sources or [
            {"id": "doc-1", "title": "Sprint Review", "sourceType": "notion", "date": "2026-03-10"},
            {"id": "doc-2", "title": "Meeting Notes", "sourceType": "zoom", "date": "2026-03-12"},
        ],
    }


def _hypothesis_record(
    entity_id: str = "hyp-1",
    entity_name: str = "Microservices sind performanter",
    context_count: int = 3,
    first_seen: str = "2026-01-15T00:00:00",
    last_seen: str = "2026-03-10T00:00:00",
    sources: list[dict] | None = None,
) -> dict:
    return {
        "entityId": entity_id,
        "entityName": entity_name,
        "contextCount": context_count,
        "firstSeen": first_seen,
        "lastSeen": last_seen,
        "sources": sources or [
            {"id": "doc-3", "title": "Architecture Review", "sourceType": "notion", "date": "2026-01-15"},
            {"id": "doc-4", "title": "Perf Test Results", "sourceType": "confluence", "date": "2026-03-10"},
        ],
    }


def _question_record(
    entity_id: str = "q-1",
    entity_name: str = "Welches DB-Schema fuer Events?",
    context_count: int = 4,
    first_seen: str = "2026-02-01T00:00:00",
    last_seen: str = "2026-03-13T00:00:00",
    sources: list[dict] | None = None,
) -> dict:
    return {
        "entityId": entity_id,
        "entityName": entity_name,
        "contextCount": context_count,
        "firstSeen": first_seen,
        "lastSeen": last_seen,
        "sources": sources or [
            {"id": "doc-5", "title": "DB Design Meeting", "sourceType": "zoom", "date": "2026-02-01"},
        ],
    }


# ------------------------------------------------------------------
# PatternType enum
# ------------------------------------------------------------------


class TestPatternType:
    def test_values(self) -> None:
        assert PatternType.RECURRING_THEME.value == "recurring_theme"
        assert PatternType.CHANGING_ASSUMPTION.value == "changing_assumption"
        assert PatternType.UNRESOLVED_QUESTION.value == "unresolved_question"

    def test_from_string(self) -> None:
        assert PatternType("recurring_theme") == PatternType.RECURRING_THEME


# ------------------------------------------------------------------
# PatternSourceRef
# ------------------------------------------------------------------


class TestPatternSourceRef:
    def test_create(self) -> None:
        ref = PatternSourceRef(
            document_id="doc-1",
            title="Sprint Review",
            source_type="notion",
            date="2026-03-10",
        )
        assert ref.document_id == "doc-1"
        assert ref.title == "Sprint Review"


# ------------------------------------------------------------------
# DetectedPattern
# ------------------------------------------------------------------


class TestDetectedPattern:
    def test_create(self) -> None:
        pattern = DetectedPattern(
            pattern_type=PatternType.RECURRING_THEME,
            entity_id="topic-1",
            entity_name="Architektur",
            summary="Thema taucht wiederholt auf",
            context_count=5,
            first_seen="2026-01-01",
            last_seen="2026-03-14",
        )
        assert pattern.pattern_type == PatternType.RECURRING_THEME
        assert pattern.context_count == 5
        assert pattern.sources == []

    def test_with_sources(self) -> None:
        ref = PatternSourceRef("doc-1", "Title", "notion", "2026-03-10")
        pattern = DetectedPattern(
            pattern_type=PatternType.UNRESOLVED_QUESTION,
            entity_id="q-1",
            entity_name="Was?",
            summary="Frage bleibt offen",
            context_count=3,
            first_seen="2026-01-01",
            last_seen="2026-03-10",
            sources=[ref],
        )
        assert len(pattern.sources) == 1
        assert pattern.sources[0].document_id == "doc-1"


# ------------------------------------------------------------------
# PatternRecognitionConfig
# ------------------------------------------------------------------


class TestPatternRecognitionConfig:
    def test_defaults(self) -> None:
        cfg = PatternRecognitionConfig()
        assert cfg.recurring_theme_days == 30
        assert cfg.recurring_theme_min_contexts == 3
        assert cfg.unresolved_min_mentions == 2
        assert cfg.max_results_per_type == 10

    def test_custom(self) -> None:
        cfg = PatternRecognitionConfig(
            recurring_theme_days=60,
            recurring_theme_min_contexts=5,
        )
        assert cfg.recurring_theme_days == 60
        assert cfg.recurring_theme_min_contexts == 5


# ------------------------------------------------------------------
# NullPatternGraphService
# ------------------------------------------------------------------


class TestNullPatternGraphService:
    @pytest.mark.asyncio
    async def test_returns_empty(self) -> None:
        svc = NullPatternGraphService()
        result = await svc.run("MATCH (n) RETURN n", {})
        records = await result.data()
        assert records == []


class TestEmptyResult:
    @pytest.mark.asyncio
    async def test_data_returns_empty_list(self) -> None:
        r = _EmptyResult()
        assert await r.data() == []


# ------------------------------------------------------------------
# PatternRecognitionService  recurring themes
# ------------------------------------------------------------------


class TestRecurringThemes:
    @pytest.mark.asyncio
    async def test_finds_recurring_topics(self) -> None:
        records = [_topic_record(), _topic_record(entity_id="topic-2", entity_name="DSGVO", context_count=4)]
        session = _mock_session({"Topic": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)

        assert len(patterns) == 2
        assert patterns[0].pattern_type == PatternType.RECURRING_THEME
        assert patterns[0].entity_name == "Architektur"
        assert patterns[0].context_count == 5

    @pytest.mark.asyncio
    async def test_empty_graph_returns_empty(self) -> None:
        session = _mock_session()
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)
        assert patterns == []

    @pytest.mark.asyncio
    async def test_sources_are_converted(self) -> None:
        records = [_topic_record(sources=[
            {"id": "d1", "title": "Doc 1", "sourceType": "notion", "date": "2026-03-10"},
        ])]
        session = _mock_session({"Topic": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)
        assert len(patterns[0].sources) == 1
        assert patterns[0].sources[0].document_id == "d1"

    @pytest.mark.asyncio
    async def test_summary_contains_entity_name(self) -> None:
        records = [_topic_record(entity_name="Security")]
        session = _mock_session({"Topic": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)
        assert "Security" in patterns[0].summary

    @pytest.mark.asyncio
    async def test_passes_owner_id_to_query(self) -> None:
        session = _mock_session()
        svc = PatternRecognitionService(session)

        await svc.find_recurring_themes(USER_ID)

        session.run.assert_called_once()
        call_args = session.run.call_args
        assert call_args[0][1]["userId"] == str(USER_ID)


# ------------------------------------------------------------------
# PatternRecognitionService  changing assumptions
# ------------------------------------------------------------------


class TestChangingAssumptions:
    @pytest.mark.asyncio
    async def test_finds_changing_hypotheses(self) -> None:
        records = [_hypothesis_record()]
        session = _mock_session({"Hypothesis": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_changing_assumptions(USER_ID)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.CHANGING_ASSUMPTION
        assert "Microservices" in patterns[0].entity_name

    @pytest.mark.asyncio
    async def test_empty_when_no_hypotheses(self) -> None:
        session = _mock_session()
        svc = PatternRecognitionService(session)

        patterns = await svc.find_changing_assumptions(USER_ID)
        assert patterns == []

    @pytest.mark.asyncio
    async def test_summary_mentions_documents(self) -> None:
        records = [_hypothesis_record(context_count=4)]
        session = _mock_session({"Hypothesis": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_changing_assumptions(USER_ID)
        assert "4" in patterns[0].summary


# ------------------------------------------------------------------
# PatternRecognitionService  unresolved questions
# ------------------------------------------------------------------


class TestUnresolvedQuestions:
    @pytest.mark.asyncio
    async def test_finds_unresolved(self) -> None:
        records = [_question_record()]
        session = _mock_session({"OpenQuestion": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_unresolved_questions(USER_ID)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.UNRESOLVED_QUESTION
        assert "DB-Schema" in patterns[0].entity_name

    @pytest.mark.asyncio
    async def test_empty_when_no_questions(self) -> None:
        session = _mock_session()
        svc = PatternRecognitionService(session)

        patterns = await svc.find_unresolved_questions(USER_ID)
        assert patterns == []

    @pytest.mark.asyncio
    async def test_passes_min_mentions(self) -> None:
        cfg = PatternRecognitionConfig(unresolved_min_mentions=5)
        session = _mock_session()
        svc = PatternRecognitionService(session, config=cfg)

        await svc.find_unresolved_questions(USER_ID)

        call_args = session.run.call_args
        assert call_args[0][1]["minMentions"] == 5


# ------------------------------------------------------------------
# PatternRecognitionService  detect_all_patterns
# ------------------------------------------------------------------


class TestDetectAllPatterns:
    @pytest.mark.asyncio
    async def test_combines_all_types(self) -> None:
        async def _run(query: str, parameters: dict | None = None) -> AsyncMock:
            if "Topic" in query:
                return _mock_result([_topic_record(context_count=5)])
            if "Hypothesis" in query:
                return _mock_result([_hypothesis_record(context_count=3)])
            if "OpenQuestion" in query:
                return _mock_result([_question_record(context_count=4)])
            return _mock_result([])

        session = AsyncMock()
        session.run = AsyncMock(side_effect=_run)
        svc = PatternRecognitionService(session)

        patterns = await svc.detect_all_patterns(USER_ID)

        assert len(patterns) == 3
        types = {p.pattern_type for p in patterns}
        assert types == {
            PatternType.RECURRING_THEME,
            PatternType.CHANGING_ASSUMPTION,
            PatternType.UNRESOLVED_QUESTION,
        }

    @pytest.mark.asyncio
    async def test_sorted_by_context_count_desc(self) -> None:
        async def _run(query: str, parameters: dict | None = None) -> AsyncMock:
            if "Topic" in query:
                return _mock_result([_topic_record(context_count=2)])
            if "Hypothesis" in query:
                return _mock_result([_hypothesis_record(context_count=7)])
            if "OpenQuestion" in query:
                return _mock_result([_question_record(context_count=4)])
            return _mock_result([])

        session = AsyncMock()
        session.run = AsyncMock(side_effect=_run)
        svc = PatternRecognitionService(session)

        patterns = await svc.detect_all_patterns(USER_ID)

        counts = [p.context_count for p in patterns]
        assert counts == [7, 4, 2]

    @pytest.mark.asyncio
    async def test_empty_graph_returns_empty(self) -> None:
        session = _mock_session()
        svc = PatternRecognitionService(session)

        patterns = await svc.detect_all_patterns(USER_ID)
        assert patterns == []


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_null_sources_handled(self) -> None:
        record = _topic_record()
        record["sources"] = None  # Simulate Neo4j returning null
        session = _mock_session({"Topic": [record]})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)
        assert patterns[0].sources == []

    @pytest.mark.asyncio
    async def test_source_with_none_id_skipped(self) -> None:
        records = [_topic_record(sources=[{"id": None, "title": "X", "sourceType": "n", "date": ""}])]
        session = _mock_session({"Topic": records})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)
        assert patterns[0].sources == []

    @pytest.mark.asyncio
    async def test_missing_fields_use_defaults(self) -> None:
        record = {"entityId": "x", "contextCount": 1}
        session = _mock_session({"Topic": [record]})
        svc = PatternRecognitionService(session)

        patterns = await svc.find_recurring_themes(USER_ID)
        assert patterns[0].entity_name == ""
        assert patterns[0].first_seen == ""
        assert patterns[0].last_seen == ""

    @pytest.mark.asyncio
    async def test_config_property(self) -> None:
        cfg = PatternRecognitionConfig(recurring_theme_days=60)
        svc = PatternRecognitionService(AsyncMock(), config=cfg)
        assert svc.config.recurring_theme_days == 60

    @pytest.mark.asyncio
    async def test_null_service_as_session(self) -> None:
        """NullPatternGraphService works as a valid session for the service."""
        svc = PatternRecognitionService(NullPatternGraphService())
        patterns = await svc.detect_all_patterns(USER_ID)
        assert patterns == []