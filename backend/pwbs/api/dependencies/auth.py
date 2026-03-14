"""Auth dependencies for FastAPI route injection (TASK-086).

Provides `get_current_user` as a FastAPI `Depends` callable that
extracts and validates the JWT from the `Authorization: Bearer <token>`
header and returns the corresponding `User` ORM instance.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.exceptions import AuthenticationError
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.services.auth import validate_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Validate JWT and return the authenticated user.

    Raises `HTTPException(401)` if the token is missing, invalid or the
    user no longer exists.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = validate_access_token(credentials.credentials)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == payload.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User no longer exists"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
