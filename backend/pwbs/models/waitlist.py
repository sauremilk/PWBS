"""Waitlist ORM model (TASK-178)."""

from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WaitlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "waitlist"

    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="landing")
