"""Rule-based Named Entity Recognition for the PWBS Processing Pipeline (TASK-061).

First stage of the NER pipeline. Extracts entities from document
chunks using deterministic regex patterns:

- **E-Mail addresses** -> Person entities
- **@-Mentions** -> Person entities
- **Calendar participants** (from metadata `participants` field) -> Person entities
- **Notion links** (from metadata) -> diverse entities
- **Dates / deadlines** -> Date entities (ADR-017)
- **Decisions** -> Decision entities (ADR-017)
- **Open questions** -> OpenQuestion entities (ADR-017)
- **Goals** -> Goal entities (ADR-017)
- **Risks** -> Risk entities (ADR-017)

All rule-based extractions carry ``confidence=1.0`` for exact structural
matches and ``confidence=0.85`` for keyword heuristics.
``extraction_method='rule'`` throughout.

D1 Section 3.2, AGENTS.md ProcessingAgent, ADR-017.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pwbs.schemas.enums import EntityType

__all__ = [
    "ExtractedEntity",
    "ExtractedMention",
    "NERConfig",
    "RuleBasedNER",
]


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# RFC 5322 simplified  covers the vast majority of real-world addresses.
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

# @-mentions: @username or @First.Last (no spaces).
_AT_MENTION_RE = re.compile(
    r"(?<!\w)@([a-zA-Z][a-zA-Z0-9._\-]{0,63})",
)

# ---------------------------------------------------------------------------
# Date / deadline patterns (ADR-017)
# ---------------------------------------------------------------------------

# ISO dates: 2026-03-16, 16.03.2026, 03/16/2026
_ISO_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2})\b"
    r"|\b(\d{1,2}\.\d{1,2}\.\d{4})\b"
    r"|\b(\d{1,2}/\d{1,2}/\d{4})\b",
)

# Deadline keywords (DE + EN) followed by a date-like or day reference.
_DEADLINE_RE = re.compile(
    r"(?:deadline|frist|bis zum|bis|due by|due|faellig|fällig)"
    r"\s*:?\s*"
    r"(\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\.\d{1,2}\.\d{4}"
    r"|(?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag"
    r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|morgen|tomorrow|heute|today"
    r"|next\s+week|nächste\s+woche|naechste\s+woche"
    r"|end\s+of\s+(?:week|month|quarter|year)"
    r"|ende\s+(?:der\s+woche|des\s+monats|des\s+quartals|des\s+jahres))"
    r")",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Decision patterns (ADR-017)
# ---------------------------------------------------------------------------

_DECISION_RE = re.compile(
    r"(?:"
    r"(?:entscheidung|beschluss|decision|action\s*item|ergebnis)\s*:\s*(.{5,120})"
    r"|(?:wir\s+haben\s+(?:uns\s+)?entschieden|we\s+(?:have\s+)?decided|decision\s+was\s+made)\s*[,:.]?\s*(.{5,120})"
    r")",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Open-question patterns (ADR-017)
# ---------------------------------------------------------------------------

_OPEN_QUESTION_RE = re.compile(
    r"(?:"
    r"(?:offene\s+frage|open\s+question|ungeklaert|ungeklärt"
    r"|noch\s+zu\s+(?:klaeren|klären)"
    r"|to\s+be\s+determined|tbd|open\s+item|ausstehend)\s*:?\s*(.{5,200})"
    r")",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Goal patterns (ADR-017)
# ---------------------------------------------------------------------------

_GOAL_RE = re.compile(
    r"(?:ziel|goal|objective|milestone|target)\s*:\s*(.{5,200})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Risk patterns (ADR-017)
# ---------------------------------------------------------------------------

_RISK_RE = re.compile(
    r"(?:risiko|risk|gefahr|blocker)\s*:\s*(.{5,200})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NERConfig:
    """Configuration for the rule-based NER extractor."""

    extract_emails: bool = True
    extract_mentions: bool = True
    extract_participants: bool = True
    extract_notion_links: bool = True
    extract_dates: bool = True
    extract_decisions: bool = True
    extract_questions: bool = True
    extract_goals: bool = True
    extract_risks: bool = True


@dataclass(frozen=True, slots=True)
class ExtractedMention:
    """A single mention of an entity in a chunk."""

    entity_name: str
    entity_type: EntityType
    normalized_name: str
    confidence: float = 1.0
    extraction_method: str = "rule"
    source_pattern: str = ""


@dataclass(slots=True)
class ExtractedEntity:
    """Aggregated entity with all its mentions from one extraction run."""

    entity_type: EntityType
    name: str
    normalized_name: str
    mentions: list[ExtractedMention] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RuleBasedNER:
    """Extracts entities from text and metadata using deterministic rules.

    Parameters
    ----------
    config:
        Optional NER configuration.
    """

    def __init__(self, config: NERConfig | None = None) -> None:
        self._config = config or NERConfig()

    @property
    def config(self) -> NERConfig:
        return self._config

    def extract(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[ExtractedEntity]:
        """Extract entities from *content* and optional *metadata*.

        Parameters
        ----------
        content:
            The text content to scan.
        metadata:
            Source-specific metadata dict.  Supported keys:
            - `participants`: list of dicts with `email` and/or `name`
            - `notion_links`: list of dicts with `title` and optionally `type`

        Returns
        -------
        list[ExtractedEntity]
            Deduplicated entities with their mentions.
        """
        metadata = metadata or {}
        mentions: list[ExtractedMention] = []

        if self._config.extract_emails:
            mentions.extend(self._extract_emails(content))

        if self._config.extract_mentions:
            mentions.extend(self._extract_at_mentions(content))

        if self._config.extract_participants:
            mentions.extend(self._extract_participants(metadata))

        if self._config.extract_notion_links:
            mentions.extend(self._extract_notion_links(metadata))

        if self._config.extract_dates:
            mentions.extend(self._extract_dates(content))

        if self._config.extract_decisions:
            mentions.extend(self._extract_decisions(content))

        if self._config.extract_questions:
            mentions.extend(self._extract_questions(content))

        if self._config.extract_goals:
            mentions.extend(self._extract_goals(content))

        if self._config.extract_risks:
            mentions.extend(self._extract_risks(content))

        return self._deduplicate(mentions)

    # ------------------------------------------------------------------
    # Extraction rules
    # ------------------------------------------------------------------

    def _extract_emails(self, content: str) -> list[ExtractedMention]:
        """Extract e-mail addresses as Person entities."""
        results: list[ExtractedMention] = []
        for match in _EMAIL_RE.finditer(content):
            email = match.group(0)
            name = self._email_to_name(email)
            results.append(
                ExtractedMention(
                    entity_name=name,
                    entity_type=EntityType.PERSON,
                    normalized_name=self._normalize(name),
                    source_pattern="email",
                )
            )
        return results

    def _extract_at_mentions(self, content: str) -> list[ExtractedMention]:
        """Extract @-mentions as Person entities."""
        results: list[ExtractedMention] = []
        for match in _AT_MENTION_RE.finditer(content):
            username = match.group(1)
            name = username.replace(".", " ").replace("_", " ").replace("-", " ")
            results.append(
                ExtractedMention(
                    entity_name=name,
                    entity_type=EntityType.PERSON,
                    normalized_name=self._normalize(name),
                    source_pattern="at_mention",
                )
            )
        return results

    def _extract_participants(
        self,
        metadata: dict[str, Any],
    ) -> list[ExtractedMention]:
        """Extract calendar participants as Person entities.

        Expects `metadata['participants']` as a list of dicts, each with
        optional `name` and/or `email` keys.
        """
        participants = metadata.get("participants")
        if not isinstance(participants, list):
            return []

        results: list[ExtractedMention] = []
        for entry in participants:
            if not isinstance(entry, dict):
                continue

            name = entry.get("name", "").strip()
            email = entry.get("email", "").strip()

            if not name and email:
                name = self._email_to_name(email)
            elif not name:
                continue

            results.append(
                ExtractedMention(
                    entity_name=name,
                    entity_type=EntityType.PERSON,
                    normalized_name=self._normalize(name),
                    source_pattern="participant",
                )
            )
        return results

    def _extract_notion_links(
        self,
        metadata: dict[str, Any],
    ) -> list[ExtractedMention]:
        """Extract Notion page links as entities.

        Expects `metadata['notion_links']` as a list of dicts with
        `title` (required) and optional `type` (maps to EntityType).
        """
        links = metadata.get("notion_links")
        if not isinstance(links, list):
            return []

        results: list[ExtractedMention] = []
        for entry in links:
            if not isinstance(entry, dict):
                continue

            title = entry.get("title", "").strip()
            if not title:
                continue

            entity_type = self._notion_type_to_entity_type(
                entry.get("type", ""),
            )

            results.append(
                ExtractedMention(
                    entity_name=title,
                    entity_type=entity_type,
                    normalized_name=self._normalize(title),
                    source_pattern="notion_link",
                )
            )
        return results

    # ------------------------------------------------------------------
    # ADR-017: Date, Decision, Question, Goal, Risk extraction
    # ------------------------------------------------------------------

    def _extract_dates(self, content: str) -> list[ExtractedMention]:
        """Extract date references and deadlines."""
        results: list[ExtractedMention] = []
        seen: set[str] = set()

        for match in _ISO_DATE_RE.finditer(content):
            date_str = match.group(1) or match.group(2) or match.group(3)
            if date_str in seen:
                continue
            seen.add(date_str)
            results.append(
                ExtractedMention(
                    entity_name=date_str,
                    entity_type=EntityType.DATE_REF,
                    normalized_name=self._normalize(date_str),
                    confidence=1.0,
                    source_pattern="date_iso",
                ),
            )

        for match in _DEADLINE_RE.finditer(content):
            date_ref = match.group(1).strip()
            norm = self._normalize(date_ref)
            if norm in seen:
                continue
            seen.add(norm)
            results.append(
                ExtractedMention(
                    entity_name=date_ref,
                    entity_type=EntityType.DATE_REF,
                    normalized_name=norm,
                    confidence=0.85,
                    source_pattern="deadline_keyword",
                ),
            )

        return results

    def _extract_decisions(self, content: str) -> list[ExtractedMention]:
        """Extract decision statements from keyword patterns."""
        results: list[ExtractedMention] = []
        for match in _DECISION_RE.finditer(content):
            text = (match.group(1) or match.group(2) or "").strip()
            text = self._trim_to_sentence(text)
            if not text:
                continue
            results.append(
                ExtractedMention(
                    entity_name=text,
                    entity_type=EntityType.DECISION,
                    normalized_name=self._normalize(text),
                    confidence=0.85,
                    source_pattern="decision_keyword",
                ),
            )
        return results

    def _extract_questions(self, content: str) -> list[ExtractedMention]:
        """Extract open questions from keyword patterns."""
        results: list[ExtractedMention] = []
        for match in _OPEN_QUESTION_RE.finditer(content):
            text = match.group(1).strip()
            text = self._trim_to_sentence(text)
            if not text:
                continue
            results.append(
                ExtractedMention(
                    entity_name=text,
                    entity_type=EntityType.OPEN_QUESTION,
                    normalized_name=self._normalize(text),
                    confidence=0.85,
                    source_pattern="question_keyword",
                ),
            )
        return results

    def _extract_goals(self, content: str) -> list[ExtractedMention]:
        """Extract goal statements from keyword patterns."""
        results: list[ExtractedMention] = []
        for match in _GOAL_RE.finditer(content):
            text = match.group(1).strip()
            text = self._trim_to_sentence(text)
            if not text:
                continue
            results.append(
                ExtractedMention(
                    entity_name=text,
                    entity_type=EntityType.GOAL,
                    normalized_name=self._normalize(text),
                    confidence=0.85,
                    source_pattern="goal_keyword",
                ),
            )
        return results

    def _extract_risks(self, content: str) -> list[ExtractedMention]:
        """Extract risk statements from keyword patterns."""
        results: list[ExtractedMention] = []
        for match in _RISK_RE.finditer(content):
            text = match.group(1).strip()
            text = self._trim_to_sentence(text)
            if not text:
                continue
            results.append(
                ExtractedMention(
                    entity_name=text,
                    entity_type=EntityType.RISK,
                    normalized_name=self._normalize(text),
                    confidence=0.85,
                    source_pattern="risk_keyword",
                ),
            )
        return results

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(
        self,
        mentions: list[ExtractedMention],
    ) -> list[ExtractedEntity]:
        """Deduplicate mentions by (entity_type, normalized_name).

        Keeps the first-seen display name.
        """
        seen: dict[tuple[EntityType, str], ExtractedEntity] = {}

        for mention in mentions:
            key = (mention.entity_type, mention.normalized_name)

            if key not in seen:
                seen[key] = ExtractedEntity(
                    entity_type=mention.entity_type,
                    name=mention.entity_name,
                    normalized_name=mention.normalized_name,
                    mentions=[mention],
                )
            else:
                seen[key].mentions.append(mention)

        return list(seen.values())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a name: lowercase, collapse whitespace, strip."""
        return re.sub(r"\s+", " ", name.lower().strip())

    @staticmethod
    def _email_to_name(email: str) -> str:
        """Derive a human-readable name from an e-mail address.

        `john.doe@example.com` -> `John Doe`
        """
        local = email.split("@")[0]
        parts = re.split(r"[._\-+]", local)
        return " ".join(p.capitalize() for p in parts if p)

    @staticmethod
    def _notion_type_to_entity_type(raw_type: str) -> EntityType:
        """Map a Notion link `type` hint to an EntityType."""
        mapping: dict[str, EntityType] = {
            "person": EntityType.PERSON,
            "project": EntityType.PROJECT,
            "topic": EntityType.TOPIC,
            "decision": EntityType.DECISION,
        }
        return mapping.get(raw_type.lower().strip(), EntityType.TOPIC)

    @staticmethod
    def _trim_to_sentence(text: str) -> str:
        """Trim *text* at the first sentence boundary (., !, or newline).

        Returns the trimmed string (may be empty if nothing usable).
        """
        # Stop at the first full stop, exclamation mark, or newline
        end = len(text)
        for ch in (".\n", ".\r", ". ", ".\t", "!\n", "! ", "\n"):
            idx = text.find(ch)
            if idx != -1 and idx < end:
                end = idx
        result = text[:end].strip().rstrip(".!,;:")
        return result
