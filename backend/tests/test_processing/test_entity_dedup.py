"""Tests for Entity-Deduplizierung (TASK-063)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.processing.entity_dedup import (
    DeduplicationConfig,
    DeduplicationResult,
    EntityDeduplicationService,
    UpsertedEntity,
    _fuzzy_ratio,
    normalize_name,
)
from pwbs.processing.ner import ExtractedEntity, ExtractedMention
from pwbs.schemas.enums import EntityType

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CHUNK_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _entity(
    name: str = "Alice Smith",
    entity_type: EntityType = EntityType.PERSON,
    confidence: float = 0.9,
    method: str = "rule",
    metadata: dict[str, Any] | None = None,
) -> ExtractedEntity:
    norm = name.lower().strip()
    return ExtractedEntity(
        entity_type=entity_type,
        name=name,
        normalized_name=norm,
        mentions=[
            ExtractedMention(
                entity_name=name,
                entity_type=entity_type,
                normalized_name=norm,
                confidence=confidence,
                extraction_method=method,
                source_pattern="test",
            ),
        ],
        metadata=metadata or {},
    )


def _make_session(
    upsert_row: tuple[str, bool] | None = None,
    fuzzy_rows: list[tuple[str]] | None = None,
) -> AsyncMock:
    """Mock AsyncSession that returns different results per query."""
    session = AsyncMock()
    call_count = 0

    async def _execute(sql: Any, params: dict[str, Any] | None = None) -> MagicMock:
        nonlocal call_count
        call_count += 1
        result = MagicMock()

        sql_text = str(sql.text) if hasattr(sql, "text") else str(sql)

        if "SELECT normalized_name FROM entities" in sql_text:
            # Fuzzy match query
            result.fetchall.return_value = fuzzy_rows or []
        elif "INSERT INTO entities" in sql_text:
            # UPSERT query
            row = upsert_row or (str(uuid.uuid4()), True)
            result.fetchone.return_value = row
        elif "INSERT INTO entity_mentions" in sql_text:
            # Mention insert (no return value needed)
            pass

        return result

    session.execute = AsyncMock(side_effect=_execute)
    return session


def _make_service(
    session: AsyncMock | None = None,
    config: DeduplicationConfig | None = None,
    upsert_row: tuple[str, bool] | None = None,
    fuzzy_rows: list[tuple[str]] | None = None,
) -> EntityDeduplicationService:
    sess = session or _make_session(upsert_row=upsert_row, fuzzy_rows=fuzzy_rows)
    return EntityDeduplicationService(session=sess, config=config)


# ===================================================================
# normalize_name
# ===================================================================


class TestNormalizeName:
    def test_lowercase(self) -> None:
        assert normalize_name("Alice Smith") == "alice smith"

    def test_strip_whitespace(self) -> None:
        assert normalize_name("  Alice  Smith  ") == "alice smith"

    def test_umlaut_ae(self) -> None:
        assert normalize_name("Müller") == "mueller"

    def test_umlaut_oe(self) -> None:
        assert normalize_name("Böhm") == "boehm"

    def test_umlaut_ue(self) -> None:
        assert normalize_name("Lübeck") == "luebeck"

    def test_umlaut_ss(self) -> None:
        assert normalize_name("Straße") == "strasse"

    def test_accented_chars(self) -> None:
        result = normalize_name("José García")
        assert "jose" in result
        assert "garcia" in result

    def test_empty(self) -> None:
        assert normalize_name("") == ""

    def test_already_normalized(self) -> None:
        assert normalize_name("alice smith") == "alice smith"


# ===================================================================
# Fuzzy Ratio
# ===================================================================


class TestFuzzyRatio:
    def test_identical(self) -> None:
        assert _fuzzy_ratio("alice", "alice") == 1.0

    def test_similar(self) -> None:
        ratio = _fuzzy_ratio("thomas k", "thomas klein")
        assert 0.5 < ratio < 1.0

    def test_different(self) -> None:
        ratio = _fuzzy_ratio("alice", "zebra")
        assert ratio < 0.5

    def test_empty_a(self) -> None:
        assert _fuzzy_ratio("", "alice") == 0.0

    def test_empty_b(self) -> None:
        assert _fuzzy_ratio("alice", "") == 0.0


# ===================================================================
# Config
# ===================================================================


class TestDeduplicationConfig:
    def test_defaults(self) -> None:
        cfg = DeduplicationConfig()
        assert cfg.fuzzy_threshold == 0.85
        assert cfg.fuzzy_enabled is True
        assert EntityType.PERSON in cfg.fuzzy_entity_types

    def test_custom(self) -> None:
        cfg = DeduplicationConfig(fuzzy_threshold=0.9, fuzzy_enabled=False)
        assert cfg.fuzzy_threshold == 0.9
        assert cfg.fuzzy_enabled is False


# ===================================================================
# UPSERT (new entity)
# ===================================================================


class TestUpsertNew:
    @pytest.mark.asyncio
    async def test_new_entity_created(self) -> None:
        eid = str(uuid.uuid4())
        svc = _make_service(
            upsert_row=(eid, True),
            config=DeduplicationConfig(fuzzy_enabled=False),
        )
        result = await svc.deduplicate_and_persist(
            [_entity()], USER_ID, CHUNK_ID,
        )
        assert len(result.upserted) == 1
        assert result.upserted[0].is_new is True

    @pytest.mark.asyncio
    async def test_mention_created(self) -> None:
        svc = _make_service(config=DeduplicationConfig(fuzzy_enabled=False))
        result = await svc.deduplicate_and_persist(
            [_entity()], USER_ID, CHUNK_ID,
        )
        assert result.mentions_created == 1


# ===================================================================
# UPSERT (existing entity  update)
# ===================================================================


class TestUpsertExisting:
    @pytest.mark.asyncio
    async def test_existing_entity_updated(self) -> None:
        eid = str(uuid.uuid4())
        svc = _make_service(
            upsert_row=(eid, False),
            config=DeduplicationConfig(fuzzy_enabled=False),
        )
        result = await svc.deduplicate_and_persist(
            [_entity()], USER_ID, CHUNK_ID,
        )
        assert result.upserted[0].is_new is False
        assert result.upserted[0].merged_with is not None


# ===================================================================
# Fuzzy Matching
# ===================================================================


class TestFuzzyMatching:
    @pytest.mark.asyncio
    async def test_fuzzy_match_found(self) -> None:
        # Existing DB has "thomas klein", new entity is "Thomas K."
        svc = _make_service(
            fuzzy_rows=[("thomas klein",)],
            config=DeduplicationConfig(fuzzy_threshold=0.7),
        )
        entity = _entity(name="Thomas K.", entity_type=EntityType.PERSON)
        result = await svc.deduplicate_and_persist(
            [entity], USER_ID, CHUNK_ID,
        )
        assert result.fuzzy_merges == 1

    @pytest.mark.asyncio
    async def test_fuzzy_disabled_no_merge(self) -> None:
        svc = _make_service(
            fuzzy_rows=[("thomas klein",)],
            config=DeduplicationConfig(fuzzy_enabled=False),
        )
        entity = _entity(name="Thomas K.")
        result = await svc.deduplicate_and_persist(
            [entity], USER_ID, CHUNK_ID,
        )
        assert result.fuzzy_merges == 0

    @pytest.mark.asyncio
    async def test_fuzzy_only_for_persons(self) -> None:
        svc = _make_service(
            fuzzy_rows=[("kubernetes",)],
            config=DeduplicationConfig(fuzzy_threshold=0.5),
        )
        entity = _entity(name="Kubernetes", entity_type=EntityType.TOPIC)
        result = await svc.deduplicate_and_persist(
            [entity], USER_ID, CHUNK_ID,
        )
        assert result.fuzzy_merges == 0

    @pytest.mark.asyncio
    async def test_exact_match_no_fuzzy_merge(self) -> None:
        # If exact match exists, fuzzy should not count as merge
        svc = _make_service(
            fuzzy_rows=[("alice smith",)],
        )
        entity = _entity(name="Alice Smith")
        result = await svc.deduplicate_and_persist(
            [entity], USER_ID, CHUNK_ID,
        )
        # Exact match returns None from _find_fuzzy_match  no fuzzy merge
        assert result.fuzzy_merges == 0


# ===================================================================
# Empty Input
# ===================================================================


class TestEmptyInput:
    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        svc = _make_service()
        result = await svc.deduplicate_and_persist([], USER_ID, CHUNK_ID)
        assert result.upserted == []
        assert result.mentions_created == 0

    @pytest.mark.asyncio
    async def test_no_db_calls_for_empty(self) -> None:
        session = _make_session()
        svc = EntityDeduplicationService(session=session)
        await svc.deduplicate_and_persist([], USER_ID, CHUNK_ID)
        session.execute.assert_not_awaited()


# ===================================================================
# Multiple Entities
# ===================================================================


class TestMultipleEntities:
    @pytest.mark.asyncio
    async def test_multiple_entities_upserted(self) -> None:
        svc = _make_service(config=DeduplicationConfig(fuzzy_enabled=False))
        entities = [
            _entity(name="Alice", entity_type=EntityType.PERSON),
            _entity(name="Phoenix", entity_type=EntityType.PROJECT),
        ]
        result = await svc.deduplicate_and_persist(entities, USER_ID, CHUNK_ID)
        assert len(result.upserted) == 2
        assert result.mentions_created == 2


# ===================================================================
# Error Handling
# ===================================================================


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_upsert_failure_logged(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("DB error"))
        svc = EntityDeduplicationService(
            session=session,
            config=DeduplicationConfig(fuzzy_enabled=False),
        )
        result = await svc.deduplicate_and_persist(
            [_entity()], USER_ID, CHUNK_ID,
        )
        assert len(result.errors) == 1
        assert "DB error" in result.errors[0]


# ===================================================================
# Helper Methods
# ===================================================================


class TestHelpers:
    def test_best_confidence(self) -> None:
        entity = _entity(confidence=0.85)
        assert EntityDeduplicationService._best_confidence(entity) == 0.85

    def test_best_confidence_empty_mentions(self) -> None:
        entity = ExtractedEntity(
            entity_type=EntityType.PERSON,
            name="X",
            normalized_name="x",
            mentions=[],
        )
        assert EntityDeduplicationService._best_confidence(entity) == 1.0

    def test_extraction_method_rule(self) -> None:
        entity = _entity(method="rule")
        assert EntityDeduplicationService._extraction_method(entity) == "rule"

    def test_extraction_method_llm(self) -> None:
        entity = _entity(method="llm")
        assert EntityDeduplicationService._extraction_method(entity) == "llm"

    def test_extraction_method_empty(self) -> None:
        entity = ExtractedEntity(
            entity_type=EntityType.PERSON,
            name="X",
            normalized_name="x",
            mentions=[],
        )
        assert EntityDeduplicationService._extraction_method(entity) == "rule"


# ===================================================================
# Config property
# ===================================================================


class TestConfigProperty:
    def test_config_accessible(self) -> None:
        cfg = DeduplicationConfig(fuzzy_threshold=0.9)
        svc = _make_service(config=cfg)
        assert svc.config.fuzzy_threshold == 0.9
