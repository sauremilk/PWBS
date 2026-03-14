"""Google Docs connector – OAuth2 flow + Drive/Docs API (TASK-127).

Implements:
- OAuth2 authorization URL generation (scopes: drive.readonly + documents.readonly)
- Authorization code → token exchange (reuses Google client credentials)
- Cursor-based incremental sync via ``modifiedTime`` (Drive API)
- Google Docs structured JSON → Markdown conversion
- Content-hash deduplication via normalizer
- Shared-docs handling via ``driveId`` + ``includeItemsFromAllDrives``
- Health check via Drive API about endpoint

Privacy: Only text content is imported.
Embedded images are referenced by URL but not downloaded in MVP.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncError, SyncResult
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
# Google OAuth2 / API constants
# ---------------------------------------------------------------------------

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DRIVE_API = "https://www.googleapis.com/drive/v3"
_DOCS_API = "https://docs.googleapis.com/v1"

GOOGLE_DOCS_SCOPES = (
    "https://www.googleapis.com/auth/drive.readonly "
    "https://www.googleapis.com/auth/documents.readonly"
)

_HTTP_TIMEOUT = 30.0

# Drive API fields to retrieve per file
_DRIVE_FILE_FIELDS = "files(id,name,modifiedTime,createdTime,owners,lastModifyingUser,mimeType)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on 429/503 so base-class retry kicks in."""
    if response.status_code in (429, 503):
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            f"Google API rate-limited: HTTP {response.status_code}",
            retry_after=int(retry_after) if retry_after and retry_after.isdigit() else None,
        )


