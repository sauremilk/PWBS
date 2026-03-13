"""Pydantic v2 schemas for the Unified Document Format (TASK-032).

The ``UnifiedDocument`` is the central data-transfer object between the
Ingestion and Processing layers.  Every connector normalises its raw data
into this format before handing it off to chunking / embedding / NER.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from pwbs.schemas.enums import ContentType, SourceType


class UnifiedDocument(BaseModel):
    """Unified Document Format (UDF).

    Canonical schema produced by connectors and consumed by the processing
    pipeline.  ``raw_hash`` (SHA-256 of the source content) is used for
    deduplication via the DB UNIQUE constraint
    ``(user_id, source_type, source_id)``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID
    user_id: UUID
    source_type: SourceType
    source_id: str = Field(min_length=1)
    title: str
    content: str
    content_type: ContentType
    metadata: dict[str, Any] = Field(default_factory=dict)
    participants: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    fetched_at: datetime
    language: str = Field(
        pattern=r"^[a-z]{2}$",
        description="ISO 639-1 language code",
    )
    raw_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the raw source content",
    )
    # DSGVO: every data record must carry an optional expiry date
    expires_at: datetime | None = Field(
        default=None,
        description="DSGVO: data expiry date after which the record must be deleted",
    )


class Chunk(BaseModel):
    """Schema for a document chunk produced by the processing pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID
    document_id: UUID
    user_id: UUID
    chunk_index: int = Field(ge=0)
    token_count: int = Field(ge=1)
    weaviate_id: UUID | None = None
    content_preview: str | None = None
    created_at: datetime
