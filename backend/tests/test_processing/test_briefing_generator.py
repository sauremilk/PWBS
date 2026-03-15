"""Tests for Briefing LLM-Call with Prompt Template (TASK-078)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.briefing.generator import (
    BriefingGenerator,
    BriefingGeneratorConfig,
    BriefingLLMResult,
    BriefingType,
)
from pwbs.core.grounding import Confidence, GroundedStatement, GroundingResult, SourceReference
from pwbs.core.llm_gateway import LLMProvider, LLMResponse, LLMUsage

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()

MOCK_USAGE = LLMUsage(
    provider=LLMProvider.CLAUDE,
    model="claude-sonnet-4-20250514",
    input_tokens=500,
    output_tokens=300,
    duration_ms=1200.0,
    estimated_cost_usd=0.005,
)


def _make_template(
    template_id: str = "briefing_morning.v1",
    use_case: str = "briefing_morning",
    system_prompt: str = "Du bist ein Briefing-Assistent.",
    template_body: str = "## Briefing\n{{ date }}\n{% for e in calendar_events %}{{ e.title }}\n{% endfor %}",
    required_context: list[str] | None = None,
    temperature: float = 0.3,
    max_output_tokens: int = 2000,
) -> MagicMock:
    tpl = MagicMock()
    tpl.id = template_id
    tpl.system_prompt = system_prompt
    tpl.template = template_body
    tpl.required_context = required_context or ["date", "calendar_events", "recent_documents"]
    tpl.temperature = temperature
    tpl.max_output_tokens = max_output_tokens
    return tpl


def _make_registry(template: MagicMock | None = None) -> MagicMock:
    tpl = template or _make_template()
    registry = MagicMock()
    registry.get.return_value = tpl
    registry.render.return_value = "## Briefing\n2026-03-14\nSprint Planning\n"
    return registry


def _make_gateway(
    content: str = "# Fakten\n\nDie Planung wurde besprochen. [Quelle: Sprint Notes, 2026-03-14]",
) -> AsyncMock:
    gw = AsyncMock()
    gw.generate = AsyncMock(
        return_value=LLMResponse(
            content=content,
            usage=MOCK_USAGE,
            provider=LLMProvider.CLAUDE,
            model="claude-sonnet-4-20250514",
        )
    )
    return gw


def _make_context() -> dict[str, Any]:
    return {
        "date": "2026-03-14",
        "calendar_events": [{"title": "Sprint Planning", "time": "10:00"}],
        "recent_documents": [{"title": "Sprint Notes", "source": "notion", "date": "2026-03-13"}],
    }


# ------------------------------------------------------------------
# Basic generation
# ------------------------------------------------------------------


class TestBriefingGenerator:
    @pytest.mark.asyncio
    async def test_generates_morning_briefing(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
        )

        assert isinstance(result, BriefingLLMResult)
        assert result.briefing_type == BriefingType.MORNING
        assert result.content != ""
        assert result.template_id == "briefing_morning.v1"

    @pytest.mark.asyncio
    async def test_template_loaded_for_type(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)
        registry.get.assert_called_once_with("briefing_morning")

    @pytest.mark.asyncio
    async def test_meeting_prep_uses_correct_template(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MEETING_PREP, _make_context(), USER_ID)
        registry.get.assert_called_once_with("briefing_meeting_prep")

    @pytest.mark.asyncio
    async def test_context_rendered_into_template(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        ctx = _make_context()
        await gen.generate(BriefingType.MORNING, ctx, USER_ID)

        registry.render.assert_called_once()
        call_args = registry.render.call_args[0]
        assert call_args[1] is ctx


# ------------------------------------------------------------------
# LLM call
# ------------------------------------------------------------------


class TestLLMCall:
    @pytest.mark.asyncio
    async def test_llm_gateway_called(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)
        gateway.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_temperature_from_template(self) -> None:
        tpl = _make_template(temperature=0.3)
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert request.temperature == 0.3

    @pytest.mark.asyncio
    async def test_max_tokens_from_template(self) -> None:
        tpl = _make_template(max_output_tokens=2000)
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert request.max_tokens == 2000

    @pytest.mark.asyncio
    async def test_system_prompt_includes_grounding(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert (
            "bereitgestellten Quellen" in request.system_prompt.lower()
            or "grounding" in request.system_prompt.lower()
            or "Quelle" in request.system_prompt
        )

    @pytest.mark.asyncio
    async def test_system_prompt_includes_word_limit(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert "800" in request.system_prompt

    @pytest.mark.asyncio
    async def test_meeting_prep_word_limit(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.MEETING_PREP, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert "400" in request.system_prompt


# ------------------------------------------------------------------
# Grounding
# ------------------------------------------------------------------


class TestGrounding:
    @pytest.mark.asyncio
    async def test_grounding_analysis_with_sources(self) -> None:
        registry = _make_registry()
        content = "Das Meeting war produktiv. [Quelle: Sprint Notes, 2026-03-14]"
        gateway = _make_gateway(content=content)
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            known_sources=[{"title": "Sprint Notes"}],
        )

        assert result.grounding_result is not None
        assert result.grounding_result.valid_source_count >= 1

    @pytest.mark.asyncio
    async def test_no_grounding_without_sources(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            known_sources=None,
        )

        assert result.grounding_result is None

    @pytest.mark.asyncio
    async def test_grounding_disabled_in_config(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        config = BriefingGeneratorConfig(enable_grounding=False)
        gen = BriefingGenerator(gateway, registry, config)

        result = await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            known_sources=[{"title": "Test"}],
        )

        assert result.grounding_result is None

    @pytest.mark.asyncio
    async def test_grounding_disabled_no_augmentation(self) -> None:
        tpl = _make_template(system_prompt="Simple prompt.")
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        config = BriefingGeneratorConfig(enable_grounding=False)
        gen = BriefingGenerator(gateway, registry, config)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        # System prompt should NOT have grounding augmentation
        assert "bereitgestellten Quellen" not in request.system_prompt.lower()


# ------------------------------------------------------------------
# Result metadata
# ------------------------------------------------------------------


class TestResultMetadata:
    @pytest.mark.asyncio
    async def test_usage_from_llm(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        assert result.usage is not None
        assert result.usage.input_tokens == 500

    @pytest.mark.asyncio
    async def test_model_from_response(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        assert result.model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_generated_at_set(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        assert result.generated_at is not None
        assert result.generated_at.tzinfo is not None

    @pytest.mark.asyncio
    async def test_word_count_calculated(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway(content="eins zwei drei vier fuenf")
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        assert result.word_count == 5


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------


class TestConfig:
    def test_default_values(self) -> None:
        config = BriefingGeneratorConfig()
        assert config.default_temperature == 0.3
        assert config.morning_max_output_tokens == 2000
        assert config.meeting_max_output_tokens == 1000
        assert config.enable_grounding is True

    @pytest.mark.asyncio
    async def test_fallback_max_tokens_morning(self) -> None:
        tpl = _make_template(max_output_tokens=0)  # Falsy -> use config
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        config = BriefingGeneratorConfig(morning_max_output_tokens=3000)
        gen = BriefingGenerator(gateway, registry, config)

        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert request.max_tokens == 3000

    @pytest.mark.asyncio
    async def test_fallback_max_tokens_meeting(self) -> None:
        tpl = _make_template(max_output_tokens=0)
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        config = BriefingGeneratorConfig(meeting_max_output_tokens=1500)
        gen = BriefingGenerator(gateway, registry, config)

        await gen.generate(BriefingType.MEETING_PREP, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert request.max_tokens == 1500


# ------------------------------------------------------------------
# Vertical profile integration (TASK-154)
# ------------------------------------------------------------------


class TestVerticalProfileIntegration:
    @pytest.mark.asyncio
    async def test_researcher_supplement_in_system_prompt(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            vertical_profile="researcher",
        )

        request = gateway.generate.call_args[0][0]
        assert "Forscher" in request.system_prompt

    @pytest.mark.asyncio
    async def test_consultant_supplement_in_system_prompt(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            vertical_profile="consultant",
        )

        request = gateway.generate.call_args[0][0]
        assert "Berater" in request.system_prompt

    @pytest.mark.asyncio
    async def test_developer_supplement_in_system_prompt(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            vertical_profile="developer",
        )

        request = gateway.generate.call_args[0][0]
        assert "Software-Entwickler" in request.system_prompt

    @pytest.mark.asyncio
    async def test_general_profile_no_vertical_supplement(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            vertical_profile="general",
        )

        request = gateway.generate.call_args[0][0]
        # General profile has empty supplement, so no "Forscher"/"Berater"/"Entwickler"
        assert "Forscher" not in request.system_prompt
        assert "Berater" not in request.system_prompt
        assert "Software-Entwickler" not in request.system_prompt

    @pytest.mark.asyncio
    async def test_default_vertical_profile_is_general(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        # No vertical_profile arg -> defaults to "general"
        await gen.generate(BriefingType.MORNING, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert "Forscher" not in request.system_prompt

    @pytest.mark.asyncio
    async def test_unknown_vertical_fallback_to_general(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MORNING,
            _make_context(),
            USER_ID,
            vertical_profile="nonexistent",
        )

        request = gateway.generate.call_args[0][0]
        # Should not crash, should fall back to general
        assert "Forscher" not in request.system_prompt


# ------------------------------------------------------------------
# Quarterly briefing integration (TASK-155)
# ------------------------------------------------------------------


class TestQuarterlyBriefingIntegration:
    @pytest.mark.asyncio
    async def test_quarterly_uses_correct_template(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.QUARTERLY, _make_context(), USER_ID)
        registry.get.assert_called_once_with("briefing_quarterly")

    @pytest.mark.asyncio
    async def test_quarterly_word_limit_1500(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(BriefingType.QUARTERLY, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert "1500" in request.system_prompt

    @pytest.mark.asyncio
    async def test_quarterly_max_tokens_from_config(self) -> None:
        tpl = _make_template(max_output_tokens=0)
        registry = _make_registry(tpl)
        gateway = _make_gateway()
        config = BriefingGeneratorConfig(quarterly_max_output_tokens=5000)
        gen = BriefingGenerator(gateway, registry, config)

        await gen.generate(BriefingType.QUARTERLY, _make_context(), USER_ID)

        request = gateway.generate.call_args[0][0]
        assert request.max_tokens == 5000

    @pytest.mark.asyncio
    async def test_quarterly_result_type(self) -> None:
        registry = _make_registry()
        gateway = _make_gateway()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(BriefingType.QUARTERLY, _make_context(), USER_ID)

        assert result.briefing_type == BriefingType.QUARTERLY
