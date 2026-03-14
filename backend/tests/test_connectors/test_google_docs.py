"""Tests for Google Docs connector - OAuth2 + Drive/Docs API (TASK-127)."""

from __future__ import annotations

import json
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.google_docs import (
    GOOGLE_DOCS_SCOPES,
    GoogleDocsConnector,
    _DOCS_API,
    _DRIVE_API,
    _GOOGLE_AUTH_URL,
    _GOOGLE_TOKEN_URL,
    _decode_cursor,
    _encode_cursor,
    _raise_for_rate_limit,
    convert_doc_to_markdown,
)
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------

OWNER_ID = uuid.uuid4()


def _make_connector(
    access_token: str = "test-gdocs-token",
    max_batch_size: int = 100,
) -> GoogleDocsConnector:
    return GoogleDocsConnector(
        owner_id=OWNER_ID,
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.GOOGLE_DOCS,
            max_batch_size=max_batch_size,
            extra={"access_token": access_token},
        ),
    )


def _clear_settings() -> None:
    get_settings.cache_clear()


def _set_google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    _clear_settings()


REDIRECT_URI = "http://localhost:3000/api/connectors/google-docs/callback"
STATE_TOKEN = "csrf-state-gdocs-123"


def _make_doc_json(
    *,
    title: str = "Test Document",
    paragraphs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Build a minimal Google Docs API document JSON response."""
    if paragraphs is None:
        paragraphs = [
            {
                "paragraph": {
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "elements": [
                        {
                            "textRun": {
                                "content": "Hello World",
                                "textStyle": {},
                            }
                        }
                    ],
                }
            },
            {
                "paragraph": {
                    "elements": [
                        {
                            "textRun": {
                                "content": "This is a test document.",
                                "textStyle": {},
                            }
                        }
                    ],
                }
            },
        ]
    return {
        "documentId": "doc-123",
        "title": title,
        "body": {"content": paragraphs},
    }


def _make_drive_file(
    *,
    doc_id: str = "doc-123",
    name: str = "Test Document",
    modified_time: str = "2025-01-15T10:00:00Z",
    created_time: str = "2025-01-10T08:00:00Z",
) -> dict[str, object]:
    """Build a Drive API file metadata entry."""
    return {
        "id": doc_id,
        "name": name,
        "mimeType": "application/vnd.google-apps.document",
        "modifiedTime": modified_time,
        "createdTime": created_time,
        "owners": [{"displayName": "Test User", "emailAddress": "test@example.com"}],
        "lastModifyingUser": {"displayName": "Test User"},
    }


# ---------------------------------------------------------------------------
# build_auth_url tests
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_google_env(monkeypatch)

        url = GoogleDocsConnector.build_auth_url(
            redirect_uri=REDIRECT_URI, state=STATE_TOKEN
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert parsed.netloc == "accounts.google.com"
        assert params["client_id"] == ["test-client-id"]
        assert params["redirect_uri"] == [REDIRECT_URI]
        assert params["response_type"] == ["code"]
        assert params["scope"] == [GOOGLE_DOCS_SCOPES]
        assert params["access_type"] == ["offline"]
        assert params["prompt"] == ["consent"]
        assert params["state"] == [STATE_TOKEN]

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        _clear_settings()

        with pytest.raises(ConnectorError, match="GOOGLE_CLIENT_ID"):
            GoogleDocsConnector.build_auth_url(
                redirect_uri=REDIRECT_URI, state=STATE_TOKEN
            )


# ---------------------------------------------------------------------------
# exchange_code tests
# ---------------------------------------------------------------------------


class TestExchangeCode:
    async def test_successful_exchange(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_google_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "access-abc",
                    "refresh_token": "refresh-xyz",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": GOOGLE_DOCS_SCOPES,
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await GoogleDocsConnector.exchange_code(
            code="auth-code-123", redirect_uri=REDIRECT_URI
        )

        assert tokens.access_token.get_secret_value() == "access-abc"
        assert tokens.refresh_token is not None
        assert tokens.refresh_token.get_secret_value() == "refresh-xyz"
        assert tokens.expires_at is not None

    async def test_missing_credentials_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="credentials"):
            await GoogleDocsConnector.exchange_code(
                code="auth-code", redirect_uri=REDIRECT_URI
            )

    async def test_exchange_http_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_google_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "invalid_grant", "error_description": "Code expired"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="Code expired"):
            await GoogleDocsConnector.exchange_code(
                code="expired-code", redirect_uri=REDIRECT_URI
            )


# ---------------------------------------------------------------------------
# Cursor encoding/decoding tests
# ---------------------------------------------------------------------------


class TestCursor:
    def test_encode_decode_roundtrip(self) -> None:
        cursor = _encode_cursor(
            modified_time="2025-01-15T10:00:00Z", page_token="abc123"
        )
        modified_time, page_token = _decode_cursor(cursor)
        assert modified_time == "2025-01-15T10:00:00Z"
        assert page_token == "abc123"

    def test_encode_without_page_token(self) -> None:
        cursor = _encode_cursor(modified_time="2025-01-15T10:00:00Z")
        modified_time, page_token = _decode_cursor(cursor)
        assert modified_time == "2025-01-15T10:00:00Z"
        assert page_token is None

    def test_decode_invalid_cursor(self) -> None:
        modified_time, page_token = _decode_cursor("not-valid-base64!!!")
        assert modified_time is None
        assert page_token is None


# ---------------------------------------------------------------------------
# Markdown conversion tests
# ---------------------------------------------------------------------------


class TestConvertDocToMarkdown:
    def test_heading_and_body(self) -> None:
        doc_json = _make_doc_json()
        md = convert_doc_to_markdown(doc_json)
        assert "# Hello World" in md
        assert "This is a test document." in md

    def test_bold_italic(self) -> None:
        doc_json = _make_doc_json(
            paragraphs=[
                {
                    "paragraph": {
                        "elements": [
                            {
                                "textRun": {
                                    "content": "bold text",
                                    "textStyle": {"bold": True},
                                }
                            },
                            {
                                "textRun": {
                                    "content": " and ",
                                    "textStyle": {},
                                }
                            },
                            {
                                "textRun": {
                                    "content": "italic text",
                                    "textStyle": {"italic": True},
                                }
                            },
                        ],
                    }
                }
            ]
        )
        md = convert_doc_to_markdown(doc_json)
        assert "**bold text**" in md
        assert "*italic text*" in md

    def test_link(self) -> None:
        doc_json = _make_doc_json(
            paragraphs=[
                {
                    "paragraph": {
                        "elements": [
                            {
                                "textRun": {
                                    "content": "click here",
                                    "textStyle": {
                                        "link": {"url": "https://example.com"}
                                    },
                                }
                            }
                        ],
                    }
                }
            ]
        )
        md = convert_doc_to_markdown(doc_json)
        assert "[click here](https://example.com)" in md

    def test_bullet_list(self) -> None:
        doc_json = _make_doc_json(
            paragraphs=[
                {
                    "paragraph": {
                        "bullet": {"listId": "list-1", "nestingLevel": 0},
                        "elements": [
                            {
                                "textRun": {
                                    "content": "Item one",
                                    "textStyle": {},
                                }
                            }
                        ],
                    }
                },
                {
                    "paragraph": {
                        "bullet": {"listId": "list-1", "nestingLevel": 1},
                        "elements": [
                            {
                                "textRun": {
                                    "content": "Nested item",
                                    "textStyle": {},
                                }
                            }
                        ],
                    }
                },
            ]
        )
        md = convert_doc_to_markdown(doc_json)
        assert "- Item one" in md
        assert "  - Nested item" in md

    def test_table(self) -> None:
        doc_json = _make_doc_json(
            paragraphs=[
                {
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Header 1",
                                                                "textStyle": {},
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Header 2",
                                                                "textStyle": {},
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            },
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Cell 1",
                                                                "textStyle": {},
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Cell 2",
                                                                "textStyle": {},
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            },
                        ]
                    }
                }
            ]
        )
        md = convert_doc_to_markdown(doc_json)
        assert "| Header 1 | Header 2 |" in md
        assert "| --- | --- |" in md
        assert "| Cell 1 | Cell 2 |" in md

    def test_section_break(self) -> None:
        doc_json = _make_doc_json(
            paragraphs=[
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Before", "textStyle": {}}}
                        ],
                    }
                },
                {"sectionBreak": {}},
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "After", "textStyle": {}}}
                        ],
                    }
                },
            ]
        )
        md = convert_doc_to_markdown(doc_json)
        assert "Before" in md
        assert "---" in md
        assert "After" in md

    def test_empty_document(self) -> None:
        doc_json = {"body": {"content": []}}
        md = convert_doc_to_markdown(doc_json)
        assert md == ""

    def test_strikethrough(self) -> None:
        doc_json = _make_doc_json(
            paragraphs=[
                {
                    "paragraph": {
                        "elements": [
                            {
                                "textRun": {
                                    "content": "deleted text",
                                    "textStyle": {"strikethrough": True},
                                }
                            }
                        ],
                    }
                }
            ]
        )
        md = convert_doc_to_markdown(doc_json)
        assert "~~deleted text~~" in md

    def test_heading_levels(self) -> None:
        paragraphs = []
        for i in range(1, 7):
            paragraphs.append(
                {
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": f"HEADING_{i}"},
                        "elements": [
                            {
                                "textRun": {
                                    "content": f"Level {i}",
                                    "textStyle": {},
                                }
                            }
                        ],
                    }
                }
            )
        doc_json = _make_doc_json(paragraphs=paragraphs)
        md = convert_doc_to_markdown(doc_json)
        assert "# Level 1" in md
        assert "## Level 2" in md
        assert "### Level 3" in md
        assert "#### Level 4" in md
        assert "##### Level 5" in md
        assert "###### Level 6" in md


# ---------------------------------------------------------------------------
# Rate limit helper
# ---------------------------------------------------------------------------


class TestRateLimitHelper:
    def test_429_raises(self) -> None:
        response = httpx.Response(429, headers={"Retry-After": "60"})
        with pytest.raises(RateLimitError):
            _raise_for_rate_limit(response)

    def test_503_raises(self) -> None:
        response = httpx.Response(503)
        with pytest.raises(RateLimitError):
            _raise_for_rate_limit(response)

    def test_200_ok(self) -> None:
        response = httpx.Response(200)
        _raise_for_rate_limit(response)  # should not raise


# ---------------------------------------------------------------------------
# fetch_since tests
# ---------------------------------------------------------------------------


class TestFetchSince:
    async def test_initial_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Initial sync (cursor=None) lists files and fetches content."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    200,
                    json={"files": [_make_drive_file()]},
                    request=httpx.Request("GET", url),
                )
            if "/documents/doc-123" in url:
                return httpx.Response(
                    200,
                    json=_make_doc_json(),
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)

        assert result.success_count == 1
        assert result.error_count == 0
        assert result.has_more is False
        assert result.new_cursor is not None

        doc = result.documents[0]
        assert doc.source_type == SourceType.GOOGLE_DOCS
        assert doc.title == "Test Document"
        assert "# Hello World" in doc.content
        assert doc.user_id == connector.owner_id

    async def test_incremental_sync_with_cursor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Incremental sync uses modifiedTime filter."""
        connector = _make_connector()
        cursor = _encode_cursor(modified_time="2025-01-10T00:00:00Z")

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                # Verify the query includes modifiedTime filter
                params = kwargs.get("params", {})
                q = params.get("q", "") if isinstance(params, dict) else ""
                assert "modifiedTime > '2025-01-10T00:00:00Z'" in str(q)
                return httpx.Response(
                    200,
                    json={
                        "files": [
                            _make_drive_file(
                                doc_id="doc-456",
                                name="Updated Doc",
                                modified_time="2025-01-15T12:00:00Z",
                            )
                        ],
                    },
                    request=httpx.Request("GET", url),
                )
            if "/documents/doc-456" in url:
                return httpx.Response(
                    200,
                    json=_make_doc_json(title="Updated Doc"),
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(cursor)

        assert result.success_count == 1
        doc = result.documents[0]
        assert doc.title == "Updated Doc"

        # Cursor should be updated to latest modifiedTime
        new_mt, _ = _decode_cursor(result.new_cursor)
        assert new_mt == "2025-01-15T12:00:00Z"

    async def test_pagination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """has_more=True when nextPageToken is present."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    200,
                    json={
                        "files": [_make_drive_file()],
                        "nextPageToken": "page2-token",
                    },
                    request=httpx.Request("GET", url),
                )
            if "/documents/doc-123" in url:
                return httpx.Response(
                    200,
                    json=_make_doc_json(),
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)

        assert result.has_more is True
        _, page_token = _decode_cursor(result.new_cursor)
        assert page_token == "page2-token"

    async def test_partial_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Individual doc fetch failure doesn't abort the batch."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    200,
                    json={
                        "files": [
                            _make_drive_file(
                                doc_id="doc-ok", modified_time="2025-01-15T10:00:00Z"
                            ),
                            _make_drive_file(
                                doc_id="doc-fail", modified_time="2025-01-15T11:00:00Z"
                            ),
                        ],
                    },
                    request=httpx.Request("GET", url),
                )
            if "/documents/doc-ok" in url:
                return httpx.Response(
                    200,
                    json=_make_doc_json(),
                    request=httpx.Request("GET", url),
                )
            if "/documents/doc-fail" in url:
                return httpx.Response(
                    403,
                    json={"error": {"message": "Permission denied"}},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)

        assert result.success_count == 1
        assert result.error_count == 1
        assert result.errors[0].source_id == "doc-fail"

    async def test_drive_api_error_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Drive API failure raises ConnectorError."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    500,
                    json={"error": {"message": "Internal server error"}},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(ConnectorError, match="Drive API error"):
            await connector.fetch_since(None)

    async def test_missing_token_raises(self) -> None:
        """Missing access_token in config.extra raises ConnectorError."""
        connector = GoogleDocsConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.GOOGLE_DOCS,
                extra={},
            ),
        )

        with pytest.raises(ConnectorError, match="Missing access_token"):
            await connector.fetch_since(None)

    async def test_empty_file_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No files returned produces empty SyncResult."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    200,
                    json={"files": []},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.new_cursor is None

    async def test_rate_limit_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """429 from Drive API raises RateLimitError."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "30"},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        with pytest.raises(RateLimitError):
            await connector.fetch_since(None)


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_health_check_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/about" in url:
                return httpx.Response(
                    200,
                    json={"user": {"displayName": "Test User"}},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.health_check()
        assert result is True

    async def test_health_check_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                401,
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.health_check()
        assert result is False


# ---------------------------------------------------------------------------
# normalize (standalone) tests
# ---------------------------------------------------------------------------


class TestNormalize:
    async def test_normalize_raw_data(self) -> None:
        connector = _make_connector()
        raw_data = _make_doc_json(title="My Doc")
        raw_data["id"] = "doc-normalize-test"
        raw_data["name"] = "My Doc"

        doc = await connector.normalize(raw_data)

        assert doc.source_type == SourceType.GOOGLE_DOCS
        assert doc.source_id == "doc-normalize-test"
        assert doc.title == "My Doc"
        assert "# Hello World" in doc.content

    async def test_normalize_empty_doc(self) -> None:
        connector = _make_connector()
        raw_data = {
            "id": "empty-doc",
            "name": "Empty",
            "body": {"content": []},
        }

        doc = await connector.normalize(raw_data)
        assert doc.content == ""


# ---------------------------------------------------------------------------
# Content hash deduplication test
# ---------------------------------------------------------------------------


class TestContentHash:
    async def test_same_content_same_hash(self) -> None:
        """Two documents with identical content produce the same content_hash."""
        connector = _make_connector()
        raw_data_a = _make_doc_json(title="Doc A")
        raw_data_a["id"] = "doc-a"
        raw_data_a["name"] = "Doc A"

        doc_a = await connector.normalize(raw_data_a)

        raw_data_b = _make_doc_json(title="Doc B")
        raw_data_b["id"] = "doc-b"
        raw_data_b["name"] = "Doc B"

        doc_b = await connector.normalize(raw_data_b)

        # Same content -> same hash (titles differ but content body is same)
        assert doc_a.raw_hash == doc_b.raw_hash
        # Different source_id
        assert doc_a.source_id != doc_b.source_id


# ---------------------------------------------------------------------------
# Shared docs / metadata extraction
# ---------------------------------------------------------------------------


class TestMetadataExtraction:
    async def test_owner_names_extracted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Owner and modifier names are extracted from Drive metadata."""
        connector = _make_connector()

        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            if "/drive/v3/files" in url:
                return httpx.Response(
                    200,
                    json={"files": [_make_drive_file()]},
                    request=httpx.Request("GET", url),
                )
            if "/documents/doc-123" in url:
                return httpx.Response(
                    200,
                    json=_make_doc_json(),
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        result = await connector.fetch_since(None)
        doc = result.documents[0]

        assert doc.metadata["owners"] == ["Test User"]
        assert doc.metadata["last_modifier"] == "Test User"
        assert "Test User" in doc.participants
