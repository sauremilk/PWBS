"""Tests für Structured Output mit JSON-Schema-Validierung (TASK-068)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, Field

from pwbs.core.llm_gateway import LLMProvider, LLMResponse, LLMUsage
from pwbs.core.structured_output import (
    StructuredOutputError,
    StructuredOutputService,
)

# ------------------------------------------------------------------
# Test schemas
# ------------------------------------------------------------------


class SimpleOutput(BaseModel):
    title: str
    score: float = Field(ge=0, le=1)


class NestedOutput(BaseModel):
    name: str
    tags: list[str]
    metadata: dict[str, str] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_USAGE = LLMUsage(
    provider=LLMProvider.CLAUDE,
    model="claude-sonnet-4-20250514",
    input_tokens=100,
    output_tokens=50,
    duration_ms=200.0,
    estimated_cost_usd=0.001,
)


def _make_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        usage=_USAGE,
        provider=LLMProvider.CLAUDE,
        model="claude-sonnet-4-20250514",
    )


def _make_gateway(*responses: LLMResponse) -> AsyncMock:
    """Create a mock LLMGateway returning the given responses in sequence."""
    gw = AsyncMock()
    gw.generate = AsyncMock(side_effect=list(responses))
    return gw


# ------------------------------------------------------------------
# JSON Extraction tests
# ------------------------------------------------------------------


class TestJsonExtraction:
    """Tests for _extract_json static method."""

    def test_plain_json(self) -> None:
        raw = '{"title": "Test", "score": 0.5}'
        result = StructuredOutputService._extract_json(raw)
        assert result is not None
        assert json.loads(result)["title"] == "Test"

    def test_json_in_code_fence(self) -> None:
        raw = 'Here is the result:\n```json\n{"title": "Test", "score": 0.8}\n```'
        result = StructuredOutputService._extract_json(raw)
        assert result is not None
        assert json.loads(result)["score"] == 0.8

    def test_json_in_plain_fence(self) -> None:
        raw = '```\n{"title": "X", "score": 0.1}\n```'
        result = StructuredOutputService._extract_json(raw)
        assert result is not None
        assert json.loads(result)["title"] == "X"

    def test_bare_json_object_in_text(self) -> None:
        raw = 'Some text before {"title": "Embedded", "score": 0.3} and after.'
        result = StructuredOutputService._extract_json(raw)
        assert result is not None
        assert json.loads(result)["title"] == "Embedded"

    def test_no_json_returns_none(self) -> None:
        result = StructuredOutputService._extract_json("No JSON here at all.")
        assert result is None

    def test_whitespace_padding(self) -> None:
        raw = '   \n  {"title": "Padded", "score": 0.9}  \n  '
        result = StructuredOutputService._extract_json(raw)
        assert result is not None
        assert json.loads(result)["title"] == "Padded"


# ------------------------------------------------------------------
# Successful generation tests
# ------------------------------------------------------------------


class TestSuccessfulGeneration:
    """Tests for successful structured output generation."""

    @pytest.mark.asyncio
    async def test_valid_json_first_attempt(self) -> None:
        content = json.dumps({"title": "Test", "score": 0.5})
        gw = _make_gateway(_make_response(content))
        svc = StructuredOutputService(gw)

        result = await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input text",
            output_schema=SimpleOutput,
        )

        assert result.parsed.title == "Test"
        assert result.parsed.score == 0.5
        assert not result.retried
        gw.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_nested_schema(self) -> None:
        content = json.dumps({"name": "Project X", "tags": ["alpha", "beta"]})
        gw = _make_gateway(_make_response(content))
        svc = StructuredOutputService(gw)

        result = await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input",
            output_schema=NestedOutput,
        )

        assert result.parsed.name == "Project X"
        assert result.parsed.tags == ["alpha", "beta"]
        assert result.parsed.metadata == {}

    @pytest.mark.asyncio
    async def test_json_in_code_fence_parsed(self) -> None:
        content = '```json\n{"title": "Fenced", "score": 0.7}\n```'
        gw = _make_gateway(_make_response(content))
        svc = StructuredOutputService(gw)

        result = await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input",
            output_schema=SimpleOutput,
        )

        assert result.parsed.title == "Fenced"
        assert not result.retried


# ------------------------------------------------------------------
# Retry tests
# ------------------------------------------------------------------


class TestRetryBehavior:
    """Tests for retry on validation failure."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_first_failure(self) -> None:
        bad_response = _make_response("This is not JSON at all.")
        good_response = _make_response(json.dumps({"title": "Fixed", "score": 0.4}))
        gw = _make_gateway(bad_response, good_response)
        svc = StructuredOutputService(gw)

        result = await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input",
            output_schema=SimpleOutput,
        )

        assert result.parsed.title == "Fixed"
        assert result.retried
        assert gw.generate.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_invalid_schema_then_valid(self) -> None:
        # First: valid JSON but fails schema (score > 1)
        bad_response = _make_response(json.dumps({"title": "Bad", "score": 5.0}))
        good_response = _make_response(json.dumps({"title": "Good", "score": 0.8}))
        gw = _make_gateway(bad_response, good_response)
        svc = StructuredOutputService(gw)

        result = await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input",
            output_schema=SimpleOutput,
        )

        assert result.parsed.title == "Good"
        assert result.retried

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises(self) -> None:
        bad1 = _make_response("not json")
        bad2 = _make_response("still not json")
        gw = _make_gateway(bad1, bad2)
        svc = StructuredOutputService(gw, max_retries=1)

        with pytest.raises(StructuredOutputError) as exc_info:
            await svc.generate(
                system_prompt="Extract.",
                user_prompt="Input",
                output_schema=SimpleOutput,
            )

        assert "SimpleOutput" in str(exc_info.value)
        assert exc_info.value.raw_response == "still not json"
        assert len(exc_info.value.validation_errors) > 0

    @pytest.mark.asyncio
    async def test_retry_prompt_contains_errors(self) -> None:
        bad_response = _make_response(json.dumps({"title": "Bad", "score": 5.0}))
        good_response = _make_response(json.dumps({"title": "OK", "score": 0.5}))
        gw = _make_gateway(bad_response, good_response)
        svc = StructuredOutputService(gw)

        await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input",
            output_schema=SimpleOutput,
        )

        # Verify the retry request mentions validation errors
        retry_call = gw.generate.call_args_list[1]
        retry_request = retry_call[0][0]
        assert "Validierungsfehler" in retry_request.user_prompt


