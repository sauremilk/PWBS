"""LLM Audit Log ORM model (TASK-172).

Tracks every LLM call with timestamp, provider, model, token counts.
Supports DSGVO transparency reporting.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pwbs.models.base import Base, UUIDPrimaryKeyMixin


class LlmAuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "llm_audit_log"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    purpose: Mapped[str] = mapped_column(Text, nullable=False, server_default="general")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
