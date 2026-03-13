"""Pydantic v2 schemas for knowledge-graph entities (TASK-033).

``Entity`` and ``EntityMention`` represent the NER output from the
processing pipeline and map to the corresponding PostgreSQL / Neo4j
structures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pwbs.schemas.enums import EntityType


class Entity(BaseModel):
    """A named entity extracted from one or more document chunks."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID
    user_id: UUID
    entity_type: EntityType
    name: str = Field(min_length=1)
    normalized_name: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    first_seen: datetime
    last_seen: datetime
    mention_count: int = Field(ge=1)
    neo4j_node_id: str | None = None


class EntityMention(BaseModel):
    """A single occurrence of an entity within a chunk."""

    entity_id: UUID
    chunk_id: UUID
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_method: Literal["rule", "llm"]
