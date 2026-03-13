"""User ORM model (TASK-015)."""

from __future__ import annotations

import uuid

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_enc: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    connections: Mapped[list["Connection"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )
    chunks: Mapped[list["Chunk"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )
    entities: Mapped[list["Entity"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )
    briefings: Mapped[list["Briefing"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        back_populates="user", lazy="selectin",
    )