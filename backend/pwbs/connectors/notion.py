"""Notion connector — OAuth2, Polling-Sync, health check (TASK-048, TASK-049).

Notion uses a *Public Integration* OAuth2 flow.  Unlike Google, Notion does
**not** issue refresh tokens — the access token stays valid until the user
revokes the integration in their Notion workspace settings.

References
----------
- https://developers.notion.com/docs/authorization
- https://developers.notion.com/reference/post-search
- Architecture: D1 §3.1 (Connector table), PRD US-1.3 / F-005
"""

from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, JsonValue, SyncError, SyncResult
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
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


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------


def _encode_cursor(
    *, watermark: str | None, start_cursor: str | None = None
) -> str:
    """Encode a sync cursor as a JSON string.

    If only ``watermark`` is present (no pagination in progress), the cursor
    is the plain ISO timestamp.  When a ``start_cursor`` (Notion pagination
    token) is also present, a compact JSON payload is used.
    """
    if start_cursor:
        return json.dumps(
            {"watermark": watermark, "start_cursor": start_cursor},
            separators=(",", ":"),
        )
    return watermark or ""


def _decode_cursor(cursor: str) -> tuple[str | None, str | None]:
    """Decode a cursor into ``(watermark, start_cursor)``.

    Returns ``(None, None)`` for an empty / initial cursor.
    """
    if not cursor:
        return None, None
    if cursor.startswith("{"):
        try:
            data = json.loads(cursor)
            return data.get("watermark"), data.get("start_cursor")
        except json.JSONDecodeError:
            return cursor, None
    return cursor, None


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on HTTP 429."""
    if response.status_code == 429:  # noqa: PLR2004
        retry_after = int(response.headers.get("Retry-After", "60"))
        raise RateLimitError(
            f"Notion API rate limited: {response.text}",
            status_code=429,
            retry_after=retry_after,
        )


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
        """Fetch pages modified since the last sync (TASK-049).

        Uses ``POST /search`` with ``filter.timestamp = last_edited_time`` for
        incremental syncs.  Initial full sync (cursor=None) fetches all pages.

        Cursor encoding:
        - ``None``                → initial full sync (no watermark)
        - ISO timestamp           → incremental sync from that point
        - JSON with start_cursor  → continue pagination within a sync

        Returns
        -------
        SyncResult
            Documents (will be empty until TASK-050 normalizer), errors,
            new cursor, and ``has_more`` flag for pagination.

        Raises
        ------
        ConnectorError
            On API errors or network failures.
        RateLimitError
            On HTTP 429 (handled by base-class retry).
        """
        access_token = self._get_access_token()
        watermark, start_cursor = _decode_cursor(cursor or "")

        # Build search request body
        body: dict[str, object] = {
            "page_size": min(self.config.max_batch_size, 100),
            "sort": {
                "direction": "ascending",
                "timestamp": "last_edited_time",
            },
        }

        if watermark:
            body["filter"] = {
                "timestamp": "last_edited_time",
                "last_edited_time": {"after": watermark},
            }

        if start_cursor:
            body["start_cursor"] = start_cursor

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    f"{_NOTION_API}/search",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Notion-Version": _NOTION_API_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Notion API network error: {exc}",
                code="NOTION_NETWORK_ERROR",
            ) from exc

        _raise_for_rate_limit(response)

        if response.status_code != 200:  # noqa: PLR2004
            raise ConnectorError(
                f"Notion search failed: HTTP {response.status_code} — {response.text}",
                code="NOTION_API_ERROR",
            )

        data = response.json()
        results: list[dict[str, JsonValue]] = data.get("results", [])
        has_more: bool = data.get("has_more", False)
        next_cursor: str | None = data.get("next_cursor")

        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []

        # Track the latest last_edited_time for the new watermark
        latest_edited: str | None = watermark

        for page in results:
            page_id = str(page.get("id", "unknown"))
            try:
                doc = await self.normalize(page)
                documents.append(doc)

                # Update watermark to the latest edited time seen
                page_edited = str(page.get("last_edited_time", ""))
                if page_edited and (not latest_edited or page_edited > latest_edited):
                    latest_edited = page_edited

            except NotImplementedError:
                # TASK-050 not yet implemented — record as error
                errors.append(
                    SyncError(
                        source_id=page_id,
                        error="TASK-050: normalize not yet implemented",
                    )
                )
                # Still update watermark even if normalize not ready
                page_edited = str(page.get("last_edited_time", ""))
                if page_edited and (not latest_edited or page_edited > latest_edited):
                    latest_edited = page_edited

            except Exception as exc:
                errors.append(
                    SyncError(
                        source_id=page_id,
                        error=str(exc),
                    )
                )

        # Build new cursor
        if has_more and next_cursor:
            new_cursor = _encode_cursor(
                watermark=latest_edited,
                start_cursor=next_cursor,
            )
        else:
            new_cursor = latest_edited

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=has_more,
        )

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
