"""Decision ORM model (TASK-129).

Stores structured decisions with pro/contra arguments, assumptions,
dependencies, and status tracking. Links to users and optionally
to source documents.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Decision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A structured decision extracted or manually created."""

    __tablename__ = "decisions"
    __table_args__ = (
        Index("idx_decisions_user_status", "user_id", "status"),
        Index("idx_decisions_user_decided_at", "user_id", "decided_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    pro_arguments: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="[]"
    )
    contra_arguments: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="[]"
    )
    assumptions: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="[]"
    )
    dependencies: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="[]"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    decided_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional link to source document
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Neo4j reference for graph queries
    neo4j_node_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # DSGVO: expiration date
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="decisions")  # noqa: F821  # type: ignore[name-defined]
    source_document: Mapped[Document | None] = relationship()  # noqa: F821  # type: ignore[name-defined]
