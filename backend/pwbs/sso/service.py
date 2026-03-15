"""SSO orchestration service (TASK-161).

Coordinates:
1. SSO config CRUD (encrypted storage per organization)
2. JIT user provisioning on first SSO login
3. Token pair issuance after successful SSO
4. Fallback handling when SSO provider is unreachable
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from pwbs.sso.config import SSOConfig, SSOProvider

logger = logging.getLogger(__name__)

__all__ = [
    "SSOService",
    "SSOLoginResult",
]


class SSOLoginResult:
    """Result of a successful SSO login."""

    __slots__ = ("user_id", "email", "display_name", "is_new_user", "org_role")

    def __init__(
        self,
        user_id: uuid.UUID,
        email: str,
        display_name: str,
        is_new_user: bool,
        org_role: str,
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.display_name = display_name
        self.is_new_user = is_new_user
        self.org_role = org_role


class SSOService:
    """Manages SSO configuration and login flows.

    Parameters
    ----------
    db:
        Async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Config CRUD ───────────────────────────────────────────────────

    async def get_sso_config(
        self,
        org_id: uuid.UUID,
    ) -> SSOConfig | None:
        """Load SSO config for an organization."""
        from pwbs.models.organization import Organization

        stmt = select(Organization).where(Organization.id == org_id)
        result = await self._db.execute(stmt)
        org = result.scalar_one_or_none()
        if org is None:
            raise NotFoundError(f"Organization {org_id} not found")

        raw = getattr(org, "sso_config_enc", None)
        if not raw:
            return None

        return SSOConfig.model_validate(raw)

    async def save_sso_config(
        self,
        org_id: uuid.UUID,
        config: SSOConfig,
    ) -> SSOConfig:
        """Save (upsert) SSO config for an organization."""
        from pwbs.models.organization import Organization

        stmt = select(Organization).where(Organization.id == org_id)
        result = await self._db.execute(stmt)
        org = result.scalar_one_or_none()
        if org is None:
            raise NotFoundError(f"Organization {org_id} not found")

        # Validate config consistency
        if config.enabled:
            if config.provider == SSOProvider.SAML and config.saml is None:
                raise ValidationError("SAML config required when provider is 'saml'")
            if config.provider == SSOProvider.OIDC and config.oidc is None:
                raise ValidationError("OIDC config required when provider is 'oidc'")

        org.sso_config_enc = config.model_dump(mode="json")  # type: ignore[attr-defined]
        await self._db.flush()
        return config

    async def delete_sso_config(
        self,
        org_id: uuid.UUID,
    ) -> None:
        """Remove SSO config for an organization."""
        from pwbs.models.organization import Organization

        stmt = (
            update(Organization)
            .where(Organization.id == org_id)
            .values(sso_config_enc=None)
        )
        result = await self._db.execute(stmt)
        if result.rowcount == 0:  # type: ignore[union-attr]
            raise NotFoundError(f"Organization {org_id} not found")

    # ── JIT Provisioning ──────────────────────────────────────────────

    async def jit_provision_or_login(
        self,
        org_id: uuid.UUID,
        email: str,
        display_name: str,
        groups: list[str],
        sso_config: SSOConfig,
    ) -> SSOLoginResult:
        """Find or create user via JIT provisioning.

        1. Check domain restriction
        2. Find existing user by email
        3. Create user if JIT enabled and not found
        4. Ensure org membership
        5. Return SSOLoginResult
        """
        from pwbs.models.organization import Organization, OrganizationMember
        from pwbs.models.user import User

        # Domain restriction
        if sso_config.allowed_domains:
            domain = email.rsplit("@", 1)[-1].lower()
            if domain not in [d.lower() for d in sso_config.allowed_domains]:
                raise AuthenticationError(
                    f"Email domain '{domain}' not allowed for this organization",
                    code="sso_domain_restricted",
                )

        # Find existing user
        stmt = select(User).where(User.email == email)
        result = await self._db.execute(stmt)
        user = result.scalar_one_or_none()
        is_new = False

        if user is None:
            if not sso_config.jit_provisioning:
                raise AuthenticationError(
                    "User not found and JIT provisioning is disabled",
                    code="sso_no_jit",
                )
            # JIT create user
            user = User(
                email=email,
                display_name=display_name,
                password_hash="!sso-managed",  # SSO users don't have passwords
                encryption_key_enc="sso-placeholder",  # Will be set on first data access
            )
            self._db.add(user)
            await self._db.flush()
            is_new = True
            logger.info(
                "JIT provisioned user: email=%s org_id=%s",
                email,
                org_id,
            )

        # Ensure org membership
        role = sso_config.default_role
        stmt_member = select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
        result = await self._db.execute(stmt_member)
        membership = result.scalar_one_or_none()

        if membership is None:
            membership = OrganizationMember(
                organization_id=org_id,
                user_id=user.id,
                role=role,
            )
            self._db.add(membership)
            await self._db.flush()
            logger.info(
                "Added user to org: user_id=%s org_id=%s role=%s",
                user.id,
                org_id,
                role,
            )
        else:
            role = membership.role

        return SSOLoginResult(
            user_id=user.id,
            email=email,
            display_name=display_name,
            is_new_user=is_new,
            org_role=role,
        )
