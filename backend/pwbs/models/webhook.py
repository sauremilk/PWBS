"""Outbound Webhook ORM models (TASK-189).

Webhook: user-registered endpoint that subscribes to PWBS events.
WebhookDelivery: delivery attempt log with status and response info.
"""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Webhook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-registered outbound webhook subscription."""

    __tablename__ = "webhooks"
    __table_args__ = (
        Index("idx_webhooks_user", "user_id"),
        Index("idx_webhooks_active", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="HMAC-SHA256 signing secret (generated server-side)",
    )
    events: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        comment="Subscribed event types, e.g. briefing.generated",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="webhook",
        lazy="selectin",
        order_by="desc(WebhookDelivery.created_at)",
    )


class WebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Record of a single webhook delivery attempt."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("idx_wh_deliveries_webhook", "webhook_id"),
        Index("idx_wh_deliveries_created", "created_at"),
    )

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(default=False, nullable=False)
    attempt: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="1-based attempt number",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    webhook: Mapped["Webhook"] = relationship(back_populates="deliveries")
