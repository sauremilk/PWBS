"""Tests for user registration service (TASK-082)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError

from pwbs.core.config import get_settings
from pwbs.core.exceptions import AuthenticationError
from pwbs.models.user import User
from pwbs.services.auth import TokenPair, validate_access_token
from pwbs.services.user import (
    RegisterRequest,
    _generate_encrypted_dek,
    hash_password,
    register_user,
    verify_password,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture()
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture()
def valid_request() -> RegisterRequest:
    return RegisterRequest(
        email="test@example.com",
        password="SecurePass123",
        display_name="Test User",
    )


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------


class TestPasswordValidation:
    def test_valid_password(self) -> None:
        req = RegisterRequest(email="a@b.com", password="ValidPass123", display_name="User")
        assert req.password == "ValidPass123"

    def test_too_short(self) -> None:
        with pytest.raises(PydanticValidationError, match="12 Zeichen"):
            RegisterRequest(email="a@b.com", password="Short1A", display_name="User")

    def test_no_uppercase(self) -> None:
        with pytest.raises(PydanticValidationError, match="Großbuchstaben"):
            RegisterRequest(email="a@b.com", password="alllowercase123", display_name="User")

    def test_no_digit(self) -> None:
        with pytest.raises(PydanticValidationError, match="Zahl"):
            RegisterRequest(email="a@b.com", password="NoDigitsHereABC", display_name="User")

    def test_exactly_12_chars_valid(self) -> None:
        req = RegisterRequest(email="a@b.com", password="Abcdefghij1!", display_name="User")
        assert len(req.password) == 12


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------


class TestEmailValidation:
    def test_valid_email(self) -> None:
        req = RegisterRequest(email="USER@Example.COM", password="SecurePass123", display_name="U")
        assert req.email == "user@example.com"  # lowered

    def test_invalid_email(self) -> None:
        with pytest.raises(PydanticValidationError, match="E-Mail"):
            RegisterRequest(email="not-an-email", password="SecurePass123", display_name="U")


# ---------------------------------------------------------------------------
# Argon2 hashing
# ---------------------------------------------------------------------------


class TestArgon2Hashing:
    def test_hash_password_returns_argon2_hash(self) -> None:
        h = hash_password("SecurePass123")
        assert h.startswith("")

    def test_hash_is_not_plaintext(self) -> None:
        h = hash_password("SecurePass123")
        assert h != "SecurePass123"

    def test_verify_correct_password(self) -> None:
        h = hash_password("SecurePass123")
        assert verify_password("SecurePass123", h) is True

    def test_verify_wrong_password(self) -> None:
        h = hash_password("SecurePass123")
        assert verify_password("WrongPassword1", h) is False

    def test_different_hashes_per_call(self) -> None:
        h1 = hash_password("SecurePass123")
        h2 = hash_password("SecurePass123")
        assert h1 != h2  # different salts


# ---------------------------------------------------------------------------
# DEK generation
# ---------------------------------------------------------------------------


class TestDEKGeneration:
    def test_generates_encrypted_dek(self) -> None:
        dek = _generate_encrypted_dek()
        assert isinstance(dek, str)
        assert len(dek) > 0

    def test_different_deks_per_call(self) -> None:
        dek1 = _generate_encrypted_dek()
        dek2 = _generate_encrypted_dek()
        assert dek1 != dek2


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_successful_registration(
        self, valid_request: RegisterRequest, mock_db: AsyncMock
    ) -> None:
        pair = await register_user(valid_request, mock_db)
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    @pytest.mark.asyncio
    async def test_user_saved_to_db(
        self, valid_request: RegisterRequest, mock_db: AsyncMock
    ) -> None:
        await register_user(valid_request, mock_db)
        # db.add should be called at least once with a User object
        add_calls = [c for c in mock_db.add.call_args_list if isinstance(c[0][0], User)]
        assert len(add_calls) >= 1
        user = add_calls[0][0][0]
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.password_hash.startswith("")
        assert user.encryption_key_enc  # DEK was generated

    @pytest.mark.asyncio
    async def test_duplicate_email_generic_error(
        self, valid_request: RegisterRequest, mock_db: AsyncMock
    ) -> None:
        """Duplicate email must return generic error (no email leak)."""
        mock_db.flush.side_effect = IntegrityError(
            "duplicate", params=None, orig=Exception("unique_violation")
        )
        with pytest.raises(AuthenticationError, match="Registrierung fehlgeschlagen"):
            await register_user(valid_request, mock_db)

    @pytest.mark.asyncio
    async def test_password_not_stored_as_plaintext(
        self, valid_request: RegisterRequest, mock_db: AsyncMock
    ) -> None:
        await register_user(valid_request, mock_db)
        add_calls = [c for c in mock_db.add.call_args_list if isinstance(c[0][0], User)]
        user = add_calls[0][0][0]
        assert user.password_hash != valid_request.password