# ------------------------------------------------------------------
# Schema injection tests
# ------------------------------------------------------------------


class TestSchemaInjection:
    """Tests that JSON schema is properly injected into system prompt."""

    @pytest.mark.asyncio
    async def test_system_prompt_contains_schema(self) -> None:
        content = json.dumps({"title": "Test", "score": 0.5})
        gw = _make_gateway(_make_response(content))
        svc = StructuredOutputService(gw)

        await svc.generate(
            system_prompt="Extract data.",
            user_prompt="Input",
            output_schema=SimpleOutput,
        )

        call_request = gw.generate.call_args_list[0][0][0]
        assert "JSON-Schema" in call_request.system_prompt
        assert "title" in call_request.system_prompt
        assert "score" in call_request.system_prompt
        assert call_request.json_mode is True

    @pytest.mark.asyncio
    async def test_temperature_and_max_tokens_forwarded(self) -> None:
        content = json.dumps({"title": "T", "score": 0.1})
        gw = _make_gateway(_make_response(content))
        svc = StructuredOutputService(gw)

        await svc.generate(
            system_prompt="Extract.",
            user_prompt="Input",
            output_schema=SimpleOutput,
            temperature=0.7,
            max_tokens=500,
        )

        call_request = gw.generate.call_args_list[0][0][0]
        assert call_request.temperature == 0.7
        assert call_request.max_tokens == 500


# ------------------------------------------------------------------
# Error reporting tests
# ------------------------------------------------------------------


class TestErrorReporting:
    """Tests for validation error details."""

    @pytest.mark.asyncio
    async def test_error_contains_raw_response(self) -> None:
        gw = _make_gateway(
            _make_response("garbage1"),
            _make_response("garbage2"),
        )
        svc = StructuredOutputService(gw, max_retries=1)

        with pytest.raises(StructuredOutputError) as exc_info:
            await svc.generate(
                system_prompt="Extract.",
                user_prompt="Input",
                output_schema=SimpleOutput,
            )

        assert exc_info.value.raw_response == "garbage2"

    @pytest.mark.asyncio
    async def test_error_logs_validation_failure(self) -> None:
        bad = _make_response("not json")
        gw = _make_gateway(bad, bad)
        svc = StructuredOutputService(gw, max_retries=1)

        with (
            pytest.raises(StructuredOutputError),
            patch("pwbs.core.structured_output.logger") as mock_logger,
        ):
            await svc.generate(
                system_prompt="Extract.",
                user_prompt="Input",
                output_schema=SimpleOutput,
            )

        mock_logger.warning.assert_called()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Validierung fehlgeschlagen" in warning_msg
