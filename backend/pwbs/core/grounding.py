"""Halluzinations-Mitigation mit Quellenreferenz-Pflicht (TASK-069).

Implements the grounding layer from D1 §3.4:

1. **Grounding Instruktion** – System-Prompt-Baustein, der das LLM zwingt,
   nur auf bereitgestellten Quellen basiert zu antworten.
2. **Quellenreferenzierung** – Parsen und Validieren von
   ``[Quelle: Titel, Datum]``-Annotationen im LLM-Output.
3. **Confidence Scoring** – ``high`` (direkte Quelle), ``medium`` (abgeleitet),
   ``low`` (keine direkte Quelle).
4. **Prompt-Struktur** – erzwingt Abschnitte: Fakten, Zusammenhänge, Empfehlungen.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "Confidence",
    "GroundingConfig",
    "GroundingService",
    "GroundedStatement",
    "GroundingResult",
    "SourceReference",
    "build_grounding_system_prompt",
    "build_structured_prompt",
]


# ------------------------------------------------------------------
# Enums & data types
# ------------------------------------------------------------------


class Confidence(str, Enum):
    """Confidence level for a grounded statement."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class SourceReference:
    """A parsed ``[Quelle: Titel, Datum]`` reference from LLM output."""

    title: str
    date: str
    raw: str  # the original matched string


@dataclass(frozen=True, slots=True)
class GroundedStatement:
    """A single statement from LLM output with confidence metadata."""

    text: str
    sources: list[SourceReference]
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class GroundingResult:
    """Result of grounding analysis on LLM output."""

    statements: list[GroundedStatement]
    valid_source_count: int
    invalid_source_count: int
    cleaned_text: str


@dataclass(frozen=True, slots=True)
class GroundingConfig:
    """Configuration for the grounding service."""

    remove_invalid_refs: bool = True
    mark_low_confidence: bool = True
    low_confidence_marker: str = " ⚠️"


# ------------------------------------------------------------------
# Regex patterns
# ------------------------------------------------------------------

# Matches [Quelle: Some Title, 2026-03-14] or [Quelle: Title, März 2026] etc.
_SOURCE_REF_RE = re.compile(r"\[Quelle:\s*([^,\]]+),\s*([^\]]+)\]")

# Splits text into statements (sentences or bullet points)
_STATEMENT_SPLIT_RE = re.compile(r"(?:^|\n)\s*[-•*]\s+|(?<=[.!?])\s+(?=[A-ZÄÖÜ])")


# ------------------------------------------------------------------
# Prompt builders
# ------------------------------------------------------------------


GROUNDING_INSTRUCTION = (
    "WICHTIG: Antworte ausschließlich basierend auf den bereitgestellten Quellen. "
    "Verwende KEIN Vorwissen oder externe Informationen. "
    "Kennzeichne JEDE Aussage mit einer Quellenreferenz im Format "
    "[Quelle: Dokumenttitel, Datum]. "
    "Wenn du eine Information nicht aus den Quellen ableiten kannst, "
    "sage explizit: 'Hierzu liegen keine Quellen vor.' "
    "Trenne klar zwischen Fakten (direkt belegbar) und Interpretationen."
)

STRUCTURED_SECTIONS = (
    "Strukturiere deine Antwort in folgende Abschnitte:\n"
    "1. **Fakten** – Direkt aus den Quellen belegbare Aussagen.\n"
    "2. **Zusammenhänge** – Abgeleitete Verbindungen zwischen Fakten.\n"
    "3. **Empfehlungen** – Handlungsvorschläge basierend auf den Fakten."
)


def build_grounding_system_prompt(base_system_prompt: str) -> str:
    """Augment a system prompt with the grounding instruction.

    Prepends the grounding instruction to enforce source-based answers.
    """
    return f"{GROUNDING_INSTRUCTION}\n\n{base_system_prompt}"


def build_structured_prompt(
    user_prompt: str,
    sources: list[dict[str, Any]],
) -> str:
    """Build a user prompt that includes source context and structure enforcement.

    Parameters
    ----------
    user_prompt:
        The original user question or task.
    sources:
        List of source dicts with at least ``title``, ``date``, ``content`` keys.
    """
    source_block = "\n\n".join(
        f"### Quelle: {s.get('title', 'Unbekannt')} ({s.get('date', '?')})\n{s.get('content', '')}"
        for s in sources
    )

    return (
        f"## Bereitgestellte Quellen\n\n{source_block}\n\n"
        f"---\n\n"
        f"## Aufgabe\n\n{user_prompt}\n\n"
        f"---\n\n{STRUCTURED_SECTIONS}"
    )


# ------------------------------------------------------------------
# Grounding Service
# ------------------------------------------------------------------


