"""Referral ORM model (TASK-180).

Tracks user-to-user referrals with UUID-based invite codes.
No PII in the referral code itself (UUID only).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from pwbs.models.user import User  # noqa: F401


class Referral(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A referral link between an inviting user and a referred user."""

    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("code", name="uq_referrals_code"),
        UniqueConstraint("referee_id", name="uq_referrals_referee"),
        Index("idx_referrals_referrer", "referrer_id"),
        Index("idx_referrals_status", "status"),
    )

    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    referee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="pending",
    )
    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    referrer: Mapped["User"] = relationship(
        foreign_keys=[referrer_id],
        lazy="selectin",
    )
    referee: Mapped["User | None"] = relationship(
        foreign_keys=[referee_id],
        lazy="selectin",
    )
