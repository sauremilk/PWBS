"""Team/organization service for multi-tenancy (TASK-144).

Provides:
1. Organization CRUD with slug generation
2. Membership management (add/remove/change role)
3. Document visibility access checks
4. Team-scoped document queries
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from pwbs.models.document import Document
from pwbs.models.organization import Organization, OrganizationMember
from pwbs.schemas.enums import DocumentVisibility, OrgRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert an organization name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")[:64]


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


async def create_organization(
    db: AsyncSession,
    *,
    name: str,
    owner_id: UUID,
    description: str = "",
) -> Organization:
    """Create a new organization and add the creator as owner."""
    slug = _slugify(name)

    # Check slug uniqueness
    existing = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if existing.scalar_one_or_none() is not None:
        slug = f"{slug}-{str(owner_id)[:8]}"

    org = Organization(name=name, slug=slug, description=description)
    db.add(org)
    await db.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=owner_id,
        role=OrgRole.OWNER.value,
    )
    db.add(member)
    await db.flush()

    logger.info("Created organization %s (slug=%s) by user %s", org.id, slug, owner_id)
    return org


async def get_user_organizations(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> list[Organization]:
    """Get all organizations a user belongs to."""
    stmt = (
        select(Organization)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == user_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_organization(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
) -> Organization | None:
    """Get an organization if the user is a member."""
    stmt = (
        select(Organization)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .where(
            Organization.id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------


async def add_member(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    role: OrgRole = OrgRole.MEMBER,
    acting_user_id: UUID,
) -> OrganizationMember | None:
    """Add a user to an organization. Only owners can add members.

    Returns the new membership or None if the acting user is not an owner.
    """
    acting_member = await _get_membership(db, org_id=org_id, user_id=acting_user_id)
    if acting_member is None or acting_member.role != OrgRole.OWNER.value:
        return None

    # Check if already a member
    existing = await _get_membership(db, org_id=org_id, user_id=user_id)
    if existing is not None:
        return existing

    member = OrganizationMember(
        organization_id=org_id,
        user_id=user_id,
        role=role.value,
    )
    db.add(member)
    await db.flush()
    return member


async def remove_member(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    acting_user_id: UUID,
) -> bool:
    """Remove a member from an organization. Only owners can remove members.

    Returns True if removed, False if not authorized or not found.
    """
    acting_member = await _get_membership(db, org_id=org_id, user_id=acting_user_id)
    if acting_member is None or acting_member.role != OrgRole.OWNER.value:
        return False

    target_member = await _get_membership(db, org_id=org_id, user_id=user_id)
    if target_member is None:
        return False

    await db.delete(target_member)
    await db.flush()
    return True


async def change_member_role(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    new_role: OrgRole,
    acting_user_id: UUID,
) -> OrganizationMember | None:
    """Change a member's role. Only owners can change roles.

    Returns the updated membership or None if not authorized.
    """
    acting_member = await _get_membership(db, org_id=org_id, user_id=acting_user_id)
    if acting_member is None or acting_member.role != OrgRole.OWNER.value:
        return None

    target_member = await _get_membership(db, org_id=org_id, user_id=user_id)
    if target_member is None:
        return None

    target_member.role = new_role.value
    await db.flush()
    return target_member


# ---------------------------------------------------------------------------
# Document visibility and access
# ---------------------------------------------------------------------------


async def get_team_documents(
    db: AsyncSession,
    *,
    user_id: UUID,
    org_id: UUID,
    limit: int = 50,
) -> list[Document]:
    """Get team-visible documents for an organization member.

    Returns documents that are either:
    - Owned by the user (any visibility)
    - Shared with the team (visibility='team' and same org)
    """
    membership = await _get_membership(db, org_id=org_id, user_id=user_id)
    if membership is None:
        return []

    stmt = (
        select(Document)
        .where(
            Document.organization_id == org_id,
            (Document.user_id == user_id) | (Document.visibility == DocumentVisibility.TEAM.value),
        )
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def set_document_visibility(
    db: AsyncSession,
    *,
    document_id: UUID,
    user_id: UUID,
    visibility: DocumentVisibility,
    org_id: UUID | None = None,
) -> Document | None:
    """Update a document's visibility. Only the document owner can change visibility.

    When setting to 'team', org_id must be provided.
    """
    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        return None

    if visibility == DocumentVisibility.TEAM and org_id is None:
        return None

    doc.visibility = visibility.value
    if visibility == DocumentVisibility.TEAM:
        doc.organization_id = org_id
    elif visibility == DocumentVisibility.PRIVATE:
        doc.organization_id = None

    await db.flush()
    return doc


async def can_access_document(
    db: AsyncSession,
    *,
    document_id: UUID,
    user_id: UUID,
) -> bool:
    """Check if a user can access a document.

    Access is granted if:
    - The user owns the document
    - The document is team-visible and the user is in the same org
    """
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        return False

    if doc.user_id == user_id:
        return True

    if doc.visibility == DocumentVisibility.TEAM.value and doc.organization_id is not None:
        membership = await _get_membership(
            db, org_id=doc.organization_id, user_id=user_id
        )
        return membership is not None

    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_membership(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
) -> OrganizationMember | None:
    """Get a user's membership in an organization."""
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
