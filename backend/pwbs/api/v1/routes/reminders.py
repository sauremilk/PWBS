"""Reminders API endpoints (TASK-131).

GET    /api/v1/reminders            -- List pending reminders (sorted by urgency)
PATCH  /api/v1/reminders/{id}       -- Update reminder status
POST   /api/v1/reminders/trigger    -- Manually run trigger engine
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.reminders.service import (
    get_pending_reminders,
    run_trigger_engine,
    update_reminder_status,
)
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import ReminderStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/reminders",
    tags=["reminders"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reminder_type: str
    title: str
    description: str
    status: str
    urgency: str
    due_at: datetime | None = None
    responsible_person: str | None = None
    source_document_id: uuid.UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    count: int


class UpdateStatusRequest(BaseModel):
    status: ReminderStatus


class TriggerResponse(BaseModel):
    new_reminders: int
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    response: Response,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReminderListResponse:
    """List pending reminders for the authenticated user, sorted by urgency."""
    if limit < 1 or limit > 200:
        limit = 50
    reminders = await get_pending_reminders(db, user_id=user.id, limit=limit)
    return ReminderListResponse(
        items=[ReminderResponse.model_validate(r) for r in reminders],
        count=len(reminders),
    )


@router.patch("/{reminder_id}", response_model=ReminderResponse)
async def patch_reminder_status(
    reminder_id: uuid.UUID,
    body: UpdateStatusRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReminderResponse:
    """Update a reminder's status (acknowledge, dismiss, snooze)."""
    reminder = await update_reminder_status(
        db,
        reminder_id=reminder_id,
        user_id=user.id,
        new_status=body.status,
    )
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Reminder not found"},
        )
    await db.commit()
    return ReminderResponse.model_validate(reminder)


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_engine(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> TriggerResponse:
    """Manually trigger the reminder engine for the authenticated user."""
    new_reminders = await run_trigger_engine(db, user_id=user.id)
    await db.commit()
    return TriggerResponse(
        new_reminders=len(new_reminders),
        message=f"{len(new_reminders)} neue Erinnerungen generiert.",
    )