def _encode_cursor(*, modified_time: str, page_token: str | None = None) -> str:
    """Encode sync state as an opaque JSON cursor."""
    payload: dict[str, str] = {"modifiedTime": modified_time}
    if page_token:
        payload["pageToken"] = page_token
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str | None, str | None]:
    """Decode cursor → (modifiedTime, pageToken)."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
        return data.get("modifiedTime"), data.get("pageToken")
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Google Docs JSON → Markdown conversion
# ---------------------------------------------------------------------------


def _convert_text_run(text_run: dict[str, object]) -> str:
    """Convert a single TextRun element to Markdown."""
    content = str(text_run.get("content", ""))
    style = text_run.get("textStyle", {})
    if not isinstance(style, dict):
        return content

    # Don't apply formatting to whitespace-only content
    stripped = content.strip()
    if not stripped:
        return content

    # Preserve leading/trailing whitespace around formatted text
    leading = content[: len(content) - len(content.lstrip())]
    trailing = content[len(content.rstrip()) :]
    inner = stripped

    if style.get("bold"):
        inner = f"**{inner}**"
    if style.get("italic"):
        inner = f"*{inner}*"
    if style.get("strikethrough"):
        inner = f"~~{inner}~~"
    if style.get("underline") and not style.get("link"):
        # Markdown has no native underline; skip if it's a link
        pass

    link = style.get("link", {})
    if isinstance(link, dict) and link.get("url"):
        inner = f"[{inner}]({link['url']})"

    return f"{leading}{inner}{trailing}"


def _convert_paragraph(paragraph: dict[str, object]) -> str:
    """Convert a Paragraph element to a Markdown line."""
    style = paragraph.get("paragraphStyle", {})
    named_style = style.get("namedStyleType", "") if isinstance(style, dict) else ""

    elements = paragraph.get("elements", [])
    text_parts: list[str] = []
    for elem in elements if isinstance(elements, list) else []:
        if not isinstance(elem, dict):
            continue
        text_run = elem.get("textRun")
        if isinstance(text_run, dict):
            text_parts.append(_convert_text_run(text_run))

    line = "".join(text_parts).rstrip("\n")

    # Map heading styles
    heading_map: dict[str, str] = {
        "HEADING_1": "# ",
        "HEADING_2": "## ",
        "HEADING_3": "### ",
        "HEADING_4": "#### ",
        "HEADING_5": "##### ",
        "HEADING_6": "###### ",
    }

    prefix = heading_map.get(str(named_style), "")

    # Bullet/numbered list detection via bullet property
    bullet = paragraph.get("bullet")
    if isinstance(bullet, dict):
        nesting = bullet.get("nestingLevel", 0)
        indent = "  " * (int(nesting) if isinstance(nesting, int) else 0)
        list_id = bullet.get("listId", "")
        # Simple heuristic: if listId exists, it's a list item
        if list_id:
            return f"{indent}- {line}"

    if prefix:
        return f"{prefix}{line}"
    return line


def _convert_table(table: dict[str, object]) -> str:
    """Convert a Table element to Markdown table."""
    rows = table.get("tableRows", [])
    if not isinstance(rows, list) or not rows:
        return ""

    md_rows: list[str] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        cells = row.get("tableCells", [])
        cell_texts: list[str] = []
        for cell in cells if isinstance(cells, list) else []:
            if not isinstance(cell, dict):
                continue
            # Each cell contains content (paragraphs)
            cell_content = cell.get("content", [])
            cell_lines: list[str] = []
            for block in cell_content if isinstance(cell_content, list) else []:
                if isinstance(block, dict) and "paragraph" in block:
                    cell_lines.append(_convert_paragraph(block["paragraph"]))
            cell_texts.append(" ".join(cell_lines).strip())

        md_rows.append("| " + " | ".join(cell_texts) + " |")
        # Add separator after header row
        if i == 0:
            md_rows.append("| " + " | ".join("---" for _ in cell_texts) + " |")

    return "\n".join(md_rows)


def convert_doc_to_markdown(doc_json: dict[str, object]) -> str:
    """Convert a Google Docs API document JSON response to Markdown.

    Handles paragraphs (headings, body text, lists) and tables.
    Inline formatting (bold, italic, links) is preserved.

    Args:
        doc_json: The full document resource from ``documents.get``.

    Returns:
        Markdown string representation of the document content.
    """
    body = doc_json.get("body", {})
    content = body.get("content", []) if isinstance(body, dict) else []

    lines: list[str] = []
    for element in content if isinstance(content, list) else []:
        if not isinstance(element, dict):
            continue

        if "paragraph" in element:
            lines.append(_convert_paragraph(element["paragraph"]))
        elif "table" in element:
            lines.append(_convert_table(element["table"]))
        elif "sectionBreak" in element:
            lines.append("---")

    # Clean up excessive blank lines
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class GoogleDocsConnector(BaseConnector):
    """Google Docs data-source connector (TASK-127).

    Reuses the same Google OAuth2 credentials (``google_client_id``,
    ``google_client_secret``) as other Google connectors, but with
    Drive + Docs API scopes.

    For sync and normalization, pass the decrypted ``access_token`` in
    ``config.extra["access_token"]``.
    """

    # ---- OAuth2 flow (static) ----------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Google Docs OAuth2 authorization URL."""
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
            "scope": GOOGLE_DOCS_SCOPES,
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
                f"Google Docs OAuth code exchange failed: {error_desc}",
                code="OAUTH_CODE_EXCHANGE_FAILED",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Google Docs OAuth code exchange network error: {exc}",
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
            scope=data.get("scope", GOOGLE_DOCS_SCOPES),
        )

    # ---- BaseConnector abstract methods ------------------------------------

    def _get_access_token(self) -> str:
        """Extract the access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "Missing access_token in config.extra for Google Docs connector",
                code="GDOCS_MISSING_TOKEN",
            )
        return token

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Google Docs modified since *cursor*.

        Uses the Drive API ``files.list`` with ``modifiedTime > cursor``
        filter, restricted to ``mimeType = application/vnd.google-apps.document``.
        For each file, fetches content via the Docs API and converts to Markdown.

        Args:
            cursor: Opaque cursor encoding ``modifiedTime`` and ``pageToken``,
                    or ``None`` for initial full sync.

        Returns:
            SyncResult with normalized documents and the new cursor.
        """
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        # Build Drive API query
        query_parts = ["mimeType = 'application/vnd.google-apps.document'", "trashed = false"]
        modified_time: str | None = None
        page_token: str | None = None

        if cursor is not None:
            modified_time, page_token = _decode_cursor(cursor)
            if modified_time:
                query_parts.append(f"modifiedTime > '{modified_time}'")

        params: dict[str, str | int] = {
            "q": " and ".join(query_parts),
            "orderBy": "modifiedTime asc",
            "pageSize": min(self.config.max_batch_size, 100),
            "fields": f"nextPageToken,{_DRIVE_FILE_FIELDS}",
            "includeItemsFromAllDrives": "true",
            "supportsAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        # List files from Drive API
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_DRIVE_API}/files",
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
                f"Drive API error: HTTP {exc.response.status_code}",
                code="DRIVE_API_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Drive API network error: {exc}",
                code="DRIVE_NETWORK_ERROR",
            ) from exc

        files = data.get("files", [])
        next_page_token = data.get("nextPageToken")
        has_more = next_page_token is not None

        # Fetch content for each document
        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []
        latest_modified: str | None = modified_time

        for file_meta in files:
            if not isinstance(file_meta, dict):
                continue
            doc_id = file_meta.get("id", "")
            doc_name = file_meta.get("name", "Untitled")
            doc_modified = file_meta.get("modifiedTime", "")

            try:
                doc = await self._fetch_and_normalize(
                    access_token=access_token,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    file_meta=file_meta,
                )
                documents.append(doc)

                # Track latest modifiedTime for cursor
                if doc_modified and (latest_modified is None or doc_modified > latest_modified):
                    latest_modified = doc_modified

            except Exception as exc:
                logger.warning("Failed to fetch Google Doc %s: %s", doc_id, exc)
                errors.append(SyncError(source_id=doc_id, error=str(exc)))

        # Build new cursor
        new_cursor: str | None = None
        if latest_modified:
            new_cursor = _encode_cursor(
                modified_time=latest_modified,
                page_token=next_page_token,
            )

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=has_more,
        )

    async def _fetch_and_normalize(
        self,
        *,
        access_token: str,
        doc_id: str,
        doc_name: str,
        file_meta: dict[str, object],
    ) -> UnifiedDocument:
        """Fetch a single Google Doc's content and normalize to UDF."""
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_DOCS_API}/documents/{doc_id}",
                    headers=headers,
                )
                _raise_for_rate_limit(response)
                response.raise_for_status()
                doc_json = response.json()
        except RateLimitError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ConnectorError(
                f"Docs API error for {doc_id}: HTTP {exc.response.status_code}",
                code="DOCS_API_ERROR",
            ) from exc
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Docs API network error for {doc_id}: {exc}",
                code="DOCS_NETWORK_ERROR",
            ) from exc

        # Convert structured JSON to Markdown
        markdown_content = convert_doc_to_markdown(doc_json)

        # Extract metadata
        owners = file_meta.get("owners", [])
        owner_names: list[str] = []
        if isinstance(owners, list):
            for owner in owners:
                if isinstance(owner, dict):
                    name = owner.get("displayName") or owner.get("emailAddress", "")
                    if name:
                        owner_names.append(str(name))

        last_modifier = file_meta.get("lastModifyingUser", {})
        modifier_name = ""
        if isinstance(last_modifier, dict):
            modifier_name = str(
                last_modifier.get("displayName")
                or last_modifier.get("emailAddress", "")
            )

        created_time = file_meta.get("createdTime")
        modified_time = file_meta.get("modifiedTime")

        metadata: dict[str, object] = {
            "doc_id": doc_id,
            "mime_type": "application/vnd.google-apps.document",
            "owners": owner_names,
            "last_modifier": modifier_name,
        }

        created_at = (
            datetime.fromisoformat(str(created_time).replace("Z", "+00:00"))
            if created_time
            else None
        )
        updated_at = (
            datetime.fromisoformat(str(modified_time).replace("Z", "+00:00"))
            if modified_time
            else None
        )

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.GOOGLE_DOCS,
            source_id=doc_id,
            title=doc_name,
            content=markdown_content,
            content_type=ContentType.MARKDOWN,
            metadata=metadata,
            participants=owner_names,
            created_at=created_at,
            updated_at=updated_at,
        )

    async def normalize(self, raw_data: dict[str, object]) -> UnifiedDocument:
        """Normalize a raw Google Docs document to UDF.

        This method is provided for the BaseConnector interface but is not
        the primary normalization path. ``_fetch_and_normalize`` handles
        the full flow during ``fetch_since``.
        """
        doc_id = str(raw_data.get("id", ""))
        doc_name = str(raw_data.get("name", "Untitled"))
        markdown_content = convert_doc_to_markdown(raw_data)

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.GOOGLE_DOCS,
            source_id=doc_id,
            title=doc_name,
            content=markdown_content,
            content_type=ContentType.MARKDOWN,
        )

    async def health_check(self) -> bool:
        """Check connectivity to Google Drive API."""
        access_token = self._get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_DRIVE_API}/about",
                    params={"fields": "user"},
                    headers=headers,
                )
                return response.status_code == 200
        except Exception:
            return False
