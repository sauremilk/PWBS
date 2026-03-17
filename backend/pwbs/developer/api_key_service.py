"""API Key management service (TASK-150).

Handles creation, validation, revocation and usage tracking of API keys
for the public developer API.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.exceptions import PWBSError
from pwbs.models.api_key import ApiKey
from pwbs.models.user import User

logger = logging.getLogger(__name__)

_KEY_BYTES = 32
_PREFIX_LEN = 8
_MAX_KEYS_PER_USER = 10


class ApiKeyError(PWBSError):
    """Raised for API-key-related errors."""


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash the raw API key for storage."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_raw_key() -> str:
    """Generate a cryptographically random API key with ``pwbs_`` prefix."""
    token = secrets.token_urlsafe(_KEY_BYTES)
    return f"pwbs_{token}"


async def create_api_key(
    db: AsyncSession,
    owner_id: uuid.UUID,
    name: str,
    scopes: list[str] | None = None,
    rate_limit_per_minute: int = 60,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key.

    Returns ``(api_key_row, raw_key)``  the raw key is returned only once.
    """
    # Enforce per-user limit
    count_stmt = select(func.count()).where(ApiKey.owner_id == owner_id, ApiKey.is_active.is_(True))
    result = await db.execute(count_stmt)
    active_count = result.scalar_one()

    if active_count >= _MAX_KEYS_PER_USER:
        raise ApiKeyError(
            f"Maximum {_MAX_KEYS_PER_USER} active API keys per user",
            code="API_KEY_LIMIT_REACHED",
        )

    if scopes is None:
        scopes = ["read"]

    raw_key = generate_raw_key()
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:_PREFIX_LEN]

    api_key = ApiKey(
        owner_id=owner_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        scopes=scopes,
        rate_limit_per_minute=rate_limit_per_minute,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()
    return api_key, raw_key


async def validate_api_key(db: AsyncSession, raw_key: str) -> tuple[ApiKey, User]:
    """Validate a raw API key and return the key row + owning user.

    Raises ``ApiKeyError`` if the key is invalid, expired or revoked.
    """
    key_hash = _hash_key(raw_key)

    stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise ApiKeyError("Invalid API key", code="API_KEY_INVALID")

    now = datetime.now(UTC)
    if api_key.expires_at is not None and api_key.expires_at < now:
        raise ApiKeyError("API key expired", code="API_KEY_EXPIRED")

    # Update usage stats
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=now, usage_count=ApiKey.usage_count + 1)
    )

    # Load the owning user
    user_stmt = select(User).where(User.id == api_key.owner_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if user is None:
        raise ApiKeyError("API key owner not found", code="API_KEY_OWNER_MISSING")

    return api_key, user


async def list_api_keys(db: AsyncSession, owner_id: uuid.UUID) -> list[ApiKey]:
    """Return all API keys (active + inactive) for a user."""
    stmt = select(ApiKey).where(ApiKey.owner_id == owner_id).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: uuid.UUID, owner_id: uuid.UUID) -> ApiKey:
    """Revoke (deactivate) an API key."""
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.owner_id == owner_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise ApiKeyError("API key not found", code="API_KEY_NOT_FOUND")

    api_key.is_active = False
    await db.flush()
    return api_key


async def get_usage_stats(
    db: AsyncSession, key_id: uuid.UUID, owner_id: uuid.UUID
) -> dict[str, object]:
    """Return usage statistics for an API key."""
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.owner_id == owner_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise ApiKeyError("API key not found", code="API_KEY_NOT_FOUND")

    return {
        "key_id": str(api_key.id),
        "name": api_key.name,
        "prefix": api_key.key_prefix,
        "usage_count": api_key.usage_count,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "created_at": api_key.created_at.isoformat(),
        "is_active": api_key.is_active,
        "rate_limit_per_minute": api_key.rate_limit_per_minute,
        "scopes": api_key.scopes,
    }
