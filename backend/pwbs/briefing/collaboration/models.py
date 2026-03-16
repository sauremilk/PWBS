"""ORM models for collaborative briefings (TASK-163).

BriefingShare: M2M table tracking shared briefings with read receipts.
BriefingComment: Inline comments on briefing sections.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class BriefingShare(UUIDPrimaryKeyMixin, Base):
    """Tracks that a briefing was shared with a specific user."""

    __tablename__ = "briefing_shares"
    __table_args__ = (
        Index("idx_shares_briefing", "briefing_id"),
        Index("idx_shares_recipient", "recipient_id"),
        Index(
            "uq_shares_briefing_recipient",
            "briefing_id",
            "recipient_id",
            unique=True,
        ),
    )

    briefing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("briefings.id", ondelete="CASCADE"),
        nullable=False,
    )
    shared_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    briefing: Mapped["Briefing"] = relationship()  # noqa: F821
    sharer: Mapped["User"] = relationship(foreign_keys=[shared_by])  # noqa: F821
    recipient: Mapped["User"] = relationship(foreign_keys=[recipient_id])  # noqa: F821


class BriefingComment(UUIDPrimaryKeyMixin, Base):
    """Inline comment on a specific section of a briefing."""

    __tablename__ = "briefing_comments"
    __table_args__ = (
        Index("idx_comments_briefing", "briefing_id"),
        Index("idx_comments_author", "author_id"),
        Index("idx_comments_briefing_section", "briefing_id", "section_ref"),
    )

    briefing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("briefings.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Section reference: e.g. "summary", "section-2", "open-items"
    section_ref: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    briefing: Mapped["Briefing"] = relationship()  # noqa: F821
    author: Mapped["User"] = relationship()  # noqa: F821
