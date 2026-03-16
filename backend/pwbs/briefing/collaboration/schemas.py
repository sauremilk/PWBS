"""Pydantic schemas for collaborative briefings (TASK-163)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Share Schemas ─────────────────────────────────────────────────────────────


class ShareBriefingRequest(BaseModel):
    """Request to share a briefing with one or more users."""

    recipient_ids: list[UUID] = Field(
        ..., min_length=1, max_length=50, description="User IDs to share with."
    )


class ShareResponse(BaseModel):
    """Response for a single share record."""

    id: UUID
    briefing_id: UUID
    shared_by: UUID
    recipient_id: UUID
    shared_at: datetime
    read_at: datetime | None = None


class ShareListResponse(BaseModel):
    """List of shares for a briefing."""

    shares: list[ShareResponse]
    total: int


class ReadReceiptResponse(BaseModel):
    """Read receipt confirmation."""

    briefing_id: UUID
    recipient_id: UUID
    read_at: datetime


# ── Comment Schemas ───────────────────────────────────────────────────────────


class CreateCommentRequest(BaseModel):
    """Request to create an inline comment."""

    section_ref: str = Field(
        default="",
        max_length=200,
        description="Section anchor, e.g. 'summary', 'open-items'.",
    )
    content: str = Field(
        ..., min_length=1, max_length=5000, description="Comment text."
    )


class CommentResponse(BaseModel):
    """Response for a single comment."""

    id: UUID
    briefing_id: UUID
    author_id: UUID
    section_ref: str
    content: str
    created_at: datetime
    updated_at: datetime


class CommentListResponse(BaseModel):
    """Paginated list of comments."""

    comments: list[CommentResponse]
    total: int