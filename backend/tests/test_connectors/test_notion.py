"""Tests for Notion connector — OAuth2 flow and health check (TASK-048)."""

from __future__ import annotations

import base64
import uuid

import httpx
import pytest

from pwbs.connectors.notion import NotionConnector, _NOTION_AUTH_URL
from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError
from pwbs.schemas.enums import SourceType


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------


def _make_connector(
    access_token: str = "test-notion-token",
) -> NotionConnector:
    return NotionConnector(
        owner_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.NOTION,
            extra={"access_token": access_token},
        ),
    )


def _clear_settings() -> None:
    get_settings.cache_clear()


def _set_notion_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set Notion OAuth env vars and clear settings cache."""
    monkeypatch.setenv("NOTION_CLIENT_ID", "test-notion-id")
    monkeypatch.setenv("NOTION_CLIENT_SECRET", "test-notion-secret")
    _clear_settings()


# ---------------------------------------------------------------------------
# build_auth_url
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    def test_generates_valid_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        url = NotionConnector.build_auth_url(
            redirect_uri="http://localhost:3000/callback",
            state="csrf-token",
        )
        assert _NOTION_AUTH_URL in url
        assert "client_id=test-notion-id" in url
        assert "redirect_uri=" in url
        assert "state=csrf-token" in url
        assert "response_type=code" in url
        assert "owner=user" in url

    def test_missing_client_id_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTION_CLIENT_ID", "")
        monkeypatch.setenv("NOTION_CLIENT_SECRET", "test-notion-secret")
        _clear_settings()

        with pytest.raises(ConnectorError, match="notion_client_id"):
            NotionConnector.build_auth_url(
                redirect_uri="http://localhost:3000/callback",
                state="csrf",
            )


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    async def test_successful_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        captured_headers: dict[str, str] = {}

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            headers = kwargs.get("headers", {})
            if isinstance(headers, dict):
                captured_headers.update(headers)
            return httpx.Response(
                200,
                json={
                    "access_token": "ntn_new_token_123",
                    "token_type": "bearer",
                    "bot_id": "bot-id",
                    "workspace_id": "ws-id",
                    "workspace_name": "Test Workspace",
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        tokens = await NotionConnector.exchange_code(
            code="auth-code-123",
            redirect_uri="http://localhost:3000/callback",
        )

        assert isinstance(tokens, OAuthTokens)
        assert tokens.access_token.get_secret_value() == "ntn_new_token_123"
        assert tokens.refresh_token is None  # Notion has no refresh tokens
        assert tokens.expires_at is None  # Notion tokens don't expire

        # Verify Basic Auth header was sent
        expected_creds = base64.b64encode(b"test-notion-id:test-notion-secret").decode()
        assert captured_headers.get("Authorization") == f"Basic {expected_creds}"

    async def test_invalid_code_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "invalid_grant"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="token exchange failed"):
            await NotionConnector.exchange_code(
                code="bad-code",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_network_error_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_notion_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="network error"):
            await NotionConnector.exchange_code(
                code="code",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_missing_access_token_in_response_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_notion_env(monkeypatch)

        async def mock_post(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={"bot_id": "bot-id"},
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(ConnectorError, match="missing access_token"):
            await NotionConnector.exchange_code(
                code="code",
                redirect_uri="http://localhost:3000/callback",
            )

    async def test_missing_credentials_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTION_CLIENT_ID", "")
        monkeypatch.setenv("NOTION_CLIENT_SECRET", "")
        _clear_settings()

        with pytest.raises(ConnectorError, match="not configured"):
            await NotionConnector.exchange_code(
                code="code",
                redirect_uri="http://localhost:3000/callback",
            )


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_healthy_with_valid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(200, json={}, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        assert await conn.health_check() is True

    async def test_unhealthy_with_invalid_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def mock_get(
            self: httpx.AsyncClient, url: str, **kwargs: object
        ) -> httpx.Response:
            return httpx.Response(401, json={}, request=httpx.Request("GET", url))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        conn = _make_connector()
        assert await conn.health_check() is False

    async def test_no_token_returns_false(self) -> None:
        conn = NotionConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.NOTION),
        )
        assert await conn.health_check() is False


# ---------------------------------------------------------------------------
# BaseConnector integration
# ---------------------------------------------------------------------------


class TestBaseConnectorIntegration:
    def test_source_type(self) -> None:
        conn = _make_connector()
        assert conn.source_type == SourceType.NOTION

    async def test_fetch_since_not_implemented(self) -> None:
        conn = _make_connector()
        with pytest.raises(NotImplementedError, match="TASK-049"):
            await conn.fetch_since(None)

    async def test_normalize_not_implemented(self) -> None:
        conn = _make_connector()
        with pytest.raises(NotImplementedError, match="TASK-050"):
            await conn.normalize({})  # type: ignore[arg-type]
