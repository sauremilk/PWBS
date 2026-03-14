"""Tests for Connectors API endpoints (TASK-087)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from pwbs.api.v1.routes.connectors import (
    _resolve_source_type,
    router,
)
from pwbs.models.connection import Connection
from pwbs.models.user import User
from pwbs.schemas.enums import ConnectionStatus, SourceType

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(user_id: uuid.UUID | None = None) -> User:
    """Create a fake User ORM object."""
    u = MagicMock(spec=User)
    u.id = user_id or uuid.uuid4()
    u.email = "test@example.com"
    u.display_name = "Test User"
    u.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return u


def _make_connection(
    user_id: uuid.UUID,
    source_type: str = "google_calendar",
    status: str = "active",
    watermark: datetime | None = None,
    config: dict | None = None,
) -> Connection:
    """Create a fake Connection ORM object."""
    c = MagicMock(spec=Connection)
    c.id = uuid.uuid4()
    c.user_id = user_id
    c.source_type = source_type
    c.status = status
    c.watermark = watermark
    c.config = config or {}
    c.credentials_enc = "encrypted-data"
    return c


# ---------------------------------------------------------------------------
# _resolve_source_type
# ---------------------------------------------------------------------------


class TestResolveSourceType:
    def test_valid_underscore(self) -> None:
        assert _resolve_source_type("google_calendar") == SourceType.GOOGLE_CALENDAR

    def test_valid_hyphen(self) -> None:
        assert _resolve_source_type("google-calendar") == SourceType.GOOGLE_CALENDAR

    def test_case_insensitive(self) -> None:
        assert _resolve_source_type("NOTION") == SourceType.NOTION

    def test_unknown_raises_404(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _resolve_source_type("unknown_type")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /connectors/
# ---------------------------------------------------------------------------


class TestListConnectors:
    @pytest.mark.asyncio
    async def test_returns_all_connector_types(self) -> None:
        from pwbs.api.v1.routes.connectors import list_connectors

        user = _make_user()
        db = AsyncMock()
        # No existing connections
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        result = await list_connectors(current_user=user, db=db)
        assert len(result.connectors) == len(SourceType)
        types = {c.type for c in result.connectors}
        assert "google_calendar" in types
        assert "notion" in types
        assert "obsidian" in types
        assert "zoom" in types

    @pytest.mark.asyncio
    async def test_shows_connected_status(self) -> None:
        from pwbs.api.v1.routes.connectors import list_connectors

        user = _make_user()
        db = AsyncMock()
        # User has Google Calendar connected
        mock_result = MagicMock()
        mock_result.all.return_value = [("google_calendar",)]
        db.execute.return_value = mock_result

        result = await list_connectors(current_user=user, db=db)
        gc = next(c for c in result.connectors if c.type == "google_calendar")
        notion = next(c for c in result.connectors if c.type == "notion")
        assert gc.status == "connected"
        assert notion.status == "available"


# ---------------------------------------------------------------------------
# GET /connectors/status
# ---------------------------------------------------------------------------


class TestConnectionStatus:
    @pytest.mark.asyncio
    async def test_empty_connections(self) -> None:
        from pwbs.api.v1.routes.connectors import connection_status

        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await connection_status(current_user=user, db=db)
        assert result.connections == []

    @pytest.mark.asyncio
    async def test_returns_connection_details(self) -> None:
        from pwbs.api.v1.routes.connectors import connection_status

        user = _make_user()
        conn = _make_connection(user.id, watermark=datetime(2026, 3, 1, tzinfo=timezone.utc))

        db = AsyncMock()

        # First call returns connections, second returns doc count
        conn_result = MagicMock()
        conn_result.scalars.return_value.all.return_value = [conn]
        doc_count_result = MagicMock()
        doc_count_result.scalar.return_value = 42
        db.execute.side_effect = [conn_result, doc_count_result]

        result = await connection_status(current_user=user, db=db)
        assert len(result.connections) == 1
        assert result.connections[0].type == "google_calendar"
        assert result.connections[0].doc_count == 42
        assert result.connections[0].status == "active"


# ---------------------------------------------------------------------------
# GET /connectors/{type}/auth-url
# ---------------------------------------------------------------------------


class TestGetAuthUrl:
    @pytest.mark.asyncio
    async def test_generates_google_auth_url(self) -> None:
        from pwbs.api.v1.routes.connectors import get_auth_url

        user = _make_user()

        with patch("pwbs.api.v1.routes.connectors.get_settings") as mock_settings:
            s = MagicMock()
            s.google_client_id = "test-client-id"
            s.google_oauth_redirect_uri = "http://localhost:3000/callback"
            mock_settings.return_value = s

            result = await get_auth_url(type="google-calendar", current_user=user)

        assert "accounts.google.com" in result.auth_url
        assert "test-client-id" in result.auth_url
        assert len(result.state) > 0

    @pytest.mark.asyncio
    async def test_obsidian_no_oauth(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import get_auth_url

        user = _make_user()

        with pytest.raises(HTTPException) as exc_info:
            await get_auth_url(type="obsidian", current_user=user)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_type_404(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import get_auth_url

        user = _make_user()

        with pytest.raises(HTTPException) as exc_info:
            await get_auth_url(type="invalid", current_user=user)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_client_id_400(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import get_auth_url

        user = _make_user()

        with patch("pwbs.api.v1.routes.connectors.get_settings") as mock_settings:
            s = MagicMock()
            s.google_client_id = ""
            mock_settings.return_value = s

            with pytest.raises(HTTPException) as exc_info:
                await get_auth_url(type="google-calendar", current_user=user)
            assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# POST /connectors/{type}/callback
# ---------------------------------------------------------------------------


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_creates_connection(self) -> None:
        from pwbs.api.v1.routes.connectors import CallbackRequest, oauth_callback

        user = _make_user()
        db = AsyncMock()

        # No existing connection
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        db.execute.return_value = existing_result

        body = CallbackRequest(code="auth-code-123", state="state-abc")

        with (
            patch("pwbs.api.v1.routes.connectors._exchange_code_for_tokens") as mock_exchange,
            patch(
                "pwbs.api.v1.routes.connectors.encrypt_tokens",
                return_value="encrypted",
            ),
        ):
            from pwbs.connectors.oauth import OAuthTokens

            mock_exchange.return_value = OAuthTokens(
                access_token=SecretStr("access-tok"),
                refresh_token=SecretStr("refresh-tok"),
                expires_at=9999999999.0,
            )

            result = await oauth_callback(
                type="google-calendar",
                body=body,
                request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
                current_user=user,
                db=db,
            )

        assert result.status == "active"
        assert result.initial_sync_started is False
        assert db.add.call_count == 2  # Connection + AuditLog
        assert db.commit.await_count == 2  # Connection commit + audit commit

    @pytest.mark.asyncio
    async def test_duplicate_connection_409(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import CallbackRequest, oauth_callback

        user = _make_user()
        db = AsyncMock()

        # Existing connection found
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = _make_connection(user.id)
        db.execute.return_value = existing_result

        body = CallbackRequest(code="auth-code-123", state="state-abc")

        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(
                type="google-calendar",
                body=body,
                request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# POST /connectors/{type}/config
# ---------------------------------------------------------------------------


class TestConfigureConnector:
    @pytest.mark.asyncio
    async def test_obsidian_config(self) -> None:
        from pwbs.api.v1.routes.connectors import ConfigRequest, configure_connector

        user = _make_user()
        db = AsyncMock()

        # No existing connection
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        db.execute.return_value = existing_result

        body = ConfigRequest(vault_path="/home/user/vault")

        result = await configure_connector(
            type="obsidian",
            body=body,
            request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
            current_user=user,
            db=db,
        )
        assert result.status == "active"
        assert result.file_count == 0
        assert db.add.call_count == 2  # Connection + AuditLog

    @pytest.mark.asyncio
    async def test_non_obsidian_rejected(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import ConfigRequest, configure_connector

        user = _make_user()
        db = AsyncMock()
        body = ConfigRequest(vault_path="/path")

        with pytest.raises(HTTPException) as exc_info:
            await configure_connector(
                type="notion",
                body=body,
                request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /connectors/{type}
# ---------------------------------------------------------------------------


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_cascade_delete(self) -> None:
        from pwbs.api.v1.routes.connectors import disconnect

        user = _make_user()
        conn = _make_connection(user.id)
        db = AsyncMock()

        # First call: find connection; second: doc count
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = conn
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        # Third call: delete documents; fourth: nothing (delete connection is via db.delete)
        db.execute.side_effect = [find_result, count_result, MagicMock()]

        result = await disconnect(type="google-calendar", request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), current_user=user, db=db)
        assert result.deleted_doc_count == 5
        assert "google_calendar" in result.message
        db.delete.assert_called_once_with(conn)
        assert db.commit.await_count == 2  # Delete commit + audit commit

    @pytest.mark.asyncio
    async def test_not_found_404(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import disconnect

        user = _make_user()
        db = AsyncMock()
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = None
        db.execute.return_value = find_result

        with pytest.raises(HTTPException) as exc_info:
            await disconnect(type="notion", request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), current_user=user, db=db)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# POST /connectors/{type}/sync
# ---------------------------------------------------------------------------


class TestTriggerSync:
    @pytest.mark.asyncio
    async def test_sync_succeeds(self) -> None:
        from pwbs.api.v1.routes.connectors import trigger_sync

        user = _make_user()
        conn = _make_connection(user.id, watermark=None)
        db = AsyncMock()
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = find_result

        result = await trigger_sync(type="google-calendar", current_user=user, db=db)
        assert result.status == "started"

    @pytest.mark.asyncio
    async def test_not_found_404(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import trigger_sync

        user = _make_user()
        db = AsyncMock()
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = None
        db.execute.return_value = find_result

        with pytest.raises(HTTPException) as exc_info:
            await trigger_sync(type="google-calendar", current_user=user, db=db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_inactive_connection_400(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import trigger_sync

        user = _make_user()
        conn = _make_connection(user.id, status="error")
        db = AsyncMock()
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = find_result

        with pytest.raises(HTTPException) as exc_info:
            await trigger_sync(type="google-calendar", current_user=user, db=db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rate_limited_429(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import trigger_sync

        user = _make_user()
        # Watermark is very recent (< 5 min ago)
        recent = datetime.now(timezone.utc)
        conn = _make_connection(user.id, watermark=recent)
        db = AsyncMock()
        find_result = MagicMock()
        find_result.scalar_one_or_none.return_value = conn
        db.execute.return_value = find_result

        with pytest.raises(HTTPException) as exc_info:
            await trigger_sync(type="google-calendar", current_user=user, db=db)
        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Router metadata
# ---------------------------------------------------------------------------


class TestRouterMetadata:
    def test_router_prefix(self) -> None:
        assert router.prefix == "/api/v1/connectors"

    def test_router_has_expected_routes(self) -> None:
        paths = {r.path for r in router.routes}
        prefix = "/api/v1/connectors"
        assert f"{prefix}/" in paths
        assert f"{prefix}/status" in paths
        assert f"{prefix}/{{type}}/auth-url" in paths
        assert f"{prefix}/{{type}}/callback" in paths
        assert f"{prefix}/{{type}}/config" in paths
        assert f"{prefix}/{{type}}" in paths
        assert f"{prefix}/{{type}}/sync" in paths
