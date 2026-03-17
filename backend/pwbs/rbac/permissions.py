"""Permission definitions and role-to-permission mapping (TASK-153).

Role hierarchy (highest to lowest): OWNER > ADMIN > MANAGER > MEMBER > VIEWER.
Each higher role inherits all permissions of lower roles.
"""

from __future__ import annotations

from pwbs.schemas.enums import OrgRole, Permission

# ---- Role-to-permission mapping (cumulative) ----

_VIEWER_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.ORG_VIEW,
        Permission.MEMBERS_VIEW,
        Permission.CONNECTORS_VIEW,
        Permission.DOCUMENTS_VIEW_TEAM,
        Permission.BRIEFINGS_VIEW,
    }
)

_MEMBER_PERMISSIONS: frozenset[Permission] = _VIEWER_PERMISSIONS | frozenset(
    {
        Permission.BRIEFINGS_GENERATE,
        Permission.DOCUMENTS_MANAGE_VISIBILITY,
    }
)

_MANAGER_PERMISSIONS: frozenset[Permission] = _MEMBER_PERMISSIONS | frozenset(
    {
        Permission.MEMBERS_INVITE,
        Permission.MEMBERS_REMOVE,
        Permission.CONNECTORS_MANAGE,
        Permission.CONNECTORS_SHARE,
        Permission.AUDIT_VIEW,
    }
)

_ADMIN_PERMISSIONS: frozenset[Permission] = _MANAGER_PERMISSIONS | frozenset(
    {
        Permission.MEMBERS_CHANGE_ROLE,
        Permission.ORG_EDIT,
        Permission.SSO_MANAGE,
    }
)

_OWNER_PERMISSIONS: frozenset[Permission] = _ADMIN_PERMISSIONS | frozenset(
    {
        Permission.ORG_DELETE,
    }
)

ROLE_PERMISSIONS: dict[OrgRole, frozenset[Permission]] = {
    OrgRole.VIEWER: _VIEWER_PERMISSIONS,
    OrgRole.MEMBER: _MEMBER_PERMISSIONS,
    OrgRole.MANAGER: _MANAGER_PERMISSIONS,
    OrgRole.ADMIN: _ADMIN_PERMISSIONS,
    OrgRole.OWNER: _OWNER_PERMISSIONS,
}

# ---- Role hierarchy (for demotion/promotion guards) ----

ROLE_RANK: dict[OrgRole, int] = {
    OrgRole.VIEWER: 0,
    OrgRole.MEMBER: 1,
    OrgRole.MANAGER: 2,
    OrgRole.ADMIN: 3,
    OrgRole.OWNER: 4,
}


def role_has_permission(role: OrgRole, permission: Permission) -> bool:
    """Check whether *role* includes *permission*."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def can_assign_role(acting_role: OrgRole, target_role: OrgRole) -> bool:
    """Return True if *acting_role* may assign *target_role* to another user.

    Rules:
    - A role can only assign roles strictly below its own rank.
    - OWNER can assign any role except OWNER (ownership transfer is separate).
    """
    acting_rank = ROLE_RANK.get(acting_role, -1)
    target_rank = ROLE_RANK.get(target_role, -1)
    if acting_role == OrgRole.OWNER:
        return target_role != OrgRole.OWNER
    return acting_rank > target_rank


def get_all_permissions_for_role(role: OrgRole) -> list[Permission]:
    """Return sorted list of permissions granted to *role*."""
    return sorted(ROLE_PERMISSIONS.get(role, frozenset()), key=lambda p: p.value)
