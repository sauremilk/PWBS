"""Tests for Google OAuth2 Login Flow (TASK-083)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from pwbs.api.v1.routes.auth_google import (
    GoogleCallbackRequest,
    GoogleCallbackResponse,
    _find_or_create_user,
    _validate_state,
    router,
)
from pwbs.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(
    user_id: uuid.UUID | None = None,
    email: str = "test@example.com",
) -> User:
    """Create a fake User ORM object."""
    u = MagicMock(spec=User)
    u.id = user_id or uuid.uuid4()
    u.email = email
    u.display_name = "Test User"
    u.password_hash = "hashed"
    u.encryption_key_enc = "encrypted"
    u.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return u


def _mock_settings(
    client_id: str = "test-client-id",
    client_secret: str = "test-secret",
    redirect_uri: str = "http://localhost:3000/api/auth/google/callback",
) -> MagicMock:
    s = MagicMock()
    s.google_client_id = client_id
    s.google_client_secret = SecretStr(client_secret)
    s.google_login_redirect_uri = redirect_uri
    return s


# ---------------------------------------------------------------------------
# GET /auth/google/auth-url
# ---------------------------------------------------------------------------


class TestGoogleAuthUrl:
    @pytest.mark.asyncio
    async def test_generates_auth_url(self) -> None:
        from pwbs.api.v1.routes.auth_google import google_auth_url

        mock_redis = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google.get_redis_client") as mock_rc,
        ):
            mock_gs.return_value = _mock_settings()
            mock_rc.return_value = mock_redis

            result = await google_auth_url()

        assert "accounts.google.com" in result.auth_url
        assert "test-client-id" in result.auth_url
        assert "openid" in result.auth_url
        assert "email" in result.auth_url
        assert len(result.state) > 0
        # State should be stored in Redis
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("google_login_state:")

    @pytest.mark.asyncio
    async def test_returns_503_when_not_configured(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.auth_google import google_auth_url

        with patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs:
            mock_gs.return_value = _mock_settings(client_id="")

            with pytest.raises(HTTPException) as exc_info:
                await google_auth_url()

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_auth_url_contains_redirect_uri(self) -> None:
        from pwbs.api.v1.routes.auth_google import google_auth_url

        mock_redis = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google.get_redis_client") as mock_rc,
        ):
            mock_gs.return_value = _mock_settings(
                redirect_uri="http://myapp.com/callback",
            )
            mock_rc.return_value = mock_redis

            result = await google_auth_url()

        assert "myapp.com" in result.auth_url


# ---------------------------------------------------------------------------
# _validate_state
# ---------------------------------------------------------------------------


class TestValidateState:
    @pytest.mark.asyncio
    async def test_valid_state(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.getdel.return_value = "valid"

        with patch("pwbs.api.v1.routes.auth_google.get_redis_client") as mock_rc:
            mock_rc.return_value = mock_redis
            # Should not raise
            await _validate_state("abc123")

        mock_redis.getdel.assert_called_once_with("google_login_state:abc123")

    @pytest.mark.asyncio
    async def test_invalid_state_raises_400(self) -> None:
        from fastapi import HTTPException

        mock_redis = AsyncMock()
        mock_redis.getdel.return_value = None

        with patch("pwbs.api.v1.routes.auth_google.get_redis_client") as mock_rc:
            mock_rc.return_value = mock_redis

            with pytest.raises(HTTPException) as exc_info:
                await _validate_state("expired-state")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_state_consumed_after_validation(self) -> None:
        """State should be deleted via getdel (one-time use)."""
        mock_redis = AsyncMock()
        mock_redis.getdel.return_value = "valid"

        with patch("pwbs.api.v1.routes.auth_google.get_redis_client") as mock_rc:
            mock_rc.return_value = mock_redis
            await _validate_state("one-time")

        # getdel atomically gets and deletes
        mock_redis.getdel.assert_called_once()


# ---------------------------------------------------------------------------
# _find_or_create_user
# ---------------------------------------------------------------------------


class TestFindOrCreateUser:
    @pytest.mark.asyncio
    async def test_existing_user_returned(self) -> None:
        existing = _make_user(email="existing@gmail.com")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        db.execute.return_value = mock_result

        user, is_new = await _find_or_create_user(
            email="existing@gmail.com",
            display_name="Existing User",
            google_sub="google-123",
            db=db,
        )

        assert user is existing
        assert is_new is False

    @pytest.mark.asyncio
    async def test_new_user_created(self) -> None:
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with patch("pwbs.api.v1.routes.auth_google._generate_encrypted_dek") as mock_dek:
            mock_dek.return_value = "encrypted-dek-value"
            user, is_new = await _find_or_create_user(
                email="new@gmail.com",
                display_name="New User",
                google_sub="google-456",
                db=db,
            )

        assert is_new is True
        db.add.assert_called_once()
        db.flush.assert_called_once()
        # Check the user passed to db.add
        added_user = db.add.call_args[0][0]
        assert added_user.email == "new@gmail.com"
        assert added_user.display_name == "New User"
        assert added_user.password_hash == ""  # Google-only user


# ---------------------------------------------------------------------------
# POST /auth/google/callback (full flow)
# ---------------------------------------------------------------------------


class TestGoogleCallback:
    @pytest.mark.asyncio
    async def test_successful_login_existing_user(self) -> None:
        from pwbs.api.v1.routes.auth_google import google_callback

        existing_user = _make_user(email="user@gmail.com")
        db = AsyncMock()

        mock_pair = MagicMock()
        mock_pair.access_token = "access-jwt"
        mock_pair.refresh_token = "refresh-token"
        mock_pair.token_type = "bearer"
        mock_pair.expires_in = 900

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google._validate_state") as mock_vs,
            patch("pwbs.api.v1.routes.auth_google._exchange_code") as mock_ex,
            patch("pwbs.api.v1.routes.auth_google._fetch_google_userinfo") as mock_ui,
            patch("pwbs.api.v1.routes.auth_google._find_or_create_user") as mock_fc,
            patch("pwbs.api.v1.routes.auth_google.create_token_pair") as mock_tp,
        ):
            mock_gs.return_value = _mock_settings()
            mock_vs.return_value = None
            mock_ex.return_value = {"access_token": "google-at", "id_token": "google-id"}
            mock_ui.return_value = {
                "email": "user@gmail.com",
                "email_verified": True,
                "name": "Test User",
                "sub": "google-123",
            }
            mock_fc.return_value = (existing_user, False)
            mock_tp.return_value = mock_pair

            body = GoogleCallbackRequest(code="auth-code", state="valid-state")
            result = await google_callback(body=body, db=db)

        assert isinstance(result, GoogleCallbackResponse)
        assert result.access_token == "access-jwt"
        assert result.refresh_token == "refresh-token"
        assert result.is_new_user is False

    @pytest.mark.asyncio
    async def test_successful_login_new_user(self) -> None:
        from pwbs.api.v1.routes.auth_google import google_callback

        new_user = _make_user(email="new@gmail.com")
        db = AsyncMock()

        mock_pair = MagicMock()
        mock_pair.access_token = "access-jwt"
        mock_pair.refresh_token = "refresh-token"
        mock_pair.token_type = "bearer"
        mock_pair.expires_in = 900

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google._validate_state") as mock_vs,
            patch("pwbs.api.v1.routes.auth_google._exchange_code") as mock_ex,
            patch("pwbs.api.v1.routes.auth_google._fetch_google_userinfo") as mock_ui,
            patch("pwbs.api.v1.routes.auth_google._find_or_create_user") as mock_fc,
            patch("pwbs.api.v1.routes.auth_google.create_token_pair") as mock_tp,
        ):
            mock_gs.return_value = _mock_settings()
            mock_vs.return_value = None
            mock_ex.return_value = {"access_token": "google-at"}
            mock_ui.return_value = {
                "email": "new@gmail.com",
                "email_verified": True,
                "name": "New Person",
                "sub": "google-789",
            }
            mock_fc.return_value = (new_user, True)
            mock_tp.return_value = mock_pair

            body = GoogleCallbackRequest(code="auth-code", state="valid-state")
            result = await google_callback(body=body, db=db)

        assert result.is_new_user is True

    @pytest.mark.asyncio
    async def test_unverified_email_rejected(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.auth_google import google_callback

        db = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google._validate_state"),
            patch("pwbs.api.v1.routes.auth_google._exchange_code") as mock_ex,
            patch("pwbs.api.v1.routes.auth_google._fetch_google_userinfo") as mock_ui,
        ):
            mock_gs.return_value = _mock_settings()
            mock_ex.return_value = {"access_token": "google-at"}
            mock_ui.return_value = {
                "email": "user@gmail.com",
                "email_verified": False,
                "name": "User",
                "sub": "google-123",
            }

            body = GoogleCallbackRequest(code="auth-code", state="valid-state")

            with pytest.raises(HTTPException) as exc_info:
                await google_callback(body=body, db=db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_email_rejected(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.auth_google import google_callback

        db = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google._validate_state"),
            patch("pwbs.api.v1.routes.auth_google._exchange_code") as mock_ex,
            patch("pwbs.api.v1.routes.auth_google._fetch_google_userinfo") as mock_ui,
        ):
            mock_gs.return_value = _mock_settings()
            mock_ex.return_value = {"access_token": "google-at"}
            mock_ui.return_value = {
                "email": "",
                "email_verified": True,
                "sub": "google-123",
            }

            body = GoogleCallbackRequest(code="auth-code", state="valid-state")

            with pytest.raises(HTTPException) as exc_info:
                await google_callback(body=body, db=db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_not_configured_returns_503(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.auth_google import google_callback

        db = AsyncMock()

        with patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs:
            mock_gs.return_value = _mock_settings(client_id="")

            body = GoogleCallbackRequest(code="auth-code", state="valid-state")

            with pytest.raises(HTTPException) as exc_info:
                await google_callback(body=body, db=db)

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_state_validated_before_code_exchange(self) -> None:
        """State must be validated before any Google API calls."""
        from fastapi import HTTPException

        from pwbs.api.v1.routes.auth_google import google_callback

        db = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.auth_google.get_settings") as mock_gs,
            patch("pwbs.api.v1.routes.auth_google._validate_state") as mock_vs,
            patch("pwbs.api.v1.routes.auth_google._exchange_code") as mock_ex,
        ):
            mock_gs.return_value = _mock_settings()
            mock_vs.side_effect = HTTPException(status_code=400, detail="Bad state")

            body = GoogleCallbackRequest(code="auth-code", state="bad-state")

            with pytest.raises(HTTPException) as exc_info:
                await google_callback(body=body, db=db)

        assert exc_info.value.status_code == 400
        # Code exchange should NOT have been called
        mock_ex.assert_not_called()


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


class TestGoogleCallbackRequestValidation:
    def test_empty_code_rejected(self) -> None:
        with pytest.raises(Exception):
            GoogleCallbackRequest(code="", state="valid")

    def test_empty_state_rejected(self) -> None:
        with pytest.raises(Exception):
            GoogleCallbackRequest(code="valid-code", state="")

    def test_valid_request(self) -> None:
        req = GoogleCallbackRequest(code="auth-code", state="csrf-state")
        assert req.code == "auth-code"
        assert req.state == "csrf-state"


# ---------------------------------------------------------------------------
# Router metadata
# ---------------------------------------------------------------------------


class TestRouterMetadata:
    def test_router_prefix(self) -> None:
        assert router.prefix == "/api/v1/auth/google"

    def test_router_has_auth_url_route(self) -> None:
        paths = [r.path for r in router.routes]
        assert "/api/v1/auth/google/auth-url" in paths

    def test_router_has_callback_route(self) -> None:
        paths = [r.path for r in router.routes]
        assert "/api/v1/auth/google/callback" in paths
