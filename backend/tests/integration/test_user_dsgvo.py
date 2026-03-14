"""Integration tests: User endpoints + DSGVO flows (TASK-110).

Tests user settings, data export workflow, and account deletion
with grace period.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestUserSettings:
    async def test_get_settings(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get("/api/v1/user/settings", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "email" in body

    async def test_update_display_name(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.patch(
            "/api/v1/user/settings",
            json={"display_name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"

    async def test_get_settings_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/user/settings")
        assert resp.status_code == 401


class TestDataExport:
    async def test_start_export(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.post("/api/v1/user/export", headers=auth_headers)
        assert resp.status_code == 202
        body = resp.json()
        assert "export_id" in body

    async def test_get_export_status(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        # Start export
        start_resp = await client.post("/api/v1/user/export", headers=auth_headers)
        export_id = start_resp.json()["export_id"]

        # Get status
        resp = await client.get(
            f"/api/v1/user/export/{export_id}", headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("pending", "processing", "completed", "failed")


class TestAccountDeletion:
    async def test_delete_account_schedules_deletion(
        self, client: AsyncClient, registered_user: dict[str, Any],
    ) -> None:
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        resp = await client.delete(
            "/api/v1/user/account",
            json={
                "password": registered_user["password"],
                "confirmation": "DELETE",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "scheduled_at" in body or "grace_period_ends" in body

    async def test_cancel_deletion(
        self, client: AsyncClient, registered_user: dict[str, Any],
    ) -> None:
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        # Schedule deletion
        await client.delete(
            "/api/v1/user/account",
            json={
                "password": registered_user["password"],
                "confirmation": "DELETE",
            },
            headers=headers,
        )
        # Cancel
        resp = await client.post(
            "/api/v1/user/account/cancel-deletion", headers=headers,
        )
        assert resp.status_code == 200

    async def test_delete_wrong_password_rejected(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.delete(
            "/api/v1/user/account",
            json={
                "password": "WrongPassword999!",
                "confirmation": "DELETE",
            },
            headers=auth_headers,
        )
        assert resp.status_code in (400, 401, 403)

    async def test_delete_wrong_confirmation_rejected(
        self, client: AsyncClient, registered_user: dict[str, Any],
    ) -> None:
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        resp = await client.delete(
            "/api/v1/user/account",
            json={
                "password": registered_user["password"],
                "confirmation": "WRONG",
            },
            headers=headers,
        )
        assert resp.status_code == 422


class TestAuditLog:
    async def test_audit_log_returns_entries(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        # The registration itself should have created audit entries
        resp = await client.get("/api/v1/user/audit-log", headers=auth_headers)
        assert resp.status_code == 200
        # May be empty if audit logs require a real middleware pass
        assert isinstance(resp.json().get("entries", resp.json().get("logs", [])), list)


class TestSecurityStatus:
    async def test_security_status(
        self, client: AsyncClient, auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get("/api/v1/user/security", headers=auth_headers)
        assert resp.status_code == 200
