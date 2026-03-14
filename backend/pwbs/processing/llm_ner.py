"""LLM-basierte Entitätsextraktion mit Structured Output (TASK-062).

Second stage of the two-stage NER pipeline.  Uses the
`ENTITY_EXTRACTION_PROMPT` (D1 §3.2) with Structured Output
(JSON-Schema) via the :class:StructuredOutputService / Claude API.

Extracts: Persons, Projects, Topics, Decisions, Open Questions, Dates.

Only invoked for chunks not fully covered by the rule-based stage
(TASK-061).  Cost control: max 100 extraction calls per user/day
via :class:LLMRateLimiter (TASK-070).

Token budget (D1 §3.4):
  context_tokens = 2000, output_tokens = 1000, model = claude-haiku.

Confidence threshold: entities with confidence < 0.75 are dropped
(not written to the graph).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from pwbs.core.rate_limiter import LLMRateLimiter, RateLimitExceededError
from pwbs.core.structured_output import (
    StructuredOutputError,
    StructuredOutputResult,
    StructuredOutputService,
)
from pwbs.processing.ner import ExtractedEntity, ExtractedMention
from pwbs.schemas.enums import EntityType

logger = logging.getLogger(__name__)

__all__ = [
    "LLMEntityExtractor",
    "LLMExtractionConfig",
    "LLMExtractionResult",
    "ExtractionResponse",
]

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

_DEFAULT_CONFIDENCE_THRESHOLD = 0.75
_DEFAULT_MAX_TOKENS = 1000
_DEFAULT_TEMPERATURE = 0.1
_USE_CASE = "entity.extraction"


@dataclass(frozen=True, slots=True)
class LLMExtractionConfig:
    """Configuration for LLM-based entity extraction."""

    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD
    max_output_tokens: int = _DEFAULT_MAX_TOKENS
    temperature: float = _DEFAULT_TEMPERATURE
    use_case: str = _USE_CASE


# ------------------------------------------------------------------
# Pydantic response models (Structured Output schema)
# ------------------------------------------------------------------


class PersonEntity(BaseModel):
    """A person extracted by the LLM."""

    name: str
    role: str = ""
    context: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ProjectEntity(BaseModel):
    """A project extracted by the LLM."""

    name: str
    status: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class DecisionEntity(BaseModel):
    """A decision extracted by the LLM."""

    what: str
    by: str = ""
    date: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class TopicEntry(BaseModel):
    """A topic/theme extracted by the LLM."""

    name: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class OpenQuestion(BaseModel):
    """An open question extracted by the LLM."""

    text: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class DateReference(BaseModel):
    """A date/deadline reference extracted by the LLM."""

    description: str
    date: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ExtractionResponse(BaseModel):
    """Root schema for the LLM entity extraction response.

    Validated via StructuredOutputService against this schema.
    """

    persons: list[PersonEntity] = Field(default_factory=list)
    projects: list[ProjectEntity] = Field(default_factory=list)
    topics: list[TopicEntry] = Field(default_factory=list)
    decisions: list[DecisionEntity] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    dates: list[DateReference] = Field(default_factory=list)


# ------------------------------------------------------------------
# Result container
# ------------------------------------------------------------------


@dataclass(slots=True)
class LLMExtractionResult:
    """Result of a single LLM extraction call."""

    entities: list[ExtractedEntity] = field(default_factory=list)
    raw_response: str = ""
    filtered_count: int = 0
    rate_limited: bool = False
    error: str | None = None


# ------------------------------------------------------------------
# System Prompt (D1 §3.2)
# ------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Du bist ein NER-Extraktionssystem. Analysiere den bereitgestellten "
    "Text und extrahiere strukturiert alle genannten Entitäten.\n\n"
    "Regeln:\n"
    "- Extrahiere NUR Entitäten, die EXPLIZIT im Text genannt werden.\n"
    "- Erfinde KEINE Informationen.\n"
    "- Vergib einen confidence-Wert zwischen 0.0 und 1.0 für jede Entität.\n"
    "- confidence=1.0: Name wird explizit und eindeutig genannt.\n"
    "- confidence=0.8: Entität wird kontextuell klar referenziert.\n"
    "- confidence<0.7: Vage oder unsichere Referenz."
)

_USER_PROMPT_TEMPLATE = (
    "Analysiere den folgenden Text und extrahiere strukturiert:\n\n"
    "1. PERSONEN: Name, Rolle (falls erkennbar), Kontext\n"
    "2. PROJEKTE: Name, Status (falls erkennbar)\n"
    "3. THEMEN: Schlüsselthemen und -konzepte\n"
    "4. ENTSCHEIDUNGEN: Was wurde entschieden, von wem, wann\n"
    "5. OFFENE FRAGEN: Unbeantwortete Fragen oder ausstehende Klärungen\n"
    "6. TERMINE: Referenzierte Daten oder Deadlines\n\n"
    "TEXT:\n{chunk_text}"
)


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class LLMEntityExtractor:
    """LLM-based entity extraction (second NER stage).

    Parameters
    ----------
    structured_output:
        Service for validated LLM calls.
    rate_limiter:
        Per-user rate limiter (optional; skipped if None).
    config:
        Extraction configuration.
    """

    def __init__(
        self,
        structured_output: StructuredOutputService,
        rate_limiter: LLMRateLimiter | None = None,
        config: LLMExtractionConfig | None = None,
    ) -> None:
        self._structured = structured_output
        self._limiter = rate_limiter
        self._config = config or LLMExtractionConfig()

    @property
    def config(self) -> LLMExtractionConfig:
        return self._config

    async def extract(
        self,
        chunk_text: str,
        user_id: uuid.UUID,
        chunk_id: uuid.UUID | None = None,
    ) -> LLMExtractionResult:
        """Extract entities from *chunk_text* via LLM.

        Parameters
        ----------
        chunk_text:
            The text chunk to analyze.
        user_id:
            Owner ID for rate limiting.
        chunk_id:
            Optional chunk reference for logging.

        Returns
        -------
        LLMExtractionResult
            Extracted entities (above confidence threshold),
            or an empty result if rate-limited / failed.
        """
        if not chunk_text or not chunk_text.strip():
            return LLMExtractionResult()

        # --- Rate limit check ---
        if self._limiter is not None:
            try:
                await self._limiter.check_limits(
                    user_id=user_id,
                    use_case=self._config.use_case,
                    input_tokens=len(chunk_text.split()),
                )
            except RateLimitExceededError as exc:
                logger.warning(
                    "Rate limit exceeded for user %s: %s",
                    user_id,
                    exc.reason,
                )
                return LLMExtractionResult(rate_limited=True, error=exc.reason)

        # --- LLM call ---
        user_prompt = _USER_PROMPT_TEMPLATE.format(chunk_text=chunk_text)

        try:
            result: StructuredOutputResult[ExtractionResponse] = await self._structured.generate(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=ExtractionResponse,
                temperature=self._config.temperature,
                max_tokens=self._config.max_output_tokens,
            )
        except StructuredOutputError as exc:
            logger.error(
                "LLM entity extraction failed for chunk %s: %s",
                chunk_id,
                exc,
            )
            return LLMExtractionResult(
                raw_response=exc.raw_response,
                error=str(exc),
            )

        # --- Record usage ---
        if self._limiter is not None:
            try:
                await self._limiter.record_usage(
                    user_id=user_id,
                    use_case=self._config.use_case,
                    model=result.usage.model,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    estimated_cost_usd=result.usage.estimated_cost_usd,
                )
            except Exception as exc:
                logger.warning("Failed to record usage: %s", exc)

        # --- Convert to ExtractedEntity list ---
        response = result.parsed
        entities = self._convert_response(response)

        # --- Filter by confidence threshold ---
        all_count = len(entities)
        entities = [
            e
            for e in entities
            if any(m.confidence >= self._config.confidence_threshold for m in e.mentions)
        ]
        filtered_count = all_count - len(entities)

        if filtered_count:
            logger.info(
                "Filtered %d entities below confidence %.2f for chunk %s",
                filtered_count,
                self._config.confidence_threshold,
                chunk_id,
            )

        return LLMExtractionResult(
            entities=entities,
            raw_response=result.raw,
            filtered_count=filtered_count,
        )

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_response(response: ExtractionResponse) -> list[ExtractedEntity]:
        """Convert LLM structured output to ExtractedEntity list."""
        entities: list[ExtractedEntity] = []

        # Persons
        for p in response.persons:
            name = p.name.strip()
            if not name:
                continue
            metadata: dict[str, Any] = {}
            if p.role:
                metadata["role"] = p.role
            if p.context:
                metadata["context"] = p.context
            entities.append(
                ExtractedEntity(
                    entity_type=EntityType.PERSON,
                    name=name,
                    normalized_name=_normalize(name),
                    mentions=[
                        ExtractedMention(
                            entity_name=name,
                            entity_type=EntityType.PERSON,
                            normalized_name=_normalize(name),
                            confidence=p.confidence,
                            extraction_method="llm",
                            source_pattern="llm_extraction",
                        ),
                    ],
                    metadata=metadata,
                ),
            )

        # Projects
        for proj in response.projects:
            name = proj.name.strip()
            if not name:
                continue
            metadata = {}
            if proj.status:
                metadata["status"] = proj.status
            entities.append(
                ExtractedEntity(
                    entity_type=EntityType.PROJECT,
                    name=name,
                    normalized_name=_normalize(name),
                    mentions=[
                        ExtractedMention(
                            entity_name=name,
                            entity_type=EntityType.PROJECT,
                            normalized_name=_normalize(name),
                            confidence=proj.confidence,
                            extraction_method="llm",
                            source_pattern="llm_extraction",
                        ),
                    ],
                    metadata=metadata,
                ),
            )

        # Topics
        for topic in response.topics:
            name = topic.name.strip()
            if not name:
                continue
            entities.append(
                ExtractedEntity(
                    entity_type=EntityType.TOPIC,
                    name=name,
                    normalized_name=_normalize(name),
                    mentions=[
                        ExtractedMention(
                            entity_name=name,
                            entity_type=EntityType.TOPIC,
                            normalized_name=_normalize(name),
                            confidence=topic.confidence,
                            extraction_method="llm",
                            source_pattern="llm_extraction",
                        ),
                    ],
                ),
            )

        # Decisions
        for dec in response.decisions:
            desc = dec.what.strip()
            if not desc:
                continue
            metadata = {}
            if dec.by:
                metadata["decided_by"] = dec.by
            if dec.date:
                metadata["decision_date"] = dec.date
            entities.append(
                ExtractedEntity(
                    entity_type=EntityType.DECISION,
                    name=desc,
                    normalized_name=_normalize(desc),
                    mentions=[
                        ExtractedMention(
                            entity_name=desc,
                            entity_type=EntityType.DECISION,
                            normalized_name=_normalize(desc),
                            confidence=dec.confidence,
                            extraction_method="llm",
                            source_pattern="llm_extraction",
                        ),
                    ],
                    metadata=metadata,
                ),
            )

        # Open questions -> Topic entities (no dedicated type)
        for q in response.open_questions:
            text = q.text.strip()
            if not text:
                continue
            entities.append(
                ExtractedEntity(
                    entity_type=EntityType.TOPIC,
                    name=text,
                    normalized_name=_normalize(text),
                    mentions=[
                        ExtractedMention(
                            entity_name=text,
                            entity_type=EntityType.TOPIC,
                            normalized_name=_normalize(text),
                            confidence=q.confidence,
                            extraction_method="llm",
                            source_pattern="llm_open_question",
                        ),
                    ],
                    metadata={"kind": "open_question"},
                ),
            )

        # Dates -> Topic entities (no dedicated date type in MVP)
        for d in response.dates:
            desc = d.description.strip()
            if not desc:
                continue
            metadata = {}
            if d.date:
                metadata["date"] = d.date
            entities.append(
                ExtractedEntity(
                    entity_type=EntityType.TOPIC,
                    name=desc,
                    normalized_name=_normalize(desc),
                    mentions=[
                        ExtractedMention(
                            entity_name=desc,
                            entity_type=EntityType.TOPIC,
                            normalized_name=_normalize(desc),
                            confidence=d.confidence,
                            extraction_method="llm",
                            source_pattern="llm_date_reference",
                        ),
                    ],
                    metadata=metadata,
                ),
            )

        return entities


def _normalize(text: str) -> str:
    """Normalize entity name: lowercase + collapse whitespace."""
    return " ".join(text.lower().split())
