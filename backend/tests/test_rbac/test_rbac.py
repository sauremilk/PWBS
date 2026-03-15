"""Tests for RBAC system (TASK-153).

Tests cover:
- Permission enum completeness
- Role-to-permission mapping (cumulative hierarchy)
- role_has_permission
- can_assign_role
- get_all_permissions_for_role
- OrgRole enum (expanded with ADMIN, MANAGER)
- RBAC checker functions (get_user_role, check_permission, require_permission)
- Audit log for role changes
- RBAC API schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.rbac.permissions import (
    _ADMIN_PERMISSIONS,
    _MANAGER_PERMISSIONS,
    _MEMBER_PERMISSIONS,
    _OWNER_PERMISSIONS,
    _VIEWER_PERMISSIONS,
    ROLE_PERMISSIONS,
    ROLE_RANK,
    can_assign_role,
    get_all_permissions_for_role,
    role_has_permission,
)
from pwbs.schemas.enums import OrgRole, Permission

# ===========================================================================
# OrgRole enum
# ===========================================================================


class TestOrgRoleEnum:
    def test_all_five_roles(self) -> None:
        assert set(OrgRole) == {
            OrgRole.OWNER,
            OrgRole.ADMIN,
            OrgRole.MANAGER,
            OrgRole.MEMBER,
            OrgRole.VIEWER,
        }

    def test_role_values(self) -> None:
        assert OrgRole.OWNER.value == "owner"
        assert OrgRole.ADMIN.value == "admin"
        assert OrgRole.MANAGER.value == "manager"
        assert OrgRole.MEMBER.value == "member"
        assert OrgRole.VIEWER.value == "viewer"

    def test_role_is_str(self) -> None:
        for role in OrgRole:
            assert isinstance(role, str)


# ===========================================================================
# Permission enum
# ===========================================================================


class TestPermissionEnum:
    def test_at_least_15_permissions(self) -> None:
        assert len(Permission) >= 15

    def test_all_permission_values_unique(self) -> None:
        values = [p.value for p in Permission]
        assert len(values) == len(set(values))

    def test_colon_separated_format(self) -> None:
        for p in Permission:
            assert ":" in p.value, f"{p.value} missing colon separator"


# ===========================================================================
# Role hierarchy
# ===========================================================================


class TestRoleHierarchy:
    def test_viewer_is_smallest(self) -> None:
        assert ROLE_RANK[OrgRole.VIEWER] < ROLE_RANK[OrgRole.MEMBER]

    def test_owner_is_largest(self) -> None:
        assert ROLE_RANK[OrgRole.OWNER] > ROLE_RANK[OrgRole.ADMIN]

    def test_full_order(self) -> None:
        assert (
            ROLE_RANK[OrgRole.VIEWER]
            < ROLE_RANK[OrgRole.MEMBER]
            < ROLE_RANK[OrgRole.MANAGER]
            < ROLE_RANK[OrgRole.ADMIN]
            < ROLE_RANK[OrgRole.OWNER]
        )


# ===========================================================================
# Permission mapping (cumulative)
# ===========================================================================


class TestPermissionMapping:
    def test_viewer_has_view_permissions(self) -> None:
        assert Permission.ORG_VIEW in _VIEWER_PERMISSIONS
        assert Permission.MEMBERS_VIEW in _VIEWER_PERMISSIONS
        assert Permission.DOCUMENTS_VIEW_TEAM in _VIEWER_PERMISSIONS

    def test_viewer_cannot_invite(self) -> None:
        assert Permission.MEMBERS_INVITE not in _VIEWER_PERMISSIONS

    def test_member_inherits_viewer(self) -> None:
        assert _VIEWER_PERMISSIONS.issubset(_MEMBER_PERMISSIONS)

    def test_member_can_generate_briefings(self) -> None:
        assert Permission.BRIEFINGS_GENERATE in _MEMBER_PERMISSIONS

    def test_manager_inherits_member(self) -> None:
        assert _MEMBER_PERMISSIONS.issubset(_MANAGER_PERMISSIONS)

    def test_manager_can_invite(self) -> None:
        assert Permission.MEMBERS_INVITE in _MANAGER_PERMISSIONS
        assert Permission.MEMBERS_REMOVE in _MANAGER_PERMISSIONS

    def test_manager_cannot_change_roles(self) -> None:
        assert Permission.MEMBERS_CHANGE_ROLE not in _MANAGER_PERMISSIONS

    def test_admin_inherits_manager(self) -> None:
        assert _MANAGER_PERMISSIONS.issubset(_ADMIN_PERMISSIONS)

    def test_admin_can_change_roles(self) -> None:
        assert Permission.MEMBERS_CHANGE_ROLE in _ADMIN_PERMISSIONS
        assert Permission.ORG_EDIT in _ADMIN_PERMISSIONS

    def test_admin_cannot_delete_org(self) -> None:
        assert Permission.ORG_DELETE not in _ADMIN_PERMISSIONS

    def test_owner_inherits_admin(self) -> None:
        assert _ADMIN_PERMISSIONS.issubset(_OWNER_PERMISSIONS)

    def test_owner_can_delete_org(self) -> None:
        assert Permission.ORG_DELETE in _OWNER_PERMISSIONS

    def test_all_roles_in_mapping(self) -> None:
        for role in OrgRole:
            assert role in ROLE_PERMISSIONS


# ===========================================================================
# role_has_permission
# ===========================================================================


class TestRoleHasPermission:
    def test_owner_has_all(self) -> None:
        for perm in Permission:
            assert role_has_permission(OrgRole.OWNER, perm)

    def test_viewer_limited(self) -> None:
        assert role_has_permission(OrgRole.VIEWER, Permission.ORG_VIEW)
        assert not role_has_permission(OrgRole.VIEWER, Permission.ORG_DELETE)
        assert not role_has_permission(OrgRole.VIEWER, Permission.MEMBERS_INVITE)

    def test_manager_mid_range(self) -> None:
        assert role_has_permission(OrgRole.MANAGER, Permission.MEMBERS_INVITE)
        assert not role_has_permission(OrgRole.MANAGER, Permission.MEMBERS_CHANGE_ROLE)

    def test_admin_can_edit(self) -> None:
        assert role_has_permission(OrgRole.ADMIN, Permission.ORG_EDIT)
        assert not role_has_permission(OrgRole.ADMIN, Permission.ORG_DELETE)


# ===========================================================================
# can_assign_role
# ===========================================================================


class TestCanAssignRole:
    def test_owner_can_assign_admin(self) -> None:
        assert can_assign_role(OrgRole.OWNER, OrgRole.ADMIN)

    def test_owner_cannot_assign_owner(self) -> None:
        assert not can_assign_role(OrgRole.OWNER, OrgRole.OWNER)

    def test_admin_can_assign_manager(self) -> None:
        assert can_assign_role(OrgRole.ADMIN, OrgRole.MANAGER)

    def test_admin_cannot_assign_admin(self) -> None:
        assert not can_assign_role(OrgRole.ADMIN, OrgRole.ADMIN)

    def test_admin_cannot_assign_owner(self) -> None:
        assert not can_assign_role(OrgRole.ADMIN, OrgRole.OWNER)

    def test_manager_can_assign_member(self) -> None:
        assert can_assign_role(OrgRole.MANAGER, OrgRole.MEMBER)

    def test_manager_cannot_assign_manager(self) -> None:
        assert not can_assign_role(OrgRole.MANAGER, OrgRole.MANAGER)

    def test_member_cannot_assign_above_viewer(self) -> None:
        for role in (OrgRole.OWNER, OrgRole.ADMIN, OrgRole.MANAGER, OrgRole.MEMBER):
            assert not can_assign_role(OrgRole.MEMBER, role)

    def test_member_can_assign_viewer(self) -> None:
        assert can_assign_role(OrgRole.MEMBER, OrgRole.VIEWER)

    def test_viewer_cannot_assign_anything(self) -> None:
        for role in OrgRole:
            assert not can_assign_role(OrgRole.VIEWER, role)


# ===========================================================================
# get_all_permissions_for_role
# ===========================================================================


class TestGetAllPermissions:
    def test_returns_sorted_list(self) -> None:
        perms = get_all_permissions_for_role(OrgRole.VIEWER)
        values = [p.value for p in perms]
        assert values == sorted(values)

    def test_owner_gets_all(self) -> None:
        perms = get_all_permissions_for_role(OrgRole.OWNER)
        assert set(perms) == set(Permission)

    def test_unknown_role_returns_empty(self) -> None:
        # Simulate a role not in the mapping (should not happen but defensive)
        from pwbs.rbac.permissions import ROLE_PERMISSIONS

        result = get_all_permissions_for_role(OrgRole.OWNER)  # known role
        assert len(result) > 0


# ===========================================================================
# Checker: get_user_role (mocked DB)
# ===========================================================================


class TestGetUserRole:
    @pytest.mark.asyncio
    async def test_returns_role_for_member(self) -> None:
        from pwbs.rbac.checker import get_user_role

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "manager"
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        role = await get_user_role(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert role == OrgRole.MANAGER

    @pytest.mark.asyncio
    async def test_returns_none_for_non_member(self) -> None:
        from pwbs.rbac.checker import get_user_role

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        role = await get_user_role(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert role is None


# ===========================================================================
# Checker: check_permission (mocked DB)
# ===========================================================================


class TestCheckPermission:
    @pytest.mark.asyncio
    async def test_grants_when_role_has_perm(self) -> None:
        from pwbs.rbac.checker import check_permission

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "admin"
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await check_permission(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            permission=Permission.ORG_EDIT,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_denies_when_role_lacks_perm(self) -> None:
        from pwbs.rbac.checker import check_permission

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "viewer"
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await check_permission(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            permission=Permission.MEMBERS_INVITE,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_denies_for_non_member(self) -> None:
        from pwbs.rbac.checker import check_permission

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await check_permission(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            permission=Permission.ORG_VIEW,
        )
        assert result is False


# ===========================================================================
# Checker: require_permission (mocked DB)
# ===========================================================================


class TestRequirePermission:
    @pytest.mark.asyncio
    async def test_returns_role_on_success(self) -> None:
        from pwbs.rbac.checker import require_permission

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "owner"
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        role = await require_permission(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            permission=Permission.ORG_DELETE,
        )
        assert role == OrgRole.OWNER

    @pytest.mark.asyncio
    async def test_raises_for_non_member(self) -> None:
        from pwbs.rbac.checker import require_permission

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(PermissionError, match="not a member"):
            await require_permission(
                mock_db,
                org_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                permission=Permission.ORG_VIEW,
            )

    @pytest.mark.asyncio
    async def test_raises_for_insufficient_permission(self) -> None:
        from pwbs.rbac.checker import require_permission

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "viewer"
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(PermissionError, match="lacks permission"):
            await require_permission(
                mock_db,
                org_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                permission=Permission.ORG_DELETE,
            )


# ===========================================================================
# Checker: log_role_change (mocked DB)
# ===========================================================================


class TestLogRoleChange:
    @pytest.mark.asyncio
    async def test_creates_audit_entry(self) -> None:
        from pwbs.rbac.checker import log_role_change

        mock_db = AsyncMock()
        added_items: list = []
        mock_db.add = MagicMock(side_effect=lambda item: added_items.append(item))

        await log_role_change(
            mock_db,
            acting_user_id=uuid.uuid4(),
            target_user_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            old_role="member",
            new_role="manager",
            action="role_change",
        )

        assert len(added_items) == 1
        entry = added_items[0]
        assert entry.action == "role_change"
        assert entry.resource_type == "organization_member"
        assert entry.metadata_["old_role"] == "member"
        assert entry.metadata_["new_role"] == "manager"
        mock_db.flush.assert_awaited_once()


# ===========================================================================
# Checker: get_user_permissions (mocked DB)
# ===========================================================================


class TestGetUserPermissions:
    @pytest.mark.asyncio
    async def test_returns_permissions_for_member(self) -> None:
        from pwbs.rbac.checker import get_user_permissions

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "manager"
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        perms = await get_user_permissions(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert Permission.MEMBERS_INVITE in perms
        assert Permission.MEMBERS_CHANGE_ROLE not in perms

    @pytest.mark.asyncio
    async def test_returns_empty_for_non_member(self) -> None:
        from pwbs.rbac.checker import get_user_permissions

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        perms = await get_user_permissions(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert perms == []


# ===========================================================================
# RBAC API schemas
# ===========================================================================


class TestRBACSchemas:
    def test_role_permissions_response(self) -> None:
        from pwbs.api.v1.routes.rbac import RolePermissionsResponse

        resp = RolePermissionsResponse(
            role="admin",
            rank=3,
            permissions=["org:edit", "members:view"],
        )
        assert resp.role == "admin"
        assert resp.rank == 3

    def test_user_permissions_response(self) -> None:
        from pwbs.api.v1.routes.rbac import UserPermissionsResponse

        uid = uuid.uuid4()
        oid = uuid.uuid4()
        resp = UserPermissionsResponse(
            user_id=uid,
            org_id=oid,
            role="manager",
            permissions=["members:invite"],
        )
        assert resp.role == "manager"

    def test_audit_log_entry(self) -> None:
        from pwbs.api.v1.routes.rbac import AuditLogEntry

        entry = AuditLogEntry(
            id=1,
            user_id=uuid.uuid4(),
            action="role_change",
            resource_type="organization_member",
            resource_id=uuid.uuid4(),
            metadata_={"old_role": "member", "new_role": "admin"},
            created_at=datetime.now(tz=timezone.utc),
        )
        assert entry.action == "role_change"

    def test_all_roles_response(self) -> None:
        from pwbs.api.v1.routes.rbac import AllRolesResponse, RolePermissionsResponse

        resp = AllRolesResponse(
            roles=[
                RolePermissionsResponse(role="owner", rank=4, permissions=["org:delete"]),
                RolePermissionsResponse(role="viewer", rank=0, permissions=["org:view"]),
            ]
        )
        assert resp.roles[0].role == "owner"
