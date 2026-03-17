"""Chunk ORM model (TASK-019)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class Chunk(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (Index("idx_chunks_document", "document_id"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weaviate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="chunks")  # noqa: F821
    user: Mapped[User] = relationship(back_populates="chunks")  # noqa: F821
    entity_mentions: Mapped[list[EntityMention]] = relationship(  # noqa: F821
        back_populates="chunk",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
