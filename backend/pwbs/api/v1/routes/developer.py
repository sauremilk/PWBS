"""Developer Portal API routes (TASK-150).

Key management:
  GET    /api/v1/developer/keys             List user's API keys
  POST   /api/v1/developer/keys             Create new API key
  DELETE /api/v1/developer/keys/{key_id}    Revoke an API key
  GET    /api/v1/developer/keys/{key_id}/usage  Usage stats for a key
  GET    /api/v1/developer/docs             API documentation info
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.developer.api_key_service import (
    ApiKeyError,
    create_api_key,
    get_usage_stats,
    list_api_keys,
    revoke_api_key,
)
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/developer",
    tags=["developer"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateKeyRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str = Field(..., min_length=1, max_length=100, description="Human-readable key name")
    scopes: list[str] = Field(
        default=["read"],
        description="Permission scopes: read, write, search, briefings",
    )
    rate_limit_per_minute: int = Field(
        default=60, ge=1, le=1000, description="Max requests per minute"
    )
    expires_at: datetime | None = Field(default=None, description="Optional expiry (ISO-8601)")


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    rate_limit_per_minute: int
    is_active: bool
    usage_count: int
    last_used_at: datetime | None
    created_at: datetime
    expires_at: datetime | None


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only on creation -- includes the raw key (shown once)."""

    raw_key: str


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse]
    total: int


class UsageStatsResponse(BaseModel):
    key_id: str
    name: str
    prefix: str
    usage_count: int
    last_used_at: str | None
    created_at: str
    is_active: bool
    rate_limit_per_minute: int
    scopes: list[str]


class ApiDocsResponse(BaseModel):
    openapi_url: str
    docs_url: str
    version: str
    available_scopes: list[str]
    rate_limit_info: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/keys",
    response_model=ApiKeyListResponse,
    summary="List API keys",
)
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiKeyListResponse:
    """List all API keys for the authenticated user."""
    keys = await list_api_keys(db, current_user.id)
    return ApiKeyListResponse(
        keys=[ApiKeyResponse.model_validate(k) for k in keys],
        total=len(keys),
    )


@router.post(
    "/keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
)
async def create_key(
    body: CreateKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiKeyCreatedResponse:
    """Create a new API key. The raw key is returned **only once**."""
    valid_scopes = {"read", "write", "search", "briefings"}
    invalid = set(body.scopes) - valid_scopes
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_SCOPES", "message": f"Invalid scopes: {invalid}"},
        )

    try:
        api_key, raw_key = await create_api_key(
            db=db,
            owner_id=current_user.id,
            name=body.name,
            scopes=body.scopes,
            rate_limit_per_minute=body.rate_limit_per_minute,
            expires_at=body.expires_at,
        )
        await db.commit()
    except ApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    resp = ApiKeyCreatedResponse.model_validate(api_key)
    resp.raw_key = raw_key
    return resp


@router.delete(
    "/keys/{key_id}",
    response_model=MessageResponse,
    summary="Revoke API key",
)
async def delete_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Revoke an API key (cannot be undone)."""
    try:
        await revoke_api_key(db, key_id, current_user.id)
        await db.commit()
    except ApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return MessageResponse(message="API key revoked")


@router.get(
    "/keys/{key_id}/usage",
    response_model=UsageStatsResponse,
    summary="API key usage statistics",
)
async def key_usage(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UsageStatsResponse:
    """Return usage statistics for a specific API key."""
    try:
        stats = await get_usage_stats(db, key_id, current_user.id)
    except ApiKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return UsageStatsResponse(**stats)


@router.get(
    "/docs",
    response_model=ApiDocsResponse,
    summary="API documentation info",
)
async def docs_info() -> ApiDocsResponse:
    """Return metadata about the public API documentation."""
    return ApiDocsResponse(
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/public/docs",
        version="1.0.0",
        available_scopes=["read", "write", "search", "briefings"],
        rate_limit_info="Default 60 requests/minute per API key, configurable up to 1000.",
    )
