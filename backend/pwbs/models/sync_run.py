"""Sync run ORM model (TASK-184).

Tracks individual connector sync executions with timing,
document counts and error details for the sync history UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SyncRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single connector sync execution."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        Index("idx_sync_runs_connection", "connection_id"),
        Index("idx_sync_runs_status", "status"),
        Index("idx_sync_runs_started", "started_at"),
    )

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
        comment="pending | running | success | failed",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    document_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    errors_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of {step, message} error objects",
    )

    # Relationships
    connection: Mapped["Connection"] = relationship(lazy="selectin")
