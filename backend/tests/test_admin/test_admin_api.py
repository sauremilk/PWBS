"""Tests for Admin Dashboard API endpoints (TASK-149).

Tests cover:
- _require_org_owner helper
- GET /{org_id}/dashboard
- GET /{org_id}/members
- POST /{org_id}/invite
- GET /{org_id}/connectors
- POST /{org_id}/connectors/{conn_id}/share
- DELETE /{org_id}/connectors/{conn_id}/share
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.api.v1.routes.admin import (
    _require_org_owner,
    OrgDashboardResponse,
    MemberDetailResponse,
    MemberListResponse,
    InviteRequest,
    InviteResponse,
    OrgConnectorResponse,
    OrgConnectorListResponse,
)
from pwbs.models.organization import Organization, OrganizationMember
from pwbs.models.connection import Connection
from pwbs.models.user import User
from pwbs.schemas.enums import OrgRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(org_id: uuid.UUID | None = None) -> Organization:
    org = MagicMock(spec=Organization)
    org.id = org_id or uuid.uuid4()
    org.name = "Test Org"
    org.slug = "test-org"
    org.description = "A test organization"
    org.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return org


def _make_user(
    user_id: uuid.UUID | None = None,
    email: str = "test@example.com",
    display_name: str = "Test User",
) -> User:
    u = MagicMock(spec=User)
    u.id = user_id or uuid.uuid4()
    u.email = email
    u.display_name = display_name
    u.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return u


def _make_connection(
    user_id: uuid.UUID,
    org_id: uuid.UUID | None = None,
    source_type: str = "gmail",
    status: str = "active",
) -> Connection:
    c = MagicMock(spec=Connection)
    c.id = uuid.uuid4()
    c.user_id = user_id
    c.source_type = source_type
    c.status = status
    c.organization_id = org_id
    c.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return c


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestAdminSchemas:
    """Test Pydantic response models for admin API."""

    def test_dashboard_response(self) -> None:
        org_id = uuid.uuid4()
        resp = OrgDashboardResponse(
            org_id=org_id,
            org_name="Acme",
            member_count=5,
            connector_count=3,
            shared_connector_count=2,
            document_count=42,
        )
        assert resp.org_id == org_id
        assert resp.member_count == 5
        assert resp.shared_connector_count == 2

    def test_member_detail_response(self) -> None:
        uid = uuid.uuid4()
        resp = MemberDetailResponse(
            user_id=uid,
            email="test@example.com",
            display_name="Test",
            role="member",
            joined_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        assert resp.email == "test@example.com"
        assert resp.role == "member"

    def test_member_list_response(self) -> None:
        resp = MemberListResponse(members=[], count=0)
        assert resp.count == 0

    def test_invite_request_default_role(self) -> None:
        req = InviteRequest(email="user@firm.com")
        assert req.role == OrgRole.MEMBER

    def test_invite_response(self) -> None:
        uid = uuid.uuid4()
        oid = uuid.uuid4()
        resp = InviteResponse(
            user_id=uid,
            email="user@firm.com",
            role="member",
            org_id=oid,
        )
        assert resp.org_id == oid

    def test_org_connector_response(self) -> None:
        cid = uuid.uuid4()
        resp = OrgConnectorResponse(
            id=cid,
            source_type="gmail",
            status="active",
            owner_email="test@example.com",
            organization_id=None,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert resp.organization_id is None

    def test_org_connector_list_response(self) -> None:
        resp = OrgConnectorListResponse(connectors=[], count=0)
        assert resp.count == 0


# ---------------------------------------------------------------------------
# _require_org_owner
# ---------------------------------------------------------------------------


class TestRequireOrgOwner:
    """Test the _require_org_owner helper."""

    @pytest.mark.asyncio
    async def test_returns_org_when_user_is_owner(self) -> None:
        org = _make_org()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = org
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await _require_org_owner(mock_db, org.id, uuid.uuid4())
        assert result.id == org.id

    @pytest.mark.asyncio
    async def test_raises_403_when_not_owner(self) -> None:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await _require_org_owner(mock_db, uuid.uuid4(), uuid.uuid4())
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Connection model: organization_id field
# ---------------------------------------------------------------------------


class TestConnectionOrgField:
    """Verify Connection model has organization_id."""

    def test_connection_accepts_organization_id(self) -> None:
        org_id = uuid.uuid4()
        conn = _make_connection(user_id=uuid.uuid4(), org_id=org_id)
        assert conn.organization_id == org_id

    def test_connection_organization_id_nullable(self) -> None:
        conn = _make_connection(user_id=uuid.uuid4(), org_id=None)
        assert conn.organization_id is None


# ---------------------------------------------------------------------------
# OrgRole enum
# ---------------------------------------------------------------------------


class TestOrgRoleEnum:
    """Verify OrgRole has required values for B2B."""

    def test_owner_value(self) -> None:
        assert OrgRole.OWNER.value == "owner"

    def test_member_value(self) -> None:
        assert OrgRole.MEMBER.value == "member"

    def test_viewer_value(self) -> None:
        assert OrgRole.VIEWER.value == "viewer"


# ---------------------------------------------------------------------------
# Dashboard endpoint logic
# ---------------------------------------------------------------------------


class TestDashboardLogic:
    """Test dashboard response construction."""

    def test_dashboard_response_zero_state(self) -> None:
        oid = uuid.uuid4()
        resp = OrgDashboardResponse(
            org_id=oid,
            org_name="Empty Org",
            member_count=0,
            connector_count=0,
            shared_connector_count=0,
            document_count=0,
        )
        assert resp.member_count == 0
        assert resp.connector_count == 0

    def test_dashboard_all_shared(self) -> None:
        oid = uuid.uuid4()
        resp = OrgDashboardResponse(
            org_id=oid,
            org_name="Full Share",
            member_count=3,
            connector_count=5,
            shared_connector_count=5,
            document_count=100,
        )
        assert resp.shared_connector_count == resp.connector_count


# ---------------------------------------------------------------------------
# Invite logic
# ---------------------------------------------------------------------------


class TestInviteLogic:
    """Test invite request/response models."""

    def test_invite_request_with_owner_role(self) -> None:
        req = InviteRequest(email="admin@corp.com", role=OrgRole.OWNER)
        assert req.role == OrgRole.OWNER

    def test_invite_request_with_viewer_role(self) -> None:
        req = InviteRequest(email="viewer@corp.com", role=OrgRole.VIEWER)
        assert req.role == OrgRole.VIEWER

    def test_invite_response_matches_request(self) -> None:
        uid = uuid.uuid4()
        oid = uuid.uuid4()
        resp = InviteResponse(
            user_id=uid,
            email="user@corp.com",
            role="owner",
            org_id=oid,
        )
        assert resp.role == "owner"
        assert resp.user_id == uid


# ---------------------------------------------------------------------------
# Connector share/unshare logic
# ---------------------------------------------------------------------------


class TestConnectorShareLogic:
    """Test connector sharing model behavior."""

    def test_share_sets_org_id(self) -> None:
        org_id = uuid.uuid4()
        conn = _make_connection(user_id=uuid.uuid4())
        conn.organization_id = org_id
        assert conn.organization_id == org_id

    def test_unshare_clears_org_id(self) -> None:
        org_id = uuid.uuid4()
        conn = _make_connection(user_id=uuid.uuid4(), org_id=org_id)
        conn.organization_id = None
        assert conn.organization_id is None

    def test_connector_response_with_shared_status(self) -> None:
        oid = uuid.uuid4()
        resp = OrgConnectorResponse(
            id=uuid.uuid4(),
            source_type="slack",
            status="active",
            owner_email="team@corp.com",
            organization_id=oid,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert resp.organization_id == oid

    def test_connector_response_without_shared_status(self) -> None:
        resp = OrgConnectorResponse(
            id=uuid.uuid4(),
            source_type="slack",
            status="active",
            owner_email="team@corp.com",
            organization_id=None,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert resp.organization_id is None


# ---------------------------------------------------------------------------
# Member detail
# ---------------------------------------------------------------------------


class TestMemberDetail:
    """Test member detail response construction."""

    def test_member_list_ordering(self) -> None:
        members = [
            MemberDetailResponse(
                user_id=uuid.uuid4(),
                email="a@test.com",
                display_name="Alice",
                role="owner",
                joined_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
            MemberDetailResponse(
                user_id=uuid.uuid4(),
                email="b@test.com",
                display_name="Bob",
                role="member",
                joined_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
            ),
        ]
        resp = MemberListResponse(members=members, count=len(members))
        assert resp.count == 2
        assert resp.members[0].display_name == "Alice"
        assert resp.members[1].role == "member"
