"""Workflow ORM models (TASK-160).

WorkflowRule: User-defined trigger-action rule stored as JSON.
WorkflowExecution: Execution log for each rule firing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pwbs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-defined workflow automation rule."""

    __tablename__ = "workflow_rules"
    __table_args__ = (
        Index("idx_workflow_rules_user", "user_id"),
        Index("idx_workflow_rules_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    # Trigger definition as JSON:
    # {"type": "new_document"|"keyword_match"|"schedule",  ...trigger-specific fields}
    trigger_config: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False
    )

    # Action definition as JSON:
    # {"type": "email"|"create_reminder"|"generate_briefing", ...action-specific fields}
    action_config: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Execution count for monitoring
    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # DSGVO: expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship()  # noqa: F821
    executions: Mapped[list[WorkflowExecution]] = relationship(
        back_populates="rule", cascade="all, delete-orphan", lazy="selectin"
    )


class WorkflowExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Log entry for a single workflow rule execution."""

    __tablename__ = "workflow_executions"
    __table_args__ = (
        Index("idx_workflow_exec_rule", "rule_id"),
        Index("idx_workflow_exec_user_time", "user_id", "executed_at"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Which trigger event fired this execution
    trigger_event: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured trigger event data
    trigger_data: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="{}"
    )

    # Action result: "success"|"failed"|"skipped"
    action_result: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured action result data
    action_data: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, server_default="{}"
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    rule: Mapped[WorkflowRule] = relationship(back_populates="executions")
    user: Mapped[User] = relationship()  # noqa: F821
