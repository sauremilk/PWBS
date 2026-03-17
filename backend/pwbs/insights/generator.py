"""Proactive Insight Generator (TASK-158).

Detects patterns via Knowledge Graph analysis and generates
human-readable insights via LLM. Respects per-user opt-in preferences
and feedback history.

Architecture:
  PatternRecognitionService → detected patterns
  → filter by user prefs + feedback history
  → LLM formulation (temperature 0.3)
  → persist to proactive_insights table
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pwbs.core.llm_gateway import LLMGateway, LLMRequest, LLMResponse
from pwbs.graph.pattern_recognition import (
    DetectedPattern,
    PatternRecognitionService,
    PatternType,
)

logger = logging.getLogger(__name__)

__all__ = [
    "InsightCategory",
    "InsightGeneratorConfig",
    "InsightResult",
    "ProactiveInsightGenerator",
    "SourceRef",
]

# ── Category mapping ──────────────────────────────────────────────────

PATTERN_TO_CATEGORY: dict[PatternType, str] = {
    PatternType.CHANGING_ASSUMPTION: "contradictions",
    PatternType.RECURRING_THEME: "forgotten_topics",
    PatternType.UNRESOLVED_QUESTION: "trends",
}

VALID_CATEGORIES: frozenset[str] = frozenset({"contradictions", "forgotten_topics", "trends"})


# ── Data types ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SourceRef:
    """A source reference attached to a generated insight."""

    document_id: str
    title: str
    source_type: str
    date: str


@dataclass(frozen=True, slots=True)
class InsightResult:
    """A single generated insight ready for persistence."""

    category: str
    title: str
    content: str
    sources: list[SourceRef]
    pattern_data: dict[str, Any]


class InsightCategory:
    """Constants for insight categories."""

    CONTRADICTIONS = "contradictions"
    FORGOTTEN_TOPICS = "forgotten_topics"
    TRENDS = "trends"


# ── Configuration ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class InsightGeneratorConfig:
    """Configuration for the proactive insight generator.

    Attributes
    ----------
    max_insights_per_run:
        Maximum insights to generate per user per run.
    llm_temperature:
        LLM temperature for insight formulation (sachlich).
    llm_max_tokens:
        Maximum output tokens per LLM call.
    min_pattern_context_count:
        Minimum context count for a pattern to be considered.
    exclude_recently_rated_days:
        Suppress patterns the user rated 'not_helpful' within N days.
    """

    max_insights_per_run: int = 3
    llm_temperature: float = 0.3
    llm_max_tokens: int = 512
    min_pattern_context_count: int = 2
    exclude_recently_rated_days: int = 30


# ── System prompt ─────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Du bist ein proaktiver Wissensassistent im PWBS (Persönliches Wissens-Betriebssystem).
Deine Aufgabe: Formuliere aus erkannten Mustern im Knowledge Graph des Nutzers
kurze, handlungsrelevante Insights.

Regeln:
- Schreibe auf Deutsch, sachlich und präzise.
- Jeder Insight hat einen Titel (max 80 Zeichen) und einen Inhalt (max 200 Wörter).
- Verweise auf die genannten Quellendokumente mit [Quelle: Titel, Datum].
- Verwende KEIN Vorwissen – nur die bereitgestellten Muster und Quellen.
- Formuliere eine konkrete Handlungsempfehlung oder Frage am Ende.

Antworte als JSON-Array:
[{"title": "...", "content": "..."}]
"""


# ── Generator ─────────────────────────────────────────────────────────


