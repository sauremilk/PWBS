"""SSO API endpoints (TASK-161).

POST   /api/v1/organizations/{org_id}/sso     -- Configure SSO
GET    /api/v1/organizations/{org_id}/sso     -- Get SSO config
DELETE /api/v1/organizations/{org_id}/sso     -- Remove SSO config
GET    /api/v1/sso/{org_slug}/login           -- Initiate SSO login
POST   /api/v1/sso/{org_slug}/callback/oidc   -- OIDC callback
POST   /api/v1/sso/{org_slug}/callback/saml   -- SAML ACS callback
"""

from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.core.exceptions import (
    AuthenticationError,
    NotFoundError,
    ValidationError,
)
from pwbs.db.postgres import get_db_session
from pwbs.models.organization import Organization
from pwbs.models.user import User
from pwbs.rbac.checker import require_permission
from pwbs.schemas.enums import Permission
from pwbs.services.auth import create_token_pair
from pwbs.sso.config import (
    AttributeMapping,
    OIDCProviderConfig,
    SAMLProviderConfig,
    SSOConfig,
    SSOProvider,
)
from pwbs.sso.oidc_handler import OIDCCallbackParams, OIDCHandler
from pwbs.sso.saml_handler import SAMLHandler
from pwbs.sso.service import SSOService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sso"])

# ── Schemas ───────────────────────────────────────────────────────────


class SSOConfigRequest(BaseModel):
    """Request body for configuring SSO."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    provider: SSOProvider = SSOProvider.OIDC
    saml: SAMLProviderConfig | None = None
    oidc: OIDCProviderConfig | None = None
    attribute_mapping: AttributeMapping = Field(default_factory=AttributeMapping)
    jit_provisioning: bool = True
    default_role: str = "member"
    allowed_domains: list[str] = Field(default_factory=list)


class SSOConfigResponse(BaseModel):
    """Response for SSO configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    provider: SSOProvider
    jit_provisioning: bool
    default_role: str
    allowed_domains: list[str]
    has_saml: bool
    has_oidc: bool


class SSOLoginInitResponse(BaseModel):
    """Response when initiating SSO login."""

    model_config = ConfigDict(frozen=True)

    redirect_url: str
    provider: SSOProvider


