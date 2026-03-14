"""User work profile ORM model (TASK-134).

Stores analysed work patterns for briefing personalisation.
Versioned: each weekly analysis creates a new row so trends can
be tracked over time.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted work-pattern profile for a user (versioned)."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    analysis_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Top themes as JSON list: [{"name": "...", "mention_count": N}, ...]
    top_themes: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Average meetings per week (float)
    avg_meetings_per_week: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Preferred work hours as JSON: {"hours": {0: count, 1: count, ...}, "peak_start": 9, "peak_end": 17}
    preferred_hours: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Average days from decision creation to status=made
    decision_speed_avg_days: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # DSGVO: expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="profiles")  # noqa: F821