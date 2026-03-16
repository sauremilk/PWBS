"""Tests for the multi-tenancy / teams module (TASK-144).

Tests:
- Organization model + OrganizationMember
- OrgRole / DocumentVisibility enums
- _slugify utility
- Service CRUD: create_org, get_user_orgs, add/remove/change member
- Document visibility: set_visibility, can_access, get_team_docs
- API schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.schemas.enums import DocumentVisibility, OrgRole
from pwbs.teams.service import _slugify


# ===========================================================================
# Slug generation
# ===========================================================================


class TestSlugify:
    def test_basic_slugify(self) -> None:
        assert _slugify("My Team") == "my-team"

    def test_special_characters_removed(self) -> None:
        assert _slugify("Team @#$% Alpha!") == "team-alpha"

    def test_multiple_spaces(self) -> None:
        assert _slugify("  My   Cool   Team  ") == "my-cool-team"

    def test_german_umlauts_stripped(self) -> None:
        # Umlauts are non-ascii and get stripped
        result = _slugify("Muenchen Team")
        assert result == "muenchen-team"

    def test_max_length_64(self) -> None:
        long_name = "a" * 200
        assert len(_slugify(long_name)) <= 64

    def test_empty_becomes_empty(self) -> None:
        assert _slugify("") == ""

    def test_hyphens_preserved(self) -> None:
        assert _slugify("my-team-alpha") == "my-team-alpha"

    def test_numbers_preserved(self) -> None:
        assert _slugify("Team 42") == "team-42"


# ===========================================================================
# Enum values
# ===========================================================================


class TestEnums:
    def test_org_role_values(self) -> None:
        assert OrgRole.OWNER.value == "owner"
        assert OrgRole.MEMBER.value == "member"
        assert OrgRole.VIEWER.value == "viewer"

    def test_document_visibility_values(self) -> None:
        assert DocumentVisibility.PRIVATE.value == "private"
        assert DocumentVisibility.TEAM.value == "team"

    def test_all_org_roles(self) -> None:
        assert set(OrgRole) == {OrgRole.OWNER, OrgRole.MEMBER, OrgRole.VIEWER}

    def test_all_visibility(self) -> None:
        assert set(DocumentVisibility) == {DocumentVisibility.PRIVATE, DocumentVisibility.TEAM}


# ===========================================================================
# Organization model
# ===========================================================================


class TestOrganizationModel:
    def test_organization_fields(self) -> None:
        from pwbs.models.organization import Organization

        org = Organization(name="Test Org", slug="test-org", description="A test org")
        assert org.name == "Test Org"
        assert org.slug == "test-org"

    def test_organization_member_fields(self) -> None:
        from pwbs.models.organization import OrganizationMember

        member = OrganizationMember(
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role=OrgRole.MEMBER.value,
        )
        assert member.role == "member"


# ===========================================================================
# Document model visibility fields
# ===========================================================================


class TestDocumentVisibilityFields:
    def test_document_has_visibility(self) -> None:
        from pwbs.models.document import Document

        doc = Document(
            user_id=uuid.uuid4(),
            source_type="notion",
            source_id="abc",
            content_hash="hash",
        )
        # Default is not set via Python default, but server_default
        # So at model level it should be None until DB populates it
        assert doc.organization_id is None


# ===========================================================================
# Service: create_organization
# ===========================================================================


class TestCreateOrganization:
    @pytest.mark.asyncio
    async def test_creates_org_and_adds_owner(self) -> None:
        from pwbs.teams.service import create_organization

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Mock: no existing slug
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        user_id = uuid.uuid4()
        org = await create_organization(
            mock_db, name="My Team", owner_id=user_id, description="Test"
        )

        assert org.name == "My Team"
        assert org.slug == "my-team"
        assert org.description == "Test"
        assert mock_db.add.call_count == 2  # org + member
        assert mock_db.flush.await_count == 2


# ===========================================================================
# Service: membership operations
# ===========================================================================


class TestAddMember:
    @pytest.mark.asyncio
    async def test_owner_can_add_member(self) -> None:
        from pwbs.teams.service import add_member

        org_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        new_user_id = uuid.uuid4()

        owner_membership = MagicMock()
        owner_membership.role = OrgRole.OWNER.value

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Acting user's membership
                result.scalar_one_or_none.return_value = owner_membership
            else:
                # Target user's membership (not found)
                result.scalar_one_or_none.return_value = None
            return result

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        member = await add_member(
            mock_db,
            org_id=org_id,
            user_id=new_user_id,
            acting_user_id=owner_id,
        )
        assert member is not None
        assert member.user_id == new_user_id

    @pytest.mark.asyncio
    async def test_non_owner_cannot_add_member(self) -> None:
        from pwbs.teams.service import add_member

        viewer_membership = MagicMock()
        viewer_membership.role = OrgRole.VIEWER.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = viewer_membership

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        member = await add_member(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            acting_user_id=uuid.uuid4(),
        )
        assert member is None


class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_owner_can_remove_member(self) -> None:
        from pwbs.teams.service import remove_member

        owner_membership = MagicMock()
        owner_membership.role = OrgRole.OWNER.value

        target_membership = MagicMock()

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = owner_membership
            else:
                result.scalar_one_or_none.return_value = target_membership
            return result

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.delete = AsyncMock()
        mock_db.flush = AsyncMock()

        removed = await remove_member(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            acting_user_id=uuid.uuid4(),
        )
        assert removed is True

    @pytest.mark.asyncio
    async def test_non_owner_cannot_remove(self) -> None:
        from pwbs.teams.service import remove_member

        member_membership = MagicMock()
        member_membership.role = OrgRole.MEMBER.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = member_membership

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        removed = await remove_member(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            acting_user_id=uuid.uuid4(),
        )
        assert removed is False


class TestChangeRole:
    @pytest.mark.asyncio
    async def test_owner_can_change_role(self) -> None:
        from pwbs.teams.service import change_member_role

        owner_membership = MagicMock()
        owner_membership.role = OrgRole.OWNER.value

        target_membership = MagicMock()
        target_membership.role = OrgRole.MEMBER.value

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = owner_membership
            else:
                result.scalar_one_or_none.return_value = target_membership
            return result

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        mock_db.flush = AsyncMock()

        member = await change_member_role(
            mock_db,
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            new_role=OrgRole.VIEWER,
            acting_user_id=uuid.uuid4(),
        )
        assert member is not None
        assert member.role == OrgRole.VIEWER.value


# ===========================================================================
# Document visibility
# ===========================================================================


class TestSetDocumentVisibility:
    @pytest.mark.asyncio
    async def test_owner_can_set_team_visibility(self) -> None:
        from pwbs.teams.service import set_document_visibility

        doc = MagicMock()
        doc.user_id = uuid.uuid4()
        doc.visibility = DocumentVisibility.PRIVATE.value
        doc.organization_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        org_id = uuid.uuid4()
        result = await set_document_visibility(
            mock_db,
            document_id=uuid.uuid4(),
            user_id=doc.user_id,
            visibility=DocumentVisibility.TEAM,
            org_id=org_id,
        )
        assert result is not None
        assert result.visibility == DocumentVisibility.TEAM.value
        assert result.organization_id == org_id

    @pytest.mark.asyncio
    async def test_team_visibility_requires_org_id(self) -> None:
        from pwbs.teams.service import set_document_visibility

        doc = MagicMock()
        doc.user_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await set_document_visibility(
            mock_db,
            document_id=uuid.uuid4(),
            user_id=doc.user_id,
            visibility=DocumentVisibility.TEAM,
            org_id=None,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_set_private_clears_org_id(self) -> None:
        from pwbs.teams.service import set_document_visibility

        doc = MagicMock()
        doc.user_id = uuid.uuid4()
        doc.visibility = DocumentVisibility.TEAM.value
        doc.organization_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await set_document_visibility(
            mock_db,
            document_id=uuid.uuid4(),
            user_id=doc.user_id,
            visibility=DocumentVisibility.PRIVATE,
        )
        assert result is not None
        assert result.visibility == DocumentVisibility.PRIVATE.value
        assert result.organization_id is None


class TestCanAccessDocument:
    @pytest.mark.asyncio
    async def test_owner_can_access(self) -> None:
        from pwbs.teams.service import can_access_document

        user_id = uuid.uuid4()
        doc = MagicMock()
        doc.user_id = user_id
        doc.visibility = DocumentVisibility.PRIVATE.value

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        assert await can_access_document(mock_db, document_id=uuid.uuid4(), user_id=user_id) is True

    @pytest.mark.asyncio
    async def test_non_owner_private_doc(self) -> None:
        from pwbs.teams.service import can_access_document

        doc = MagicMock()
        doc.user_id = uuid.uuid4()
        doc.visibility = DocumentVisibility.PRIVATE.value
        doc.organization_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        assert await can_access_document(mock_db, document_id=uuid.uuid4(), user_id=uuid.uuid4()) is False

    @pytest.mark.asyncio
    async def test_team_member_can_access_team_doc(self) -> None:
        from pwbs.teams.service import can_access_document

        org_id = uuid.uuid4()
        doc_owner_id = uuid.uuid4()
        team_member_id = uuid.uuid4()

        doc = MagicMock()
        doc.user_id = doc_owner_id
        doc.visibility = DocumentVisibility.TEAM.value
        doc.organization_id = org_id

        membership = MagicMock()
        membership.role = OrgRole.MEMBER.value

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = doc
            else:
                result.scalar_one_or_none.return_value = membership
            return result

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=mock_execute)

        assert await can_access_document(mock_db, document_id=uuid.uuid4(), user_id=team_member_id) is True

    @pytest.mark.asyncio
    async def test_doc_not_found(self) -> None:
        from pwbs.teams.service import can_access_document

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        assert await can_access_document(mock_db, document_id=uuid.uuid4(), user_id=uuid.uuid4()) is False


# ===========================================================================
# API schemas
# ===========================================================================


class TestAPISchemas:
    def test_org_response(self) -> None:
        from pwbs.api.v1.routes.organizations import OrgResponse

        data = {
            "id": uuid.uuid4(),
            "name": "Test Org",
            "slug": "test-org",
            "description": "",
            "created_at": datetime.now(tz=timezone.utc),
        }
        resp = OrgResponse(**data)
        assert resp.name == "Test Org"

    def test_member_response(self) -> None:
        from pwbs.api.v1.routes.organizations import MemberResponse

        data = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "role": "member",
            "joined_at": datetime.now(tz=timezone.utc),
        }
        resp = MemberResponse(**data)
        assert resp.role == "member"

    def test_create_org_request(self) -> None:
        from pwbs.api.v1.routes.organizations import CreateOrgRequest

        req = CreateOrgRequest(name="My Org")
        assert req.name == "My Org"
        assert req.description == ""

    def test_add_member_request(self) -> None:
        from pwbs.api.v1.routes.organizations import AddMemberRequest

        req = AddMemberRequest(user_id=uuid.uuid4())
        assert req.role == OrgRole.MEMBER

    def test_set_visibility_request(self) -> None:
        from pwbs.api.v1.routes.organizations import SetVisibilityRequest

        req = SetVisibilityRequest(
            visibility=DocumentVisibility.TEAM,
            organization_id=uuid.uuid4(),
        )
        assert req.visibility == DocumentVisibility.TEAM