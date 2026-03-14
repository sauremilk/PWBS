"""Rule-based Named Entity Recognition for the PWBS Processing Pipeline (TASK-061).

First stage of the two-stage NER pipeline. Extracts entities from document
chunks using deterministic regex patterns:

- **E-Mail addresses** -> Person entities
- **@-Mentions** -> Person entities
- **Calendar participants** (from metadata `participants` field) -> Person entities
- **Notion links** (from metadata) -> diverse entities

All rule-based extractions carry `confidence=1.0` and
`extraction_method='rule'`.

D1 Section 3.2, AGENTS.md ProcessingAgent.
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
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NERConfig:
    """Configuration for the rule-based NER extractor."""

    extract_emails: bool = True
    extract_mentions: bool = True
    extract_participants: bool = True
    extract_notion_links: bool = True


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
