"""Waitlist API endpoint (TASK-178).

POST /api/v1/waitlist  -- Add email to beta waitlist (public, no auth)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.db.postgres import get_db_session
from pwbs.models.waitlist import WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])


class WaitlistRequest(BaseModel):
    email: EmailStr
    source: str = "landing"


class WaitlistResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "",
    response_model=WaitlistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def join_waitlist(
    body: WaitlistRequest,
    db: AsyncSession = Depends(get_db_session),
) -> WaitlistResponse:
    """Add an email to the beta waitlist.

    Public endpoint — no authentication required.
    Returns 201 for new entries, 200 for already-registered emails
    (no information leakage about existing entries).
    """
    email_lower = body.email.lower().strip()

    existing = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email_lower))
    if existing.scalar_one_or_none() is not None:
        # Silently succeed — don't reveal whether the email was already registered
        return WaitlistResponse(
            success=True,
            message="Vielen Dank! Sie wurden auf die Warteliste gesetzt.",
        )

    entry = WaitlistEntry(email=email_lower, source=body.source)
    db.add(entry)
    await db.commit()

    logger.info("Waitlist signup: source=%s", body.source)
    return WaitlistResponse(
        success=True,
        message="Vielen Dank! Sie wurden auf die Warteliste gesetzt.",
    )
