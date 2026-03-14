"""Slack connector - OAuth2 V2 flow + Events API webhook (TASK-125, TASK-126).

Implements:
- OAuth2 V2 authorization URL generation (Bot Token Scopes)
- Authorization code -> token exchange
- Cursor-based incremental sync via conversations.history
- 90-day backfill for initial sync (TASK-126)
- Thread-Resolution: conversations.replies merging (TASK-126)
- Reactions as UDF metadata (TASK-126)
- Channel listing for user channel selection
- Event signature validation (HMAC-SHA256) for Events API
- Health check via auth.test endpoint

Privacy: Only message text and metadata are imported.
Files/attachments are not imported in the MVP.
"""

from __future__ import annotations

import hashlib
import hmac
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
# Slack OAuth2 / API constants
# ---------------------------------------------------------------------------

_SLACK_AUTH_URL = "https://slack.com/oauth/v2/authorize"
_SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
_SLACK_API = "https://slack.com/api"
SLACK_SCOPES = "channels:history,channels:read,users:read"
_HTTP_TIMEOUT = 30.0
_MAX_MESSAGES_PER_SYNC = 200  # Slack default limit per page
_BACKFILL_DAYS = 90  # Initial sync: import messages from the last N days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on 429 so base-class retry kicks in.

    Slack returns Retry-After header in seconds on rate limit.
    """
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            f"Slack API rate-limited: HTTP {response.status_code}",
            retry_after=int(retry_after) if retry_after and retry_after.isdigit() else None,
        )


def _check_slack_error(data: dict[str, object], context: str) -> None:
    """Raise ``ConnectorError`` if the Slack API response indicates failure."""
    if not data.get("ok"):
        error = data.get("error", "unknown_error")
        raise ConnectorError(
            f"Slack API error ({context}): {error}",
            code="SLACK_API_ERROR",
        )


def validate_event_signature(
    *,
    signing_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> bool:
    """Validate a Slack Events API request signature (HMAC-SHA256).

    See: https://api.slack.com/authentication/verifying-requests-from-slack

    Returns True if the signature is valid.
    Rejects requests older than 5 minutes to prevent replay attacks.
    """
    # Reject stale requests (replay protection)
    try:
        request_time = int(timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - request_time) > 300:
        return False

    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected, signature)


def _encode_cursor(*, channel_cursors: dict[str, str], oldest: str | None = None) -> str:
    """Encode sync state as an opaque JSON cursor.

    channel_cursors: mapping of channel_id -> last message timestamp (ts)
    oldest: overall oldest timestamp for initial sync boundary
    """
    import base64

    payload: dict[str, object] = {"channels": channel_cursors}
    if oldest:
        payload["oldest"] = oldest
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[dict[str, str], str | None]:
    """Decode cursor -> (channel_cursors, oldest)."""
    import base64

    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
        return data.get("channels", {}), data.get("oldest")
    except Exception:
        return {}, None


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class SlackConnector(BaseConnector):
    """Slack data-source connector (TASK-125).

    Uses Slack OAuth2 V2 Bot Token flow. Messages from configured
    channels are fetched via conversations.history with cursor-based
    pagination.

    For sync, pass the decrypted ``access_token`` in
    ``config.extra["access_token"]``. Optionally pass
    ``config.extra["channels"]`` as a list of channel IDs to sync.
    """

    # ---- OAuth2 flow (static) ----------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Slack OAuth2 V2 authorization URL."""
        settings = get_settings()
        if not settings.slack_client_id:
            raise ConnectorError(
                "SLACK_CLIENT_ID not configured",
                code="MISSING_CLIENT_CREDENTIALS",
            )

        params = {
            "client_id": settings.slack_client_id,
            "redirect_uri": redirect_uri,
            "scope": SLACK_SCOPES,
            "state": state,
        }
        return f"{_SLACK_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(*, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange an OAuth2 V2 authorization code for tokens."""
        settings = get_settings()
        client_id = settings.slack_client_id
        client_secret = settings.slack_client_secret.get_secret_value()

        if not client_id or not client_secret:
            raise ConnectorError(
                "Slack OAuth client credentials not configured",
                code="MISSING_CLIENT_CREDENTIALS",
            )

        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(_SLACK_TOKEN_URL, data=payload)
                _raise_for_rate_limit(response)
                response.raise_for_status()
                data = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.json() if exc.response.content else {}
            error_desc = error_body.get("error", str(exc))
            raise ConnectorError(
                f"Slack OAuth code exchange failed: {error_desc}",
                code="OAUTH_CODE_EXCHANGE_FAILED",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Slack OAuth code exchange network error: {exc}",
                code="OAUTH_NETWORK_ERROR",
            ) from exc

        _check_slack_error(data, "oauth.v2.access")

        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Slack OAuth response missing access_token",
                code="OAUTH_INVALID_RESPONSE",
            )

        return OAuthTokens(
            access_token=SecretStr(access_token),
            refresh_token=None,  # Slack bot tokens don't expire
            token_type=data.get("token_type", "bearer"),
            expires_at=None,  # Bot tokens are long-lived
            scope=data.get("scope", SLACK_SCOPES),
        )

    # ---- Channel listing ---------------------------------------------------

    @staticmethod
    async def list_channels(access_token: str) -> list[dict[str, str]]:
        """List public channels the bot has access to.

        Returns a list of dicts with 'id', 'name', 'num_members'.
        Used for channel selection during connector setup.
        """
        channels: list[dict[str, str]] = []
        cursor: str | None = None

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                while True:
                    params: dict[str, str | int] = {
                        "types": "public_channel",
                        "exclude_archived": "true",
                        "limit": 200,
                    }
                    if cursor:
                        params["cursor"] = cursor

                    response = await client.get(
                        f"{_SLACK_API}/conversations.list",
                        params=params,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    _raise_for_rate_limit(response)
                    response.raise_for_status()
                    data = response.json()
                    _check_slack_error(data, "conversations.list")

                    for ch in data.get("channels", []):
                        channels.append(
                            {
                                "id": ch.get("id", ""),
                                "name": ch.get("name", ""),
                                "num_members": str(ch.get("num_members", 0)),
                            }
                        )

                    # Pagination
                    next_cursor = data.get("response_metadata", {}).get("next_cursor", "")
                    if not next_cursor:
                        break
                    cursor = next_cursor

        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Slack channels list failed: HTTP {exc.response.status_code}",
                code="SLACK_CHANNELS_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Slack channels list network error: {exc}",
                code="SLACK_NETWORK_ERROR",
            ) from exc

        return channels

    # ---- BaseConnector abstract methods ------------------------------------

    def _get_access_token(self) -> str:
        """Extract the Slack access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "Missing access_token in config.extra for Slack connector",
                code="SLACK_MISSING_TOKEN",
            )
        return token

    def _get_channels(self) -> list[str]:
        """Get the list of channel IDs to sync from ``config.extra``."""
        channels = self.config.extra.get("channels", [])
        if not isinstance(channels, list):
            return []
        return [ch for ch in channels if isinstance(ch, str)]

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Slack messages since *cursor*.

        - ``cursor=None`` -> initial sync: fetches messages from the last 90 days
          from all configured channels. Threaded messages are resolved via
          ``conversations.replies`` and merged into one UDF per thread (TASK-126).
        - ``cursor=<encoded>`` -> incremental sync using per-channel timestamps.

        Returns a SyncResult with normalised documents and the new cursor.
        """
        access_token = self._get_access_token()
        channels = self._get_channels()

        if not channels:
            logger.warning(
                "No channels configured for Slack connector: connection_id=%s",
                self.connection_id,
            )
            return SyncResult(
                documents=[],
                new_cursor=cursor,
                errors=[],
            )

        channel_cursors: dict[str, str] = {}
        if cursor is not None:
            channel_cursors, _ = _decode_cursor(cursor)

        # Initial sync: 90-day backfill boundary (TASK-126)
        backfill_oldest: str | None = None
        if cursor is None:
            from datetime import UTC, datetime, timedelta

            boundary = datetime.now(tz=UTC) - timedelta(days=_BACKFILL_DAYS)
            backfill_oldest = f"{boundary.timestamp():.6f}"

        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []
        new_channel_cursors: dict[str, str] = dict(channel_cursors)

        headers = {"Authorization": f"Bearer {access_token}"}

        for channel_id in channels:
            oldest = channel_cursors.get(channel_id) or backfill_oldest or "0"
            latest_ts = oldest
            # Collect thread parents to resolve after fetching messages
            thread_parents: dict[str, dict[str, object]] = {}
            standalone_messages: list[dict[str, object]] = []

            try:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    api_cursor: str | None = None

                    while True:
                        params: dict[str, str | int] = {
                            "channel": channel_id,
                            "oldest": oldest,
                            "limit": _MAX_MESSAGES_PER_SYNC,
                            "inclusive": "false",
                        }
                        if api_cursor:
                            params["cursor"] = api_cursor

                        response = await client.get(
                            f"{_SLACK_API}/conversations.history",
                            params=params,
                            headers=headers,
                        )
                        _raise_for_rate_limit(response)
                        response.raise_for_status()
                        data = response.json()
                        _check_slack_error(data, "conversations.history")

                        messages = data.get("messages", [])
                        for msg in messages:
                            if not isinstance(msg, dict):
                                continue
                            # Skip bot messages and subtypes (joins, leaves, etc.)
                            if msg.get("subtype") and msg.get("subtype") != "thread_broadcast":
                                continue

                            msg_ts = msg.get("ts", "0")
                            if msg_ts > latest_ts:
                                latest_ts = msg_ts

                            # Detect thread parents (reply_count > 0) for resolution
                            reply_count = msg.get("reply_count", 0)
                            if isinstance(reply_count, int) and reply_count > 0:
                                thread_parents[str(msg.get("ts", ""))] = {
                                    **msg,
                                    "_channel_id": channel_id,
                                }
                            else:
                                standalone_messages.append({**msg, "_channel_id": channel_id})

                        # Pagination
                        has_more = data.get("has_more", False)
                        next_cursor = data.get("response_metadata", {}).get("next_cursor", "")
                        if not has_more or not next_cursor:
                            break
                        api_cursor = next_cursor

                # Resolve threads: fetch replies and build merged UDFs (TASK-126)
                for thread_ts, parent_msg in thread_parents.items():
                    try:
                        replies = await self._fetch_thread_replies(
                            access_token=access_token,
                            channel_id=channel_id,
                            thread_ts=thread_ts,
                        )
                        doc = self._normalize_thread(
                            parent_msg=parent_msg,
                            replies=replies,
                            channel_id=channel_id,
                        )
                        documents.append(doc)
                    except ConnectorError as exc:
                        errors.append(
                            SyncError(
                                source_id=f"{channel_id}:{thread_ts}",
                                error=str(exc),
                            )
                        )

                # Normalize standalone (non-threaded) messages
                for msg in standalone_messages:
                    try:
                        doc = await self.normalize(msg)
                        documents.append(doc)
                    except ConnectorError as exc:
                        errors.append(
                            SyncError(
                                source_id=msg.get("ts", "unknown"),
                                error=str(exc),
                            )
                        )

            except RateLimitError:
                raise
            except httpx.HTTPStatusError as exc:
                errors.append(
                    SyncError(
                        source_id=channel_id,
                        error=f"HTTP {exc.response.status_code} for channel {channel_id}",
                    )
                )
            except httpx.RequestError as exc:
                errors.append(
                    SyncError(
                        source_id=channel_id,
                        error=f"Network error for channel {channel_id}: {exc}",
                    )
                )

            new_channel_cursors[channel_id] = latest_ts

        new_cursor = _encode_cursor(channel_cursors=new_channel_cursors)

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
        )

    async def _fetch_thread_replies(
        self,
        *,
        access_token: str,
        channel_id: str,
        thread_ts: str,
    ) -> list[dict[str, object]]:
        """Fetch all replies for a Slack thread via conversations.replies.

        Returns the list of reply messages (excluding the parent, which is
        always the first element returned by Slack).
        """
        replies: list[dict[str, object]] = []
        api_cursor: str | None = None
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            while True:
                params: dict[str, str | int] = {
                    "channel": channel_id,
                    "ts": thread_ts,
                    "limit": _MAX_MESSAGES_PER_SYNC,
                }
                if api_cursor:
                    params["cursor"] = api_cursor

                response = await client.get(
                    f"{_SLACK_API}/conversations.replies",
                    params=params,
                    headers=headers,
                )
                _raise_for_rate_limit(response)
                response.raise_for_status()
                data = response.json()
                _check_slack_error(data, "conversations.replies")

                messages = data.get("messages", [])
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                    # Skip the parent (ts == thread_ts); we already have it
                    if msg.get("ts") == thread_ts:
                        continue
                    replies.append(msg)

                next_cursor = data.get("response_metadata", {}).get("next_cursor", "")
                if not next_cursor:
                    break
                api_cursor = next_cursor

        return replies

    def _normalize_thread(
        self,
        *,
        parent_msg: dict[str, object],
        replies: list[dict[str, object]],
        channel_id: str,
    ) -> UnifiedDocument:
        """Merge a Slack thread (parent + replies) into a single UDF document.

        The resulting document has:
        - source_id: ``{channel_id}:thread:{thread_ts}``
        - content: concatenated messages in chronological order
        - metadata: reactions, participant list, reply_count
        """
        from datetime import UTC, datetime

        thread_ts = str(parent_msg.get("ts", ""))
        all_messages = [parent_msg, *replies]
        # Sort by timestamp
        all_messages.sort(key=lambda m: float(str(m.get("ts", "0"))))

        participants: list[str] = []
        seen_users: set[str] = set()
        content_parts: list[str] = []
        all_reactions: list[dict[str, object]] = []

        for msg in all_messages:
            user_id = str(msg.get("user", ""))
            text = msg.get("text", "")
            if not isinstance(text, str):
                text = str(text) if text else ""
            ts = str(msg.get("ts", ""))

            # Collect unique participants
            if user_id and user_id not in seen_users:
                seen_users.add(user_id)
                participants.append(user_id)

            # Build per-message content block
            msg_parts: list[str] = []
            if user_id:
                msg_parts.append(f"[{user_id}]")
            if text:
                msg_parts.append(text)
            if msg_parts:
                content_parts.append(" ".join(msg_parts))

            # Collect reactions (TASK-126)
            reactions = msg.get("reactions")
            if isinstance(reactions, list):
                for reaction in reactions:
                    if isinstance(reaction, dict):
                        all_reactions.append(
                            {
                                "name": reaction.get("name", ""),
                                "count": reaction.get("count", 0),
                                "users": reaction.get("users", []),
                            }
                        )

        separator = "\n---\n"
        merged_content = separator.join(content_parts) if content_parts else "(leer)"

        # Use parent timestamp for created_at
        try:
            created_at = datetime.fromtimestamp(float(thread_ts), tz=UTC)
        except (ValueError, TypeError, OSError):
            created_at = None

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.SLACK,
            source_id=f"{channel_id}:thread:{thread_ts}",
            title=f"Slack-Thread #{channel_id}",
            content=merged_content,
            created_at=created_at,
            participants=participants,
            metadata={
                "channel_id": str(channel_id),
                "thread_ts": thread_ts,
                "reply_count": len(replies),
                "message_count": len(all_messages),
                "reactions": all_reactions,
            },
        )

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        """Normalize a Slack message to UnifiedDocument."""
        ts = raw.get("ts")
        if not ts or not isinstance(ts, str):
            raise ConnectorError("Slack message missing 'ts'", code="SLACK_INVALID_MESSAGE")

        channel_id = raw.get("_channel_id", "unknown")
        user_id = raw.get("user", "")
        text = raw.get("text", "")
        thread_ts = raw.get("thread_ts", "")

        if not isinstance(text, str):
            text = str(text) if text else ""

        # Build source_id from channel + timestamp (unique per message)
        source_id = f"{channel_id}:{ts}"

        # Convert Slack timestamp to readable format
        try:
            msg_time = float(str(ts))
            from datetime import UTC, datetime

            created_at = datetime.fromtimestamp(msg_time, tz=UTC)
        except (ValueError, TypeError, OSError):
            created_at = None

        content_parts: list[str] = []
        if text:
            content_parts.append(text)
        content = "\n".join(content_parts) if content_parts else "(leer)"

        # Extract reactions as metadata (TASK-126)
        reactions_raw = raw.get("reactions")
        reactions_meta: list[dict[str, object]] = []
        if isinstance(reactions_raw, list):
            for r in reactions_raw:
                if isinstance(r, dict):
                    reactions_meta.append(
                        {
                            "name": r.get("name", ""),
                            "count": r.get("count", 0),
                            "users": r.get("users", []),
                        }
                    )

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.SLACK,
            source_id=source_id,
            title=f"Slack-Nachricht #{channel_id}",
            content=content,
            created_at=created_at,
            metadata={
                "channel_id": str(channel_id),
                "user_id": str(user_id),
                "ts": str(ts),
                "thread_ts": str(thread_ts) if thread_ts else None,
                "reactions": reactions_meta,
            },
        )

    async def health_check(self) -> bool:
        """Verify Slack API is reachable with stored credentials."""
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped - no access_token: connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    f"{_SLACK_API}/auth.test",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code != 200:
                    return False
                data = response.json()
                return data.get("ok", False) is True
        except httpx.RequestError:
            logger.warning(
                "Health check failed - network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
