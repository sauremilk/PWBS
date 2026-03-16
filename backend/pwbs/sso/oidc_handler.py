"""OIDC handler with PKCE flow (TASK-161).

Implements OpenID Connect Authorization Code + PKCE using authlib.
Supports Google Workspace, Azure AD, Keycloak, and other standard providers.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx

from pwbs.sso.config import AttributeMapping, OIDCProviderConfig

logger = logging.getLogger(__name__)

__all__ = [
    "OIDCAuthResult",
    "OIDCHandler",
    "OIDCCallbackParams",
]


@dataclass(frozen=True, slots=True)
class OIDCAuthResult:
    """Result of a successful OIDC authentication."""

    email: str
    display_name: str
    groups: list[str]
    id_token_claims: dict[str, Any]
    access_token: str


@dataclass(frozen=True, slots=True)
class OIDCCallbackParams:
    """Parameters received in the OIDC callback."""

    code: str
    state: str


@dataclass(frozen=True, slots=True)
class _PKCEChallenge:
    """PKCE code verifier and challenge pair."""

    verifier: str
    challenge: str
    method: str = "S256"


def _generate_pkce() -> _PKCEChallenge:
    """Generate a PKCE code verifier + S256 challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return _PKCEChallenge(verifier=verifier, challenge=challenge)


class OIDCHandler:
    """Handles OIDC Authorization Code + PKCE flow.

    Parameters
    ----------
    provider_config:
        OIDC provider connection settings.
    attribute_mapping:
        Maps IdP claims to PWBS fields.
    http_client:
        Optional httpx.AsyncClient for testing.
    """

    def __init__(
        self,
        provider_config: OIDCProviderConfig,
        attribute_mapping: AttributeMapping,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = provider_config
        self._mapping = attribute_mapping
        self._http = http_client
        self._discovery_cache: dict[str, Any] | None = None

    async def get_authorization_url(
        self,
        state: str,
        redirect_uri: str | None = None,
    ) -> tuple[str, str]:
        """Build the authorization URL with PKCE.

        Returns
        -------
        tuple[str, str]
            (authorization_url, code_verifier) — store code_verifier in session.
        """
        discovery = await self._discover()
        pkce = _generate_pkce()

        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": redirect_uri or self._config.redirect_uri,
            "scope": " ".join(self._config.scopes),
            "state": state,
            "code_challenge": pkce.challenge,
            "code_challenge_method": pkce.method,
        }

        auth_endpoint = discovery["authorization_endpoint"]
        url = f"{auth_endpoint}?{urlencode(params)}"
        return url, pkce.verifier

    async def handle_callback(
        self,
        callback: OIDCCallbackParams,
        code_verifier: str,
        redirect_uri: str | None = None,
    ) -> OIDCAuthResult:
        """Exchange authorization code for tokens and extract user info.

        Parameters
        ----------
        callback:
            The code + state from the IdP redirect.
        code_verifier:
            The PKCE verifier stored during authorization.
        redirect_uri:
            The same redirect_uri used in the authorization request.

        Returns
        -------
        OIDCAuthResult
            Authenticated user details.
        """
        discovery = await self._discover()

        # Exchange code for tokens
        token_data = await self._exchange_code(
            discovery["token_endpoint"],
            callback.code,
            code_verifier,
            redirect_uri or self._config.redirect_uri,
        )

        # Extract user info from id_token or userinfo endpoint
        claims = token_data.get("id_token_claims", {})
        if not claims.get(self._mapping.email):
            userinfo = await self._fetch_userinfo(
                discovery.get("userinfo_endpoint", ""),
                token_data["access_token"],
            )
            claims.update(userinfo)

        email = str(claims.get(self._mapping.email, ""))
        display_name = str(claims.get(self._mapping.display_name, email))
        groups: list[str] = []
        if self._mapping.groups and self._mapping.groups in claims:
            raw_groups = claims[self._mapping.groups]
            groups = raw_groups if isinstance(raw_groups, list) else [raw_groups]

        return OIDCAuthResult(
            email=email,
            display_name=display_name,
            groups=groups,
            id_token_claims=claims,
            access_token=token_data["access_token"],
        )

    async def _discover(self) -> dict[str, Any]:
        """Fetch OIDC discovery document (cached)."""
        if self._discovery_cache is not None:
            return self._discovery_cache

        url = urljoin(
            self._config.issuer_url.rstrip("/") + "/",
            ".well-known/openid-configuration",
        )
        async with self._get_client() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            self._discovery_cache = resp.json()

        return self._discovery_cache  # type: ignore[return-value]

    async def _exchange_code(
        self,
        token_endpoint: str,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._config.client_id,
            "code_verifier": code_verifier,
        }
        if self._config.client_secret:
            data["client_secret"] = self._config.client_secret

        async with self._get_client() as client:
            resp = await client.post(token_endpoint, data=data)
            resp.raise_for_status()
            return resp.json()

    async def _fetch_userinfo(
        self,
        userinfo_endpoint: str,
        access_token: str,
    ) -> dict[str, Any]:
        """Fetch user info from the OIDC userinfo endpoint."""
        if not userinfo_endpoint:
            return {}

        async with self._get_client() as client:
            resp = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    def _get_client(self) -> httpx.AsyncClient:
        """Return the configured HTTP client or a new one."""
        if self._http is not None:
            # Wrap in a no-op context manager for consistent usage
            return _NoCloseClient(self._http)
        return httpx.AsyncClient(timeout=10.0)


class _NoCloseClient(httpx.AsyncClient):
    """Wrapper that prevents closing an injected client."""

    def __init__(self, inner: httpx.AsyncClient) -> None:
        self._inner = inner

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._inner

    async def __aexit__(self, *args: Any) -> None:
        pass  # Don't close the injected client
