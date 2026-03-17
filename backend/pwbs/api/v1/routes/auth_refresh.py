"""Auth refresh endpoint (TASK-084).

POST /api/v1/auth/refresh  Rotate a refresh token and return a new token pair.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.exceptions import AuthenticationError
from pwbs.db.postgres import get_db_session
from pwbs.services.auth import TokenPair, rotate_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RefreshRequest(BaseModel):
    """POST body for token refresh."""

    model_config = ConfigDict(strict=True)

    refresh_token: str


class RefreshResponse(BaseModel):
    """Successful refresh response with new token pair."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description=(
        "Present a valid refresh token to obtain a new access + refresh token "
        "pair. The old refresh token is immediately invalidated (Token Rotation). "
        "Re-using an already-invalidated refresh token triggers replay-detection "
        "and revokes all tokens in the rotation family."
    ),
    responses={
        401: {"description": "Invalid, expired, or revoked refresh token"},
    },
)
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RefreshResponse:
    try:
        pair: TokenPair = await rotate_refresh_token(body.refresh_token, db)
        await db.commit()
    except AuthenticationError as exc:
        logger.warning("Token refresh failed: code=%s", exc.code)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": exc.code or "AUTHENTICATION_ERROR", "message": str(exc)},
        ) from exc

    return RefreshResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )
