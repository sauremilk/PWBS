"""Notion connector — OAuth2, Polling-Sync, Normalizer (TASK-048..050).

Notion uses a *Public Integration* OAuth2 flow.  Unlike Google, Notion does
**not** issue refresh tokens — the access token stays valid until the user
revokes the integration in their Notion workspace settings.

References
----------
- https://developers.notion.com/docs/authorization
- https://developers.notion.com/reference/post-search
- https://developers.notion.com/reference/get-block-children
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
from pwbs.connectors.normalizer import normalize_document
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import ContentType, SourceType

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


def _encode_cursor(*, watermark: str | None, start_cursor: str | None = None) -> str:
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


# ---------------------------------------------------------------------------
# Block → Markdown conversion helpers (TASK-050)
# ---------------------------------------------------------------------------

_MAX_BLOCK_DEPTH = 5


def _extract_plain_text(rich_text: list[dict[str, JsonValue]]) -> str:
    """Extract plain text from a Notion ``rich_text`` array."""
    parts: list[str] = []
    for segment in rich_text:
        if isinstance(segment, dict):
            text = segment.get("plain_text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def _extract_mentions(rich_text: list[dict[str, JsonValue]]) -> list[dict[str, str]]:
    """Extract @-mentions and page/database links from ``rich_text``."""
    mentions: list[dict[str, str]] = []
    for segment in rich_text:
        if not isinstance(segment, dict) or segment.get("type") != "mention":
            continue
        mention_data = segment.get("mention")
        if not isinstance(mention_data, dict):
            continue
        mention_type = str(mention_data.get("type", ""))
        if mention_type == "user":
            user = mention_data.get("user", {})
            if isinstance(user, dict):
                mentions.append(
                    {
                        "type": "user",
                        "id": str(user.get("id", "")),
                        "name": str(user.get("name", "")),
                    }
                )
        elif mention_type == "page":
            page = mention_data.get("page", {})
            if isinstance(page, dict):
                mentions.append(
                    {
                        "type": "page",
                        "id": str(page.get("id", "")),
                    }
                )
        elif mention_type == "database":
            db = mention_data.get("database", {})
            if isinstance(db, dict):
                mentions.append(
                    {
                        "type": "database",
                        "id": str(db.get("id", "")),
                    }
                )
    return mentions


def _block_to_markdown(block: dict[str, JsonValue], *, indent: int = 0) -> str:
    """Convert a single Notion block to its Markdown representation."""
    block_type = str(block.get("type", ""))
    prefix = "  " * indent

    type_data = block.get(block_type)
    if not isinstance(type_data, dict):
        if block_type == "divider":
            return f"{prefix}---"
        return ""

    rich_text: list[dict[str, JsonValue]] = type_data.get("rich_text", [])  # type: ignore[assignment]
    text = _extract_plain_text(rich_text)

    # Recursively render pre-fetched children (attached as "_children")
    children_blocks: list[dict[str, JsonValue]] = block.get("_children", [])  # type: ignore[assignment]
    children_md = ""
    if isinstance(children_blocks, list) and children_blocks:
        child_parts = [_block_to_markdown(child, indent=indent + 1) for child in children_blocks]
        children_md = "\n".join(p for p in child_parts if p)

    if block_type == "paragraph":
        result = f"{prefix}{text}"
    elif block_type == "heading_1":
        result = f"{prefix}# {text}"
    elif block_type == "heading_2":
        result = f"{prefix}## {text}"
    elif block_type == "heading_3":
        result = f"{prefix}### {text}"
    elif block_type == "bulleted_list_item":
        result = f"{prefix}- {text}"
    elif block_type == "numbered_list_item":
        result = f"{prefix}1. {text}"
    elif block_type == "to_do":
        checked = type_data.get("checked", False)
        marker = "[x]" if checked else "[ ]"
        result = f"{prefix}- {marker} {text}"
    elif block_type == "toggle":
        result = f"{prefix}> **{text}**"
    elif block_type == "callout":
        icon = ""
        icon_data = type_data.get("icon")
        if isinstance(icon_data, dict):
            emoji = icon_data.get("emoji")
            if isinstance(emoji, str):
                icon = f"{emoji} "
        result = f"{prefix}> {icon}{text}"
    elif block_type == "quote":
        result = f"{prefix}> {text}"
    elif block_type == "code":
        language = str(type_data.get("language", ""))
        result = f"{prefix}```{language}\n{prefix}{text}\n{prefix}```"
    elif block_type == "divider":
        result = f"{prefix}---"
    elif block_type == "image":
        caption = _extract_plain_text(type_data.get("caption", []))  # type: ignore[arg-type]
        image_data = type_data.get("external") or type_data.get("file")
        url = ""
        if isinstance(image_data, dict):
            url = str(image_data.get("url", ""))
        result = f"{prefix}![{caption}]({url})" if url else f"{prefix}[Image: {caption}]"
    elif block_type == "child_page":
        child_title = str(type_data.get("title", ""))
        result = f"{prefix}[Page: {child_title}]"
    elif block_type == "child_database":
        child_title = str(type_data.get("title", ""))
        result = f"{prefix}[Database: {child_title}]"
    elif block_type == "bookmark":
        bookmark_url = str(type_data.get("url", ""))
        caption = _extract_plain_text(type_data.get("caption", []))  # type: ignore[arg-type]
        result = f"{prefix}[{caption or bookmark_url}]({bookmark_url})"
    elif block_type == "equation":
        expression = str(type_data.get("expression", ""))
        result = f"{prefix}$${expression}$$"
    else:
        result = f"{prefix}{text}" if text else ""

    if children_md:
        result = f"{result}\n{children_md}"

    return result


def _blocks_to_markdown(blocks: list[dict[str, JsonValue]]) -> str:
    """Convert a list of Notion blocks to joined Markdown content."""
    parts = [_block_to_markdown(block) for block in blocks]
    return "\n\n".join(p for p in parts if p)


def _extract_page_title(properties: dict[str, JsonValue]) -> str:
    """Extract the page title from Notion page properties."""
    for prop_value in properties.values():
        if not isinstance(prop_value, dict):
            continue
        if prop_value.get("type") == "title":
            title_array = prop_value.get("title")
            if isinstance(title_array, list):
                return _extract_plain_text(title_array) or "(Kein Titel)"  # type: ignore[arg-type]
    return "(Kein Titel)"


def _extract_page_properties(properties: dict[str, JsonValue]) -> dict[str, str | list[str]]:
    """Extract notable page properties as flat metadata dict."""
    meta: dict[str, str | list[str]] = {}
    for name, prop_value in properties.items():
        if not isinstance(prop_value, dict):
            continue
        prop_type = str(prop_value.get("type", ""))
        if prop_type == "title":
            continue  # handled separately
        elif prop_type == "rich_text":
            text = _extract_plain_text(prop_value.get("rich_text", []))  # type: ignore[arg-type]
            if text:
                meta[name] = text
        elif prop_type == "select":
            select = prop_value.get("select")
            if isinstance(select, dict):
                val = select.get("name")
                if isinstance(val, str):
                    meta[name] = val
        elif prop_type == "multi_select":
            ms = prop_value.get("multi_select")
            if isinstance(ms, list):
                vals = [str(item.get("name", "")) for item in ms if isinstance(item, dict)]
                if vals:
                    meta[name] = vals
        elif prop_type == "date":
            date_val = prop_value.get("date")
            if isinstance(date_val, dict):
                start = date_val.get("start")
                if isinstance(start, str):
                    meta[name] = start
        elif prop_type == "url":
            url = prop_value.get("url")
            if isinstance(url, str):
                meta[name] = url
        elif prop_type == "email":
            email = prop_value.get("email")
            if isinstance(email, str):
                meta[name] = email
        elif prop_type == "checkbox":
            checked = prop_value.get("checkbox")
            if isinstance(checked, bool):
                meta[name] = str(checked)
        elif prop_type == "number":
            num = prop_value.get("number")
            if num is not None:
                meta[name] = str(num)
        elif prop_type == "status":
            status = prop_value.get("status")
            if isinstance(status, dict):
                val = status.get("name")
                if isinstance(val, str):
                    meta[name] = val
    return meta


def _collect_all_mentions(blocks: list[dict[str, JsonValue]]) -> list[dict[str, str]]:
    """Recursively collect all @-mentions and page links from blocks."""
    all_mentions: list[dict[str, str]] = []
    for block in blocks:
        block_type = str(block.get("type", ""))
        type_data = block.get(block_type)
        if isinstance(type_data, dict):
            rich_text = type_data.get("rich_text", [])
            if isinstance(rich_text, list):
                all_mentions.extend(_extract_mentions(rich_text))  # type: ignore[arg-type]
        children = block.get("_children")
        if isinstance(children, list):
            all_mentions.extend(_collect_all_mentions(children))  # type: ignore[arg-type]
    return all_mentions


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
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

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

    async def _fetch_blocks(
        self,
        block_id: str,
        access_token: str,
        *,
        depth: int = 0,
    ) -> list[dict[str, JsonValue]]:
        """Recursively fetch child blocks for a page/block (TASK-050).

        Recursion is capped at ``_MAX_BLOCK_DEPTH`` (5) levels to avoid
        runaway traversals.
        """
        if depth >= _MAX_BLOCK_DEPTH:
            return []

        blocks: list[dict[str, JsonValue]] = []
        start_cursor: str | None = None

        while True:
            params: dict[str, str | int] = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            try:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    response = await client.get(
                        f"{_NOTION_API}/blocks/{block_id}/children",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Notion-Version": _NOTION_API_VERSION,
                        },
                        params=params,
                    )
            except httpx.RequestError as exc:
                logger.warning(
                    "Failed to fetch blocks for %s at depth %d: %s",
                    block_id,
                    depth,
                    exc,
                )
                break

            _raise_for_rate_limit(response)

            if response.status_code != 200:  # noqa: PLR2004
                logger.warning(
                    "Block fetch failed for %s: HTTP %d",
                    block_id,
                    response.status_code,
                )
                break

            data = response.json()
            results: list[dict[str, JsonValue]] = data.get("results", [])

            for block in results:
                if block.get("has_children"):
                    child_id = str(block.get("id", ""))
                    if child_id:
                        children = await self._fetch_blocks(
                            child_id,
                            access_token,
                            depth=depth + 1,
                        )
                        block["_children"] = children  # type: ignore[assignment]
                blocks.append(block)

            if not data.get("has_more"):
                break
            start_cursor = data.get("next_cursor")
            if not start_cursor:
                break

        return blocks

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
            Normalised documents, errors, new cursor, and ``has_more`` flag
            for pagination.

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
                # Fetch child blocks for content extraction (TASK-050)
                if page.get("object") in ("page", "database"):
                    page_blocks = await self._fetch_blocks(page_id, access_token)
                    page["_blocks"] = page_blocks  # type: ignore[assignment]

                doc = await self.normalize(page)
                documents.append(doc)

            except Exception as exc:
                errors.append(
                    SyncError(
                        source_id=page_id,
                        error=str(exc),
                    )
                )
            finally:
                # Always update watermark regardless of success/failure
                page_edited = str(page.get("last_edited_time", ""))
                if page_edited and (not latest_edited or page_edited > latest_edited):
                    latest_edited = page_edited

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
        """Normalize a raw Notion page/database entry into a *UnifiedDocument*.

        Converts Notion blocks (pre-fetched into ``raw["_blocks"]``) to
        Markdown, extracts page properties as metadata, and collects
        @-mentions and page links (TASK-050).

        ``content_type`` is always ``MARKDOWN``.
        """
        from datetime import datetime as _datetime

        page_id = str(raw.get("id", ""))
        if not page_id:
            raise ConnectorError(
                "Notion page missing 'id' field",
                code="NOTION_MISSING_PAGE_ID",
            )

        object_type = str(raw.get("object", "page"))

        # Extract properties
        properties: dict[str, JsonValue] = raw.get("properties", {})  # type: ignore[assignment]
        if not isinstance(properties, dict):
            properties = {}

        title = _extract_page_title(properties)
        prop_metadata = _extract_page_properties(properties)

        # Convert pre-fetched blocks to Markdown content
        blocks: list[dict[str, JsonValue]] = raw.get("_blocks", [])  # type: ignore[assignment]
        if not isinstance(blocks, list):
            blocks = []
        content = _blocks_to_markdown(blocks)
        if not content:
            content = title  # fallback: use title as content

        # Collect mentions from blocks and properties
        mentions = _collect_all_mentions(blocks)
        for prop_value in properties.values():
            if isinstance(prop_value, dict) and prop_value.get("type") == "rich_text":
                rt = prop_value.get("rich_text")
                if isinstance(rt, list):
                    mentions.extend(_extract_mentions(rt))  # type: ignore[arg-type]

        # Build metadata
        metadata: dict[str, str | list[str] | list[dict[str, str]]] = {
            "object_type": object_type,
            **prop_metadata,
        }
        if mentions:
            metadata["mentions"] = mentions  # type: ignore[assignment]

        # Parse timestamps
        created_at: _datetime | None = None
        updated_at: _datetime | None = None
        if raw_created := raw.get("created_time"):
            try:
                created_at = _datetime.fromisoformat(str(raw_created))
            except ValueError:
                pass
        if raw_updated := raw.get("last_edited_time"):
            try:
                updated_at = _datetime.fromisoformat(str(raw_updated))
            except ValueError:
                pass

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.NOTION,
            source_id=page_id,
            title=title,
            content=content,
            content_type=ContentType.MARKDOWN,
            metadata=metadata,  # type: ignore[arg-type]
            created_at=created_at,
            updated_at=updated_at,
        )

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
