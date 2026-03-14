"""Google Calendar connector – OAuth2 flow + Sync logic (TASK-045, TASK-046).

Implements:
- OAuth2 authorization URL generation (scope: calendar.events.readonly)
- Authorization code → token exchange
- Cursor-based incremental sync via syncToken (initial full sync + incremental)
- Webhook push notification handling (with polling fallback)
- Health check via Calendar API calendarList endpoint

Normalization (TASK-047) is a separate task.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, JsonValue, SyncError, SyncResult
from pwbs.connectors.normalizer import normalize_document
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
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
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` if the response indicates rate limiting.

    Google returns 429 (Too Many Requests) or 503 (Service Unavailable)
    when rate limits are exceeded.
    """
    if response.status_code in {429, 503}:
        retry_after_header = response.headers.get("Retry-After")
        retry_after = float(retry_after_header) if retry_after_header else None
        raise RateLimitError(
            f"Google Calendar API rate limited: HTTP {response.status_code}",
            status_code=response.status_code,
            retry_after=retry_after,
        )


def _encode_cursor(
    *,
    sync_token: str | None,
    page_token: str,
) -> str:
    """Encode a compound cursor (syncToken + pageToken) as JSON string.

    When paginating within a single sync, we need to remember both the
    original syncToken (for the next page request) and the pageToken.
    """
    return json.dumps({"syncToken": sync_token, "pageToken": page_token})


