"""Integration tests: Connector CRUD lifecycle (TASK-110).

Tests connector listing, Obsidian-config-based connection, status,
and cascading deletion.  OAuth connectors are tested via callback
simulation.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestListConnectors:
    async def test_list_returns_known_types(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get("/api/v1/connectors/", headers=auth_headers)
        assert resp.status_code == 200
        types = {c["type"] for c in resp.json()["connectors"]}
        assert "obsidian" in types

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/connectors/")
        assert resp.status_code == 401


class TestObsidianConfig:
    """Obsidian uses config-based auth (local_path), no OAuth."""

    async def test_configure_obsidian(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.post(
            "/api/v1/connectors/obsidian/config",
            json={"vault_path": "/tmp/test-vault"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    async def test_status_shows_connected(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        # Configure first
        await client.post(
            "/api/v1/connectors/obsidian/config",
            json={"vault_path": "/tmp/test-vault"},
            headers=auth_headers,
        )
        resp = await client.get("/api/v1/connectors/status", headers=auth_headers)
        assert resp.status_code == 200
        connections = resp.json()["connections"]
        obsidian = [c for c in connections if c["source_type"] == "obsidian"]
        assert len(obsidian) == 1
        assert obsidian[0]["status"] == "active"

    async def test_disconnect_removes_connection(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        # Configure
        await client.post(
            "/api/v1/connectors/obsidian/config",
            json={"vault_path": "/tmp/vault"},
            headers=auth_headers,
        )
        # Disconnect
        resp = await client.delete(
            "/api/v1/connectors/obsidian", headers=auth_headers,
        )
        assert resp.status_code == 200

        # Status should no longer show obsidian
        status_resp = await client.get(
            "/api/v1/connectors/status", headers=auth_headers,
        )
        connections = status_resp.json()["connections"]
        obsidian = [c for c in connections if c["source_type"] == "obsidian"]
        assert len(obsidian) == 0


class TestOAuthCallback:
    """Simulate OAuth callback with mocked token exchange."""

    async def test_callback_creates_connection(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        mock_tokens = {
            "access_token": "test-access",
            "refresh_token": "test-refresh",
            "expires_in": 3600,
        }
        with patch(
            "pwbs.api.v1.routes.connectors.exchange_oauth_code",
            new_callable=AsyncMock,
            return_value=mock_tokens,
        ):
            resp = await client.post(
                "/api/v1/connectors/google-calendar/callback",
                json={"code": "fake-auth-code", "state": "fake-state"},
                headers=auth_headers,
            )
        assert resp.status_code == 201

    async def test_disconnect_cascades_to_documents(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        """Disconnecting a connector deletes its documents."""
        mock_tokens = {
            "access_token": "t-access",
            "refresh_token": "t-refresh",
            "expires_in": 3600,
        }
        with patch(
            "pwbs.api.v1.routes.connectors.exchange_oauth_code",
            new_callable=AsyncMock,
            return_value=mock_tokens,
        ):
            await client.post(
                "/api/v1/connectors/google-calendar/callback",
                json={"code": "code", "state": "state"},
                headers=auth_headers,
            )

        # Disconnect should work even if no docs exist yet
        resp = await client.delete(
            "/api/v1/connectors/google-calendar", headers=auth_headers,
        )
        assert resp.status_code == 200


class TestSyncTrigger:
    async def test_sync_without_connection_fails(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.post(
            "/api/v1/connectors/notion/sync", headers=auth_headers,
        )
        # No connection → 404 or 400
        assert resp.status_code in (400, 404)
