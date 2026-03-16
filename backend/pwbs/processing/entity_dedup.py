"""Entity-Deduplizierung über normalized_name (TASK-063).

Persists extracted entities (from TASK-061 rule-based and TASK-062 LLM-based)
into PostgreSQL using UPSERT logic:

- `ON CONFLICT (user_id, entity_type, normalized_name) DO UPDATE`
- Increments `mention_count`, updates `last_seen`
- Merges metadata dicts
- Creates `entity_mentions` records

Additionally provides fuzzy matching for PERSON entities using
Levenshtein distance to detect short/long form duplicates
(e.g. "Thomas K."  "Thomas Klein").

D1 §3.3.1, AGENTS.md ProcessingAgent.
"""

from __future__ import annotations

import logging
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.processing.ner import ExtractedEntity
from pwbs.schemas.enums import EntityType

logger = logging.getLogger(__name__)

__all__ = [
    "EntityDeduplicationService",
    "DeduplicationConfig",
    "DeduplicationResult",
    "UpsertedEntity",
    "normalize_name",
]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeduplicationConfig:
    """Configuration for entity deduplication."""

    fuzzy_threshold: float = 0.85
    fuzzy_enabled: bool = True
    fuzzy_entity_types: tuple[EntityType, ...] = (EntityType.PERSON,)


# ------------------------------------------------------------------
# Result types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpsertedEntity:
    """Result of a single entity upsert."""

    entity_id: uuid.UUID
    entity_type: EntityType
    name: str
    normalized_name: str
    is_new: bool
    merged_with: str | None = None


@dataclass(slots=True)
class DeduplicationResult:
    """Result of a full deduplication run."""

    upserted: list[UpsertedEntity] = field(default_factory=list)
    mentions_created: int = 0
    fuzzy_merges: int = 0
    errors: list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Normalization
