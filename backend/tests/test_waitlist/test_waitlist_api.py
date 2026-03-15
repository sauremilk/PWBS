"""Tests for Waitlist API endpoint (TASK-178)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from pwbs.api.v1.routes.waitlist import WaitlistRequest, WaitlistResponse, router

# ── Schema tests ─────────────────────────────────────────────────────────────


class TestWaitlistSchemas:
    """Validate Pydantic request/response schemas."""

    def test_valid_request(self) -> None:
        req = WaitlistRequest(email="test@example.com")
        assert req.email == "test@example.com"
        assert req.source == "landing"

    def test_custom_source(self) -> None:
        req = WaitlistRequest(email="test@example.com", source="referral")
        assert req.source == "referral"

    def test_invalid_email_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WaitlistRequest(email="not-an-email")

    def test_response_model(self) -> None:
        resp = WaitlistResponse(success=True, message="ok")
        assert resp.success is True
        assert resp.message == "ok"


# ── Endpoint tests ───────────────────────────────────────────────────────────


def _mock_db_session(existing_entry: MagicMock | None = None) -> AsyncMock:
    """Create a mock async DB session."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_entry
    session.execute.return_value = result
    return session


def _build_app():
    """Build a minimal FastAPI app with only the waitlist router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
class TestJoinWaitlist:
    """Test POST /api/v1/waitlist endpoint."""

    async def test_new_signup_returns_201(self) -> None:
        db = _mock_db_session(existing_entry=None)
        app = _build_app()

        from pwbs.api.v1.routes.waitlist import get_db_session

        app.dependency_overrides[get_db_session] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "new@example.com"},
            )

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["success"] is True
        assert "Warteliste" in body["message"]
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_duplicate_email_returns_201_silently(self) -> None:
        existing = MagicMock()
        db = _mock_db_session(existing_entry=existing)
        app = _build_app()

        from pwbs.api.v1.routes.waitlist import get_db_session

        app.dependency_overrides[get_db_session] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "existing@example.com"},
            )

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["success"] is True
        # Must NOT reveal that a duplicate was detected
        assert "Warteliste" in body["message"]
        # Should NOT add or commit for duplicates
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_invalid_email_returns_422(self) -> None:
        app = _build_app()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "not-valid"},
            )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_missing_email_returns_422(self) -> None:
        app = _build_app()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={},
            )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_email_is_lowercased(self) -> None:
        db = _mock_db_session(existing_entry=None)
        app = _build_app()

        from pwbs.api.v1.routes.waitlist import get_db_session

        app.dependency_overrides[get_db_session] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "Test@Example.COM"},
            )

        assert resp.status_code == status.HTTP_201_CREATED
        # Verify the entry added to DB has lowercased email
        added_entry = db.add.call_args[0][0]
        assert added_entry.email == "test@example.com"

    async def test_custom_source_is_stored(self) -> None:
        db = _mock_db_session(existing_entry=None)
        app = _build_app()

        from pwbs.api.v1.routes.waitlist import get_db_session

        app.dependency_overrides[get_db_session] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/waitlist",
                json={"email": "ref@example.com", "source": "referral"},
            )

        assert resp.status_code == status.HTTP_201_CREATED
        added_entry = db.add.call_args[0][0]
        assert added_entry.source == "referral"
