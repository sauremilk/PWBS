"""Organizations API endpoints (TASK-144).

GET    /api/v1/organizations                          -- List user's orgs
POST   /api/v1/organizations                          -- Create org
GET    /api/v1/organizations/{id}                     -- Get org detail
POST   /api/v1/organizations/{id}/members             -- Add member
DELETE /api/v1/organizations/{id}/members/{user_id}   -- Remove member
PATCH  /api/v1/organizations/{id}/members/{user_id}   -- Change role
GET    /api/v1/organizations/{id}/documents            -- Team documents
PATCH  /api/v1/documents/{id}/visibility               -- Change doc visibility
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.rbac.checker import log_role_change, require_permission
from pwbs.rbac.permissions import can_assign_role
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import DocumentVisibility, OrgRole, Permission
from pwbs.teams.service import (
    add_member,
    can_access_document,
    change_member_role,
    create_organization,
    get_organization,
    get_team_documents,
    get_user_organizations,
    remove_member,
    set_document_visibility,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["organizations"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class OrgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str
    created_at: datetime


class OrgListResponse(BaseModel):
    items: list[OrgResponse]
    count: int


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: OrgRole = OrgRole.MEMBER


class ChangeRoleRequest(BaseModel):
    role: OrgRole


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    source_type: str
    visibility: str
    organization_id: uuid.UUID | None
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    count: int


class SetVisibilityRequest(BaseModel):
    visibility: DocumentVisibility
    organization_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=OrgListResponse)
async def list_organizations(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgListResponse:
    """List all organizations the user belongs to."""
    orgs = await get_user_organizations(db, user_id=user.id)
    return OrgListResponse(
        items=[OrgResponse.model_validate(o) for o in orgs],
        count=len(orgs),
    )


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: CreateOrgRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgResponse:
    """Create a new organization. The creator becomes the owner."""
    org = await create_organization(
        db,
        name=body.name,
        owner_id=user.id,
        description=body.description,
    )
    await db.commit()
    return OrgResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgResponse:
    """Get organization details. User must be a member."""
    org = await get_organization(db, org_id=org_id, user_id=user.id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Organization not found"},
        )
    return OrgResponse.model_validate(org)


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_org_member(
    org_id: uuid.UUID,
    body: AddMemberRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MemberResponse:
    """Add a member to an organization. Requires MEMBERS_INVITE permission."""
    try:
        acting_role = await require_permission(
            db, org_id=org_id, user_id=user.id, permission=Permission.MEMBERS_INVITE,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        )

    # Acting role must outrank the role being assigned
    if not can_assign_role(acting_role, body.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Cannot assign a role equal to or above your own"},
        )

    member = await add_member(
        db,
        org_id=org_id,
        user_id=body.user_id,
        role=body.role,
        acting_user_id=user.id,
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Could not add member (already a member, or org not found)"},
        )
    await log_role_change(
        db,
        acting_user_id=user.id,
        target_user_id=body.user_id,
        org_id=org_id,
        old_role=None,
        new_role=body.role.value,
        action="member_added",
    )
    await db.commit()
    return MemberResponse.model_validate(member)


@router.delete("/{org_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a member from an organization. Requires MEMBERS_REMOVE permission."""
    try:
        await require_permission(
            db, org_id=org_id, user_id=user.id, permission=Permission.MEMBERS_REMOVE,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        )

    removed = await remove_member(
        db,
        org_id=org_id,
        user_id=member_user_id,
        acting_user_id=user.id,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Member not found in this organization"},
        )
    await log_role_change(
        db,
        acting_user_id=user.id,
        target_user_id=member_user_id,
        org_id=org_id,
        old_role="member",
        new_role="removed",
        action="member_removed",
    )
    await db.commit()


@router.patch("/{org_id}/members/{member_user_id}", response_model=MemberResponse)
async def change_org_member_role(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    body: ChangeRoleRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MemberResponse:
    """Change a member's role. Requires MEMBERS_CHANGE_ROLE permission."""
    try:
        acting_role = await require_permission(
            db, org_id=org_id, user_id=user.id, permission=Permission.MEMBERS_CHANGE_ROLE,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        )

    # Acting role must outrank the target new role
    if not can_assign_role(acting_role, body.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Cannot assign a role equal to or above your own"},
        )

    # Capture old role for audit log
    from pwbs.rbac.checker import get_user_role
    old_role_enum = await get_user_role(db, org_id=org_id, user_id=member_user_id)
    old_role_value = old_role_enum.value if old_role_enum else None

    member = await change_member_role(
        db,
        org_id=org_id,
        user_id=member_user_id,
        new_role=body.role,
        acting_user_id=user.id,
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Member not found in this organization"},
        )
    await log_role_change(
        db,
        acting_user_id=user.id,
        target_user_id=member_user_id,
        org_id=org_id,
        old_role=old_role_value,
        new_role=body.role.value,
        action="role_change",
    )
    await db.commit()
    return MemberResponse.model_validate(member)


@router.get("/{org_id}/documents", response_model=DocumentListResponse)
async def list_team_documents(
    org_id: uuid.UUID,
    response: Response,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """List team-visible documents for an organization member."""
    if limit < 1 or limit > 200:
        limit = 50
    docs = await get_team_documents(db, user_id=user.id, org_id=org_id, limit=limit)
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        count=len(docs),
    )


# ---------------------------------------------------------------------------
# Document visibility route (separate prefix)
# ---------------------------------------------------------------------------

visibility_router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


@visibility_router.patch("/{document_id}/visibility", response_model=DocumentResponse)
async def update_document_visibility(
    document_id: uuid.UUID,
    body: SetVisibilityRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Change a document's visibility. Only the document owner can do this."""
    doc = await set_document_visibility(
        db,
        document_id=document_id,
        user_id=user.id,
        visibility=body.visibility,
        org_id=body.organization_id,
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Document not found or not authorized"},
        )
    await db.commit()
    return DocumentResponse.model_validate(doc)