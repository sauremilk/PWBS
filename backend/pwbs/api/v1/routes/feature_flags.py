"""Feature Flags Admin API endpoints (TASK-174).

POST   /api/v1/admin/feature-flags       -- Create/update a feature flag
GET    /api/v1/admin/feature-flags       -- List all feature flags
GET    /api/v1/admin/feature-flags/{name} -- Check flag status for current user
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.feature_flags.service import FeatureFlagService
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/feature-flags",
    tags=["admin", "feature-flags"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class FeatureFlagRequest(BaseModel):
    flag_name: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9_.-]+$")
    enabled_globally: bool | None = None
    enabled_for_users: list[uuid.UUID] | None = None


class FeatureFlagResponse(BaseModel):
    flag_name: str
    enabled_globally: bool
    enabled_for_users: list[uuid.UUID]


class FeatureFlagListResponse(BaseModel):
    flags: list[FeatureFlagResponse]


class FeatureFlagCheckResponse(BaseModel):
    flag_name: str
    enabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(user: User) -> None:
    """Raise 403 if user is not an admin."""
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADMIN_REQUIRED", "message": "Admin privileges required"},
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=FeatureFlagResponse, status_code=201)
async def upsert_feature_flag(
    body: FeatureFlagRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureFlagResponse:
    """Create or update a feature flag. Admin only."""
    _require_admin(user)

    svc = FeatureFlagService(db)
    flag = await svc.upsert(
        flag_name=body.flag_name,
        enabled_globally=body.enabled_globally,
        enabled_for_users=body.enabled_for_users,
    )

    return FeatureFlagResponse(
        flag_name=flag.flag_name,
        enabled_globally=flag.enabled_globally,
        enabled_for_users=flag.enabled_for_users or [],
    )


@router.get("", response_model=FeatureFlagListResponse)
async def list_feature_flags(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureFlagListResponse:
    """List all feature flags. Admin only."""
    _require_admin(user)

    svc = FeatureFlagService(db)
    flags = await svc.get_all()

    return FeatureFlagListResponse(
        flags=[
            FeatureFlagResponse(
                flag_name=f.flag_name,
                enabled_globally=f.enabled_globally,
                enabled_for_users=f.enabled_for_users or [],
            )
            for f in flags
        ]
    )


@router.get("/{flag_name}", response_model=FeatureFlagCheckResponse)
async def check_feature_flag(
    flag_name: str,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureFlagCheckResponse:
    """Check if a feature flag is enabled for the current user."""
    svc = FeatureFlagService(db)
    enabled = await svc.is_enabled(flag_name, user.id)

    return FeatureFlagCheckResponse(flag_name=flag_name, enabled=enabled)
