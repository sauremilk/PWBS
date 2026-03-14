"""Google OAuth2 Login Flow – Identity Provider (TASK-083).

GET  /api/v1/auth/google/auth-url  -- Generate OAuth2 auth URL (CSRF state)
POST /api/v1/auth/google/callback  -- Exchange code, create/link user, return JWT
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.db.redis_client import get_redis_client
from pwbs.models.user import User
from pwbs.services.auth import TokenPair, create_token_pair
from pwbs.services.user import _generate_encrypted_dek

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/google", tags=["auth"])

# Google OAuth2 / OpenID Connect endpoints
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# OpenID Connect scopes for identity
_GOOGLE_LOGIN_SCOPES = "openid email profile"

# State token TTL in Redis (seconds)
_STATE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class GoogleAuthUrlResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    auth_url: str
    state: str


class GoogleCallbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class GoogleCallbackResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool


# ---------------------------------------------------------------------------
# GET /auth/google/auth-url
# ---------------------------------------------------------------------------


@router.get(
    "/auth-url",
    response_model=GoogleAuthUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth2 auth URL generieren",
)
async def google_auth_url() -> GoogleAuthUrlResponse:
    """Generate a Google OAuth2 authorization URL with CSRF state."""
    settings = get_settings()

    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "GOOGLE_OAUTH_NOT_CONFIGURED",
                "message": "Google OAuth2 ist nicht konfiguriert",
            },
        )

    state = secrets.token_urlsafe(32)

    # Persist state in Redis for CSRF validation
    redis = get_redis_client()
    await redis.setex(f"google_login_state:{state}", _STATE_TTL, "valid")

    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_login_redirect_uri,
            "response_type": "code",
            "scope": _GOOGLE_LOGIN_SCOPES,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )

    auth_url = f"{_GOOGLE_AUTH_URL}?{params}"
    return GoogleAuthUrlResponse(auth_url=auth_url, state=state)


# ---------------------------------------------------------------------------
# POST /auth/google/callback
# ---------------------------------------------------------------------------


@router.post(
    "/callback",
    response_model=GoogleCallbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth2 Callback – Code austauschen",
    responses={
        400: {"description": "Ungültiger oder abgelaufener state"},
        401: {"description": "Google-Authentifizierung fehlgeschlagen"},
        503: {"description": "Google OAuth nicht konfiguriert"},
    },
)
async def google_callback(
    body: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_db_session),
) -> GoogleCallbackResponse:
    """Exchange Google authorization code for tokens and create/link user."""
    settings = get_settings()

    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "GOOGLE_OAUTH_NOT_CONFIGURED",
                "message": "Google OAuth2 ist nicht konfiguriert",
            },
        )

    # 1. Validate CSRF state
    await _validate_state(body.state)

    # 2. Exchange authorization code for tokens
    google_tokens = await _exchange_code(
        code=body.code,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret.get_secret_value(),
        redirect_uri=settings.google_login_redirect_uri,
    )

    # 3. Fetch user info from Google
    user_info = await _fetch_google_userinfo(google_tokens["access_token"])
    email = user_info.get("email", "").lower().strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "GOOGLE_EMAIL_MISSING",
                "message": "Google-Konto hat keine verifizierte E-Mail-Adresse",
            },
        )

    if not user_info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "GOOGLE_EMAIL_NOT_VERIFIED",
                "message": "Google E-Mail ist nicht verifiziert",
            },
        )

    # 4. Find or create PWBS user
    user, is_new = await _find_or_create_user(
        email=email,
        display_name=user_info.get("name", email.split("@")[0]),
        google_sub=user_info.get("sub", ""),
        db=db,
    )

    # 5. Issue PWBS JWT token pair
    pair: TokenPair = await create_token_pair(user.id, db)

    return GoogleCallbackResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
        is_new_user=is_new,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _validate_state(state: str) -> None:
    """Validate and consume a CSRF state token from Redis."""
    redis = get_redis_client()
    key = f"google_login_state:{state}"
    result = await redis.getdel(key)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATE",
                "message": "Ungültiger oder abgelaufener state-Parameter",
            },
        )


async def _exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, str]:
    """Exchange an authorization code for Google OAuth2 tokens."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if resp.status_code != 200:
        logger.warning(
            "Google token exchange failed: status=%d body=%s",
            resp.status_code,
            resp.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "GOOGLE_TOKEN_EXCHANGE_FAILED",
                "message": "Authorization-Code konnte nicht eingetauscht werden",
            },
        )

    return resp.json()


async def _fetch_google_userinfo(access_token: str) -> dict[str, str | bool]:
    """Fetch user profile from Google's userinfo endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if resp.status_code != 200:
        logger.warning(
            "Google userinfo fetch failed: status=%d",
            resp.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "GOOGLE_USERINFO_FAILED",
                "message": "Google-Nutzerprofil konnte nicht abgerufen werden",
            },
        )

    return resp.json()


async def _find_or_create_user(
    email: str,
    display_name: str,
    google_sub: str,
    db: AsyncSession,
) -> tuple[User, bool]:
    """Find an existing user by email or create a new one.

    Returns (user, is_new_user).
    """
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing is not None:
        return existing, False

    # Create new user (no password — Google-only auth)
    encryption_key_enc = _generate_encrypted_dek()
    new_user = User(
        email=email,
        display_name=display_name,
        password_hash="",  # Google-only user, no local password
        encryption_key_enc=encryption_key_enc,
    )
    db.add(new_user)
    await db.flush()

    logger.info("New user created via Google OAuth: email=%s", email)
    return new_user, True
