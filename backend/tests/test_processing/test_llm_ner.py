"""Tests for LLM-basierte Entitätsextraktion (TASK-062)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.core.llm_gateway import LLMUsage
from pwbs.core.rate_limiter import RateLimitExceededError
from pwbs.core.structured_output import (
    StructuredOutputError,
    StructuredOutputResult,
)
from pwbs.processing.llm_ner import (
    DateReference,
    DecisionEntity,
    ExtractionResponse,
    LLMEntityExtractor,
    LLMExtractionConfig,
    LLMExtractionResult,
    OpenQuestion,
    PersonEntity,
    ProjectEntity,
    TopicEntry,
    _normalize,
)
from pwbs.schemas.enums import EntityType

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CHUNK_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _usage() -> LLMUsage:
    return LLMUsage(
        provider="claude",
        model="claude-haiku",
        input_tokens=100,
        output_tokens=50,
        duration_ms=200.0,
        estimated_cost_usd=0.001,
    )


def _extraction_response(
    persons: list[PersonEntity] | None = None,
    projects: list[ProjectEntity] | None = None,
    topics: list[TopicEntry] | None = None,
    decisions: list[DecisionEntity] | None = None,
    open_questions: list[OpenQuestion] | None = None,
    dates: list[DateReference] | None = None,
) -> ExtractionResponse:
    return ExtractionResponse(
        persons=persons or [],
        projects=projects or [],
        topics=topics or [],
        decisions=decisions or [],
        open_questions=open_questions or [],
        dates=dates or [],
    )


def _structured_result(
    response: ExtractionResponse | None = None,
) -> StructuredOutputResult[ExtractionResponse]:
    return StructuredOutputResult(
        parsed=response or _extraction_response(),
        raw='{"persons":[],"projects":[],"topics":[]}',
        usage=_usage(),
        retried=False,
    )


def _make_extractor(
    response: ExtractionResponse | None = None,
    rate_limiter: AsyncMock | None = None,
    structured_output: AsyncMock | None = None,
    config: LLMExtractionConfig | None = None,
) -> LLMEntityExtractor:
    so = structured_output or AsyncMock()
    if structured_output is None:
        so.generate = AsyncMock(return_value=_structured_result(response))
    return LLMEntityExtractor(
        structured_output=so,
        rate_limiter=rate_limiter,
        config=config,
    )


# ===================================================================
# Config
# ===================================================================


class TestLLMExtractionConfig:
    def test_defaults(self) -> None:
        cfg = LLMExtractionConfig()
        assert cfg.confidence_threshold == 0.75
        assert cfg.max_output_tokens == 1000
        assert cfg.temperature == 0.1
        assert cfg.use_case == "entity.extraction"

    def test_custom(self) -> None:
        cfg = LLMExtractionConfig(confidence_threshold=0.5, max_output_tokens=500)
        assert cfg.confidence_threshold == 0.5
        assert cfg.max_output_tokens == 500


# ===================================================================
# Empty / Invalid Input
# ===================================================================


class TestEmptyInput:
    @pytest.mark.asyncio
    async def test_empty_string(self) -> None:
        ext = _make_extractor()
        result = await ext.extract("", USER_ID)
        assert result.entities == []

    @pytest.mark.asyncio
    async def test_whitespace_only(self) -> None:
        ext = _make_extractor()
        result = await ext.extract("   ", USER_ID)
        assert result.entities == []

    @pytest.mark.asyncio
    async def test_no_llm_call_for_empty(self) -> None:
        so = AsyncMock()
        so.generate = AsyncMock()
        ext = LLMEntityExtractor(structured_output=so)
        await ext.extract("", USER_ID)
        so.generate.assert_not_awaited()


# ===================================================================
# Person Extraction
# ===================================================================


class TestPersonExtraction:
    @pytest.mark.asyncio
    async def test_single_person(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="Alice Smith", role="CTO", context="Meeting", confidence=0.9)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Alice Smith is CTO.", USER_ID, CHUNK_ID)
        assert len(result.entities) == 1
        e = result.entities[0]
        assert e.entity_type == EntityType.PERSON
        assert e.name == "Alice Smith"
        assert e.normalized_name == "alice smith"
        assert e.metadata["role"] == "CTO"
        assert e.mentions[0].extraction_method == "llm"
        assert e.mentions[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_person_empty_name_skipped(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="", confidence=0.9)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Some text.", USER_ID)
        assert result.entities == []

    @pytest.mark.asyncio
    async def test_person_metadata_optional(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="Bob", confidence=0.8)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Bob was there.", USER_ID)
        e = result.entities[0]
        assert "role" not in e.metadata
        assert "context" not in e.metadata


# ===================================================================
# Project Extraction
# ===================================================================


class TestProjectExtraction:
    @pytest.mark.asyncio
    async def test_single_project(self) -> None:
        resp = _extraction_response(
            projects=[ProjectEntity(name="Phoenix", status="active", confidence=0.85)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Phoenix project.", USER_ID)
        e = result.entities[0]
        assert e.entity_type == EntityType.PROJECT
        assert e.name == "Phoenix"
        assert e.metadata["status"] == "active"

    @pytest.mark.asyncio
    async def test_project_no_status(self) -> None:
        resp = _extraction_response(
            projects=[ProjectEntity(name="Alpha", confidence=0.8)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Alpha mentioned.", USER_ID)
        assert "status" not in result.entities[0].metadata


# ===================================================================
# Topic Extraction
# ===================================================================


class TestTopicExtraction:
    @pytest.mark.asyncio
    async def test_single_topic(self) -> None:
        resp = _extraction_response(
            topics=[TopicEntry(name="Kubernetes", confidence=0.9)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Kubernetes deployment.", USER_ID)
        e = result.entities[0]
        assert e.entity_type == EntityType.TOPIC
        assert e.name == "Kubernetes"


# ===================================================================
# Decision Extraction
# ===================================================================


class TestDecisionExtraction:
    @pytest.mark.asyncio
    async def test_decision_with_metadata(self) -> None:
        resp = _extraction_response(
            decisions=[
                DecisionEntity(what="Use PostgreSQL", by="Team Lead", date="2026-01-15", confidence=0.85),
            ],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Decision: Use PostgreSQL.", USER_ID)
        e = result.entities[0]
        assert e.entity_type == EntityType.DECISION
        assert e.name == "Use PostgreSQL"
        assert e.metadata["decided_by"] == "Team Lead"
        assert e.metadata["decision_date"] == "2026-01-15"


# ===================================================================
# Open Questions  Topic
# ===================================================================


class TestOpenQuestions:
    @pytest.mark.asyncio
    async def test_open_question_becomes_topic(self) -> None:
        resp = _extraction_response(
            open_questions=[OpenQuestion(text="How to handle auth?", confidence=0.8)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("How to handle auth?", USER_ID)
        e = result.entities[0]
        assert e.entity_type == EntityType.TOPIC
        assert e.metadata["kind"] == "open_question"
        assert e.mentions[0].source_pattern == "llm_open_question"


# ===================================================================
# Date References  Topic
# ===================================================================


class TestDateReferences:
    @pytest.mark.asyncio
    async def test_date_reference_becomes_topic(self) -> None:
        resp = _extraction_response(
            dates=[DateReference(description="Release deadline", date="2026-03-01", confidence=0.8)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Release deadline March 1.", USER_ID)
        e = result.entities[0]
        assert e.entity_type == EntityType.TOPIC
        assert e.metadata["date"] == "2026-03-01"
        assert e.mentions[0].source_pattern == "llm_date_reference"


# ===================================================================
# Confidence Filtering
# ===================================================================


class TestConfidenceFiltering:
    @pytest.mark.asyncio
    async def test_below_threshold_filtered(self) -> None:
        resp = _extraction_response(
            persons=[
                PersonEntity(name="Alice", confidence=0.9),
                PersonEntity(name="Vague Person", confidence=0.5),
            ],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Some text.", USER_ID)
        assert len(result.entities) == 1
        assert result.entities[0].name == "Alice"
        assert result.filtered_count == 1

    @pytest.mark.asyncio
    async def test_exact_threshold_kept(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="Bob", confidence=0.75)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Bob.", USER_ID)
        assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_custom_threshold(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="Alice", confidence=0.6)],
        )
        ext = _make_extractor(
            response=resp,
            config=LLMExtractionConfig(confidence_threshold=0.5),
        )
        result = await ext.extract("Alice.", USER_ID)
        assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_all_below_threshold(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="A", confidence=0.3)],
            topics=[TopicEntry(name="T", confidence=0.4)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Some text.", USER_ID)
        assert result.entities == []
        assert result.filtered_count == 2


# ===================================================================
# Rate Limiting
# ===================================================================


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limited_returns_empty(self) -> None:
        limiter = AsyncMock()
        limiter.check_limits = AsyncMock(
            side_effect=RateLimitExceededError(
                user_id=USER_ID, reason="Daily limit reached",
            ),
        )
        ext = _make_extractor(rate_limiter=limiter)
        result = await ext.extract("Some text.", USER_ID)
        assert result.rate_limited is True
        assert result.entities == []
        assert "Daily limit" in (result.error or "")

    @pytest.mark.asyncio
    async def test_no_limiter_skips_check(self) -> None:
        ext = _make_extractor(rate_limiter=None)
        result = await ext.extract("Some text.", USER_ID)
        assert result.rate_limited is False

    @pytest.mark.asyncio
    async def test_usage_recorded_after_call(self) -> None:
        limiter = AsyncMock()
        limiter.check_limits = AsyncMock()
        limiter.record_usage = AsyncMock()
        ext = _make_extractor(rate_limiter=limiter)
        await ext.extract("Some text.", USER_ID)
        limiter.record_usage.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_usage_record_failure_does_not_break(self) -> None:
        limiter = AsyncMock()
        limiter.check_limits = AsyncMock()
        limiter.record_usage = AsyncMock(side_effect=RuntimeError("DB down"))
        ext = _make_extractor(rate_limiter=limiter)
        result = await ext.extract("Some text.", USER_ID)
        # Should still return entities despite usage recording failure
        assert result.error is None


# ===================================================================
# Structured Output Errors
# ===================================================================


class TestStructuredOutputErrors:
    @pytest.mark.asyncio
    async def test_structured_output_error_logged(self) -> None:
        so = AsyncMock()
        so.generate = AsyncMock(
            side_effect=StructuredOutputError(
                message="Parse failed",
                raw_response='{"invalid": true}',
                validation_errors=["field required"],
            ),
        )
        ext = LLMEntityExtractor(structured_output=so)
        result = await ext.extract("Some text.", USER_ID, CHUNK_ID)
        assert result.entities == []
        assert result.error is not None
        assert result.raw_response == '{"invalid": true}'


# ===================================================================
# Mixed Entities
# ===================================================================


class TestMixedExtraction:
    @pytest.mark.asyncio
    async def test_multiple_entity_types(self) -> None:
        resp = _extraction_response(
            persons=[PersonEntity(name="Alice", confidence=0.9)],
            projects=[ProjectEntity(name="Phoenix", confidence=0.85)],
            topics=[TopicEntry(name="Microservices", confidence=0.8)],
            decisions=[DecisionEntity(what="Use K8s", confidence=0.8)],
        )
        ext = _make_extractor(response=resp)
        result = await ext.extract("Big meeting.", USER_ID)
        types = {e.entity_type for e in result.entities}
        assert EntityType.PERSON in types
        assert EntityType.PROJECT in types
        assert EntityType.TOPIC in types
        assert EntityType.DECISION in types

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        ext = _make_extractor(response=_extraction_response())
        result = await ext.extract("Boring text.", USER_ID)
        assert result.entities == []
        assert result.filtered_count == 0


# ===================================================================
# Normalization
# ===================================================================


class TestNormalization:
    def test_lowercase(self) -> None:
        assert _normalize("Alice Smith") == "alice smith"

    def test_collapse_whitespace(self) -> None:
        assert _normalize("  Alice   Smith  ") == "alice smith"

    def test_empty(self) -> None:
        assert _normalize("") == ""


# ===================================================================
# Config property
# ===================================================================


class TestConfigProperty:
    def test_config_accessible(self) -> None:
        cfg = LLMExtractionConfig(confidence_threshold=0.5)
        ext = _make_extractor(config=cfg)
        assert ext.config.confidence_threshold == 0.5
