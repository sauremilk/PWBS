"""Slack user mapping ORM model (TASK-141)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class SlackUserMapping(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "slack_user_mappings"
    __table_args__ = (
        UniqueConstraint(
            "slack_user_id", "slack_workspace_id",
            name="uq_slack_user_workspace",
        ),
        Index("idx_slack_mapping_pwbs_user", "pwbs_user_id"),
    )

    slack_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    slack_workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    pwbs_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
