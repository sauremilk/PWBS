"""Tests for JWT authentication service (TASK-081)."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.core.config import get_settings
from pwbs.core.exceptions import AuthenticationError
from pwbs.models.refresh_token import RefreshToken
from pwbs.services.auth import (
    TokenPair,
    TokenPayload,
    _hash_token,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    revoke_all_user_tokens,
    revoke_refresh_token,
    validate_access_token,
    validate_refresh_token,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Ensure fresh settings for each test."""
    get_settings.cache_clear()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# _hash_token
# ---------------------------------------------------------------------------


class TestHashToken:
    def test_returns_sha256_hex(self) -> None:
        token = "test-token-value"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert _hash_token(token) == expected

    def test_deterministic(self) -> None:
        assert _hash_token("abc") == _hash_token("abc")

    def test_different_tokens_different_hashes(self) -> None:
        assert _hash_token("token-a") != _hash_token("token-b")


# ---------------------------------------------------------------------------
# Access token creation and validation
# ---------------------------------------------------------------------------


class TestAccessToken:
    def test_create_and_validate_roundtrip(self, user_id: uuid.UUID) -> None:
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

        payload = validate_access_token(token)
        assert isinstance(payload, TokenPayload)
        assert payload.user_id == user_id
        assert payload.exp > payload.iat

    def test_contains_required_claims(self, user_id: uuid.UUID) -> None:
        token = create_access_token(user_id)
        payload = validate_access_token(token)
        assert payload.user_id == user_id
        assert payload.exp is not None
        assert payload.iat is not None

    def test_expires_in_configured_minutes(self, user_id: uuid.UUID) -> None:
        settings = get_settings()
        token = create_access_token(user_id)
        payload = validate_access_token(token)
        delta = payload.exp - payload.iat
        expected = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        # Allow 2 seconds tolerance
        assert abs(delta.total_seconds() - expected.total_seconds()) < 2

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="Invalid or expired"):
            validate_access_token("not.a.valid.jwt")

    def test_tampered_token_raises(self, user_id: uuid.UUID) -> None:
        token = create_access_token(user_id)
        # Flip a character in the signature part
        parts = token.rsplit(".", 1)
        tampered = parts[0] + ".TAMPERED"
        with pytest.raises(AuthenticationError):
            validate_access_token(tampered)

    def test_expired_token_raises(self, user_id: uuid.UUID) -> None:
        """Manually craft an expired token to test rejection."""
        from jose import jwt as jose_jwt

        settings = get_settings()
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(user_id),
            "exp": now - timedelta(minutes=1),
            "iat": now - timedelta(minutes=16),
        }
        key = settings.jwt_secret_key.get_secret_value()
        algo = settings.jwt_algorithm
        expired_token = jose_jwt.encode(claims, key, algorithm=algo)
        with pytest.raises(AuthenticationError):
            validate_access_token(expired_token)


# ---------------------------------------------------------------------------
# Refresh token creation
# ---------------------------------------------------------------------------


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_create_returns_string(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        token = await create_refresh_token(user_id, mock_db)
        assert isinstance(token, str)
        assert len(token) > 32  # token_urlsafe(48) produces ~64 chars

    @pytest.mark.asyncio
    async def test_create_adds_to_db(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        await create_refresh_token(user_id, mock_db)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stored_token_is_hashed(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        raw = await create_refresh_token(user_id, mock_db)
        saved = mock_db.add.call_args[0][0]
        assert isinstance(saved, RefreshToken)
        assert saved.token_hash == _hash_token(raw)
        assert saved.token_hash != raw  # not stored as plaintext

    @pytest.mark.asyncio
    async def test_new_family_generated(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        await create_refresh_token(user_id, mock_db)
        saved = mock_db.add.call_args[0][0]
        assert saved.family_id is not None

    @pytest.mark.asyncio
    async def test_custom_family_id(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        family = uuid.uuid4()
        await create_refresh_token(user_id, mock_db, family_id=family)
        saved = mock_db.add.call_args[0][0]
        assert saved.family_id == family

    @pytest.mark.asyncio
    async def test_unique_tokens_per_call(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        t1 = await create_refresh_token(user_id, mock_db)
        t2 = await create_refresh_token(user_id, mock_db)
        assert t1 != t2


# ---------------------------------------------------------------------------
# Refresh token validation
# ---------------------------------------------------------------------------


class TestValidateRefreshToken:
    @pytest.mark.asyncio
    async def test_valid_token(self, user_id: uuid.UUID, mock_db: AsyncMock) -> None:
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token("valid-token"),
            family_id=uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked_at=None,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        result = await validate_refresh_token("valid-token", mock_db)
        assert result is db_token

    @pytest.mark.asyncio
    async def test_nonexistent_token_raises(self, mock_db: AsyncMock) -> None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            await validate_refresh_token("nonexistent", mock_db)

    @pytest.mark.asyncio
    async def test_revoked_token_raises(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token("revoked-token"),
            family_id=uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked_at=datetime.now(timezone.utc),
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="revoked"):
            await validate_refresh_token("revoked-token", mock_db)

    @pytest.mark.asyncio
    async def test_expired_token_raises(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token("expired-token"),
            family_id=uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            revoked_at=None,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="expired"):
            await validate_refresh_token("expired-token", mock_db)


# ---------------------------------------------------------------------------
# Token pair creation
# ---------------------------------------------------------------------------


class TestTokenPair:
    @pytest.mark.asyncio
    async def test_creates_both_tokens(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        pair = await create_token_pair(user_id, mock_db)
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    @pytest.mark.asyncio
    async def test_access_token_is_valid(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        pair = await create_token_pair(user_id, mock_db)
        payload = validate_access_token(pair.access_token)
        assert payload.user_id == user_id

    @pytest.mark.asyncio
    async def test_expires_in_matches_config(
        self, user_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        settings = get_settings()
        pair = await create_token_pair(user_id, mock_db)
        assert pair.expires_in == settings.jwt_access_token_expire_minutes * 60
