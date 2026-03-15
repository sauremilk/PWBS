"""Feedback API endpoints (TASK-188).

POST /api/v1/feedback            -- Submit feedback (authenticated user)
GET  /api/v1/feedback/admin      -- List all feedbacks paginated (admin)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.feedback import Feedback
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

VALID_FEEDBACK_TYPES = {"bug", "feature", "praise"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ContextMeta(BaseModel):
    """Non-sensitive browser/page context attached automatically."""

    url: str = ""
    browser_info: str = ""
    viewport_size: str = ""


class SubmitFeedbackRequest(BaseModel):
    feedback_type: str = Field(
        ...,
        pattern="^(bug|feature|praise)$",
        description="Type of feedback",
    )
    message: str = Field(..., min_length=1, max_length=5000)
    context: ContextMeta = Field(default_factory=ContextMeta)


class FeedbackItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feedback_type: str
    message: str
    context_meta: dict
    created_at: datetime
    user_email: str | None = None


class SubmitFeedbackResponse(BaseModel):
    id: uuid.UUID
    message: str = "feedback_submitted"


class AdminFeedbackListResponse(BaseModel):
    items: list[FeedbackItemResponse]
    total: int
    has_more: bool


# ---------------------------------------------------------------------------
# POST /api/v1/feedback
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=SubmitFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    body: SubmitFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SubmitFeedbackResponse:
    """Submit a bug report, feature request or praise with context metadata."""
    feedback = Feedback(
        user_id=current_user.id,
        feedback_type=body.feedback_type,
        message=body.message,
        context_meta={
            "url": body.context.url,
            "browser_info": body.context.browser_info,
            "viewport_size": body.context.viewport_size,
        },
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    logger.info("Feedback %s submitted by user %s", feedback.id, current_user.id)

    return SubmitFeedbackResponse(id=feedback.id)


# ---------------------------------------------------------------------------
# GET /api/v1/feedback/admin
# ---------------------------------------------------------------------------


@router.get(
    "/admin",
    response_model=AdminFeedbackListResponse,
    summary="List all feedbacks (admin)",
)
async def list_feedbacks_admin(
    offset: int = 0,
    limit: int = 20,
    feedback_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AdminFeedbackListResponse:
    """List all feedbacks with pagination. Requires admin role."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin access required"},
        )

    limit = max(1, min(limit, 50))

    base = select(Feedback)
    if feedback_type and feedback_type in VALID_FEEDBACK_TYPES:
        base = base.where(Feedback.feedback_type == feedback_type)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginated results
    stmt = base.order_by(Feedback.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    feedbacks = list(result.scalars().all())

    items = [
        FeedbackItemResponse(
            id=fb.id,
            feedback_type=fb.feedback_type,
            message=fb.message,
            context_meta=fb.context_meta,
            created_at=fb.created_at,
            user_email=fb.user.email if fb.user else None,
        )
        for fb in feedbacks
    ]

    return AdminFeedbackListResponse(
        items=items,
        total=total,
        has_more=(offset + limit) < total,
    )