class GroundingService:
    """Analyzes and validates LLM output for proper source grounding.

    Parameters
    ----------
    config:
        Grounding configuration. Uses defaults if not provided.
    known_sources:
        List of known source titles (for validation).
        Titles are normalized for fuzzy matching.
    """

    def __init__(
        self,
        config: GroundingConfig | None = None,
        known_sources: list[dict[str, str]] | None = None,
    ) -> None:
        self._config = config or GroundingConfig()
        self._known_titles: set[str] = set()
        if known_sources:
            for src in known_sources:
                title = src.get("title", "")
                self._known_titles.add(self._normalize_title(title))

    def analyze(self, llm_output: str) -> GroundingResult:
        """Analyze LLM output for source references and confidence.

        Returns a :class:`GroundingResult` with parsed statements,
        confidence scoring, and optionally cleaned text.
        """
        statements = self._split_statements(llm_output)
        grounded: list[GroundedStatement] = []
        valid_count = 0
        invalid_count = 0

        for stmt_text in statements:
            sources = self._extract_sources(stmt_text)
            valid_sources: list[SourceReference] = []
            invalid_sources: list[SourceReference] = []

            for src in sources:
                if self._is_valid_source(src):
                    valid_sources.append(src)
                    valid_count += 1
                else:
                    invalid_sources.append(src)
                    invalid_count += 1

            confidence = self._score_confidence(valid_sources, invalid_sources, stmt_text)

            grounded.append(
                GroundedStatement(
                    text=stmt_text,
                    sources=valid_sources,
                    confidence=confidence,
                )
            )

        cleaned = self._build_cleaned_text(grounded)

        return GroundingResult(
            statements=grounded,
            valid_source_count=valid_count,
            invalid_source_count=invalid_count,
            cleaned_text=cleaned,
        )

    def add_known_source(self, title: str) -> None:
        """Register an additional known source title for validation."""
        self._known_titles.add(self._normalize_title(title))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sources(text: str) -> list[SourceReference]:
        """Extract all ``[Quelle: ...]`` references from text."""
        refs: list[SourceReference] = []
        for match in _SOURCE_REF_RE.finditer(text):
            refs.append(
                SourceReference(
                    title=match.group(1).strip(),
                    date=match.group(2).strip(),
                    raw=match.group(0),
                )
            )
        return refs

    def _is_valid_source(self, ref: SourceReference) -> bool:
        """Check if a source reference matches a known source.

        If no known sources are configured, all refs are considered valid
        (validation deferred to later pipeline stages).
        """
        if not self._known_titles:
            return True

        normalized = self._normalize_title(ref.title)
        # Exact match
        if normalized in self._known_titles:
            return True

        # Fuzzy: check if the ref title is a substring of any known title
        # or if any known title is a substring of the ref title
        for known in self._known_titles:
            if normalized in known or known in normalized:
                return True

        return False

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize a title for fuzzy matching."""
        return title.strip().lower()

    @staticmethod
    def _score_confidence(
        valid_sources: list[SourceReference],
        invalid_sources: list[SourceReference],
        text: str,
    ) -> Confidence:
        """Score confidence level for a statement.

        - ``high``: at least one valid direct source reference
        - ``medium``: has source references but all invalid, or text indicates derivation
        - ``low``: no source references at all
        """
        if valid_sources:
            return Confidence.HIGH
        if invalid_sources:
            return Confidence.MEDIUM
        # Check if it's a structural element (heading, empty line)
        stripped = text.strip()
        if stripped.startswith("#") or stripped.startswith("---") or not stripped:
            return Confidence.HIGH  # structural elements don't need sources
        return Confidence.LOW

    def _build_cleaned_text(self, statements: list[GroundedStatement]) -> str:
        """Build cleaned output text.

        - Removes invalid source references if configured.
        - Marks low-confidence statements if configured.
        """
        parts: list[str] = []
        for stmt in statements:
            text = stmt.text

            if self._config.remove_invalid_refs:
                # Remove [Quelle: ...] refs that aren't in valid sources
                valid_raws = {s.raw for s in stmt.sources}
                for match in _SOURCE_REF_RE.finditer(text):
                    if match.group(0) not in valid_raws:
                        text = text.replace(match.group(0), "")

            if self._config.mark_low_confidence and stmt.confidence == Confidence.LOW:
                text = text.rstrip() + self._config.low_confidence_marker

            parts.append(text)

        return "\n".join(parts)

    @staticmethod
    def _split_statements(text: str) -> list[str]:
        """Split LLM output into individual statements.

        Preserves markdown structure (headings, bullet points) while
        splitting at sentence boundaries.
        """
        lines = text.split("\n")
        statements: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                statements.append("")
                continue

            # Headings and structural markers stay as-is
            if stripped.startswith("#") or stripped.startswith("---"):
                statements.append(line)
                continue

            # Bullet points
            if re.match(r"^\s*[-•*]\s+", line):
                statements.append(line)
                continue

            # Regular paragraph: split by sentence
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", stripped)
            statements.extend(sentences)

        return statements
