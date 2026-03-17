"""General feedback ORM model (TASK-188).

Stores user-submitted bug reports, feature requests and praise
together with context metadata (URL, browser, viewport).
No PII stored in metadata – only technical context.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from pwbs.models.user import User  # noqa: F401


class Feedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """In-app feedback with context metadata."""

    __tablename__ = "feedbacks"
    __table_args__ = (
        Index("idx_feedbacks_user", "user_id"),
        Index("idx_feedbacks_type", "feedback_type"),
        Index("idx_feedbacks_created", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="bug | feature | praise",
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    context_meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="url, browser_info, viewport_size – no sensitive data",
    )
    resolved_at: Mapped[None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")
