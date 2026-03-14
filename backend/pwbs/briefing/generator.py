"""Briefing LLM-Call mit Prompt-Template und strukturiertem Output (TASK-078).

Implements the briefing generation pipeline:
1. Load prompt template from PromptRegistry
2. Render context into Jinja2 template
3. Send to LLM Gateway with grounding instructions
4. Parse structured Markdown output with source annotations

D1 Section 3.4 / 3.5, D4 F-017 / F-018.
Temperature: 0.3 for factual content.
Token budgets: Morning (context: 8000, output: 2000), Meeting Prep (context: 6000, output: 1000).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pwbs.core.grounding import (
    GroundingResult,
    GroundingService,
    build_grounding_system_prompt,
)
from pwbs.core.llm_gateway import LLMGateway, LLMRequest, LLMResponse, LLMUsage
from pwbs.prompts.registry import PromptRegistry, PromptTemplate

logger = logging.getLogger(__name__)

__all__ = [
    "BriefingGenerator",
    "BriefingGeneratorConfig",
    "BriefingLLMResult",
    "BriefingType",
]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


class BriefingType(str, Enum):
    """Types of briefings that can be generated."""

    MORNING = "morning"
    MEETING_PREP = "meeting_prep"
    PROJECT = "project"
    WEEKLY = "weekly"


# Template use_case mapping for each briefing type
_TEMPLATE_USE_CASES: dict[BriefingType, str] = {
    BriefingType.MORNING: "briefing_morning",
    BriefingType.MEETING_PREP: "briefing_meeting_prep",
    BriefingType.PROJECT: "briefing_project",
    BriefingType.WEEKLY: "briefing_weekly",
}

# Max words per briefing type (D4 F-017, F-018)
_MAX_WORDS: dict[BriefingType, int] = {
    BriefingType.MORNING: 800,
    BriefingType.MEETING_PREP: 400,
    BriefingType.PROJECT: 1200,
    BriefingType.WEEKLY: 600,
}


@dataclass(frozen=True, slots=True)
class BriefingGeneratorConfig:
    """Configuration for the briefing generator."""

    default_temperature: float = 0.3
    morning_max_output_tokens: int = 2000
    meeting_max_output_tokens: int = 1000
    project_max_output_tokens: int = 3000
    weekly_max_output_tokens: int = 1500
    enable_grounding: bool = True


# ------------------------------------------------------------------
# Result
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BriefingLLMResult:
    """Result of a briefing LLM generation call."""

    content: str
    briefing_type: BriefingType
    grounding_result: GroundingResult | None
    usage: LLMUsage | None
    model: str
    template_id: str
    generated_at: datetime
    word_count: int


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class BriefingGenerator:
    """Generates briefings via LLM using prompt templates and grounding.

    Orchestrates:
    1. Template loading from PromptRegistry
    2. Context rendering via Jinja2
    3. Grounding system prompt augmentation
    4. LLM Gateway call
    5. Grounding analysis of the output

    Parameters
    ----------
    llm_gateway:
        LLM Gateway for API calls.
    prompt_registry:
        Registry for loading versioned prompt templates.
    config:
        Generator configuration.
    """

    def __init__(
        self,
        llm_gateway: LLMGateway,
        prompt_registry: PromptRegistry,
        config: BriefingGeneratorConfig | None = None,
    ) -> None:
        self._llm = llm_gateway
        self._registry = prompt_registry
        self._config = config or BriefingGeneratorConfig()

    async def generate(
        self,
        briefing_type: BriefingType,
        context: dict[str, Any],
        user_id: uuid.UUID,
        known_sources: list[dict[str, str]] | None = None,
    ) -> BriefingLLMResult:
        """Generate a briefing via LLM.

        Parameters
        ----------
        briefing_type:
            Type of briefing (morning or meeting_prep).
        context:
            Template context variables (calendar_events, recent_documents, etc.).
        user_id:
            Owner ID for logging/audit.
        known_sources:
            List of known source dicts for grounding validation.

        Returns
        -------
        BriefingLLMResult
            The generated briefing with grounding analysis.
        """
        # Step 1: Load template
        use_case = _TEMPLATE_USE_CASES[briefing_type]
        template = self._registry.get(use_case)

        # Step 2: Render prompt
        rendered_prompt = self._registry.render(template, context)

        # Step 3: Build system prompt with grounding instructions
        system_prompt = template.system_prompt
        if self._config.enable_grounding:
            system_prompt = build_grounding_system_prompt(system_prompt)

        # Add word limit instruction
        max_words = _MAX_WORDS.get(briefing_type, 800)
        system_prompt += f"\n\nMaximale Wortanzahl: {max_words}."

        # Step 4: LLM call
        max_tokens = self._get_max_output_tokens(briefing_type, template)
        temperature = template.temperature or self._config.default_temperature

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=rendered_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(
            "Generating %s briefing for user=%s with template=%s",
            briefing_type.value,
            user_id,
            template.id,
        )

        response: LLMResponse = await self._llm.generate(request)

        # Step 5: Grounding analysis
        grounding_result: GroundingResult | None = None
        if self._config.enable_grounding and known_sources:
            grounding_svc = GroundingService(known_sources=known_sources)
            grounding_result = grounding_svc.analyze(response.content)

        word_count = len(response.content.split())

        if word_count > max_words:
            logger.warning(
                "Briefing %s exceeds word limit: %d > %d",
                briefing_type.value,
                word_count,
                max_words,
            )

        return BriefingLLMResult(
            content=response.content,
            briefing_type=briefing_type,
            grounding_result=grounding_result,
            usage=response.usage,
            model=response.model,
            template_id=template.id,
            generated_at=datetime.now(timezone.utc),
            word_count=word_count,
        )

    def _get_max_output_tokens(
        self,
        briefing_type: BriefingType,
        template: PromptTemplate,
    ) -> int:
        """Determine max output tokens for the briefing type."""
        # Template setting takes precedence if set
        if template.max_output_tokens:
            return template.max_output_tokens

        if briefing_type == BriefingType.MORNING:
            return self._config.morning_max_output_tokens
        if briefing_type == BriefingType.PROJECT:
            return self._config.project_max_output_tokens
        if briefing_type == BriefingType.WEEKLY:
            return self._config.weekly_max_output_tokens
        return self._config.meeting_max_output_tokens
