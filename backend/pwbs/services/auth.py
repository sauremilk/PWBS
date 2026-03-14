"""JWT authentication service (TASK-081, TASK-084).

Provides access-token generation (RS256-signed) and opaque refresh-token
management backed by the ``refresh_tokens`` table.

Security notes:
- Access tokens are signed with RS256 (asymmetric).  The private key is
  loaded from the ``JWT_PRIVATE_KEY`` environment variable; the public key
  from ``JWT_PUBLIC_KEY``.  Neither is ever logged.
- Refresh tokens are opaque (``secrets.token_urlsafe``), stored in the DB
  as SHA-256 hashes so a database leak does not compromise active sessions.
- Token rotation and replay-detection are handled at the service layer.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update

from pwbs.core.config import get_settings
from pwbs.core.exceptions import AuthenticationError
from pwbs.models.refresh_token import RefreshToken

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------


class TokenPayload(BaseModel):
    """Decoded JWT access-token payload."""

    model_config = ConfigDict(frozen=True)

    user_id: uuid.UUID
    exp: datetime
    iat: datetime


class TokenPair(BaseModel):
    """Access + refresh token pair returned to the client."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hash_token(token: str) -> str:
    """SHA-256 hash of a plaintext token for safe DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_signing_key() -> str:
    """Return the RSA private key (PEM) for signing access tokens."""
    settings = get_settings()
    key = settings.jwt_private_key.get_secret_value()
    if not key:
        # Fallback to symmetric secret for dev/test when no RSA key is provided
        return settings.jwt_secret_key.get_secret_value()
    return key


def _get_verification_key() -> str:
    """Return the RSA public key (PEM) for verifying access tokens."""
    settings = get_settings()
    key = settings.jwt_public_key
    if not key:
        # Fallback to symmetric secret for dev/test when no RSA key is provided
        return settings.jwt_secret_key.get_secret_value()
    return key


def _get_algorithm() -> str:
    """Return the configured JWT algorithm."""
    return get_settings().jwt_algorithm


# ---------------------------------------------------------------------------
# Access-token operations
# ---------------------------------------------------------------------------


def create_access_token(user_id: uuid.UUID) -> str:
    """Create an RS256-signed JWT access token.

    Claims: `sub` (user_id), `exp`, `iat`.
    Lifetime is configured via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 15).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    claims = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(claims, _get_signing_key(), algorithm=_get_algorithm())


def validate_access_token(token: str) -> TokenPayload:
    """Validate and decode a JWT access token.

    Raises `AuthenticationError` if the token is invalid, expired, or
    its signature cannot be verified.
    """
    try:
        payload = jwt.decode(
            token,
            _get_verification_key(),
            algorithms=[_get_algorithm()],
            options={"require_exp": True, "require_iat": True},
        )
    except JWTError as exc:
        raise AuthenticationError(
            "Invalid or expired access token",
            code="INVALID_ACCESS_TOKEN",
        ) from exc

    try:
        return TokenPayload(
            user_id=uuid.UUID(payload["sub"]),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except (KeyError, ValueError) as exc:
        raise AuthenticationError(
            "Malformed access token payload",
            code="MALFORMED_TOKEN_PAYLOAD",
        ) from exc


# ---------------------------------------------------------------------------
# Refresh-token operations
# ---------------------------------------------------------------------------


async def create_refresh_token(
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    family_id: uuid.UUID | None = None,
) -> str:
    """Generate an opaque refresh token and persist its hash in the DB.

    Args:
        user_id: Owner of the token.
        db: Active database session (caller must commit).
        family_id: Optional rotation-family ID.  `None` starts a new family.

    Returns:
        The plaintext refresh token (sent to the client exactly once).
    """
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)

    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id or uuid.uuid4(),
        expires_at=now + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(db_token)
    await db.flush()

    logger.info("Refresh token created: user_id=%s family_id=%s", user_id, db_token.family_id)
    return raw_token


async def validate_refresh_token(
    token: str,
    db: AsyncSession,
) -> RefreshToken:
    """Look up and validate a refresh token.

    Raises `AuthenticationError` if the token does not exist, is expired,
    or has been revoked.
    """
    token_hash = _hash_token(token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if db_token is None:
        raise AuthenticationError(
            "Invalid refresh token",
            code="INVALID_REFRESH_TOKEN",
        )

    if db_token.revoked_at is not None:
        # Replay detected  revoke entire family (TASK-084 builds on this)
        await _revoke_token_family(db_token.family_id, db)
        raise AuthenticationError(
            "Refresh token has been revoked (possible replay attack)",
            code="REFRESH_TOKEN_REVOKED",
        )

    now = datetime.now(timezone.utc)
    if db_token.expires_at.tzinfo is None:
        expires_at = db_token.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = db_token.expires_at
    if now >= expires_at:
        raise AuthenticationError(
            "Refresh token has expired",
            code="REFRESH_TOKEN_EXPIRED",
        )

    return db_token


async def revoke_refresh_token(
    token: str,
    db: AsyncSession,
) -> None:
    """Revoke a single refresh token by its plaintext value."""
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def revoke_all_user_tokens(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Revoke every active refresh token for a user.

    Returns the number of tokens revoked.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    count = result.rowcount  # type: ignore[union-attr]
    if count:
        logger.info("Revoked %d refresh tokens: user_id=%s", count, user_id)
    return count


async def _revoke_token_family(
    family_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Revoke all tokens in a rotation family (replay-detection helper)."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    logger.warning("Replay detected  revoked token family: family_id=%s", family_id)


# ---------------------------------------------------------------------------
# Combined token-pair generation
# ---------------------------------------------------------------------------


async def create_token_pair(
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    family_id: uuid.UUID | None = None,
) -> TokenPair:
    """Create a full access + refresh token pair.

    Convenience wrapper that combines `create_access_token` and
    `create_refresh_token` into a single call.
    """
    settings = get_settings()
    access = create_access_token(user_id)
    refresh = await create_refresh_token(user_id, db, family_id=family_id)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )

# ---------------------------------------------------------------------------
# Token rotation (TASK-084)
# ---------------------------------------------------------------------------


async def rotate_refresh_token(
    old_token: str,
    db: AsyncSession,
) -> TokenPair:
    """Rotate a refresh token: validate → revoke old → issue new pair.

    Implements the full Token Rotation flow:
    1. Validate the presented refresh token (signature, expiry, revocation).
    2. If the token is already revoked → replay-detection triggers and
       **all** tokens in the rotation family are revoked.
    3. Revoke the old token immediately.
    4. Issue a new access + refresh token pair in the same family.

    Raises ``AuthenticationError`` (HTTP 401) when the token is invalid,
    expired, or has been revoked.
    """
    # Step 1: validate (replay-detection fires inside if revoked)
    db_token = await validate_refresh_token(old_token, db)

    # Step 2: revoke the consumed token
    now = datetime.now(timezone.utc)
    db_token.revoked_at = now
    await db.flush()

    # Step 3: issue new pair in the same family
    pair = await create_token_pair(
        db_token.user_id, db, family_id=db_token.family_id,
    )

    logger.info(
        "Refresh token rotated: user_id=%s family_id=%s",
        db_token.user_id,
        db_token.family_id,
    )
    return pair