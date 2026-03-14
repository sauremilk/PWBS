"""API-Key authentication dependency for public API routes (TASK-150).

Extracts and validates API keys from the ``X-API-Key`` header.
Returns the owning ``User`` ORM instance for downstream handlers.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.db.postgres import get_db_session
from pwbs.developer.api_key_service import ApiKeyError, validate_api_key
from pwbs.models.user import User

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key_user(
    api_key: str | None = Security(_api_key_header),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Validate the API key from ``X-API-Key`` header and return the owner.

    Raises ``HTTPException(401)`` on missing/invalid key,
    ``HTTPException(403)`` on expired key.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_API_KEY", "message": "X-API-Key header required"},
        )

    try:
        _key_row, user = await validate_api_key(db, api_key)
    except ApiKeyError as exc:
        if exc.code == "API_KEY_EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": exc.code, "message": str(exc)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "Invalid or revoked API key"},
        )

    return user
