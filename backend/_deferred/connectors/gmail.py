"""Gmail connector  OAuth2 flow + Pub/Sub push notifications (TASK-123, TASK-124).

Implements:
- OAuth2 authorization URL generation (scope: gmail.readonly)
- Authorization code  token exchange (reuses Google client credentials)
- Cursor-based incremental sync via historyId (History API)
- Thread-Resolution: merges messages in the same thread into one UDF document
- Google Pub/Sub push notification webhook endpoint
- Health check via Gmail API profile endpoint
- Idempotent ingestion via content_hash (raw_hash) deduplication

Privacy: Only metadata and text content are imported.
No attachments in the MVP (metadata only).
"""

from __future__ import annotations

import base64
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
# Google OAuth2 / Gmail API constants
# ---------------------------------------------------------------------------

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
_HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on 429/503 so base-class retry kicks in."""
    if response.status_code in (429, 503):
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            f"Gmail API rate-limited: HTTP {response.status_code}",
            retry_after=int(retry_after) if retry_after and retry_after.isdigit() else None,
        )


def _encode_cursor(*, history_id: str, page_token: str | None = None) -> str:
    """Encode sync state as an opaque JSON cursor."""
    payload: dict[str, str] = {"historyId": history_id}
    if page_token:
        payload["pageToken"] = page_token
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str | None, str | None]:
    """Decode cursor  (historyId, pageToken)."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
        return data.get("historyId"), data.get("pageToken")
    except Exception:
        return None, None


def _extract_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a header value from Gmail message headers list."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_body_part(part: dict[str, object]) -> str:
    """Decode a Gmail message body part (base64url)."""
    body = part.get("body", {})
    if isinstance(body, dict):
        data = body.get("data", "")
        if data and isinstance(data, str):
            try:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            except Exception:
                return ""
    return ""


