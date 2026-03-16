"""Referral API endpoints (TASK-180).

GET  /api/v1/referrals         -- List own referrals + own code
POST /api/v1/referrals/convert -- Convert a referral code during registration
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.referral import Referral
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/referrals", tags=["referrals"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReferralResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    status: str
    referee_email: str | None = None
    converted_at: datetime | None = None
    created_at: datetime


class ReferralListResponse(BaseModel):
    my_code: str
    referrals: list[ReferralResponse]
    total_converted: int


class ConvertReferralRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)


class ConvertReferralResponse(BaseModel):
    message: str = "referral_linked"
    referrer_display_name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_or_create_referral_code(
    db: AsyncSession, user_id: uuid.UUID
) -> str:
    """Return existing referral code or create a new one (idempotent)."""
    stmt = select(Referral).where(
        Referral.referrer_id == user_id,
        Referral.referee_id.is_(None),
        Referral.status == "pending",
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        return existing.code

    new_referral = Referral(
        referrer_id=user_id,
        code=str(uuid.uuid4()),
        status="pending",
    )
    db.add(new_referral)
    await db.flush()
    return new_referral.code


# ---------------------------------------------------------------------------
# GET /api/v1/referrals
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=ReferralListResponse,
    summary="List own referrals and referral code",
)
async def list_referrals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReferralListResponse:
    """Return the authenticated user's referral code and all referrals."""
    my_code = await get_or_create_referral_code(db, current_user.id)

    stmt = (
        select(Referral)
        .where(Referral.referrer_id == current_user.id)
        .order_by(Referral.created_at.desc())
    )
    result = await db.execute(stmt)
    referrals = list(result.scalars().all())

    await db.commit()

    items: list[ReferralResponse] = []
    for ref in referrals:
        referee_email: str | None = None
        if ref.referee is not None:
            referee_email = ref.referee.email
        items.append(
            ReferralResponse(
                id=ref.id,
                code=ref.code,
                status=ref.status,
                referee_email=referee_email,
                converted_at=ref.converted_at,
                created_at=ref.created_at,
            )
        )

    total_converted = sum(1 for r in referrals if r.status == "converted")

    return ReferralListResponse(
        my_code=my_code,
        referrals=items,
        total_converted=total_converted,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/referrals/convert
# ---------------------------------------------------------------------------


@router.post(
    "/convert",
    response_model=ConvertReferralResponse,
    summary="Convert a referral code (link new user to referrer)",
)
async def convert_referral(
    body: ConvertReferralRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConvertReferralResponse:
    """Link the current user as referee to the referral code's owner.

    Called after registration when ?ref=UUID was present.
    Idempotent: if user is already linked to this code, returns success.
    """
    # Find the referral code
    stmt = select(Referral).where(Referral.code == body.code)
    result = await db.execute(stmt)
    referral = result.scalar_one_or_none()

    if referral is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REFERRAL_NOT_FOUND", "message": "Invalid referral code"},
        )

    # Prevent self-referral
    if referral.referrer_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SELF_REFERRAL", "message": "Cannot use own referral code"},
        )

    # Idempotent: already converted by this user
    if referral.referee_id == current_user.id:
        return ConvertReferralResponse(
            referrer_display_name=referral.referrer.display_name,
        )

    # Check if code is already used by someone else
    if referral.referee_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_USED", "message": "Referral code already used"},
        )

    # Check if current user already has a referral from someone
    existing_stmt = select(Referral).where(
        Referral.referee_id == current_user.id
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_REFERRED",
                "message": "User already has a referral",
            },
        )

    # Convert the referral
    referral.referee_id = current_user.id
    referral.status = "converted"
    referral.converted_at = datetime.now(UTC)

    # Create a new pending code for the referrer (so they can invite more)
    new_pending = Referral(
        referrer_id=referral.referrer_id,
        code=str(uuid.uuid4()),
        status="pending",
    )
    db.add(new_pending)

    await db.commit()
    await db.refresh(referral)

    return ConvertReferralResponse(
        referrer_display_name=referral.referrer.display_name,
    )
