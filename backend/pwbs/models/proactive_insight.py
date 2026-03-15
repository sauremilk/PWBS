"""ProactiveInsight and InsightPreferences ORM models (TASK-158).

ProactiveInsight: Stores generated proactive insights with source references.
InsightPreferences: Per-user opt-in configuration (categories, frequency).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProactiveInsight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single proactive insight generated for a user."""

    __tablename__ = "proactive_insights"
    __table_args__ = (
        Index("idx_insights_owner_created", "owner_id", "created_at"),
        Index("idx_insights_owner_category", "owner_id", "category"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        Text, nullable=False,
    )  # "contradictions" | "forgotten_topics" | "trends"
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict] | None] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="[]",
    )  # list[{document_id, title, source_type, date}]
    pattern_data: Mapped[dict | None] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=True,
    )  # raw pattern data for reproducibility
    feedback_rating: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )  # "helpful" | "not_helpful" | None
    feedback_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )  # DSGVO: auto-expiry


class InsightPreferences(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-user insight generation preferences (opt-in)."""

    __tablename__ = "insight_preferences"
    __table_args__ = (
        UniqueConstraint("owner_id", name="uq_insight_prefs_owner"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    frequency: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="daily",
    )  # "daily" | "weekly" | "off"
    enabled_categories: Mapped[list[str] | None] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        server_default='["contradictions", "forgotten_topics", "trends"]',
    )
    max_insights_per_run: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="3",
    )
