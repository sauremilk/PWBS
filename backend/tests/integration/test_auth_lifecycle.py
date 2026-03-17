"""Integration tests: Auth lifecycle — Register → Login → Refresh → Logout (TASK-110).

Uses real PostgreSQL via Testcontainers.
External services (Weaviate, Neo4j, Redis) are mocked.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_returns_tokens(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "lifecycle_reg@example.com",
                "password": "SecurePass123!",
                "display_name": "Life Cycle",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "user_id" in body
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_duplicate_email_rejected(self, client: AsyncClient) -> None:
        payload = {
            "email": "dupecheck@example.com",
            "password": "SecurePass123!",
            "display_name": "First",
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 409

    async def test_weak_password_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak_pw@example.com",
                "password": "short",
                "display_name": "Weak",
            },
        )
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_success(
        self,
        client: AsyncClient,
        registered_user: dict[str, Any],
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(
        self,
        client: AsyncClient,
        registered_user: dict[str, Any],
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registered_user["email"],
                "password": "WrongPassword999!",
            },
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Anything123!",
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_me_returns_profile(
        self,
        client: AsyncClient,
        registered_user: dict[str, Any],
        auth_headers: dict[str, str],
    ) -> None:
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == registered_user["email"]
        assert body["display_name"] == "Integration Tester"

    async def test_me_without_token_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    async def test_refresh_rotates_tokens(
        self,
        client: AsyncClient,
        registered_user: dict[str, Any],
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        # The new refresh_token should differ from the old one
        assert body["refresh_token"] != registered_user["refresh_token"]

    async def test_reuse_of_rotated_token_rejected(
        self,
        client: AsyncClient,
        registered_user: dict[str, Any],
    ) -> None:
        old_rt = registered_user["refresh_token"]
        # First rotation succeeds
        resp1 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_rt},
        )
        assert resp1.status_code == 200

        # Second use of same old token should be rejected (replay detection)
        resp2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_rt},
        )
        assert resp2.status_code == 401

    async def test_invalid_refresh_token_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "totally-bogus-token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    async def test_logout_invalidates_refresh_token(
        self,
        client: AsyncClient,
        registered_user: dict[str, Any],
    ) -> None:
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
            headers=headers,
        )
        assert resp.status_code == 200

        # Refresh with the revoked token should fail
        resp2 = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# Full Lifecycle: Register → Login → Me → Refresh → Logout
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    async def test_complete_auth_lifecycle(self, client: AsyncClient) -> None:
        email = "lifecycle_full@example.com"
        password = "LifeCycle_Pass1!"

        # 1. Register
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": "Full LC"},
        )
        assert reg.status_code == 201
        reg_data = reg.json()

        # 2. Login
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        login_data = login.json()

        # 3. /me with login token
        me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == email

        # 4. Refresh
        refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_data["refresh_token"]},
        )
        assert refresh.status_code == 200
        new_tokens = refresh.json()

        # 5. Logout
        logout = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": new_tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert logout.status_code == 200

        # 6. Refresh should now fail
        re_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert re_refresh.status_code == 401
