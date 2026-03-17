"""Plugin and InstalledPlugin ORM models (TASK-151).

Stores community plugins published to the marketplace and tracks
per-user installations with configuration and lifecycle state.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Plugin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A marketplace plugin published by a developer."""

    __tablename__ = "plugins"
    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_plugins_slug_version"),
        Index("idx_plugins_type_status", "plugin_type", "status"),
        Index("idx_plugins_author", "author_id"),
    )

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    plugin_type: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    manifest: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        server_default="{}",
    )
    entry_point: Mapped[str] = mapped_column(Text, nullable=False)
    permissions: Mapped[list] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        server_default="[]",
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending_review",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    install_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    rating_sum: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    rating_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    author: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    installations: Mapped[list["InstalledPlugin"]] = relationship(
        back_populates="plugin",
        cascade="all, delete-orphan",
    )


class InstalledPlugin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks a user's installation of a specific plugin."""

    __tablename__ = "installed_plugins"
    __table_args__ = (
        UniqueConstraint("user_id", "plugin_id", name="uq_installed_plugins_user_plugin"),
        Index("idx_installed_plugins_user", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plugin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB,
        nullable=False,
        server_default="{}",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    plugin: Mapped["Plugin"] = relationship(
        back_populates="installations",
        lazy="selectin",
    )


class PluginRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's rating/review for a marketplace plugin (TASK-165)."""

    __tablename__ = "plugin_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "plugin_id", name="uq_plugin_ratings_user_plugin"),
        Index("idx_plugin_ratings_plugin", "plugin_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plugin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plugins.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")  # noqa: F821
    plugin: Mapped["Plugin"] = relationship(lazy="selectin")  # noqa: F821
