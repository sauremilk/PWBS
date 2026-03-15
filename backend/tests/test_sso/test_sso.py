"""Tests for Enterprise SSO (TASK-161).

Covers:
- AC1: SAML 2.0 SP-initiated with attribute mapping + JIT provisioning
- AC2: OIDC with PKCE flow for standard providers
- AC3: SSO config per org via Admin API
- AC4: Fallback to email/password with error + retry
- Config models: SSOConfig, provider configs, attribute mapping
- OIDC handler: PKCE generation, auth URL, callback handling
- SAML handler: SP settings, response parsing
- SSO service: JIT provisioning, domain restrictions
- Permission: SSO_MANAGE for admin/owner only
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from base64 import urlsafe_b64encode
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from pwbs.sso.config import (
    AttributeMapping,
    OIDCProviderConfig,
    SAMLProviderConfig,
    SSOConfig,
    SSOProvider,
)

# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1: SSOConfig Models
# ═══════════════════════════════════════════════════════════════════════


class TestSSOProvider:
    def test_saml_value(self) -> None:
        assert SSOProvider.SAML == "saml"

    def test_oidc_value(self) -> None:
        assert SSOProvider.OIDC == "oidc"


class TestAttributeMapping:
    def test_defaults(self) -> None:
        mapping = AttributeMapping()
        assert mapping.email == "email"
        assert mapping.display_name == "name"
        assert mapping.groups is None

    def test_custom_mapping(self) -> None:
        mapping = AttributeMapping(
            email="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            display_name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
            groups="http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
        )
        assert "emailaddress" in mapping.email
        assert mapping.groups is not None


class TestOIDCProviderConfig:
    def test_minimal_config(self) -> None:
        cfg = OIDCProviderConfig(
            issuer_url="https://accounts.google.com",
            client_id="test-client-id",
        )
        assert cfg.issuer_url == "https://accounts.google.com"
        assert cfg.client_id == "test-client-id"
        assert cfg.client_secret == ""
        assert "openid" in cfg.scopes

    def test_ensures_openid_scope(self) -> None:
        cfg = OIDCProviderConfig(
            issuer_url="https://example.com",
            client_id="c",
            scopes=["email", "profile"],
        )
        assert cfg.scopes[0] == "openid"

    def test_pkce_with_empty_secret(self) -> None:
        """AC2: PKCE flow for public clients."""
        cfg = OIDCProviderConfig(
            issuer_url="https://example.com",
            client_id="c",
        )
        assert cfg.client_secret == ""


class TestSAMLProviderConfig:
    def test_full_config(self) -> None:
        cfg = SAMLProviderConfig(
            idp_metadata_url="https://idp.example.com/metadata",
            idp_entity_id="https://idp.example.com",
            idp_sso_url="https://idp.example.com/sso",
            idp_x509_cert="MIICpDCCAYwC...",
        )
        assert cfg.idp_entity_id == "https://idp.example.com"
        assert cfg.sp_entity_id == "pwbs-sp"

    def test_requires_all_fields(self) -> None:
        with pytest.raises(ValidationError):
            SAMLProviderConfig()  # type: ignore[call-arg]


class TestSSOConfig:
    def test_default_disabled(self) -> None:
        cfg = SSOConfig()
        assert cfg.enabled is False
        assert cfg.provider == SSOProvider.OIDC

    def test_oidc_config_required_when_oidc_provider(self) -> None:
        with pytest.raises(ValidationError, match="OIDC config required"):
            SSOConfig(enabled=True, provider=SSOProvider.OIDC, oidc=None)

    def test_saml_config_required_when_saml_provider(self) -> None:
        with pytest.raises(ValidationError, match="SAML config required"):
            SSOConfig(enabled=True, provider=SSOProvider.SAML, saml=None)

    def test_valid_oidc_config(self) -> None:
        cfg = SSOConfig(
            enabled=True,
            provider=SSOProvider.OIDC,
            oidc=OIDCProviderConfig(
                issuer_url="https://accounts.google.com",
                client_id="test",
            ),
        )
        assert cfg.oidc is not None
        assert cfg.jit_provisioning is True

    def test_valid_saml_config(self) -> None:
        cfg = SSOConfig(
            enabled=True,
            provider=SSOProvider.SAML,
            saml=SAMLProviderConfig(
                idp_metadata_url="https://idp.example.com/metadata",
                idp_entity_id="https://idp.example.com",
                idp_sso_url="https://idp.example.com/sso",
                idp_x509_cert="CERT",
            ),
        )
        assert cfg.saml is not None

    def test_serialization_roundtrip(self) -> None:
        """AC3: Config stored as JSON in DB."""
        cfg = SSOConfig(
            enabled=True,
            provider=SSOProvider.OIDC,
            oidc=OIDCProviderConfig(
                issuer_url="https://example.com",
                client_id="c",
            ),
            allowed_domains=["example.com"],
        )
        data = cfg.model_dump(mode="json")
        restored = SSOConfig.model_validate(data)
        assert restored.enabled == cfg.enabled
        assert restored.oidc is not None
        assert restored.oidc.client_id == "c"
        assert restored.allowed_domains == ["example.com"]


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2: OIDC Handler (AC2)
# ═══════════════════════════════════════════════════════════════════════


class TestPKCEGeneration:
    def test_generates_verifier_and_challenge(self) -> None:
        from pwbs.sso.oidc_handler import _generate_pkce

        pkce = _generate_pkce()
        assert len(pkce.verifier) > 40
        assert pkce.method == "S256"

        # Verify S256 challenge
        digest = hashlib.sha256(pkce.verifier.encode("ascii")).digest()
        expected = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        assert pkce.challenge == expected


class TestOIDCHandler:
    def _make_handler(self) -> tuple:
        from pwbs.sso.oidc_handler import OIDCHandler

        config = OIDCProviderConfig(
            issuer_url="https://accounts.google.com",
            client_id="test-client",
            redirect_uri="https://app.pwbs.de/api/v1/sso/acme/callback/oidc",
        )
        mapping = AttributeMapping()
        http = AsyncMock()
        handler = OIDCHandler(config, mapping, http_client=http)
        return handler, http

    @pytest.mark.asyncio
    async def test_get_authorization_url_contains_pkce(self) -> None:
        """AC2: PKCE flow in authorization URL."""
        handler, http = self._make_handler()

        # Mock discovery
        discovery_resp = MagicMock()
        discovery_resp.json.return_value = {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
        }
        discovery_resp.raise_for_status = MagicMock()
        http.get = AsyncMock(return_value=discovery_resp)

        url, verifier = await handler.get_authorization_url(state="test-state")

        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "state=test-state" in url
        assert "client_id=test-client" in url
        assert len(verifier) > 40

    @pytest.mark.asyncio
    async def test_callback_extracts_user_info(self) -> None:
        """AC2: Extract user info from OIDC tokens."""
        from pwbs.sso.oidc_handler import OIDCCallbackParams, OIDCHandler

        config = OIDCProviderConfig(
            issuer_url="https://example.com",
            client_id="c",
            redirect_uri="https://app.pwbs.de/callback",
        )
        mapping = AttributeMapping()
        http = AsyncMock()

        # Mock discovery
        disc_resp = MagicMock()
        disc_resp.json.return_value = {
            "authorization_endpoint": "https://example.com/auth",
            "token_endpoint": "https://example.com/token",
            "userinfo_endpoint": "https://example.com/userinfo",
        }
        disc_resp.raise_for_status = MagicMock()

        # Mock token exchange
        token_resp = MagicMock()
        token_resp.json.return_value = {
            "access_token": "at-123",
            "id_token_claims": {
                "email": "alice@example.com",
                "name": "Alice Müller",
            },
        }
        token_resp.raise_for_status = MagicMock()

        http.get = AsyncMock(return_value=disc_resp)
        http.post = AsyncMock(return_value=token_resp)

        handler = OIDCHandler(config, mapping, http_client=http)
        result = await handler.handle_callback(
            OIDCCallbackParams(code="auth-code", state="s"),
            code_verifier="verifier",
        )

        assert result.email == "alice@example.com"
        assert result.display_name == "Alice Müller"
        assert result.access_token == "at-123"


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3: SAML Handler (AC1)
# ═══════════════════════════════════════════════════════════════════════


class TestSAMLHandler:
    def _make_handler(self) -> Any:
        from pwbs.sso.saml_handler import SAMLHandler

        config = SAMLProviderConfig(
            idp_metadata_url="https://idp.okta.com/metadata",
            idp_entity_id="https://idp.okta.com",
            idp_sso_url="https://idp.okta.com/sso",
            idp_x509_cert="MIIC...",
        )
        mapping = AttributeMapping(
            email="email",
            display_name="name",
            groups="groups",
        )
        return SAMLHandler(config, mapping)

    def test_sp_settings_structure(self) -> None:
        """AC1: SP settings for python3-saml."""
        handler = self._make_handler()
        settings = handler.get_sp_settings(
            acs_url="https://app.pwbs.de/api/v1/sso/acme/callback/saml"
        )
        assert settings["strict"] is True
        assert settings["sp"]["entityId"] == "pwbs-sp"
        assert "saml" in settings["sp"]["assertionConsumerService"]["url"]
        assert settings["idp"]["entityId"] == "https://idp.okta.com"
        assert "MIIC" in settings["idp"]["x509cert"]

    def test_build_auth_redirect_url(self) -> None:
        handler = self._make_handler()
        url = handler.build_auth_redirect_url(
            "https://app.pwbs.de/api/v1/sso/acme/callback/saml"
        )
        assert url == "https://idp.okta.com/sso"

    def test_parse_saml_response_success(self) -> None:
        """AC1: Attribute mapping and JIT from SAML response."""
        from pwbs.sso.saml_handler import SAMLAuthResult

        handler = self._make_handler()

        toolkit = MagicMock()
        toolkit.process_response.return_value = None
        toolkit.get_errors.return_value = []
        toolkit.is_authenticated.return_value = True
        toolkit.get_attributes.return_value = {
            "email": ["bob@acme.com"],
            "name": ["Bob Schmidt"],
            "groups": ["Engineering", "Admin"],
        }
        toolkit.get_nameid.return_value = "bob@acme.com"
        toolkit.get_session_index.return_value = "_session_abc"

        result = handler.parse_saml_response(toolkit)

        assert result.email == "bob@acme.com"
        assert result.display_name == "Bob Schmidt"
        assert result.groups == ["Engineering", "Admin"]
        assert result.name_id == "bob@acme.com"
        assert result.session_index == "_session_abc"

    def test_parse_saml_response_errors_raises(self) -> None:
        handler = self._make_handler()
        toolkit = MagicMock()
        toolkit.process_response.return_value = None
        toolkit.get_errors.return_value = ["invalid_signature"]
        toolkit.is_authenticated.return_value = False

        with pytest.raises(ValueError, match="SAML response errors"):
            handler.parse_saml_response(toolkit)

    def test_parse_saml_response_not_authenticated(self) -> None:
        handler = self._make_handler()
        toolkit = MagicMock()
        toolkit.process_response.return_value = None
        toolkit.get_errors.return_value = []
        toolkit.is_authenticated.return_value = False

        with pytest.raises(ValueError, match="authentication failed"):
            handler.parse_saml_response(toolkit)


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 4: SSO Service – JIT Provisioning (AC1)
# ═══════════════════════════════════════════════════════════════════════


class TestSSOServiceJIT:
    @pytest.mark.asyncio
    async def test_jit_creates_new_user(self) -> None:
        """AC1: JIT provisioning creates user on first SSO login."""
        from pwbs.sso.service import SSOLoginResult, SSOService

        db = AsyncMock()
        service = SSOService(db)

        # Mock: no existing user, no existing membership
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[user_result, member_result])
        db.add = MagicMock()
        db.flush = AsyncMock()

        config = SSOConfig(
            enabled=True,
            provider=SSOProvider.OIDC,
            oidc=OIDCProviderConfig(
                issuer_url="https://example.com",
                client_id="c",
            ),
            jit_provisioning=True,
            default_role="member",
        )

        result = await service.jit_provision_or_login(
            org_id=uuid.uuid4(),
            email="new@example.com",
            display_name="New User",
            groups=[],
            sso_config=config,
        )

        assert result.is_new_user is True
        assert result.email == "new@example.com"
        assert db.add.call_count == 2  # User + OrgMember

    @pytest.mark.asyncio
    async def test_existing_user_no_jit(self) -> None:
        """Existing user logs in without creating new account."""
        from pwbs.sso.service import SSOService

        db = AsyncMock()
        service = SSOService(db)

        existing_user = MagicMock()
        existing_user.id = uuid.uuid4()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = existing_user

        existing_member = MagicMock()
        existing_member.role = "admin"
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = existing_member

        db.execute = AsyncMock(side_effect=[user_result, member_result])

        config = SSOConfig(
            enabled=True,
            provider=SSOProvider.OIDC,
            oidc=OIDCProviderConfig(
                issuer_url="https://example.com",
                client_id="c",
            ),
        )

        result = await service.jit_provision_or_login(
            org_id=uuid.uuid4(),
            email="existing@example.com",
            display_name="Existing",
            groups=[],
            sso_config=config,
        )

        assert result.is_new_user is False
        assert result.org_role == "admin"

    @pytest.mark.asyncio
    async def test_domain_restriction_blocks_wrong_domain(self) -> None:
        from pwbs.core.exceptions import AuthenticationError
        from pwbs.sso.service import SSOService

        db = AsyncMock()
        service = SSOService(db)

        config = SSOConfig(
            enabled=True,
            provider=SSOProvider.OIDC,
            oidc=OIDCProviderConfig(
                issuer_url="https://example.com",
                client_id="c",
            ),
            allowed_domains=["acme.com"],
        )

        with pytest.raises(AuthenticationError, match="domain.*not allowed"):
            await service.jit_provision_or_login(
                org_id=uuid.uuid4(),
                email="hacker@evil.com",
                display_name="Hacker",
                groups=[],
                sso_config=config,
            )

    @pytest.mark.asyncio
    async def test_jit_disabled_unknown_user_raises(self) -> None:
        from pwbs.core.exceptions import AuthenticationError
        from pwbs.sso.service import SSOService

        db = AsyncMock()
        service = SSOService(db)

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=user_result)

        config = SSOConfig(
            enabled=True,
            provider=SSOProvider.OIDC,
            oidc=OIDCProviderConfig(
                issuer_url="https://example.com",
                client_id="c",
            ),
            jit_provisioning=False,
        )

        with pytest.raises(AuthenticationError, match="JIT provisioning.*disabled"):
            await service.jit_provision_or_login(
                org_id=uuid.uuid4(),
                email="nobody@example.com",
                display_name="Nobody",
                groups=[],
                sso_config=config,
            )


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 5: Permission (SSO_MANAGE)
# ═══════════════════════════════════════════════════════════════════════


class TestSSOPermissions:
    def test_sso_manage_permission_exists(self) -> None:
        from pwbs.schemas.enums import Permission

        assert hasattr(Permission, "SSO_MANAGE")
        assert Permission.SSO_MANAGE.value == "sso:manage"

    def test_admin_has_sso_manage(self) -> None:
        from pwbs.rbac.permissions import role_has_permission
        from pwbs.schemas.enums import OrgRole, Permission

        assert role_has_permission(OrgRole.ADMIN, Permission.SSO_MANAGE) is True

    def test_owner_has_sso_manage(self) -> None:
        from pwbs.rbac.permissions import role_has_permission
        from pwbs.schemas.enums import OrgRole, Permission

        assert role_has_permission(OrgRole.OWNER, Permission.SSO_MANAGE) is True

    def test_member_does_not_have_sso_manage(self) -> None:
        from pwbs.rbac.permissions import role_has_permission
        from pwbs.schemas.enums import OrgRole, Permission

        assert role_has_permission(OrgRole.MEMBER, Permission.SSO_MANAGE) is False

    def test_viewer_does_not_have_sso_manage(self) -> None:
        from pwbs.rbac.permissions import role_has_permission
        from pwbs.schemas.enums import OrgRole, Permission

        assert role_has_permission(OrgRole.VIEWER, Permission.SSO_MANAGE) is False


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 6: Organization Model – SSO config column
# ═══════════════════════════════════════════════════════════════════════


class TestOrgModelSSO:
    def test_organization_has_sso_config_column(self) -> None:
        from pwbs.models.organization import Organization

        cols = {c.name for c in Organization.__table__.columns}
        assert "sso_config_enc" in cols

    def test_sso_config_is_nullable(self) -> None:
        from pwbs.models.organization import Organization

        col = Organization.__table__.columns["sso_config_enc"]
        assert col.nullable is True


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 7: API Route Registration
# ═══════════════════════════════════════════════════════════════════════


class TestAPIRoutes:
    def test_sso_router_has_endpoints(self) -> None:
        from pwbs.api.v1.routes.sso import router

        paths = [r.path for r in router.routes]
        # Check at least the config and login endpoints exist
        assert any("/sso" in p for p in paths)

    def test_sso_config_response_schema(self) -> None:
        from pwbs.api.v1.routes.sso import SSOConfigResponse

        resp = SSOConfigResponse(
            enabled=True,
            provider=SSOProvider.OIDC,
            jit_provisioning=True,
            default_role="member",
            allowed_domains=["example.com"],
            has_saml=False,
            has_oidc=True,
        )
        assert resp.enabled is True
        assert resp.has_oidc is True

    def test_sso_error_response_has_fallback(self) -> None:
        """AC4: Error response includes fallback hint."""
        from pwbs.api.v1.routes.sso import SSOErrorResponse

        err = SSOErrorResponse(
            error="sso_provider_error",
            detail="Provider unreachable",
            fallback_available=True,
            retry_url="/api/v1/sso/acme/login",
        )
        assert err.fallback_available is True
        assert err.retry_url is not None
