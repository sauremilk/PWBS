"""User ORM model (TASK-015)."""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, Text, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    email_briefing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    briefing_email_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(6, 30),
        server_default="06:30:00",
    )
    vertical_profile: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="general",
        server_default="general",
    )
    timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Europe/Berlin",
        server_default="Europe/Berlin",
    )
    language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="de",
        server_default="de",
    )
    briefing_auto_generate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    reminder_frequency: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="daily",
        server_default="daily",
    )
    briefing_preferences: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        server_default=None,
    )
    onboarding_step: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    connections: Mapped[list[Connection]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list[Document]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chunks: Mapped[list[Chunk]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    entities: Mapped[list[Entity]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    decisions: Mapped[list[Decision]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    briefings: Mapped[list[Briefing]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(  # noqa: F821
        back_populates="user",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subscription: Mapped[Subscription | None] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    profiles: Mapped[list[UserProfile]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    api_keys: Mapped[list[ApiKey]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    assumptions: Mapped[list[Assumption]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    saved_searches: Mapped[list[SavedSearch]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    search_history_entries: Mapped[list[SearchHistory]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
