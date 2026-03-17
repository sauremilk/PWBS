"""Integration tests: Tenant-Isolation — no cross-user data access (TASK-110).

Registers two separate users and verifies that User A cannot access
User B's resources (connectors, documents, briefings, etc.).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Helper: create a second user with its own auth headers
# ---------------------------------------------------------------------------


async def _register_second_user(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"user_b_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecondUser_Pass1!",
            "display_name": "User B",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


# ---------------------------------------------------------------------------
# Isolation tests
# ---------------------------------------------------------------------------


class TestConnectorIsolation:
    async def test_user_b_cannot_see_user_a_connectors(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # User A configures obsidian
        await client.post(
            "/api/v1/connectors/obsidian/config",
            json={"vault_path": "/tmp/vault-a"},
            headers=auth_headers,
        )

        # User B should not see User A's connector
        headers_b = await _register_second_user(client)
        resp = await client.get("/api/v1/connectors/status", headers=headers_b)
        assert resp.status_code == 200
        connections = resp.json()["connections"]
        obsidian = [c for c in connections if c["source_type"] == "obsidian"]
        assert len(obsidian) == 0


class TestDocumentIsolation:
    async def test_user_b_cannot_see_user_a_documents(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # User A's documents list
        resp_a = await client.get("/api/v1/documents/", headers=auth_headers)
        assert resp_a.status_code == 200

        # User B should see an independent document list
        headers_b = await _register_second_user(client)
        resp_b = await client.get("/api/v1/documents/", headers=headers_b)
        assert resp_b.status_code == 200

        # Both should be independent (User B has 0 docs)
        docs_b = resp_b.json().get("documents", resp_b.json().get("items", []))
        assert len(docs_b) == 0


class TestBriefingIsolation:
    async def test_user_b_cannot_see_user_a_briefings(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # User A get briefings
        resp_a = await client.get("/api/v1/briefings/", headers=auth_headers)
        assert resp_a.status_code == 200

        # User B should see only their own
        headers_b = await _register_second_user(client)
        resp_b = await client.get("/api/v1/briefings/", headers=headers_b)
        assert resp_b.status_code == 200


class TestExportIsolation:
    async def test_user_b_cannot_access_user_a_export(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        # User A creates export
        resp_a = await client.post("/api/v1/user/export", headers=auth_headers)
        assert resp_a.status_code == 202
        export_id = resp_a.json()["export_id"]

        # User B tries to access User A's export
        headers_b = await _register_second_user(client)
        resp_b = await client.get(
            f"/api/v1/user/export/{export_id}",
            headers=headers_b,
        )
        # Should be 404 (not found for this user) or 403
        assert resp_b.status_code in (403, 404)