# ------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Normalize an entity name for deduplication.

    Steps:
    1. Lowercase
    2. Strip whitespace
    3. Normalize Umlaute (äae, öoe, üue, ßss)
    4. NFD unicode normalization + strip combining marks
    5. Collapse whitespace
    """
    result = name.lower().strip()

    # German Umlaute normalization
    result = (
        result
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )

    # NFD normalization: decompose accented characters
    result = unicodedata.normalize("NFD", result)
    # Remove combining diacritical marks
    result = "".join(
        ch for ch in result
        if unicodedata.category(ch) != "Mn"
    )

    # Collapse whitespace
    return " ".join(result.split())


# ------------------------------------------------------------------
# Fuzzy matching
# ------------------------------------------------------------------


def _fuzzy_ratio(a: str, b: str) -> float:
    """Compute similarity ratio between two normalized names."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class EntityDeduplicationService:
    """Persists extracted entities with deduplication.

    Uses PostgreSQL UPSERT (ON CONFLICT DO UPDATE) on the
    `(user_id, entity_type, normalized_name)` unique constraint.

    Parameters
    ----------
    session:
        SQLAlchemy async session.
    config:
        Deduplication configuration.
    """

    def __init__(
        self,
        session: AsyncSession,
        config: DeduplicationConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or DeduplicationConfig()

    @property
    def config(self) -> DeduplicationConfig:
        return self._config

    async def deduplicate_and_persist(
        self,
        entities: list[ExtractedEntity],
        user_id: uuid.UUID,
        chunk_id: uuid.UUID,
    ) -> DeduplicationResult:
        """Persist extracted entities with deduplication.

        Parameters
        ----------
        entities:
            Entities from rule-based or LLM extraction.
        user_id:
            Owner ID (tenant isolation).
        chunk_id:
            The chunk from which entities were extracted.

        Returns
        -------
        DeduplicationResult
        """
        result = DeduplicationResult()

        if not entities:
            return result

        # Step 1: Fuzzy-match persons to resolve short/long forms
        resolved = await self._resolve_fuzzy_matches(
            entities, user_id,
        )
        result.fuzzy_merges = resolved.fuzzy_merges

        # Step 2: Upsert each entity
        for entity in resolved.entities:
            try:
                upserted = await self._upsert_entity(entity, user_id)
                result.upserted.append(upserted)

                # Step 3: Create entity_mention
                await self._create_mention(
                    entity_id=upserted.entity_id,
                    chunk_id=chunk_id,
                    confidence=self._best_confidence(entity),
                    extraction_method=self._extraction_method(entity),
                )
                result.mentions_created += 1

            except Exception as exc:
                msg = f"Failed to upsert entity '{entity.name}': {exc}"
                logger.error(msg)
                result.errors.append(msg)

        return result

    # ------------------------------------------------------------------
    # Fuzzy resolution
    # ------------------------------------------------------------------

    @dataclass
    class _FuzzyResult:
        entities: list[ExtractedEntity]
        fuzzy_merges: int = 0

    async def _resolve_fuzzy_matches(
        self,
        entities: list[ExtractedEntity],
        user_id: uuid.UUID,
    ) -> _FuzzyResult:
        """Check new person entities against existing DB entries for fuzzy matches."""
        if not self._config.fuzzy_enabled:
            return self._FuzzyResult(entities=list(entities))

        resolved: list[ExtractedEntity] = []
        merges = 0

        for entity in entities:
            if entity.entity_type not in self._config.fuzzy_entity_types:
                resolved.append(entity)
                continue

            norm = normalize_name(entity.name)
            match = await self._find_fuzzy_match(
                norm, entity.entity_type, user_id,
            )

            if match is not None:
                # Replace normalized_name with the existing one
                logger.info(
                    "Fuzzy match: '%s'  '%s' (existing)",
                    entity.name, match,
                )
                resolved.append(
                    ExtractedEntity(
                        entity_type=entity.entity_type,
                        name=entity.name,
                        normalized_name=match,
                        mentions=entity.mentions,
                        metadata=entity.metadata,
                    ),
                )
                merges += 1
            else:
                # Use our own normalized name
                resolved.append(
                    ExtractedEntity(
                        entity_type=entity.entity_type,
                        name=entity.name,
                        normalized_name=norm,
                        mentions=entity.mentions,
                        metadata=entity.metadata,
                    ),
                )

        return self._FuzzyResult(entities=resolved, fuzzy_merges=merges)

    async def _find_fuzzy_match(
        self,
        normalized_name: str,
        entity_type: EntityType,
        user_id: uuid.UUID,
    ) -> str | None:
        """Find an existing entity that fuzzy-matches the given name.

        Returns the existing `normalized_name` if found, else `None`.
        """
        query = text(
            "SELECT normalized_name FROM entities "
            "WHERE user_id = :user_id AND entity_type = :entity_type"
        )
        result = await self._session.execute(
            query,
            {"user_id": str(user_id), "entity_type": entity_type.value},
        )
        rows = result.fetchall()

        best_match: str | None = None
        best_score = 0.0

        for row in rows:
            existing_norm = row[0]
            if existing_norm == normalized_name:
                # Exact match  no fuzzy needed, UPSERT handles it
                return None
            score = _fuzzy_ratio(normalized_name, existing_norm)
            if score >= self._config.fuzzy_threshold and score > best_score:
                best_score = score
                best_match = existing_norm

        return best_match

    # ------------------------------------------------------------------
    # UPSERT
    # ------------------------------------------------------------------

    async def _upsert_entity(
        self,
        entity: ExtractedEntity,
        user_id: uuid.UUID,
    ) -> UpsertedEntity:
        """UPSERT entity using ON CONFLICT DO UPDATE."""
        now = datetime.now(tz=timezone.utc)
        norm = normalize_name(entity.name) if entity.normalized_name == entity.name.lower().strip() else entity.normalized_name
        # Use the already-resolved normalized_name (may have been fuzzy-matched)
        norm = entity.normalized_name

        entity_id = uuid.uuid4()
        metadata_json = entity.metadata if entity.metadata else {}

        upsert_sql = text("""
            INSERT INTO entities (id, user_id, entity_type, name, normalized_name, metadata, first_seen, last_seen, mention_count)
            VALUES (:id, :user_id, :entity_type, :name, :normalized_name, :metadata::jsonb, :now, :now, 1)
            ON CONFLICT (user_id, entity_type, normalized_name)
            DO UPDATE SET
                last_seen = :now,
                mention_count = entities.mention_count + 1,
                metadata = entities.metadata || :metadata::jsonb
            RETURNING id, (xmax = 0) AS is_new
        """)

        import json as _json
        result = await self._session.execute(
            upsert_sql,
            {
                "id": str(entity_id),
                "user_id": str(user_id),
                "entity_type": entity.entity_type.value,
                "name": entity.name,
                "normalized_name": norm,
                "metadata": _json.dumps(metadata_json),
                "now": now,
            },
        )
        row = result.fetchone()
        actual_id = uuid.UUID(str(row[0]))  # type: ignore[index]
        is_new = bool(row[1])  # type: ignore[index]

        return UpsertedEntity(
            entity_id=actual_id,
            entity_type=entity.entity_type,
            name=entity.name,
            normalized_name=norm,
            is_new=is_new,
            merged_with=norm if not is_new else None,
        )

    # ------------------------------------------------------------------
    # Entity mentions
    # ------------------------------------------------------------------

    async def _create_mention(
        self,
        entity_id: uuid.UUID,
        chunk_id: uuid.UUID,
        confidence: float,
        extraction_method: str,
    ) -> None:
        """Insert entity_mention (idempotent via ON CONFLICT DO NOTHING)."""
        sql = text("""
            INSERT INTO entity_mentions (entity_id, chunk_id, confidence, extraction_method)
            VALUES (:entity_id, :chunk_id, :confidence, :extraction_method)
            ON CONFLICT (entity_id, chunk_id) DO NOTHING
        """)
        await self._session.execute(
            sql,
            {
                "entity_id": str(entity_id),
                "chunk_id": str(chunk_id),
                "confidence": confidence,
                "extraction_method": extraction_method,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _best_confidence(entity: ExtractedEntity) -> float:
        """Get the highest confidence from the entity's mentions."""
        if not entity.mentions:
            return 1.0
        return max(m.confidence for m in entity.mentions)

    @staticmethod
    def _extraction_method(entity: ExtractedEntity) -> str:
        """Get extraction method from the entity's mentions."""
        if not entity.mentions:
            return "rule"
        return entity.mentions[0].extraction_method
