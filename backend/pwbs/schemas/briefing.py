"""Pydantic v2 schemas for briefings and source references (TASK-034).

SourceRef implements the explainability principle: every LLM-generated
statement must carry source references back to the original chunks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pwbs.schemas.enums import BriefingType, SourceType


class SourceRef(BaseModel):
    """Reference to a source chunk that supports a generated statement."""

    chunk_id: UUID
    doc_title: str
    source_type: SourceType
    date: datetime
    relevance: float = Field(ge=0.0, le=1.0)


class Briefing(BaseModel):
    """Persisted briefing as stored in the database."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID
    user_id: UUID
    briefing_type: BriefingType
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_chunks: list[UUID]
    source_entities: list[UUID] | None = None
    trigger_context: dict[str, Any] | None = None
    generated_at: datetime
    expires_at: datetime | None = None


class BriefingCreate(BaseModel):
    """Payload for creating a new briefing (id and generated_at are server-set)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: UUID
    briefing_type: BriefingType
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_chunks: list[UUID]
    source_entities: list[UUID] | None = None
    trigger_context: dict[str, Any] | None = None
    expires_at: datetime | None = None


class BriefingResponse(Briefing):
    """API response model: briefing with resolved source references."""

    sources: list[SourceRef] = Field(default_factory=list)
