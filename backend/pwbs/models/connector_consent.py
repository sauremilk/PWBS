"""ConnectorConsent ORM model (TASK-173)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConnectorConsent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks explicit user consent per data-source connector (DSGVO Art. 7)."""

    __tablename__ = "connector_consents"
    __table_args__ = (
        UniqueConstraint("owner_id", "connector_type", name="uq_consent_owner_type"),
        Index("idx_consent_owner", "owner_id"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    connector_type: Mapped[str] = mapped_column(Text, nullable=False)
    consent_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
