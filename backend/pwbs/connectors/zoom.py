"""Zoom connector — OAuth2 flow (TASK-053).

Implements User-Level OAuth2 for accessing Zoom Cloud Recording transcripts.
Zoom uses HTTP Basic Auth (base64(client_id:client_secret)) for the token
endpoint, similar to Notion.  Unlike Notion, Zoom *does* issue refresh tokens
with a finite access-token lifetime.

References
----------
- https://developers.zoom.us/docs/integrations/oauth/
- https://developers.zoom.us/docs/api/rest/reference/zoom-api/methods/#tag/Cloud-Recording
- Architecture: D1 §3.1 (Connector table), PRD US-1.5 / F-007
"""

from __future__ import annotations

import base64
import logging
import time
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncResult
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.schemas.document import UnifiedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Zoom OAuth2 / API constants
# ---------------------------------------------------------------------------

_ZOOM_AUTH_URL = "https://zoom.us/oauth/authorize"
_ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
_ZOOM_API = "https://api.zoom.us/v2"
_HTTP_TIMEOUT = 30.0

# Scopes for reading cloud recording transcripts and meeting metadata
ZOOM_SCOPES = "cloud_recording:read:list_user_recordings cloud_recording:read:list_recording_files meeting:read:list_meetings"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on HTTP 429."""
    if response.status_code == 429:  # noqa: PLR2004
        retry_after = int(response.headers.get("Retry-After", "60"))
        raise RateLimitError(
            f"Zoom API rate limited: {response.text}",
            status_code=429,
            retry_after=retry_after,
        )


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class ZoomConnector(BaseConnector):
    """Connector for Zoom cloud recordings and meeting transcripts.

    Class methods ``build_auth_url`` and ``exchange_code`` handle the OAuth2
    flow.  The resulting ``OAuthTokens`` must be encrypted via
    ``encrypt_tokens`` and stored in the ``connections`` table by the API
    layer (TASK-087).

    For sync and normalization (TASK-054, TASK-055), pass the decrypted
    ``access_token`` in ``config.extra["access_token"]`` when instantiating
    the connector.
    """

    source_type: SourceType = SourceType.ZOOM

    # ------------------------------------------------------------------
    # OAuth2 helpers (stateless — no instance required)
    # ------------------------------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Zoom OAuth2 authorization URL.

        Parameters
        ----------
        redirect_uri:
            Where Zoom redirects after user consent.
        state:
            Opaque CSRF-protection value.

        Returns
        -------
        str
            Full authorization URL the frontend should redirect to.

        Raises
        ------
        ConnectorError
            If ``zoom_client_id`` is not configured.
        """
        settings = get_settings()
        client_id = settings.zoom_client_id
        if not client_id:
            raise ConnectorError(
                "zoom_client_id is not configured",
                code="ZOOM_MISSING_CLIENT_ID",
            )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{_ZOOM_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """Exchange an OAuth2 authorization code for access + refresh tokens.

        Zoom uses HTTP Basic Auth (base64(client_id:client_secret)) for the
        token endpoint — the same pattern as Notion.

        Parameters
        ----------
        code:
            The authorization code from the OAuth2 callback.
        redirect_uri:
            Must match the redirect_uri used in ``build_auth_url``.

        Returns
        -------
        OAuthTokens
            Token data with ``access_token``, ``refresh_token``, and
            ``expires_at``.

        Raises
        ------
        ConnectorError
            On network errors, invalid codes, or missing credentials.
        """
        settings = get_settings()
        client_id = settings.zoom_client_id
        client_secret = settings.zoom_client_secret.get_secret_value()
        if not client_id or not client_secret:
            raise ConnectorError(
                "zoom_client_id / zoom_client_secret not configured",
                code="ZOOM_MISSING_CREDENTIALS",
            )

        # Zoom requires Basic Auth: base64(client_id:client_secret)
        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode(),
        ).decode()

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    _ZOOM_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Zoom token exchange network error: {exc}",
                code="ZOOM_NETWORK_ERROR",
            ) from exc

        _raise_for_rate_limit(response)

        if response.status_code != 200:  # noqa: PLR2004
            error_body: dict[str, str] = {}
            try:
                error_body = response.json()
            except Exception:  # noqa: BLE001
                pass
            error_reason = error_body.get(
                "reason",
                error_body.get("error", f"HTTP {response.status_code}"),
            )
            logger.warning(
                "Zoom OAuth code exchange failed: HTTP %d — %s",
                response.status_code,
                error_reason,
            )
            raise ConnectorError(
                f"Zoom OAuth code exchange failed: {error_reason}",
                code="ZOOM_TOKEN_EXCHANGE_FAILED",
            )

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Zoom token response missing access_token",
                code="ZOOM_MISSING_ACCESS_TOKEN",
            )

        expires_in = data.get("expires_in")
        expires_at = time.time() + float(expires_in) if expires_in else None
        refresh_token_value = data.get("refresh_token")

        return OAuthTokens(
            access_token=SecretStr(access_token),
            refresh_token=(
                SecretStr(refresh_token_value) if refresh_token_value else None
            ),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", ZOOM_SCOPES),
        )

    # ------------------------------------------------------------------
    # Instance helpers
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """Extract the Zoom access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "Missing access_token in connector config.extra",
                code="ZOOM_MISSING_TOKEN",
            )
        return token

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Zoom recordings since *cursor*.

        Will be implemented in TASK-054 (Zoom Webhook-Receiver /
        Recording-completed events).
        """
        raise NotImplementedError("TASK-054: Zoom fetch_since not yet implemented")

    def normalize(self, raw: dict[str, object]) -> UnifiedDocument:
        """Normalize a Zoom recording/transcript into a UnifiedDocument.

        Will be implemented in TASK-055 (Zoom Normalizer).
        """
        raise NotImplementedError("TASK-055: Zoom normalize not yet implemented")

    async def health_check(self) -> bool:
        """Verify the Zoom API is reachable with stored credentials.

        Makes a lightweight GET to the ``/users/me`` endpoint.
        """
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped — no access_token in config.extra: "
                "connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_ZOOM_API}/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                _raise_for_rate_limit(response)
                return response.status_code == 200  # noqa: PLR2004
        except httpx.RequestError:
            logger.warning(
                "Health check failed — network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
