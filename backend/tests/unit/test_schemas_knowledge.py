"""Tests for pwbs.schemas – Chunk, Entity, EntityMention (TASK-033)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pwbs.schemas.document import Chunk
from pwbs.schemas.enums import EntityType
from pwbs.schemas.knowledge import Entity, EntityMention

_NOW = datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------


class TestChunkValid:
    def test_minimal_valid(self) -> None:
        chunk = Chunk(
            id=uuid4(),
            document_id=uuid4(),
            user_id=uuid4(),
            chunk_index=0,
            token_count=128,
            created_at=_NOW,
        )
        assert chunk.weaviate_id is None
        assert chunk.content_preview is None

    def test_with_optional_fields(self) -> None:
        wid = uuid4()
        chunk = Chunk(
            id=uuid4(),
            document_id=uuid4(),
            user_id=uuid4(),
            chunk_index=5,
            token_count=256,
            weaviate_id=wid,
            content_preview="Hello world...",
            created_at=_NOW,
        )
        assert chunk.weaviate_id == wid
        assert chunk.content_preview == "Hello world..."


class TestChunkInvalid:
    def test_negative_chunk_index(self) -> None:
        with pytest.raises(ValidationError):
            Chunk(
                id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                chunk_index=-1,
                token_count=128,
                created_at=_NOW,
            )

    def test_zero_token_count(self) -> None:
        with pytest.raises(ValidationError):
            Chunk(
                id=uuid4(),
                document_id=uuid4(),
                user_id=uuid4(),
                chunk_index=0,
                token_count=0,
                created_at=_NOW,
            )


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------


class TestEntityValid:
    def test_minimal_valid(self) -> None:
        entity = Entity(
            id=uuid4(),
            user_id=uuid4(),
            entity_type=EntityType.PERSON,
            name="Alice",
            normalized_name="alice",
            first_seen=_NOW,
            last_seen=_NOW,
            mention_count=1,
        )
        assert entity.metadata == {}
        assert entity.neo4j_node_id is None

    def test_all_entity_types(self) -> None:
        for et in EntityType:
            entity = Entity(
                id=uuid4(),
                user_id=uuid4(),
                entity_type=et,
                name="Test",
                normalized_name="test",
                first_seen=_NOW,
                last_seen=_NOW,
                mention_count=1,
            )
            assert entity.entity_type is et

    def test_with_metadata_and_neo4j(self) -> None:
        entity = Entity(
            id=uuid4(),
            user_id=uuid4(),
            entity_type=EntityType.PROJECT,
            name="PWBS",
            normalized_name="pwbs",
            metadata={"department": "engineering"},
            first_seen=_NOW,
            last_seen=_NOW,
            mention_count=5,
            neo4j_node_id="node-42",
        )
        assert entity.metadata["department"] == "engineering"
        assert entity.neo4j_node_id == "node-42"


class TestEntityInvalid:
    def test_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            Entity(
                id=uuid4(),
                user_id=uuid4(),
                entity_type=EntityType.PERSON,
                name="",
                normalized_name="alice",
                first_seen=_NOW,
                last_seen=_NOW,
                mention_count=1,
            )

    def test_zero_mention_count(self) -> None:
        with pytest.raises(ValidationError):
            Entity(
                id=uuid4(),
                user_id=uuid4(),
                entity_type=EntityType.PERSON,
                name="Alice",
                normalized_name="alice",
                first_seen=_NOW,
                last_seen=_NOW,
                mention_count=0,
            )

    def test_invalid_entity_type(self) -> None:
        with pytest.raises(ValidationError):
            Entity(
                id=uuid4(),
                user_id=uuid4(),
                entity_type="UNKNOWN",  # type: ignore[arg-type]
                name="Alice",
                normalized_name="alice",
                first_seen=_NOW,
                last_seen=_NOW,
                mention_count=1,
            )


# ---------------------------------------------------------------------------
# EntityMention
# ---------------------------------------------------------------------------


class TestEntityMentionValid:
    def test_rule_method(self) -> None:
        mention = EntityMention(
            entity_id=uuid4(),
            chunk_id=uuid4(),
            confidence=0.95,
            extraction_method="rule",
        )
        assert mention.extraction_method == "rule"

    def test_llm_method(self) -> None:
        mention = EntityMention(
            entity_id=uuid4(),
            chunk_id=uuid4(),
            confidence=0.75,
            extraction_method="llm",
        )
        assert mention.extraction_method == "llm"


class TestEntityMentionInvalid:
    def test_confidence_above_one(self) -> None:
        with pytest.raises(ValidationError):
            EntityMention(
                entity_id=uuid4(),
                chunk_id=uuid4(),
                confidence=1.5,
                extraction_method="rule",
            )

    def test_confidence_below_zero(self) -> None:
        with pytest.raises(ValidationError):
            EntityMention(
                entity_id=uuid4(),
                chunk_id=uuid4(),
                confidence=-0.1,
                extraction_method="rule",
            )

    def test_invalid_extraction_method(self) -> None:
        with pytest.raises(ValidationError):
            EntityMention(
                entity_id=uuid4(),
                chunk_id=uuid4(),
                confidence=0.9,
                extraction_method="regex",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# EntityType enum
# ---------------------------------------------------------------------------


class TestEntityTypeEnum:
    def test_values(self) -> None:
        expected = {"person", "project", "topic", "decision"}
        actual = {et.value for et in EntityType}
        assert actual == expected

    def test_is_str_enum(self) -> None:
        assert isinstance(EntityType.PERSON, str)
        assert EntityType.PERSON == "person"
