"""Tests for Auth API endpoints (TASK-086)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from pwbs.api.v1.routes.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    MeResponse,
    RegisterResponse,
)
from pwbs.services.auth import TokenPair
from pwbs.services.user import RegisterRequest


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestRegisterResponseSchema:
    def test_valid(self) -> None:
        resp = RegisterResponse(
            user_id=uuid.uuid4(),
            access_token="tok",
            refresh_token="rtok",
        )
        assert resp.user_id is not None

    def test_frozen(self) -> None:
        resp = RegisterResponse(
            user_id=uuid.uuid4(),
            access_token="tok",
            refresh_token="rtok",
        )
        with pytest.raises(Exception):
            resp.access_token = "changed"


class TestLoginRequestSchema:
    def test_strips_whitespace(self) -> None:
        req = LoginRequest(email="  test@example.com  ", password="pass")
        assert req.email == "test@example.com"


class TestLoginResponseSchema:
    def test_valid(self) -> None:
        resp = LoginResponse(
            access_token="tok",
            refresh_token="rtok",
            expires_in=900,
        )
        assert resp.token_type == "bearer"


class TestLogoutRequestSchema:
    def test_valid(self) -> None:
        req = LogoutRequest(refresh_token="some-token")
        assert req.refresh_token == "some-token"


class TestMeResponseSchema:
    def test_valid(self) -> None:
        resp = MeResponse(
            user_id=uuid.uuid4(),
            email="test@example.com",
            display_name="Test User",
            created_at=datetime.now(timezone.utc),
        )
        assert resp.email == "test@example.com"


# ---------------------------------------------------------------------------
# Endpoint logic tests (unit-level, mocked dependencies)
# ---------------------------------------------------------------------------


class TestRegisterEndpoint:
    @pytest.mark.asyncio
    async def test_successful_registration(self) -> None:
        from pwbs.api.v1.routes.auth import register

        uid = uuid.uuid4()
        pair = TokenPair(
            access_token="access",
            refresh_token="refresh",
            expires_in=900,
        )

        mock_db = AsyncMock()

        with (
            patch("pwbs.api.v1.routes.auth.register_user", new_callable=AsyncMock, return_value=pair),
            patch(
                "pwbs.api.v1.routes.auth.validate_access_token",
                return_value=MagicMock(user_id=uid),
            ),
        ):
            body = RegisterRequest(
                email="test@example.com",
                password="SecurePass123",
                display_name="Test",
            )
            result = await register(body=body, db=mock_db)

        assert result.user_id == uid
        assert result.access_token == "access"
        assert result.refresh_token == "refresh"

    @pytest.mark.asyncio
    async def test_validation_error_returns_400(self) -> None:
        from pwbs.api.v1.routes.auth import register
        from pwbs.core.exceptions import ValidationError

        mock_db = AsyncMock()

        with patch(
            "pwbs.api.v1.routes.auth.register_user",
            new_callable=AsyncMock,
            side_effect=ValidationError("Bad password", code="VALIDATION_ERROR"),
        ):
            body = RegisterRequest(
                email="test@example.com",
                password="SecurePass123",
                display_name="Test",
            )
            with pytest.raises(Exception) as exc_info:
                await register(body=body, db=mock_db)
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_409(self) -> None:
        from pwbs.api.v1.routes.auth import register
        from pwbs.core.exceptions import AuthenticationError

        mock_db = AsyncMock()

        with patch(
            "pwbs.api.v1.routes.auth.register_user",
            new_callable=AsyncMock,
            side_effect=AuthenticationError("Registrierung fehlgeschlagen", code="REGISTRATION_FAILED"),
        ):
            body = RegisterRequest(
                email="test@example.com",
                password="SecurePass123",
                display_name="Test",
            )
            with pytest.raises(Exception) as exc_info:
                await register(body=body, db=mock_db)
            assert exc_info.value.status_code == 409


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_successful_login(self) -> None:
        from pwbs.api.v1.routes.auth import login

        uid = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = uid
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed"

        pair = TokenPair(
            access_token="access",
            refresh_token="refresh",
            expires_in=900,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with (
            patch("pwbs.api.v1.routes.auth.verify_password", return_value=True),
            patch("pwbs.api.v1.routes.auth.create_token_pair", new_callable=AsyncMock, return_value=pair),
        ):
            body = LoginRequest(email="test@example.com", password="password")
            result = await login(body=body, db=mock_db)

        assert result.access_token == "access"
        assert result.expires_in == 900

    @pytest.mark.asyncio
    async def test_invalid_email_returns_401(self) -> None:
        from pwbs.api.v1.routes.auth import login

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        body = LoginRequest(email="wrong@example.com", password="password")
        with pytest.raises(Exception) as exc_info:
            await login(body=body, db=mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self) -> None:
        from pwbs.api.v1.routes.auth import login

        mock_user = MagicMock()
        mock_user.password_hash = "hashed"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("pwbs.api.v1.routes.auth.verify_password", return_value=False):
            body = LoginRequest(email="test@example.com", password="wrongpass")
            with pytest.raises(Exception) as exc_info:
                await login(body=body, db=mock_db)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_generic_error_message(self) -> None:
        """Login error should not reveal whether email exists."""
        from pwbs.api.v1.routes.auth import login

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        body = LoginRequest(email="nonexistent@example.com", password="pass")
        with pytest.raises(Exception) as exc_info:
            await login(body=body, db=mock_db)
        assert "INVALID_CREDENTIALS" in str(exc_info.value.detail)


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_successful_logout(self) -> None:
        from pwbs.api.v1.routes.auth import logout

        mock_user = MagicMock()
        mock_db = AsyncMock()

        with patch("pwbs.api.v1.routes.auth.revoke_refresh_token", new_callable=AsyncMock):
            body = LogoutRequest(refresh_token="some-token")
            result = await logout(body=body, current_user=mock_user, db=mock_db)

        assert result.message == "logged_out"

    @pytest.mark.asyncio
    async def test_logout_with_invalid_token_still_succeeds(self) -> None:
        from pwbs.api.v1.routes.auth import logout
        from pwbs.core.exceptions import AuthenticationError

        mock_user = MagicMock()
        mock_db = AsyncMock()

        with patch(
            "pwbs.api.v1.routes.auth.revoke_refresh_token",
            new_callable=AsyncMock,
            side_effect=AuthenticationError("Invalid token"),
        ):
            body = LogoutRequest(refresh_token="invalid")
            result = await logout(body=body, current_user=mock_user, db=mock_db)

        assert result.message == "logged_out"


class TestMeEndpoint:
    @pytest.mark.asyncio
    async def test_returns_user_profile(self) -> None:
        from pwbs.api.v1.routes.auth import me

        uid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        mock_user = MagicMock()
        mock_user.id = uid
        mock_user.email = "test@example.com"
        mock_user.display_name = "Test User"
        mock_user.created_at = now

        result = await me(current_user=mock_user)

        assert result.user_id == uid
        assert result.email == "test@example.com"
        assert result.display_name == "Test User"
        assert result.created_at == now


# ---------------------------------------------------------------------------
# get_current_user dependency tests
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self) -> None:
        from pwbs.api.dependencies.auth import get_current_user

        mock_db = AsyncMock()

        with pytest.raises(Exception) as exc_info:
            await get_current_user(credentials=None, db=mock_db)
        assert exc_info.value.status_code == 401
        assert "MISSING_TOKEN" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        from pwbs.api.dependencies.auth import get_current_user
        from pwbs.core.exceptions import AuthenticationError

        mock_db = AsyncMock()
        mock_creds = MagicMock()
        mock_creds.credentials = "invalid-jwt"

        with patch(
            "pwbs.api.dependencies.auth.validate_access_token",
            side_effect=AuthenticationError("Invalid token"),
        ):
            with pytest.raises(Exception) as exc_info:
                await get_current_user(credentials=mock_creds, db=mock_db)
            assert exc_info.value.status_code == 401
            assert "INVALID_TOKEN" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self) -> None:
        from pwbs.api.dependencies.auth import get_current_user

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_creds = MagicMock()
        mock_creds.credentials = "valid-jwt"

        with patch(
            "pwbs.api.dependencies.auth.validate_access_token",
            return_value=MagicMock(user_id=uuid.uuid4()),
        ):
            with pytest.raises(Exception) as exc_info:
                await get_current_user(credentials=mock_creds, db=mock_db)
            assert exc_info.value.status_code == 401
            assert "USER_NOT_FOUND" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self) -> None:
        from pwbs.api.dependencies.auth import get_current_user

        uid = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = uid

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_creds = MagicMock()
        mock_creds.credentials = "valid-jwt"

        with patch(
            "pwbs.api.dependencies.auth.validate_access_token",
            return_value=MagicMock(user_id=uid),
        ):
            result = await get_current_user(credentials=mock_creds, db=mock_db)

        assert result == mock_user