class ProactiveInsightGenerator:
    """Generates proactive insights from Knowledge Graph patterns.

    Parameters
    ----------
    pattern_service:
        Service for detecting patterns in the Knowledge Graph.
    llm_gateway:
        LLM Gateway for natural language formulation.
    config:
        Generator configuration.
    """

    def __init__(
        self,
        pattern_service: PatternRecognitionService,
        llm_gateway: LLMGateway,
        config: InsightGeneratorConfig | None = None,
    ) -> None:
        self._patterns = pattern_service
        self._llm = llm_gateway
        self._config = config or InsightGeneratorConfig()

    async def generate(
        self,
        owner_id: UUID,
        enabled_categories: list[str] | None = None,
        max_insights: int | None = None,
        negative_entity_ids: frozenset[str] | None = None,
    ) -> list[InsightResult]:
        """Generate proactive insights for a user.

        Parameters
        ----------
        owner_id:
            The user to generate insights for.
        enabled_categories:
            Which categories to generate. None = all.
        max_insights:
            Override for max insights per run.
        negative_entity_ids:
            Entity IDs the user previously rated 'not_helpful' – these
            patterns will be suppressed.

        Returns
        -------
        list[InsightResult]
            Generated insights with source references.
        """
        cap = max_insights or self._config.max_insights_per_run
        cats: set[str] = (
            set(enabled_categories) & VALID_CATEGORIES
            if enabled_categories
            else set(VALID_CATEGORIES)
        )
        negatives = negative_entity_ids or frozenset()

        # 1. Detect patterns from Knowledge Graph
        all_patterns = await self._patterns.detect_all_patterns(owner_id)

        # 2. Filter by category + feedback + minimum context
        filtered = self._filter_patterns(all_patterns, cats, negatives)

        if not filtered:
            logger.info(
                "No actionable patterns for owner_id=%s (cats=%s)",
                owner_id,
                cats,
            )
            return []

        # 3. Take top N patterns (already sorted by context_count)
        selected = filtered[:cap]

        # 4. Formulate via LLM
        insights = await self._formulate(selected)
        return insights

    def _filter_patterns(
        self,
        patterns: list[DetectedPattern],
        enabled_cats: set[str],
        negative_ids: frozenset[str],
    ) -> list[DetectedPattern]:
        """Filter patterns by category, feedback, and minimum context."""
        result: list[DetectedPattern] = []
        for p in patterns:
            cat = PATTERN_TO_CATEGORY.get(p.pattern_type)
            if cat is None or cat not in enabled_cats:
                continue
            if p.context_count < self._config.min_pattern_context_count:
                continue
            if p.entity_id in negative_ids:
                continue
            result.append(p)
        return result

    async def _formulate(
        self,
        patterns: list[DetectedPattern],
    ) -> list[InsightResult]:
        """Use LLM to formulate human-readable insights from patterns."""
        if not patterns:
            return []

        user_prompt = self._build_user_prompt(patterns)

        request = LLMRequest(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=self._config.llm_temperature,
            max_tokens=self._config.llm_max_tokens,
            json_mode=True,
        )

        response: LLMResponse = await self._llm.generate(request)

        return self._parse_response(response.content, patterns)

    @staticmethod
    def _build_user_prompt(patterns: list[DetectedPattern]) -> str:
        """Build the user prompt from detected patterns."""
        lines: list[str] = ["Formuliere Insights aus folgenden erkannten Mustern:\n"]
        for i, p in enumerate(patterns, 1):
            cat = PATTERN_TO_CATEGORY.get(p.pattern_type, "unknown")
            source_strs = [f"  - {s.title} ({s.source_type}, {s.date})" for s in p.sources]
            sources_block = "\n".join(source_strs) if source_strs else "  (keine Quellen)"
            lines.append(
                f"Muster {i} [{cat}]: {p.summary}\n"
                f"  Entity: {p.entity_name}\n"
                f"  Kontexte: {p.context_count}\n"
                f"  Zeitraum: {p.first_seen} – {p.last_seen}\n"
                f"  Quellen:\n{sources_block}\n"
            )
        return "\n".join(lines)

    @staticmethod
    def _parse_response(
        content: str,
        patterns: list[DetectedPattern],
    ) -> list[InsightResult]:
        """Parse LLM JSON response into InsightResult objects."""
        try:
            items = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            logger.warning("LLM returned non-JSON for insights: %s", content[:200])
            return []

        if not isinstance(items, list):
            items = [items]

        results: list[InsightResult] = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            body = str(item.get("content", "")).strip()
            if not title or not body:
                continue

            # Map back to the pattern that generated this insight
            pattern = patterns[idx] if idx < len(patterns) else None
            category = (
                PATTERN_TO_CATEGORY.get(pattern.pattern_type, "trends") if pattern else "trends"
            )
            sources = (
                [
                    SourceRef(
                        document_id=s.document_id,
                        title=s.title,
                        source_type=s.source_type,
                        date=s.date,
                    )
                    for s in pattern.sources
                ]
                if pattern
                else []
            )
            pattern_data = (
                {
                    "pattern_type": pattern.pattern_type.value,
                    "entity_id": pattern.entity_id,
                    "entity_name": pattern.entity_name,
                    "context_count": pattern.context_count,
                }
                if pattern
                else {}
            )

            results.append(
                InsightResult(
                    category=category,
                    title=title,
                    content=body,
                    sources=sources,
                    pattern_data=pattern_data,
                )
            )

        return results
