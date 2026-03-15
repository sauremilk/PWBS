"""Assumption ORM model (TASK-155).

Tracks hypotheses / assumptions with lifecycle status:
open → confirmed | refuted | revised.

Provides longitudinal intelligence: which assumptions held,
which were falsified, and when the status changed.
Links to source decisions and documents for traceability.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Assumption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tracked assumption / hypothesis with lifecycle status."""

    __tablename__ = "assumptions"
    __table_args__ = (
        Index("idx_assumptions_user_status", "user_id", "status"),
        Index("idx_assumptions_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Core content
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle: open → confirmed | refuted | revised
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Evidence trail (JSONB array of {date, note, source_id?})
    evidence: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="[]"
    )

    # Optional link to originating decision
    source_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Optional link to source document
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Neo4j reference
    neo4j_node_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # DSGVO: expiration date
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="assumptions")  # noqa: F821
    source_decision: Mapped["Decision | None"] = relationship()  # noqa: F821
    source_document: Mapped["Document | None"] = relationship()  # noqa: F821
