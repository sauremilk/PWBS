"""Admin Dashboard API endpoints (TASK-149).

Provides organization-admin-specific endpoints:
GET    /api/v1/admin/org/{id}/dashboard         -- Org stats overview
GET    /api/v1/admin/org/{id}/members            -- List members with details
POST   /api/v1/admin/org/{id}/invite             -- Invite user by email
GET    /api/v1/admin/org/{id}/connectors         -- List org-wide connectors
POST   /api/v1/admin/org/{id}/connectors/{conn_id}/share  -- Share connector with org
DELETE /api/v1/admin/org/{id}/connectors/{conn_id}/share  -- Unshare connector

All endpoints require the acting user to be an org owner.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.connection import Connection
from pwbs.models.document import Document
from pwbs.models.organization import Organization, OrganizationMember
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import OrgRole

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/org",
    tags=["admin"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _require_org_owner(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Organization:
    """Verify the user is an owner of the organization. Raises 403/404."""
    stmt = (
        select(Organization)
        .join(
            OrganizationMember,
            Organization.id == OrganizationMember.organization_id,
        )
        .where(
            Organization.id == org_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.role == OrgRole.OWNER.value,
        )
    )
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only organization owners can access admin features",
            },
        )
    return org


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class OrgDashboardResponse(BaseModel):
    """Aggregated statistics for the admin dashboard."""

    org_id: uuid.UUID
    org_name: str
    member_count: int
    connector_count: int
    shared_connector_count: int
    document_count: int


class MemberDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    display_name: str
    role: str
    joined_at: datetime


class MemberListResponse(BaseModel):
    members: list[MemberDetailResponse]
    count: int


class InviteRequest(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class InviteResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    org_id: uuid.UUID


class OrgConnectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: str
    status: str
    owner_email: str
    organization_id: uuid.UUID | None
    created_at: datetime


class OrgConnectorListResponse(BaseModel):
    connectors: list[OrgConnectorResponse]
    count: int


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/{org_id}/dashboard", response_model=OrgDashboardResponse)
async def get_org_dashboard(
    org_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgDashboardResponse:
    """Get aggregated dashboard statistics for an organization."""
    org = await _require_org_owner(db, org_id, user.id)

    # Member count
    member_count_q = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(OrganizationMember.organization_id == org_id)
    )
    member_count = member_count_q.scalar_one()

    # Connector counts: connectors owned by members
    member_ids_q = await db.execute(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == org_id,
        )
    )
    member_ids = [row[0] for row in member_ids_q.fetchall()]

    connector_count = 0
    shared_connector_count = 0
    if member_ids:
        conn_count_q = await db.execute(
            select(func.count()).select_from(Connection).where(Connection.user_id.in_(member_ids))
        )
        connector_count = conn_count_q.scalar_one()

        shared_count_q = await db.execute(
            select(func.count())
            .select_from(Connection)
            .where(
                Connection.organization_id == org_id,
            )
        )
        shared_connector_count = shared_count_q.scalar_one()

    # Document count (team-visible or owned by members)
    doc_count = 0
    if member_ids:
        doc_count_q = await db.execute(
            select(func.count()).select_from(Document).where(Document.user_id.in_(member_ids))
        )
        doc_count = doc_count_q.scalar_one()

    return OrgDashboardResponse(
        org_id=org_id,
        org_name=org.name,
        member_count=member_count,
        connector_count=connector_count,
        shared_connector_count=shared_connector_count,
        document_count=doc_count,
    )


# ---------------------------------------------------------------------------
# Members (with user details)
# ---------------------------------------------------------------------------


@router.get("/{org_id}/members", response_model=MemberListResponse)
async def list_org_members(
    org_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MemberListResponse:
    """List all organization members with user details. Owner-only."""
    await _require_org_owner(db, org_id, user.id)

    stmt = (
        select(
            OrganizationMember.user_id,
            User.email,
            User.display_name,
            OrganizationMember.role,
            OrganizationMember.joined_at,
        )
        .join(User, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == org_id)
        .order_by(OrganizationMember.joined_at)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    members = [
        MemberDetailResponse(
            user_id=row.user_id,
            email=row.email,
            display_name=row.display_name,
            role=row.role,
            joined_at=row.joined_at,
        )
        for row in rows
    ]
    return MemberListResponse(members=members, count=len(members))


# ---------------------------------------------------------------------------
# Invite (by email)
# ---------------------------------------------------------------------------


@router.post("/{org_id}/invite", response_model=InviteResponse, status_code=201)
async def invite_member(
    org_id: uuid.UUID,
    body: InviteRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> InviteResponse:
    """Invite a user to the organization by email. Owner-only.

    The user must already have a PWBS account. For MVP, this adds
    them directly as a member.
    """
    await _require_org_owner(db, org_id, user.id)

    # Find user by email
    target_q = await db.execute(select(User).where(User.email == body.email))
    target_user = target_q.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "No account found for this email address",
            },
        )

    # Check if already a member
    existing_q = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == target_user.id,
        )
    )
    if existing_q.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_MEMBER",
                "message": "This user is already a member of the organization",
            },
        )

    member = OrganizationMember(
        organization_id=org_id,
        user_id=target_user.id,
        role=body.role.value,
    )
    db.add(member)
    await db.commit()

    logger.info(
        "Invited user %s (%s) to org %s as %s by %s",
        target_user.id,
        body.email,
        org_id,
        body.role.value,
        user.id,
    )

    return InviteResponse(
        user_id=target_user.id,
        email=body.email,
        role=body.role.value,
        org_id=org_id,
    )


# ---------------------------------------------------------------------------
# Org-wide Connectors
# ---------------------------------------------------------------------------


@router.get("/{org_id}/connectors", response_model=OrgConnectorListResponse)
async def list_org_connectors(
    org_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgConnectorListResponse:
    """List all connectors owned by org members, highlighting shared ones."""
    await _require_org_owner(db, org_id, user.id)

    # All member user_ids
    member_ids_q = await db.execute(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == org_id,
        )
    )
    member_ids = [row[0] for row in member_ids_q.fetchall()]

    if not member_ids:
        return OrgConnectorListResponse(connectors=[], count=0)

    stmt = (
        select(
            Connection.id,
            Connection.source_type,
            Connection.status,
            Connection.organization_id,
            Connection.created_at,
            User.email.label("owner_email"),
        )
        .join(User, Connection.user_id == User.id)
        .where(Connection.user_id.in_(member_ids))
        .order_by(Connection.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    connectors = [
        OrgConnectorResponse(
            id=row.id,
            source_type=row.source_type,
            status=row.status,
            owner_email=row.owner_email,
            organization_id=row.organization_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return OrgConnectorListResponse(connectors=connectors, count=len(connectors))


@router.post(
    "/{org_id}/connectors/{conn_id}/share",
    status_code=status.HTTP_200_OK,
    response_model=OrgConnectorResponse,
)
async def share_connector(
    org_id: uuid.UUID,
    conn_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgConnectorResponse:
    """Share a connector with all organization members. Owner-only.

    The connector owner must be a member of the org.
    """
    await _require_org_owner(db, org_id, user.id)

    # Fetch connector and verify the owner is an org member
    conn_q = await db.execute(select(Connection).where(Connection.id == conn_id))
    conn = conn_q.scalar_one_or_none()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Connector not found"},
        )

    # Verify connector owner is org member
    membership_q = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == conn.user_id,
        )
    )
    if membership_q.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Connector owner is not a member of this organization",
            },
        )

    conn.organization_id = org_id
    await db.commit()

    # Fetch owner email
    owner_q = await db.execute(select(User.email).where(User.id == conn.user_id))
    owner_email = owner_q.scalar_one()

    logger.info("Shared connector %s with org %s", conn_id, org_id)

    return OrgConnectorResponse(
        id=conn.id,
        source_type=conn.source_type,
        status=conn.status,
        owner_email=owner_email,
        organization_id=conn.organization_id,
        created_at=conn.created_at,
    )


@router.delete(
    "/{org_id}/connectors/{conn_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unshare_connector(
    org_id: uuid.UUID,
    conn_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove org-wide sharing from a connector. Owner-only."""
    await _require_org_owner(db, org_id, user.id)

    conn_q = await db.execute(
        select(Connection).where(
            Connection.id == conn_id,
            Connection.organization_id == org_id,
        )
    )
    conn = conn_q.scalar_one_or_none()
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Shared connector not found"},
        )

    conn.organization_id = None
    await db.commit()

    logger.info("Unshared connector %s from org %s", conn_id, org_id)
