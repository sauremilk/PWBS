"""RBAC management API endpoints (TASK-153).

GET  /api/v1/rbac/org/{org_id}/roles                      -- List all roles and permissions
GET  /api/v1/rbac/org/{org_id}/members/{user_id}/permissions -- User permissions
GET  /api/v1/rbac/org/{org_id}/audit-log                   -- Role change audit log
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.audit_log import AuditLog
from pwbs.models.organization import OrganizationMember
from pwbs.models.user import User
from pwbs.rbac.checker import get_user_permissions, get_user_role, require_permission
from pwbs.rbac.permissions import ROLE_PERMISSIONS, ROLE_RANK, get_all_permissions_for_role
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import OrgRole, Permission

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/rbac/org",
    tags=["rbac"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RolePermissionsResponse(BaseModel):
    role: str
    rank: int
    permissions: list[str]


class AllRolesResponse(BaseModel):
    roles: list[RolePermissionsResponse]


class UserPermissionsResponse(BaseModel):
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str | None
    permissions: list[str]


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    metadata_: dict
    created_at: datetime


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{org_id}/roles", response_model=AllRolesResponse)
async def list_roles(
    org_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AllRolesResponse:
    """List all roles with their permissions. Requires ORG_VIEW."""
    try:
        await require_permission(
            db, org_id=org_id, user_id=user.id, permission=Permission.ORG_VIEW,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        )

    roles = []
    for role in OrgRole:
        perms = get_all_permissions_for_role(role)
        roles.append(RolePermissionsResponse(
            role=role.value,
            rank=ROLE_RANK[role],
            permissions=[p.value for p in perms],
        ))
    roles.sort(key=lambda r: r.rank, reverse=True)
    return AllRolesResponse(roles=roles)


@router.get("/{org_id}/members/{member_user_id}/permissions", response_model=UserPermissionsResponse)
async def get_member_permissions(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserPermissionsResponse:
    """Get permissions for a specific member. Requires MEMBERS_VIEW."""
    try:
        await require_permission(
            db, org_id=org_id, user_id=user.id, permission=Permission.MEMBERS_VIEW,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        )

    role = await get_user_role(db, org_id=org_id, user_id=member_user_id)
    perms = await get_user_permissions(db, org_id=org_id, user_id=member_user_id)

    return UserPermissionsResponse(
        user_id=member_user_id,
        org_id=org_id,
        role=role.value if role else None,
        permissions=[p.value for p in perms],
    )


@router.get("/{org_id}/audit-log", response_model=AuditLogResponse)
async def get_role_audit_log(
    org_id: uuid.UUID,
    response: Response,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AuditLogResponse:
    """Get role-change audit log for an organization. Requires AUDIT_VIEW."""
    try:
        await require_permission(
            db, org_id=org_id, user_id=user.id, permission=Permission.AUDIT_VIEW,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        )

    clamped_limit = min(max(limit, 1), 200)
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.resource_type == "organization_member",
            AuditLog.resource_id == org_id,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(clamped_limit)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    entries = [
        AuditLogEntry(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            metadata_=row.metadata_,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return AuditLogResponse(entries=entries, count=len(entries))
