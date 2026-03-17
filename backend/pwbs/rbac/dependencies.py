"""FastAPI dependencies for RBAC permission checks (TASK-153).

Usage in route handlers:

    @router.get("/{org_id}/members")
    async def list_members(
        org_id: uuid.UUID,
        _perm: OrgRole = Depends(require_org_permission(Permission.MEMBERS_VIEW)),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ) -> ...:
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.rbac.checker import require_permission as _require_permission
from pwbs.schemas.enums import OrgRole, Permission


def require_org_permission(
    permission: Permission,
) -> Callable[..., OrgRole]:
    """Factory that returns a FastAPI dependency checking *permission* for the org.

    The org_id is extracted from the path parameter ``org_id``.
    """

    async def _dependency(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ) -> OrgRole:
        org_id_raw = request.path_params.get("org_id")
        if org_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "MISSING_ORG_ID", "message": "org_id path parameter required"},
            )
        try:
            org_id = uuid.UUID(str(org_id_raw))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ORG_ID", "message": "org_id must be a valid UUID"},
            ) from None
        try:
            role = await _require_permission(
                db,
                org_id=org_id,
                user_id=user.id,
                permission=permission,
            )
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": str(exc)},
            ) from exc
        return role

    return _dependency
