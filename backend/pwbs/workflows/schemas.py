"""Pydantic schemas for workflow trigger-action definitions (TASK-160)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Trigger types ─────────────────────────────────────────────────


class TriggerType(str, Enum):
    """Supported trigger types for workflow rules."""

    NEW_DOCUMENT = "new_document"
    KEYWORD_MATCH = "keyword_match"
    SCHEDULE = "schedule"


class NewDocumentTrigger(BaseModel):
    """Fires when a new document is ingested."""

    type: Literal["new_document"] = "new_document"
    source_types: list[str] | None = Field(
        default=None,
        description="Filter by source types (e.g. ['notion', 'obsidian']). None = all.",
    )


class KeywordMatchTrigger(BaseModel):
    """Fires when a document contains specified keywords."""

    type: Literal["keyword_match"] = "keyword_match"
    keywords: list[str] = Field(
        ..., min_length=1, description="Keywords to match (case-insensitive)."
    )
    match_all: bool = Field(
        default=False, description="If true, ALL keywords must match."
    )


class ScheduleTrigger(BaseModel):
    """Fires on a cron schedule."""

    type: Literal["schedule"] = "schedule"
    cron_expression: str = Field(
        ...,
        description="Cron expression, e.g. '0 9 * * 1-5' (weekdays at 9:00).",
        pattern=r"^[\d\*\-/,\s]+$",
    )


TriggerConfig = NewDocumentTrigger | KeywordMatchTrigger | ScheduleTrigger


# ── Action types ──────────────────────────────────────────────────


class ActionType(str, Enum):
    """Supported action types for workflow rules."""

    EMAIL = "email"
    CREATE_REMINDER = "create_reminder"
    GENERATE_BRIEFING = "generate_briefing"


class EmailAction(BaseModel):
    """Send an email notification."""

    type: Literal["email"] = "email"
    subject_template: str = Field(
        ..., min_length=1, max_length=200, description="Email subject template."
    )
    body_template: str = Field(
        ..., min_length=1, max_length=5000, description="Email body template."
    )


class CreateReminderAction(BaseModel):
    """Create a reminder for the user."""

    type: Literal["create_reminder"] = "create_reminder"
    title_template: str = Field(
        ..., min_length=1, max_length=500, description="Reminder title template."
    )
    urgency: str = Field(default="medium", pattern=r"^(high|medium|low)$")


class GenerateBriefingAction(BaseModel):
    """Trigger briefing generation."""

    type: Literal["generate_briefing"] = "generate_briefing"
    briefing_type: str = Field(
        default="project",
        pattern=r"^(morning|meeting_prep|project|weekly)$",
    )


ActionConfig = EmailAction | CreateReminderAction | GenerateBriefingAction


# ── API request/response schemas ──────────────────────────────────


class WorkflowRuleCreate(BaseModel):
    """Request schema for creating a workflow rule."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    trigger_config: TriggerConfig
    action_config: ActionConfig
    is_active: bool = True


class WorkflowRuleUpdate(BaseModel):
    """Request schema for updating a workflow rule."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    trigger_config: TriggerConfig | None = None
    action_config: ActionConfig | None = None
    is_active: bool | None = None


class WorkflowRuleResponse(BaseModel):
    """Response schema for a workflow rule."""

    id: UUID
    name: str
    description: str
    trigger_config: dict[str, object]
    action_config: dict[str, object]
    is_active: bool
    execution_count: int
    created_at: datetime
    updated_at: datetime


class WorkflowRuleListResponse(BaseModel):
    """Response schema for listing workflow rules."""

    rules: list[WorkflowRuleResponse]
    total: int


class WorkflowExecutionResponse(BaseModel):
    """Response schema for a workflow execution log entry."""

    id: UUID
    rule_id: UUID
    trigger_event: str
    trigger_data: dict[str, object]
    action_result: str
    action_data: dict[str, object]
    executed_at: datetime


class WorkflowExecutionListResponse(BaseModel):
    """Response schema for listing workflow executions."""

    executions: list[WorkflowExecutionResponse]
    total: int