def _extract_text_content(payload: dict[str, object]) -> str:
    """Recursively extract plaintext content from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    # Simple text part
    if mime_type == "text/plain":
        return _decode_body_part(payload)

    # Multipart: recurse into parts
    parts = payload.get("parts", [])
    if isinstance(parts, list):
        text_parts: list[str] = []
        for part in parts:
            if isinstance(part, dict):
                content = _extract_text_content(part)
                if content:
                    text_parts.append(content)
        return "\n".join(text_parts)

    return ""


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class GmailConnector(BaseConnector):
    """Gmail data-source connector (TASK-123).

    Reuses the same Google OAuth2 credentials (``google_client_id``,
    ``google_client_secret``) as Google Calendar, but with Gmail-specific
    scopes.

    For sync and normalization, pass the decrypted ``access_token`` in
    ``config.extra["access_token"]``.
    """

    # ---- OAuth2 flow (static) ----------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Gmail OAuth2 authorization URL."""
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
            "scope": GMAIL_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(*, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange an OAuth2 authorization code for tokens."""
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
            raise ConnectorError(
                f"Gmail OAuth code exchange failed: {error_desc}",
                code="OAUTH_CODE_EXCHANGE_FAILED",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Gmail OAuth code exchange network error: {exc}",
                code="OAUTH_NETWORK_ERROR",
            ) from exc

        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Gmail OAuth response missing access_token",
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
            scope=data.get("scope", GMAIL_SCOPE),
        )

    # ---- Pub/Sub watch setup -----------------------------------------------

    @staticmethod
    async def setup_pubsub_watch(access_token: str) -> dict[str, str]:
        """Call Gmail API watch() to register Pub/Sub push notifications.

        Returns the watch response containing ``historyId`` and ``expiration``.
        The watch must be renewed before expiration (~7 days).
        """
        settings = get_settings()
        topic = settings.gmail_pubsub_topic
        if not topic:
            raise ConnectorError(
                "gmail_pubsub_topic is not configured",
                code="GMAIL_PUBSUB_NOT_CONFIGURED",
            )

        body = {
            "topicName": topic,
            "labelIds": ["INBOX"],
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    f"{_GMAIL_API}/users/me/watch",
                    json=body,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                _raise_for_rate_limit(response)
                response.raise_for_status()
                return response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Gmail watch setup failed: HTTP {exc.response.status_code}",
                code="GMAIL_WATCH_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Gmail watch setup network error: {exc}",
                code="GMAIL_NETWORK_ERROR",
            ) from exc

    # ---- BaseConnector abstract methods ------------------------------------

    def _get_access_token(self) -> str:
        """Extract the Gmail access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "Missing access_token in config.extra for Gmail connector",
                code="GMAIL_MISSING_TOKEN",
            )
        return token

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Gmail messages since *cursor*.

        - ``cursor=None`` -> initial full sync: fetches recent messages.
        - ``cursor=<encoded>`` -> incremental sync using history.list().

        Messages belonging to the same thread are merged into a single
        UDF document (TASK-124 Thread-Resolution).

        Returns a SyncResult with normalised documents and the new cursor.
        """
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        if cursor is not None:
            history_id, page_token = _decode_cursor(cursor)
            if history_id:
                return await self._fetch_incremental(
                    access_token=access_token,
                    history_id=history_id,
                    page_token=page_token,
                    headers=headers,
                )

        # Initial full sync: fetch recent messages
        params: dict[str, str | int] = {
            "maxResults": min(self.config.max_batch_size, 100),
            "q": "in:inbox",
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GMAIL_API}/users/me/messages",
                    params=params,
                    headers=headers,
                )
                _raise_for_rate_limit(response)
                response.raise_for_status()
                data = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Gmail API error: HTTP {exc.response.status_code}",
                code="GMAIL_API_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Gmail API network error: {exc}",
                code="GMAIL_NETWORK_ERROR",
            ) from exc

        message_refs = data.get("messages", [])
        next_page_token = data.get("nextPageToken")
        has_more = next_page_token is not None

        # Collect thread IDs from message references
        thread_ids: set[str] = set()
        for msg_ref in message_refs:
            tid = msg_ref.get("threadId")
            if tid:
                thread_ids.add(tid)

        documents, errors = await self._resolve_threads(
            access_token=access_token,
            thread_ids=thread_ids,
        )

        # Build cursor from profile historyId
        new_history_id = await self._get_history_id(access_token)
        new_cursor = (
            _encode_cursor(
                history_id=new_history_id,
                page_token=next_page_token,
            )
            if new_history_id
            else None
        )

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=has_more,
        )

    async def _fetch_incremental(
        self,
        *,
        access_token: str,
        history_id: str,
        page_token: str | None,
        headers: dict[str, str],
    ) -> SyncResult:
        """Incremental sync using Gmail history.list() API.

        Messages returned by history.list() are grouped by thread and
        each affected thread is re-fetched as a whole, producing one
        UDF document per thread (TASK-124).
        """
        params: dict[str, str | int] = {
            "startHistoryId": history_id,
            "historyTypes": "messageAdded",
            "maxResults": min(self.config.max_batch_size, 100),
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GMAIL_API}/users/me/history",
                    params=params,
                    headers=headers,
                )
                _raise_for_rate_limit(response)

                if response.status_code == 404:
                    # historyId expired  trigger full re-sync
                    logger.warning(
                        "historyId expired (404), triggering full re-sync: connection_id=%s",
                        self.connection_id,
                    )
                    return SyncResult(documents=[], new_cursor=None, has_more=True)

                response.raise_for_status()
                data = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Gmail history API error: HTTP {exc.response.status_code}",
                code="GMAIL_HISTORY_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Gmail history API network error: {exc}",
                code="GMAIL_NETWORK_ERROR",
            ) from exc

        # Collect unique thread IDs from history records
        thread_ids: set[str] = set()
        for record in data.get("history", []):
            for msg_added in record.get("messagesAdded", []):
                msg = msg_added.get("message", {})
                tid = msg.get("threadId")
                if tid:
                    thread_ids.add(tid)

        documents, errors = await self._resolve_threads(
            access_token=access_token,
            thread_ids=thread_ids,
        )

        next_page_token = data.get("nextPageToken")
        new_history_id = data.get("historyId", history_id)

        new_cursor = _encode_cursor(
            history_id=str(new_history_id),
            page_token=next_page_token,
        )

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=next_page_token is not None,
        )

    async def _resolve_threads(
        self,
        *,
        access_token: str,
        thread_ids: set[str],
    ) -> tuple[list[UnifiedDocument], list[SyncError]]:
        """Fetch full threads and merge messages into one UDF per thread.

        Each thread becomes a single ``UnifiedDocument`` with:
        - ``source_id``: the Gmail thread ID
        - ``content``: concatenated messages in chronological order
        - ``participants``: deduplicated From/To addresses across all messages
        - ``raw_hash``: SHA-256 of the merged content for idempotent upsert
        """
        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []

        for thread_id in thread_ids:
            try:
                thread_data = await self._fetch_thread(access_token, thread_id)
                doc = self._normalize_thread(thread_data)
                documents.append(doc)
            except Exception as exc:
                errors.append(SyncError(source_id=thread_id, error=str(exc)))

        return documents, errors

    async def _fetch_thread(self, access_token: str, thread_id: str) -> dict[str, object]:
        """Fetch a full Gmail thread by ID (format=full)."""
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GMAIL_API}/users/me/threads/{thread_id}",
                    params={"format": "full"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                _raise_for_rate_limit(response)
                response.raise_for_status()
                return response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Gmail fetch thread failed: HTTP {exc.response.status_code}",
                code="GMAIL_THREAD_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Gmail fetch thread network error: {exc}",
                code="GMAIL_NETWORK_ERROR",
            ) from exc

    def _normalize_thread(self, thread_data: dict[str, object]) -> UnifiedDocument:
        """Merge all messages in a thread into a single UDF document."""
        thread_id = thread_data.get("id")
        if not thread_id:
            raise ConnectorError("Gmail thread missing 'id'", code="GMAIL_INVALID_THREAD")

        messages = thread_data.get("messages", [])
        if not isinstance(messages, list) or not messages:
            raise ConnectorError(
                f"Gmail thread {thread_id} has no messages",
                code="GMAIL_EMPTY_THREAD",
            )

        # Sort messages chronologically by internalDate
        sorted_msgs = sorted(
            messages,
            key=lambda m: int(m.get("internalDate", 0))
            if isinstance(m.get("internalDate"), (str, int))
            else 0,
        )

        # Extract thread-level data from first message (subject) and all messages (participants)
        all_participants: list[str] = []
        seen_participants: set[str] = set()
        content_parts: list[str] = []
        thread_subject = ""
        earliest_date = ""
        all_label_ids: set[str] = set()

        for msg in sorted_msgs:
            payload = msg.get("payload", {})
            if not isinstance(payload, dict):
                payload = {}

            headers_list = payload.get("headers", [])
            if not isinstance(headers_list, list):
                headers_list = []

            subject = _extract_header(headers_list, "Subject")
            from_addr = _extract_header(headers_list, "From")
            to_addr = _extract_header(headers_list, "To")
            cc_addr = _extract_header(headers_list, "Cc")
            date_str = _extract_header(headers_list, "Date")

            if not thread_subject and subject:
                thread_subject = subject
            if not earliest_date and date_str:
                earliest_date = date_str

            # Collect unique participants
            for addr in [from_addr, to_addr, cc_addr]:
                if addr:
                    for part in addr.split(","):
                        normalized = part.strip()
                        lower = normalized.lower()
                        if lower and lower not in seen_participants:
                            seen_participants.add(lower)
                            all_participants.append(normalized)

            # Accumulate labels
            label_ids = msg.get("labelIds", [])
            if isinstance(label_ids, list):
                all_label_ids.update(str(lid) for lid in label_ids)

            # Build per-message content block
            text_content = _extract_text_content(payload)
            snippet = msg.get("snippet", "")

            msg_parts: list[str] = []
            if from_addr:
                msg_parts.append(f"Von: {from_addr}")
            if date_str:
                msg_parts.append(f"Datum: {date_str}")
            if text_content:
                msg_parts.append(text_content)
            elif snippet:
                msg_parts.append(str(snippet))

            if msg_parts:
                content_parts.append("\n".join(msg_parts))

        # Build merged content
        thread_header = f"Betreff: {thread_subject}" if thread_subject else ""
        separator = "\n\n---\n\n"
        merged_body = separator.join(content_parts)
        content = f"{thread_header}\n\n{merged_body}" if thread_header else merged_body

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.GMAIL,
            source_id=str(thread_id),
            title=thread_subject or "(kein Betreff)",
            content=content,
            participants=all_participants,
            metadata={
                "thread_id": str(thread_id),
                "message_count": len(sorted_msgs),
                "subject": thread_subject,
                "date": earliest_date,
                "label_ids": sorted(all_label_ids),
            },
        )

    async def _fetch_message(self, access_token: str, msg_id: str) -> dict[str, object]:
        """Fetch a single Gmail message by ID (format=full)."""
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GMAIL_API}/users/me/messages/{msg_id}",
                    params={"format": "full"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                _raise_for_rate_limit(response)
                response.raise_for_status()
                return response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Gmail fetch message failed: HTTP {exc.response.status_code}",
                code="GMAIL_MESSAGE_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Gmail fetch message network error: {exc}",
                code="GMAIL_NETWORK_ERROR",
            ) from exc

    async def _get_history_id(self, access_token: str) -> str | None:
        """Get the current historyId from Gmail profile."""
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GMAIL_API}/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return str(response.json().get("historyId", ""))
        except Exception:
            logger.warning("Failed to get Gmail historyId", exc_info=True)
            return None

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        """Normalize a Gmail message to UnifiedDocument."""
        msg_id = raw.get("id")
        if not msg_id:
            raise ConnectorError("Gmail message missing 'id'", code="GMAIL_INVALID_MESSAGE")

        payload = raw.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}

        headers_list = payload.get("headers", [])
        if not isinstance(headers_list, list):
            headers_list = []

        subject = _extract_header(headers_list, "Subject")
        from_addr = _extract_header(headers_list, "From")
        to_addr = _extract_header(headers_list, "To")
        date_str = _extract_header(headers_list, "Date")
        thread_id = raw.get("threadId", "")

        # Extract text content (no attachments in MVP)
        text_content = _extract_text_content(payload)
        snippet = raw.get("snippet", "")

        # Build normalized content
        content_parts = []
        if subject:
            content_parts.append(f"Subject: {subject}")
        if from_addr:
            content_parts.append(f"From: {from_addr}")
        if to_addr:
            content_parts.append(f"To: {to_addr}")
        if text_content:
            content_parts.append(f"\n{text_content}")
        elif snippet:
            content_parts.append(f"\n{snippet}")

        content = "\n".join(content_parts) if content_parts else str(snippet)

        label_ids = raw.get("labelIds", [])

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.GMAIL,
            source_id=str(msg_id),
            title=subject or "(kein Betreff)",
            content=content,
            metadata={
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "date": date_str,
                "thread_id": str(thread_id),
                "label_ids": label_ids if isinstance(label_ids, list) else [],
                "snippet": str(snippet),
            },
        )

    async def health_check(self) -> bool:
        """Verify Gmail API is reachable with stored credentials."""
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped  no access_token: connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GMAIL_API}/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return response.status_code == 200
        except httpx.RequestError:
            logger.warning(
                "Health check failed  network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
