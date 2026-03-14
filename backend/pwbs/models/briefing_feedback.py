"""BriefingFeedback ORM model (TASK-171).

Stores per-briefing user feedback (positive/negative + optional comment).
UniqueConstraint ensures one feedback per user per briefing (upsert pattern).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class BriefingFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "briefing_feedback"
    __table_args__ = (
        UniqueConstraint("briefing_id", "owner_id", name="uq_feedback_briefing_owner"),
        Index("idx_feedback_owner", "owner_id"),
        Index("idx_feedback_briefing", "briefing_id"),
    )

    briefing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("briefings.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[str] = mapped_column(Text, nullable=False)  # "positive" | "negative"
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
