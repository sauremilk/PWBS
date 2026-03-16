"""Outlook Mail connector - Microsoft Graph API (TASK-128).

Implements:
- OAuth2 authorization URL generation via Azure AD v2.0 (Scope: Mail.Read)
- Authorization code -> token exchange
- Delta-Sync via Microsoft Graph deltaLink for incremental queries
- Thread-Resolution: E-Mail-Threads via conversationId merged into single UDF
- HTML-Body -> plaintext conversion
- Attachments referenced as metadata (no download in MVP)
- Health check via /me endpoint

Privacy: Only metadata and text content are imported.
Attachments are not downloaded in the MVP (metadata only).
"""

from __future__ import annotations

import json
import logging
import re
import time
from html import unescape as html_unescape
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
# Microsoft Graph / Azure AD constants
# ---------------------------------------------------------------------------

_MS_AUTH_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
_MS_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_GRAPH_API = "https://graph.microsoft.com/v1.0"
OUTLOOK_SCOPE = "https://graph.microsoft.com/Mail.Read offline_access"
_HTTP_TIMEOUT = 30.0
_MAX_MESSAGES_PER_PAGE = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on 429 so base-class retry kicks in."""
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RateLimitError(
            f"Microsoft Graph rate limit hit, retry after {retry_after}s",
            retry_after=int(retry_after),
        )


def _strip_html(html: str) -> str:
    """Convert HTML to plaintext by stripping tags and decoding entities."""
    # Remove style and script blocks
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br>, <p>, <div> closings with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|tr|li)>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html_unescape(text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _encode_cursor(*, delta_link: str | None = None, page_link: str | None = None) -> str:
    """Encode sync state as an opaque JSON cursor."""
    return json.dumps({"delta_link": delta_link, "page_link": page_link})


def _decode_cursor(cursor: str) -> tuple[str | None, str | None]:
    """Decode cursor -> (delta_link, page_link)."""
    try:
        data = json.loads(cursor)
        return data.get("delta_link"), data.get("page_link")
    except (json.JSONDecodeError, TypeError):
        return None, None


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class OutlookMailConnector(BaseConnector):
    """Outlook Mail data-source connector (TASK-128).

    Uses Microsoft Identity Platform (Azure AD v2.0) for OAuth2.
    Messages are fetched via Microsoft Graph /me/messages with delta queries.
    E-Mail threads are resolved via conversationId.

    For sync, pass the decrypted ``access_token`` in
    ``config.extra["access_token"]``.
    """

    source_type: SourceType = SourceType.OUTLOOK_MAIL

    def __init__(
        self,
        *,
        owner_id: UUID,
        connection_id: UUID,
        config: ConnectorConfig,
    ) -> None:
        super().__init__(owner_id=owner_id, connection_id=connection_id, config=config)

    # ---- OAuth2 flow (static) ----------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Microsoft OAuth2 authorization URL."""
        settings = get_settings()
        if not settings.ms_client_id:
            raise ConnectorError(
                "MS_CLIENT_ID not configured",
                code="MISSING_CLIENT_CREDENTIALS",
            )

        tenant = settings.ms_tenant_id or "common"
        base_url = _MS_AUTH_URL.format(tenant=tenant)

        params = {
            "client_id": settings.ms_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": OUTLOOK_SCOPE,
            "response_mode": "query",
            "state": state,
        }
        return f"{base_url}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(*, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange an OAuth2 authorization code for tokens."""
        settings = get_settings()
        client_id = settings.ms_client_id
        client_secret = settings.ms_client_secret.get_secret_value()

        if not client_id or not client_secret:
            raise ConnectorError(
                "Microsoft OAuth client credentials not configured",
                code="MISSING_CLIENT_CREDENTIALS",
            )

        tenant = settings.ms_tenant_id or "common"
        token_url = _MS_TOKEN_URL.format(tenant=tenant)

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scope": OUTLOOK_SCOPE,
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(token_url, data=payload)
                _raise_for_rate_limit(response)
                response.raise_for_status()
                data = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.json() if exc.response.content else {}
            error_desc = error_body.get("error_description", str(exc))
            raise ConnectorError(
                f"Microsoft OAuth code exchange failed: {error_desc}",
                code="OAUTH_CODE_EXCHANGE_FAILED",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Microsoft OAuth code exchange network error: {exc}",
                code="OAUTH_NETWORK_ERROR",
            ) from exc

        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Microsoft OAuth response missing access_token",
                code="OAUTH_INVALID_RESPONSE",
            )

        expires_in = data.get("expires_in")
        expires_at = time.time() + float(expires_in) if expires_in else None

        return OAuthTokens(
            access_token=SecretStr(access_token),
            refresh_token=SecretStr(data.get("refresh_token", "")),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", OUTLOOK_SCOPE),
        )

    # ---- BaseConnector abstract methods ------------------------------------

    def _get_access_token(self) -> str:
        """Extract the access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "access_token missing in connector config",
                code="OUTLOOK_MISSING_TOKEN",
            )
        return token

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Outlook messages using Microsoft Graph delta queries.

        - ``cursor=None`` -> initial delta sync (full mailbox snapshot)
        - ``cursor=<encoded>`` -> incremental sync via deltaLink

        Messages belonging to the same thread (conversationId) are merged
        into a single UDF document.
        """
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []

        # Determine the starting URL
        delta_link: str | None = None
        page_link: str | None = None

        if cursor is not None:
            delta_link, page_link = _decode_cursor(cursor)

        # Use page_link (pagination) > delta_link (incremental) > initial delta
        url = (
            page_link
            or delta_link
            or (
                f"{_GRAPH_API}/me/mailFolders/inbox/messages/delta"
                f"?$select=id,subject,from,toRecipients,ccRecipients,"
                f"body,receivedDateTime,conversationId,hasAttachments,"
                f"importance,isRead"
                f"&$top={_MAX_MESSAGES_PER_PAGE}"
            )
        )

        # Collect all messages in this batch
        raw_messages: list[dict[str, object]] = []
        has_more = False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(url, headers=headers)
                _raise_for_rate_limit(response)
                response.raise_for_status()
                data = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            errors.append(
                SyncError(
                    source_id="inbox",
                    error=f"Graph API HTTP {exc.response.status_code}",
                )
            )
            return SyncResult(
                documents=documents,
                new_cursor=cursor,
                errors=errors,
                has_more=False,
            )
        except httpx.RequestError as exc:
            errors.append(
                SyncError(
                    source_id="inbox",
                    error=f"Network error: {exc}",
                )
            )
            return SyncResult(
                documents=documents,
                new_cursor=cursor,
                errors=errors,
                has_more=False,
            )

        raw_messages.extend(data.get("value", []))

        # Check for next page or delta link
        next_link = data.get("@odata.nextLink")
        new_delta_link_val = data.get("@odata.deltaLink")

        if next_link:
            has_more = True
            new_cursor = _encode_cursor(delta_link=delta_link, page_link=next_link)
        elif new_delta_link_val:
            new_cursor = _encode_cursor(delta_link=new_delta_link_val)
        else:
            new_cursor = cursor

        # Group messages by conversationId for thread resolution
        conversations: dict[str, list[dict[str, object]]] = {}
        for msg in raw_messages:
            conv_id = str(msg.get("conversationId", msg.get("id", "")))
            conversations.setdefault(conv_id, []).append(msg)

        # Generate one UDF per conversation
        for conv_id, messages in conversations.items():
            try:
                doc = self._normalize_thread(conv_id, messages)
                documents.append(doc)
            except Exception as exc:
                errors.append(
                    SyncError(
                        source_id=conv_id,
                        error=str(exc),
                    )
                )

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=has_more,
        )

    def _normalize_thread(
        self,
        conversation_id: str,
        messages: list[dict[str, object]],
    ) -> UnifiedDocument:
        """Merge messages with the same conversationId into a single UDF document."""
        # Sort by receivedDateTime
        messages.sort(key=lambda m: str(m.get("receivedDateTime", "")))

        subjects: list[str] = []
        content_parts: list[str] = []
        participants: set[str] = set()
        has_attachments = False

        for msg in messages:
            subject = str(msg.get("subject", ""))
            if subject and subject not in subjects:
                subjects.append(subject)

            received = str(msg.get("receivedDateTime", ""))

            # Participants
            from_obj = msg.get("from")
            if isinstance(from_obj, dict):
                email_addr = from_obj.get("emailAddress")
                if isinstance(email_addr, dict):
                    addr = str(email_addr.get("address", ""))
                    if addr:
                        participants.add(addr)

            for field in ("toRecipients", "ccRecipients"):
                recipients = msg.get(field, [])
                if isinstance(recipients, list):
                    for r in recipients:
                        if isinstance(r, dict):
                            email_addr = r.get("emailAddress")
                            if isinstance(email_addr, dict):
                                addr = str(email_addr.get("address", ""))
                                if addr:
                                    participants.add(addr)

            # Body (HTML -> plaintext)
            body_obj = msg.get("body")
            body_text = ""
            if isinstance(body_obj, dict):
                content_type = str(body_obj.get("contentType", "text")).lower()
                raw_content = str(body_obj.get("content", ""))
                if content_type == "html":
                    body_text = _strip_html(raw_content)
                else:
                    body_text = raw_content

            # Build per-message content block
            from_str = ""
            from_data = msg.get("from")
            if isinstance(from_data, dict):
                ea = from_data.get("emailAddress")
                if isinstance(ea, dict):
                    from_str = str(ea.get("address", ""))

            header = f"From: {from_str}" if from_str else ""
            if received:
                header += f"  [{received}]" if header else f"[{received}]"
            if header:
                content_parts.append(header)
            if body_text:
                content_parts.append(body_text)

            if msg.get("hasAttachments"):
                has_attachments = True

        separator = "\n---\n"
        merged_content = separator.join(content_parts) if content_parts else "(leer)"

        title = subjects[0] if subjects else "(kein Betreff)"

        # Parse timestamps
        earliest = str(messages[0].get("receivedDateTime", "")) if messages else ""
        latest = str(messages[-1].get("receivedDateTime", "")) if messages else ""

        created_at = None
        updated_at = None
        if earliest:
            try:
                from datetime import datetime

                created_at = datetime.fromisoformat(earliest.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        if latest:
            try:
                from datetime import datetime

                updated_at = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.OUTLOOK_MAIL,
            source_id=f"outlook:conv:{conversation_id}",
            title=title,
            content=merged_content,
            participants=sorted(participants),
            created_at=created_at,
            updated_at=updated_at,
            metadata={
                "conversation_id": conversation_id,
                "subjects": subjects,
                "message_count": len(messages),
                "has_attachments": has_attachments,
                "participants": sorted(participants),
                "importance": str(messages[-1].get("importance", "normal")),
            },
        )

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        """Normalize a single Outlook message to UnifiedDocument."""
        msg_id = raw.get("id")
        if not msg_id:
            raise ConnectorError(
                "Outlook message missing 'id'",
                code="OUTLOOK_INVALID_MESSAGE",
            )

        subject = str(raw.get("subject", "(kein Betreff)"))
        received = str(raw.get("receivedDateTime", ""))
        conversation_id = str(raw.get("conversationId", ""))

        # Participants
        participants: list[str] = []
        from_obj = raw.get("from")
        if isinstance(from_obj, dict):
            email_addr = from_obj.get("emailAddress")
            if isinstance(email_addr, dict):
                addr = str(email_addr.get("address", ""))
                if addr:
                    participants.append(addr)

        for field in ("toRecipients", "ccRecipients"):
            recipients = raw.get(field, [])
            if isinstance(recipients, list):
                for r in recipients:
                    if isinstance(r, dict):
                        email_addr = r.get("emailAddress")
                        if isinstance(email_addr, dict):
                            addr = str(email_addr.get("address", ""))
                            if addr and addr not in participants:
                                participants.append(addr)

        # Body
        body_obj = raw.get("body")
        body_text = ""
        if isinstance(body_obj, dict):
            content_type = str(body_obj.get("contentType", "text")).lower()
            raw_content = str(body_obj.get("content", ""))
            if content_type == "html":
                body_text = _strip_html(raw_content)
            else:
                body_text = raw_content

        content_parts: list[str] = []
        if subject:
            content_parts.append(f"Subject: {subject}")
        if participants:
            content_parts.append(f"From: {participants[0]}")
        if body_text:
            content_parts.append(f"\n{body_text}")

        content = "\n".join(content_parts) if content_parts else str(subject)

        # Parse timestamp
        created_at = None
        if received:
            try:
                from datetime import datetime

                created_at = datetime.fromisoformat(received.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.OUTLOOK_MAIL,
            source_id=str(msg_id),
            title=subject,
            content=content,
            participants=participants,
            created_at=created_at,
            metadata={
                "conversation_id": conversation_id,
                "subject": subject,
                "from": participants[0] if participants else "",
                "received_date_time": received,
                "has_attachments": bool(raw.get("hasAttachments")),
                "importance": str(raw.get("importance", "normal")),
            },
        )

    async def health_check(self) -> bool:
        """Verify Microsoft Graph API is reachable with stored credentials."""
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped - no access_token: connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_GRAPH_API}/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return response.status_code == 200
        except httpx.RequestError:
            logger.warning(
                "Health check failed - network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
