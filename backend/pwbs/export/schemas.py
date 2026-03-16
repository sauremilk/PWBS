"""Pydantic schemas for the export module (TASK-164)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExportMetadata(BaseModel):
    """Metadata included in every export."""

    generated_at: datetime
    pwbs_version: str = "0.2.0"
    briefing_id: UUID
    briefing_type: str
    title: str
    source_count: int


class ExportResult(BaseModel):
    """Result returned by an export strategy."""

    format: str
    content_type: str
    filename: str
    data: bytes
    metadata: ExportMetadata


class ConfluenceExportRequest(BaseModel):
    """Request body for Confluence page creation."""

    briefing_id: UUID
    space_key: str = Field(..., min_length=1, max_length=50)
    parent_page_id: str | None = Field(
        default=None, description="Optional Confluence parent page ID."
    )
    title: str | None = Field(
        default=None,
        description="Override title. Falls omitted, uses briefing title.",
    )
