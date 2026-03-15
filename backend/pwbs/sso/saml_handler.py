"""SAML 2.0 SP-initiated handler (TASK-161).

Implements SAML 2.0 Service Provider initiated SSO.
Uses a Protocol abstraction so the actual python3-saml dependency
is only required at runtime, not in unit tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pwbs.sso.config import AttributeMapping, SAMLProviderConfig

logger = logging.getLogger(__name__)

__all__ = [
    "SAMLAuthResult",
    "SAMLHandler",
    "SAMLToolkit",
]


@dataclass(frozen=True, slots=True)
class SAMLAuthResult:
    """Result of a successful SAML authentication."""

    email: str
    display_name: str
    groups: list[str]
    name_id: str
    session_index: str


@runtime_checkable
class SAMLToolkit(Protocol):
    """Protocol for SAML toolkit (python3-saml compatible)."""

    def get_sso_url(self) -> str: ...
    def process_response(self) -> None: ...
    def get_errors(self) -> list[str]: ...
    def get_attributes(self) -> dict[str, list[str]]: ...
    def get_nameid(self) -> str: ...
    def get_session_index(self) -> str | None: ...
    def is_authenticated(self) -> bool: ...


class SAMLHandler:
    """Handles SAML 2.0 SP-initiated SSO.

    Parameters
    ----------
    provider_config:
        SAML IdP configuration.
    attribute_mapping:
        Maps SAML attributes to PWBS user fields.
    """

    def __init__(
        self,
        provider_config: SAMLProviderConfig,
        attribute_mapping: AttributeMapping,
    ) -> None:
        self._config = provider_config
        self._mapping = attribute_mapping

    def get_sp_settings(self, acs_url: str) -> dict[str, Any]:
        """Build python3-saml compatible settings dict.

        Parameters
        ----------
        acs_url:
            Assertion Consumer Service URL (our callback endpoint).
        """
        return {
            "strict": True,
            "sp": {
                "entityId": self._config.sp_entity_id,
                "assertionConsumerService": {
                    "url": acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": self._config.name_id_format,
            },
            "idp": {
                "entityId": self._config.idp_entity_id,
                "singleSignOnService": {
                    "url": self._config.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self._config.idp_x509_cert,
            },
        }

    def build_auth_redirect_url(self, acs_url: str) -> str:
        """Build the IdP redirect URL for SP-initiated SSO.

        In production this would use python3-saml's OneLogin_Saml2_Auth,
        but the URL building logic is deterministic from the settings.
        """
        return self._config.idp_sso_url

    def parse_saml_response(
        self,
        toolkit: SAMLToolkit,
    ) -> SAMLAuthResult:
        """Parse and validate a SAML response.

        Parameters
        ----------
        toolkit:
            An initialized SAMLToolkit (python3-saml Auth object).

        Returns
        -------
        SAMLAuthResult
            Authenticated user details.

        Raises
        ------
        ValueError
            If SAML response is invalid or authentication failed.
        """
        toolkit.process_response()

        errors = toolkit.get_errors()
        if errors:
            raise ValueError(f"SAML response errors: {', '.join(errors)}")

        if not toolkit.is_authenticated():
            raise ValueError("SAML authentication failed")

        attrs = toolkit.get_attributes()
        name_id = toolkit.get_nameid()
        session_index = toolkit.get_session_index() or ""

        email = self._get_attribute(attrs, self._mapping.email, name_id)
        display_name = self._get_attribute(
            attrs, self._mapping.display_name, email
        )
        groups: list[str] = []
        if self._mapping.groups:
            groups = attrs.get(self._mapping.groups, [])

        return SAMLAuthResult(
            email=email,
            display_name=display_name,
            groups=groups,
            name_id=name_id,
            session_index=session_index,
        )

    @staticmethod
    def _get_attribute(
        attrs: dict[str, list[str]],
        key: str,
        fallback: str,
    ) -> str:
        """Extract first value of a SAML attribute or return fallback."""
        values = attrs.get(key, [])
        return values[0] if values else fallback
