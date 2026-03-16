"""SSO configuration models (TASK-161).

Pydantic models for per-organization SSO setup:
- SSOProvider enum (SAML, OIDC)
- SSOConfig: encrypted JSON stored on Organization
- Attribute mapping: IdP claims → PWBS user fields
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "AttributeMapping",
    "OIDCProviderConfig",
    "SAMLProviderConfig",
    "SSOConfig",
    "SSOProvider",
]


class SSOProvider(str, Enum):
    """Supported SSO identity provider protocols."""

    SAML = "saml"
    OIDC = "oidc"


class AttributeMapping(BaseModel):
    """Maps IdP attributes/claims to PWBS user fields."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(
        default="email",
        description="IdP attribute for user email",
    )
    display_name: str = Field(
        default="name",
        description="IdP attribute for display name",
    )
    groups: str | None = Field(
        default=None,
        description="IdP attribute for group membership (maps to PWBS roles)",
    )


class SAMLProviderConfig(BaseModel):
    """Configuration for SAML 2.0 SP-initiated SSO."""

    model_config = ConfigDict(frozen=True)

    idp_metadata_url: str = Field(
        ...,
        description="URL to IdP SAML metadata XML",
    )
    idp_entity_id: str = Field(
        ...,
        description="IdP Entity ID from metadata",
    )
    idp_sso_url: str = Field(
        ...,
        description="IdP Single Sign-On Service URL",
    )
    idp_x509_cert: str = Field(
        ...,
        description="IdP X.509 signing certificate (PEM)",
    )
    sp_entity_id: str = Field(
        default="pwbs-sp",
        description="Service Provider Entity ID",
    )
    name_id_format: str = Field(
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    )


class OIDCProviderConfig(BaseModel):
    """Configuration for OpenID Connect with PKCE."""

    model_config = ConfigDict(frozen=True)

    issuer_url: str = Field(
        ...,
        description="OIDC Issuer URL (used for .well-known discovery)",
    )
    client_id: str = Field(
        ...,
        description="OAuth 2.0 Client ID",
    )
    client_secret: str = Field(
        default="",
        description="OAuth 2.0 Client Secret (empty for public clients with PKCE)",
    )
    scopes: list[str] = Field(
        default=["openid", "profile", "email"],
    )
    redirect_uri: str = Field(
        default="",
        description="Callback URI (auto-generated if empty)",
    )

    @field_validator("scopes")
    @classmethod
    def _ensure_openid_scope(cls, v: list[str]) -> list[str]:
        if "openid" not in v:
            v = ["openid", *v]
        return v


class SSOConfig(BaseModel):
    """Per-organization SSO configuration (stored encrypted in DB)."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    provider: SSOProvider = SSOProvider.OIDC
    saml: SAMLProviderConfig | None = None
    oidc: OIDCProviderConfig | None = None
    attribute_mapping: AttributeMapping = Field(default_factory=AttributeMapping)
    jit_provisioning: bool = Field(
        default=True,
        description="Auto-create user on first SSO login",
    )
    default_role: str = Field(
        default="member",
        description="Default org role for JIT-provisioned users",
    )
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="Restrict SSO to these email domains (empty = all)",
    )

    @field_validator("saml")
    @classmethod
    def _require_saml_for_saml_provider(
        cls, v: SAMLProviderConfig | None, info: Any
    ) -> SAMLProviderConfig | None:
        data = info.data
        if data.get("provider") == SSOProvider.SAML and v is None:
            raise ValueError("SAML config required when provider is 'saml'")
        return v

    @field_validator("oidc")
    @classmethod
    def _require_oidc_for_oidc_provider(
        cls, v: OIDCProviderConfig | None, info: Any
    ) -> OIDCProviderConfig | None:
        data = info.data
        if data.get("provider") == SSOProvider.OIDC and v is None:
            raise ValueError("OIDC config required when provider is 'oidc'")
        return v