class SSOLoginResponse(BaseModel):
    """Response after successful SSO authentication."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool


class SSOErrorResponse(BaseModel):
    """Error response with fallback hint."""

    model_config = ConfigDict(frozen=True)

    error: str
    detail: str
    fallback_available: bool = True
    retry_url: str | None = None


# ── Admin endpoints (require SSO_MANAGE permission) ──────────────────


@router.post(
    "/api/v1/organizations/{org_id}/sso",
    response_model=SSOConfigResponse,
    status_code=status.HTTP_200_OK,
)
async def configure_sso(
    org_id: uuid.UUID,
    body: SSOConfigRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> SSOConfigResponse:
    """Configure SSO for an organization (Admin/Owner only)."""
    await require_permission(db, org_id=org_id, user_id=user.id, permission=Permission.SSO_MANAGE)

    sso_config = SSOConfig(
        enabled=body.enabled,
        provider=body.provider,
        saml=body.saml,
        oidc=body.oidc,
        attribute_mapping=body.attribute_mapping,
        jit_provisioning=body.jit_provisioning,
        default_role=body.default_role,
        allowed_domains=body.allowed_domains,
    )

    service = SSOService(db)
    try:
        saved = await service.save_sso_config(org_id, sso_config)
        await db.commit()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Organization not found")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return SSOConfigResponse(
        enabled=saved.enabled,
        provider=saved.provider,
        jit_provisioning=saved.jit_provisioning,
        default_role=saved.default_role,
        allowed_domains=saved.allowed_domains,
        has_saml=saved.saml is not None,
        has_oidc=saved.oidc is not None,
    )


@router.get(
    "/api/v1/organizations/{org_id}/sso",
    response_model=SSOConfigResponse,
)
async def get_sso_config(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> SSOConfigResponse:
    """Get SSO configuration for an organization."""
    await require_permission(db, org_id=org_id, user_id=user.id, permission=Permission.SSO_MANAGE)

    service = SSOService(db)
    try:
        config = await service.get_sso_config(org_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Organization not found")

    if config is None:
        raise HTTPException(status_code=404, detail="SSO not configured")

    return SSOConfigResponse(
        enabled=config.enabled,
        provider=config.provider,
        jit_provisioning=config.jit_provisioning,
        default_role=config.default_role,
        allowed_domains=config.allowed_domains,
        has_saml=config.saml is not None,
        has_oidc=config.oidc is not None,
    )


@router.delete(
    "/api/v1/organizations/{org_id}/sso",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sso_config(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> None:
    """Remove SSO configuration for an organization."""
    await require_permission(db, org_id=org_id, user_id=user.id, permission=Permission.SSO_MANAGE)

    service = SSOService(db)
    try:
        await service.delete_sso_config(org_id)
        await db.commit()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Organization not found")


# ── Public SSO login endpoints ────────────────────────────────────────


@router.get(
    "/api/v1/sso/{org_slug}/login",
    response_model=SSOLoginInitResponse,
)
async def initiate_sso_login(
    org_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> SSOLoginInitResponse:
    """Initiate SSO login for an organization (public endpoint).

    Redirects user to the configured IdP.
    """
    org = await _get_org_by_slug(db, org_slug)
    config = _get_enabled_sso_config(org)

    state = secrets.token_urlsafe(32)

    if config.provider == SSOProvider.OIDC and config.oidc:
        handler = OIDCHandler(config.oidc, config.attribute_mapping)
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/v1/sso/{org_slug}/callback/oidc"
        auth_url, code_verifier = await handler.get_authorization_url(
            state=state,
            redirect_uri=redirect_uri,
        )
        # In production: store (state, code_verifier) in server-side session
        return SSOLoginInitResponse(
            redirect_url=auth_url,
            provider=SSOProvider.OIDC,
        )
    elif config.provider == SSOProvider.SAML and config.saml:
        handler = SAMLHandler(config.saml, config.attribute_mapping)
        base_url = str(request.base_url).rstrip("/")
        acs_url = f"{base_url}/api/v1/sso/{org_slug}/callback/saml"
        redirect_url = handler.build_auth_redirect_url(acs_url)
        return SSOLoginInitResponse(
            redirect_url=redirect_url,
            provider=SSOProvider.SAML,
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="SSO provider configuration incomplete",
        )


@router.post(
    "/api/v1/sso/{org_slug}/callback/oidc",
    response_model=SSOLoginResponse,
)
async def oidc_callback(
    org_slug: str,
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> SSOLoginResponse:
    """Handle OIDC callback after IdP authentication."""
    org = await _get_org_by_slug(db, org_slug)
    config = _get_enabled_sso_config(org)

    if config.provider != SSOProvider.OIDC or config.oidc is None:
        raise HTTPException(status_code=400, detail="OIDC not configured")

    handler = OIDCHandler(config.oidc, config.attribute_mapping)
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/sso/{org_slug}/callback/oidc"

    try:
        # In production: retrieve code_verifier from server-side session
        # For now, we pass empty string (PKCE verifier should come from session)
        oidc_result = await handler.handle_callback(
            OIDCCallbackParams(code=code, state=state),
            code_verifier="",  # Retrieved from session in production
            redirect_uri=redirect_uri,
        )
    except Exception as exc:
        logger.error("OIDC callback failed for org=%s: %s", org_slug, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "sso_provider_error",
                "detail": "SSO provider authentication failed. Please try again or use email/password login.",
                "fallback_available": True,
                "retry_url": f"/api/v1/sso/{org_slug}/login",
            },
        )

    # JIT provision or find existing user
    service = SSOService(db)
    try:
        login_result = await service.jit_provision_or_login(
            org_id=org.id,
            email=oidc_result.email,
            display_name=oidc_result.display_name,
            groups=oidc_result.groups,
            sso_config=config,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    # Issue PWBS token pair
    token_pair = await create_token_pair(login_result.user_id, db)
    await db.commit()

    return SSOLoginResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
        is_new_user=login_result.is_new_user,
    )


# ── Helpers ───────────────────────────────────────────────────────────


async def _get_org_by_slug(
    db: AsyncSession,
    slug: str,
) -> Organization:
    """Find organization by slug."""
    stmt = select(Organization).where(Organization.slug == slug)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _get_enabled_sso_config(org: Organization) -> SSOConfig:
    """Extract and validate SSO config from organization."""
    raw = getattr(org, "sso_config_enc", None)
    if not raw:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "sso_not_configured",
                "detail": "SSO is not configured for this organization. Use email/password login.",
                "fallback_available": True,
            },
        )

    config = SSOConfig.model_validate(raw)
    if not config.enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "sso_disabled",
                "detail": "SSO is disabled for this organization. Use email/password login.",
                "fallback_available": True,
            },
        )

    return config
