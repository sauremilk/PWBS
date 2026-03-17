"""Auth API endpoints (TASK-086).

POST /api/v1/auth/register  -- Register new user
POST /api/v1/auth/login     -- Login with email/password
POST /api/v1/auth/logout    -- Invalidate refresh token
GET  /api/v1/auth/me        -- Current user profile

POST /api/v1/auth/refresh is in auth_refresh.py (TASK-084).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.audit.audit_service import AuditAction, get_client_ip, log_event
from pwbs.core.exceptions import AuthenticationError, ValidationError
from pwbs.core.posthog import capture as posthog_capture
from pwbs.core.posthog import identify as posthog_identify
from pwbs.db.postgres import get_db_session
from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.models.connection import Connection
from pwbs.models.user import User
from pwbs.services.auth import (
    TokenPair,
    create_token_pair,
    revoke_refresh_token,
    validate_access_token,
)
from pwbs.services.user import RegisterRequest, register_user, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: uuid.UUID
    access_token: str
    refresh_token: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str = "logged_out"


class MeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with email and password. "
    "Returns a JWT token pair (access + refresh). Email must be unique.",
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    try:
        pair: TokenPair = await register_user(body, db)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code or "VALIDATION_ERROR", "message": str(exc)},
        ) from exc
    except AuthenticationError as exc:
        # Generic error for duplicate email (no email leak)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code or "REGISTRATION_FAILED", "message": str(exc)},
        ) from exc

    # Extract user_id from the access token (it was just created)
    payload = validate_access_token(pair.access_token)

    ip = get_client_ip(request)
    await log_event(
        db,
        action=AuditAction.USER_REGISTERED,
        user_id=payload.user_id,
        resource_type="user",
        resource_id=payload.user_id,
        ip_address=ip,
    )
    await db.commit()

    posthog_capture(str(payload.user_id), "auth_user_registered")

    return RegisterResponse(
        user_id=payload.user_id,
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description="Authenticates a user with email and password. "
    "Returns a JWT token pair. Constant-time password comparison even for unknown users.",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    # Constant-time-ish: always verify a hash even if user not found
    stmt = select(User).where(User.email == body.email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    ip = get_client_ip(request)

    if user is None or not verify_password(body.password, user.password_hash):
        # Log failed attempt as security event (A09) before raising
        await log_event(
            db,
            action=AuditAction.USER_LOGIN_FAILED,
            ip_address=ip,
            metadata={"reason": "invalid_credentials"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "E-Mail oder Passwort ist falsch",
            },
        )

    pair = await create_token_pair(user.id, db)
    await log_event(
        db,
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip,
    )
    await db.commit()

    posthog_capture(str(user.id), "auth_user_logged_in")

    # PostHog identify: sync user properties for analytics segmentation
    conn_count_stmt = (
        select(func.count())
        .select_from(Connection)
        .where(
            Connection.user_id == user.id,
            Connection.status == "active",
        )
    )
    briefing_count_stmt = (
        select(func.count())
        .select_from(BriefingORM)
        .where(
            BriefingORM.user_id == user.id,
        )
    )
    conn_count = (await db.execute(conn_count_stmt)).scalar_one()
    briefing_count = (await db.execute(briefing_count_stmt)).scalar_one()
    posthog_identify(
        str(user.id),
        {
            "connected_sources_count": conn_count,
            "total_briefings_generated": briefing_count,
            "account_created_at": user.created_at.isoformat() if user.created_at else None,
            "plan": "beta",
        },
    )

    return LoginResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout (invalidate refresh token)",
    description=(
        "Invalidates the provided refresh token. The access token remains valid until expiry."
    ),
)
async def logout(
    body: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LogoutResponse:
    try:
        await revoke_refresh_token(body.refresh_token, db)
    except AuthenticationError:
        # Token already revoked or invalid -- still return success
        pass

    await log_event(
        db,
        action=AuditAction.USER_LOGOUT,
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=get_client_ip(request),
    )
    await db.commit()

    posthog_capture(str(current_user.id), "auth_user_logged_out")

    return LogoutResponse()


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description=(
        "Returns the profile of the currently authenticated user"
        " (ID, email, display name, creation date)."
    ),
)
async def me(
    current_user: User = Depends(get_current_user),
) -> MeResponse:
    return MeResponse(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        created_at=current_user.created_at,
    )