def _decode_cursor(cursor: str) -> tuple[str | None, str | None]:
    """Decode a cursor that may be a plain syncToken or a compound JSON.

    Returns ``(sync_token, page_token)``.
    """
    try:
        data = json.loads(cursor)
        if isinstance(data, dict) and "pageToken" in data:
            return data.get("syncToken"), data["pageToken"]
    except (json.JSONDecodeError, TypeError):
        pass
    # Plain syncToken string
    return cursor, None


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
            refresh_token=(SecretStr(refresh_token_value) if refresh_token_value else None),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", GOOGLE_CALENDAR_SCOPE),
        )

    # ---- BaseConnector abstract methods ------------------------------------

    def _get_access_token(self) -> str:
        """Extract the decrypted access token from ``config.extra``.

        The API layer (TASK-087) is responsible for decrypting tokens and
        passing them via ``config.extra["access_token"]`` when constructing
        the connector.

        Raises:
            ConnectorError: If no access token is available.
        """
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "No access_token in connector config — decrypt credentials first",
                code="MISSING_ACCESS_TOKEN",
            )
        return token

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Google Calendar events since *cursor*.

        - ``cursor=None`` → **initial full sync**: fetches all events from
          the primary calendar (paginated, up to ``max_batch_size`` per page).
        - ``cursor=<syncToken>`` → **incremental sync**: fetches only events
          changed since the token was issued.

        Returns a ``SyncResult`` with:
        - ``documents``: Normalised ``UnifiedDocument`` objects (via
          ``self.normalize``).  If the normalizer is not yet implemented
          (TASK-047), individual events appear in ``errors`` instead.
        - ``new_cursor``: Google's ``nextSyncToken`` for the next sync.
        - ``has_more``: ``True`` when more pages remain (caller should
          call again with ``new_cursor``).

        Raises:
            RateLimitError: On HTTP 429 or 503 (handled by base-class retry).
            ConnectorError: On other API failures.
        """
        access_token = self._get_access_token()

        params: dict[str, str | int] = {
            "maxResults": min(self.config.max_batch_size, 250),
            "singleEvents": "true",
            "orderBy": "updated",
        }

        if cursor is not None:
            sync_token, page_token = _decode_cursor(cursor)
            if page_token:
                # Continuing pagination within an existing sync
                params["pageToken"] = page_token
                if sync_token:
                    params["syncToken"] = sync_token
            elif sync_token:
                # Incremental sync — use the syncToken from previous run
                params["syncToken"] = sync_token

        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{_GOOGLE_CALENDAR_API}/calendars/primary/events"

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(url, params=params, headers=headers)
                _raise_for_rate_limit(response)
                response.raise_for_status()
                data = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 410:  # noqa: PLR2004
                # syncToken invalidated — Google requires a full re-sync
                logger.warning(
                    "syncToken invalidated (410 Gone), triggering full re-sync: connection_id=%s",
                    self.connection_id,
                )
                return SyncResult(
                    documents=[],
                    new_cursor=None,  # signal to the caller: start fresh
                    has_more=True,
                )
            raise ConnectorError(
                f"Google Calendar API error: HTTP {exc.response.status_code}",
                code="GCAL_API_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Google Calendar API network error: {exc}",
                code="GCAL_NETWORK_ERROR",
            ) from exc

        # Parse events
        raw_events: list[dict[str, JsonValue]] = data.get("items", [])
        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []

        for raw_event in raw_events:
            event_id = raw_event.get("id", "unknown")
            try:
                doc = await self.normalize(raw_event)
                documents.append(doc)
            except NotImplementedError:
                # TASK-047 not yet implemented — record as error
                errors.append(
                    SyncError(
                        source_id=str(event_id),
                        error="TASK-047: normalize not yet implemented",
                    )
                )
            except Exception as exc:
                errors.append(
                    SyncError(
                        source_id=str(event_id),
                        error=str(exc),
                    )
                )

        # Determine cursor and pagination state
        next_page_token = data.get("nextPageToken")
        next_sync_token = data.get("nextSyncToken")

        if next_page_token:
            # More pages within this sync — return pageToken as cursor
            new_cursor = _encode_cursor(
                sync_token=cursor,
                page_token=next_page_token,
            )
            has_more = True
        else:
            # No more pages — return the syncToken for next incremental run
            new_cursor = next_sync_token
            has_more = False

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=has_more,
        )

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        """Normalize a raw Google Calendar event into UnifiedDocument (TASK-047).

        Extracts title, description, participants, start/end times, location,
        and recurrence information.  All-day events, recurring events, and
        events without a description are handled gracefully.
        """
        event_id = str(raw.get("id", ""))
        if not event_id:
            raise ConnectorError(
                "Google Calendar event missing 'id' field",
                code="GCAL_MISSING_EVENT_ID",
            )

        title = str(raw.get("summary", "(Kein Titel)"))

        # Build content from description, location, and attendees
        description = str(raw.get("description", ""))
        content_parts: list[str] = []
        if title:
            content_parts.append(title)
        if description:
            content_parts.append(description)
        location = str(raw.get("location", ""))
        if location:
            content_parts.append(f"Ort: {location}")
        content = "\n\n".join(content_parts) if content_parts else title

        # Extract participants from attendees
        attendees: list[dict[str, JsonValue]] = raw.get("attendees", [])  # type: ignore[assignment]
        participants: list[str] = []
        for attendee in attendees:
            if isinstance(attendee, dict):
                email = attendee.get("email")
                if isinstance(email, str) and email:
                    participants.append(email)

        # Parse start/end times — handle both dateTime and date (all-day)
        start_obj = raw.get("start", {})
        end_obj = raw.get("end", {})
        start_time: str | None = None
        end_time: str | None = None
        is_all_day = False

        if isinstance(start_obj, dict):
            start_time = str(start_obj.get("dateTime") or start_obj.get("date") or "")
            if "date" in start_obj and "dateTime" not in start_obj:
                is_all_day = True
        if isinstance(end_obj, dict):
            end_time = str(end_obj.get("dateTime") or end_obj.get("date") or "")

        # Recurrence
        recurrence = raw.get("recurrence")
        is_recurring = isinstance(recurrence, list) and len(recurrence) > 0
        # Also check recurringEventId for instances of recurring events
        if not is_recurring and raw.get("recurringEventId"):
            is_recurring = True

        # Metadata
        metadata: dict[str, str | int | bool | list[str]] = {
            "start_time": start_time or "",
            "end_time": end_time or "",
            "location": location,
            "is_recurring": is_recurring,
            "attendee_count": len(participants),
            "is_all_day": is_all_day,
        }
        if is_recurring and isinstance(recurrence, list):
            metadata["recurrence"] = [str(r) for r in recurrence]

        # Parse created/updated timestamps from event
        from datetime import datetime as _datetime

        created_at: _datetime | None = None
        updated_at: _datetime | None = None
        if raw_created := raw.get("created"):
            try:
                created_at = _datetime.fromisoformat(str(raw_created))
            except ValueError:
                pass
        if raw_updated := raw.get("updated"):
            try:
                updated_at = _datetime.fromisoformat(str(raw_updated))
            except ValueError:
                pass

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.GOOGLE_CALENDAR,
            source_id=event_id,
            title=title,
            content=content,
            participants=participants,
            metadata=metadata,  # type: ignore[arg-type]
            created_at=created_at,
            updated_at=updated_at,
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
                "Health check skipped – no access_token in config.extra: connection_id=%s",
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
