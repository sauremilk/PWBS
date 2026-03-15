"""Assumption tracking API routes (TASK-155).

GET    /api/v1/assumptions              -- List assumptions (filterable)
POST   /api/v1/assumptions              -- Create assumption
GET    /api/v1/assumptions/{id}         -- Get single assumption
PATCH  /api/v1/assumptions/{id}/status  -- Update status
POST   /api/v1/assumptions/{id}/evidence -- Add evidence
GET    /api/v1/assumptions/timeline     -- Timeline for quarterly review
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.analytics.assumption_tracker import AssumptionTrackerService
from pwbs.api.dependencies.auth import get_current_user
from pwbs.core.exceptions import NotFoundError, ValidationError
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/assumptions",
    tags=["assumptions"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AssumptionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    source_decision_id: uuid.UUID | None = None
    source_document_id: uuid.UUID | None = None


class AssumptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    status: str
    status_changed_at: datetime | None
    status_reason: str | None
    evidence: list[dict[str, Any]]
    source_decision_id: uuid.UUID | None
    source_document_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class StatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(open|confirmed|refuted|revised)$")
    reason: str | None = None


class EvidenceAdd(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)
    source_id: uuid.UUID | None = None


class TimelineResponse(BaseModel):
    total: int
    status_counts: dict[str, int]
    recently_changed: list[dict[str, Any]]
    period_months: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[AssumptionResponse])
async def list_assumptions(
    response: Response,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[AssumptionResponse]:
    """List assumptions for the current user."""
    svc = AssumptionTrackerService(db)
    try:
        assumptions = await svc.list_by_owner(
            owner_id=user.id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return [AssumptionResponse.model_validate(a) for a in assumptions]


@router.post(
    "",
    response_model=AssumptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assumption(
    body: AssumptionCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AssumptionResponse:
    """Create a new assumption."""
    svc = AssumptionTrackerService(db)
    assumption = await svc.create(
        owner_id=user.id,
        title=body.title,
        description=body.description,
        source_decision_id=body.source_decision_id,
        source_document_id=body.source_document_id,
    )
    await db.commit()
    return AssumptionResponse.model_validate(assumption)


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    months: int = 3,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    """Get assumption timeline for quarterly review."""
    if months < 1 or months > 24:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_MONTHS",
                "message": "months must be between 1 and 24",
            },
        )
    svc = AssumptionTrackerService(db)
    data = await svc.get_timeline(owner_id=user.id, months=months)
    return TimelineResponse(**data)


@router.get("/{assumption_id}", response_model=AssumptionResponse)
async def get_assumption(
    assumption_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AssumptionResponse:
    """Get a single assumption by ID."""
    svc = AssumptionTrackerService(db)
    try:
        assumption = await svc.get(assumption_id, owner_id=user.id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return AssumptionResponse.model_validate(assumption)


@router.patch(
    "/{assumption_id}/status",
    response_model=AssumptionResponse,
)
async def update_assumption_status(
    assumption_id: uuid.UUID,
    body: StatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AssumptionResponse:
    """Update the lifecycle status of an assumption."""
    svc = AssumptionTrackerService(db)
    try:
        assumption = await svc.update_status(
            assumption_id=assumption_id,
            owner_id=user.id,
            new_status=body.status,
            reason=body.reason,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    await db.commit()
    return AssumptionResponse.model_validate(assumption)


@router.post(
    "/{assumption_id}/evidence",
    response_model=AssumptionResponse,
)
async def add_evidence(
    assumption_id: uuid.UUID,
    body: EvidenceAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AssumptionResponse:
    """Add evidence to an assumption's evidence trail."""
    svc = AssumptionTrackerService(db)
    try:
        assumption = await svc.add_evidence(
            assumption_id=assumption_id,
            owner_id=user.id,
            note=body.note,
            source_id=body.source_id,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    await db.commit()
    return AssumptionResponse.model_validate(assumption)
