"""Notion connector — OAuth2 flow and health check (TASK-048).

Notion uses a *Public Integration* OAuth2 flow.  Unlike Google, Notion does
**not** issue refresh tokens — the access token stays valid until the user
revokes the integration in their Notion workspace settings.

References
----------
- https://developers.notion.com/docs/authorization
- Architecture: D1 §3.1 (Connector table), PRD US-1.3 / F-005
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, JsonValue, SyncError, SyncResult
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.schemas.document import UnifiedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Notion OAuth2 / API constants
# ---------------------------------------------------------------------------

_NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
_NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
_NOTION_API = "https://api.notion.com/v1"
_NOTION_API_VERSION = "2022-06-28"
_HTTP_TIMEOUT = 30.0


class NotionConnector(BaseConnector):
    """Connector for Notion workspaces via Public Integration OAuth2.

    Class methods ``build_auth_url`` and ``exchange_code`` handle the OAuth2
    flow.  Instance methods deal with data syncing and normalisation.
    """

    source_type: SourceType = SourceType.NOTION

    # ------------------------------------------------------------------
    # OAuth2 helpers (stateless — no instance required)
    # ------------------------------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Notion OAuth2 authorisation URL.

        Parameters
        ----------
        redirect_uri:
            Where Notion redirects after user consent.
        state:
            Opaque CSRF-protection value.

        Returns
        -------
        str
            Full authorization URL the frontend should redirect to.
        """
        settings = get_settings()
        client_id = settings.notion_client_id
        if not client_id:
            raise ConnectorError(
                "notion_client_id is not configured",
                code="NOTION_MISSING_CLIENT_ID",
            )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": state,
        }
        return f"{_NOTION_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """Exchange an authorization code for an access token.

        Notion uses HTTP Basic Auth (client_id:client_secret) for the
        token endpoint, **not** a JSON body with the credentials.

        Parameters
        ----------
        code:
            The authorization code from the OAuth2 callback.
        redirect_uri:
            Must match the redirect_uri used in ``build_auth_url``.

        Returns
        -------
        OAuthTokens
            Token data (only ``access_token`` — no refresh token for Notion).

        Raises
        ------
        ConnectorError
            On network errors, invalid codes, or missing credentials.
        """
        settings = get_settings()
        client_id = settings.notion_client_id
        client_secret = settings.notion_client_secret.get_secret_value()
        if not client_id or not client_secret:
            raise ConnectorError(
                "notion_client_id / notion_client_secret not configured",
                code="NOTION_MISSING_CREDENTIALS",
            )

        # Notion requires Basic Auth: base64(client_id:client_secret)
        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    _NOTION_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/json",
                        "Notion-Version": _NOTION_API_VERSION,
                    },
                    json={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Notion token exchange network error: {exc}",
                code="NOTION_NETWORK_ERROR",
            ) from exc

        if response.status_code != 200:  # noqa: PLR2004
            raise ConnectorError(
                f"Notion token exchange failed: HTTP {response.status_code} — {response.text}",
                code="NOTION_TOKEN_EXCHANGE_FAILED",
            )

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Notion token response missing access_token",
                code="NOTION_MISSING_ACCESS_TOKEN",
            )

        return OAuthTokens(
            access_token=SecretStr(access_token),
            refresh_token=None,  # Notion doesn't issue refresh tokens
            token_type=data.get("token_type", "bearer"),
            expires_at=None,  # Notion tokens don't expire
            scope=None,
        )

    # ------------------------------------------------------------------
    # Instance helpers
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """Extract the Notion access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "Missing access_token in connector config.extra",
                code="NOTION_MISSING_TOKEN",
            )
        return token

    # ------------------------------------------------------------------
    # BaseConnector interface
    # ------------------------------------------------------------------

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch pages modified since the last sync.

        Not yet implemented — see TASK-049.
        """
        raise NotImplementedError("TASK-049: Notion Polling-Sync ausstehend")

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        """Normalize a raw Notion page/block into UnifiedDocument.

        Not yet implemented — see TASK-050.
        """
        raise NotImplementedError("TASK-050: Notion Normalizer ausstehend")

    async def health_check(self) -> bool:
        """Verify the Notion API is reachable with stored credentials.

        Makes a lightweight GET to the ``/users/me`` endpoint.
        """
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped — no access_token in config.extra: connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_NOTION_API}/users/me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": _NOTION_API_VERSION,
                    },
                )
                return response.status_code == 200  # noqa: PLR2004
        except httpx.RequestError:
            logger.warning(
                "Health check failed — network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
