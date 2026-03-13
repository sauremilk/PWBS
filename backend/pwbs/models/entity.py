"""Entity and EntityMention ORM models (TASK-020)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class Entity(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "normalized_name", name="uq_entities_user_type_name"),
        Index("idx_entities_user_type", "user_id", "entity_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    neo4j_node_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="entities")  # noqa: F821
    mentions: Mapped[list["EntityMention"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan", lazy="selectin",
    )


class EntityMention(Base):
    __tablename__ = "entity_mentions"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False, server_default="rule")

    entity: Mapped["Entity"] = relationship(back_populates="mentions")
    chunk: Mapped["Chunk"] = relationship(back_populates="entity_mentions")  # noqa: F821