"""Knowledge Snapshot ORM model (TASK-162).

KnowledgeSnapshot: A point-in-time capture of a user's knowledge graph state.
Stores entities, relationships, and statistics as compressed JSONB.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A point-in-time snapshot of a user's knowledge graph."""

    __tablename__ = "knowledge_snapshots"
    __table_args__ = (
        Index("idx_snapshots_user", "user_id"),
        Index("idx_snapshots_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Snapshot label / description
    label: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    # Trigger: "manual" or "weekly_auto"
    trigger: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")

    # Statistics
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    relationship_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Snapshot data as JSONB:
    # {
    #   "entities": [{"id": "...", "type": "...", "name": "...", "mention_count": N, ...}],
    #   "relationships": [{"source_id": "...", "target_id": "...",
    #       "type": "co_mentioned", "weight": N}],
    #   "top_themes": [{"name": "...", "mention_count": N}]
    # }
    snapshot_data: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False
    )

    # When this snapshot was captured (distinct from created_at for precision)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # DSGVO: expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship()  # noqa: F821  # type: ignore[name-defined]
