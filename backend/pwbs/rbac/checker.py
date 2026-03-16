"""RBAC permission checker with audit logging (TASK-153).

Provides DB-level permission checking and audit trail for role changes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from pwbs.models.audit_log import AuditLog
from pwbs.models.organization import OrganizationMember
from pwbs.rbac.permissions import role_has_permission
from pwbs.schemas.enums import OrgRole, Permission

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_user_role(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
) -> OrgRole | None:
    """Return the OrgRole for *user_id* in *org_id*, or None if not a member."""
    stmt = select(OrganizationMember.role).where(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    try:
        return OrgRole(row)
    except ValueError:
        logger.warning("Unknown role %r for user %s in org %s", row, user_id, org_id)
        return None


async def check_permission(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    permission: Permission,
) -> bool:
    """Return True if *user_id* has *permission* in *org_id*."""
    role = await get_user_role(db, org_id=org_id, user_id=user_id)
    if role is None:
        return False
    return role_has_permission(role, permission)


async def require_permission(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    permission: Permission,
) -> OrgRole:
    """Like check_permission but raises if denied.

    Returns the user's OrgRole on success.
    Raises PermissionError with a descriptive message on failure.
    """
    role = await get_user_role(db, org_id=org_id, user_id=user_id)
    if role is None:
        raise PermissionError(f"User {user_id} is not a member of org {org_id}")
    if not role_has_permission(role, permission):
        raise PermissionError(
            f"Role {role.value} lacks permission {permission.value} in org {org_id}"
        )
    return role


async def get_user_permissions(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
) -> list[Permission]:
    """Return all permissions for *user_id* in *org_id*."""
    from pwbs.rbac.permissions import get_all_permissions_for_role

    role = await get_user_role(db, org_id=org_id, user_id=user_id)
    if role is None:
        return []
    return get_all_permissions_for_role(role)


async def log_role_change(
    db: AsyncSession,
    *,
    acting_user_id: UUID,
    target_user_id: UUID,
    org_id: UUID,
    old_role: str | None,
    new_role: str,
    action: str = "role_change",
    ip_address: str | None = None,
) -> None:
    """Write an audit-log entry for a role change."""
    entry = AuditLog(
        user_id=acting_user_id,
        action=action,
        resource_type="organization_member",
        resource_id=org_id,
        metadata_={
            "target_user_id": str(target_user_id),
            "org_id": str(org_id),
            "old_role": old_role,
            "new_role": new_role,
        },
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    logger.info(
        "Audit: %s changed role of %s in org %s: %s -> %s",
        acting_user_id,
        target_user_id,
        org_id,
        old_role,
        new_role,
    )