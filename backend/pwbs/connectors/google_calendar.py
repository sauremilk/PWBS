"""Google Calendar connector – OAuth2 flow (TASK-045).

Implements:
- OAuth2 authorization URL generation (scope: calendar.events.readonly)
- Authorization code → token exchange
- Health check via Calendar API calendarList endpoint

Sync logic (TASK-046) and normalization (TASK-047) are implemented separately.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, JsonValue, SyncResult
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.schemas.document import UnifiedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google OAuth2 / API constants
# ---------------------------------------------------------------------------

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"
_HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class GoogleCalendarConnector(BaseConnector):
    """Google Calendar data-source connector.

    Class methods ``build_auth_url`` and ``exchange_code`` handle the OAuth2
    flow.  The resulting ``OAuthTokens`` must be encrypted via
    ``encrypt_tokens`` and stored in the ``connections`` table by the API
    layer (TASK-087).

    For sync and normalization, pass the decrypted ``access_token`` in
    ``config.extra["access_token"]`` when instantiating the connector.
    """

    # ---- OAuth2 flow (static – no connector instance needed) ---------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Google OAuth2 authorization URL.

        Args:
            redirect_uri: Callback URL registered in Google Cloud Console.
            state: Opaque CSRF token to verify on callback.

        Returns:
            Full authorization URL the user should be redirected to.

        Raises:
            ConnectorError: If ``GOOGLE_CLIENT_ID`` is not configured.
        """
        settings = get_settings()
        if not settings.google_client_id:
            raise ConnectorError(
                "GOOGLE_CLIENT_ID not configured",
                code="MISSING_CLIENT_CREDENTIALS",
            )

        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """Exchange an OAuth2 authorization code for access + refresh tokens.

        Args:
            code: Authorization code from Google's callback.
            redirect_uri: Must match the ``redirect_uri`` used in
                ``build_auth_url``.

        Returns:
            ``OAuthTokens`` ready for encryption and storage.

        Raises:
            ConnectorError: On invalid code, aborted flow, network error, or
                missing credentials.
        """
        settings = get_settings()
        client_id = settings.google_client_id
        client_secret = settings.google_client_secret.get_secret_value()

        if not client_id or not client_secret:
            raise ConnectorError(
                "Google OAuth client credentials not configured",
                code="MISSING_CLIENT_CREDENTIALS",
            )

        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(_GOOGLE_TOKEN_URL, data=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.json() if exc.response.content else {}
            error_desc = error_body.get(
                "error_description",
                error_body.get("error", str(exc)),
            )
            logger.warning(
                "Google OAuth code exchange failed: HTTP %d – %s",
                exc.response.status_code,
                error_desc,
            )
            raise ConnectorError(
                f"Google OAuth code exchange failed: {error_desc}",
                code="OAUTH_CODE_EXCHANGE_FAILED",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Google OAuth code exchange network error: {exc}",
                code="OAUTH_NETWORK_ERROR",
            ) from exc

        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Google OAuth response missing access_token",
                code="OAUTH_INVALID_RESPONSE",
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
            scope=data.get("scope", GOOGLE_CALENDAR_SCOPE),
        )

    # ---- BaseConnector abstract methods ------------------------------------

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch calendar events since *cursor*.

        Not yet implemented – see TASK-046.
        """
        raise NotImplementedError(
            "TASK-046: Google Calendar Sync-Logik ausstehend"
        )

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        """Normalize a raw Google Calendar event into UnifiedDocument.

        Not yet implemented – see TASK-047.
        """
        raise NotImplementedError(
            "TASK-047: Google Calendar Normalizer ausstehend"
        )

    async def health_check(self) -> bool:
        """Verify the Google Calendar API is reachable with stored credentials.

        Requires ``config.extra["access_token"]`` to be set with a valid
        (decrypted) access token.  Makes a lightweight GET to the
        ``calendarList`` endpoint.
        """
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped – no access_token in config.extra: "
                "connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GOOGLE_CALENDAR_API}/users/me/calendarList",
                    params={"maxResults": 1},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return response.status_code == 200  # noqa: PLR2004
        except httpx.RequestError:
            logger.warning(
                "Health check failed – network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
