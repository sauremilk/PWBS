"""FeatureFlag ORM model (TASK-174).

Simple feature-flag storage: global toggle + per-user whitelist.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class FeatureFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feature_flags"

    flag_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    enabled_globally: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    enabled_for_users: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
