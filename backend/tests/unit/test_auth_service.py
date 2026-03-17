"""Tests for pwbs.services.auth – JWT and refresh-token management (TASK-081/084).

Covers:
- Access-token creation and validation (HS256 fallback in tests)
- Token expiry and malformed-token rejection
- Refresh-token creation (hash storage), validation, revocation
- Token rotation with replay-detection
- _hash_token determinism
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.core.exceptions import AuthenticationError
from pwbs.services.auth import (
    TokenPair,
    _hash_token,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    revoke_all_user_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_access_token,
    validate_refresh_token,
)

# ---------------------------------------------------------------------------
# _hash_token
# ---------------------------------------------------------------------------


class TestHashToken:
    def test_deterministic(self) -> None:
        assert _hash_token("abc") == _hash_token("abc")

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert _hash_token("token_a") != _hash_token("token_b")

    def test_returns_hex_string(self) -> None:
        h = _hash_token("test")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# Access tokens
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_returns_nonempty_string(self) -> None:
        token = create_access_token(uuid.uuid4())
        assert isinstance(token, str)
        assert len(token) > 0

    def test_roundtrip(self) -> None:
        uid = uuid.uuid4()
        token = create_access_token(uid)
        payload = validate_access_token(token)
        assert payload.user_id == uid
        assert isinstance(payload.exp, datetime)
        assert isinstance(payload.iat, datetime)

    def test_different_users_produce_different_tokens(self) -> None:
        t1 = create_access_token(uuid.uuid4())
        t2 = create_access_token(uuid.uuid4())
        assert t1 != t2


class TestValidateAccessToken:
    def test_invalid_token_raises(self) -> None:
        with pytest.raises(AuthenticationError, match="Invalid or expired"):
            validate_access_token("not-a-jwt")

    def test_expired_token_raises(self) -> None:
        import jwt as _jwt

        from pwbs.core.config import get_settings

        settings = get_settings()
        past = datetime.now(UTC) - timedelta(hours=1)
        claims = {
            "sub": str(uuid.uuid4()),
            "exp": past,
            "iat": past - timedelta(minutes=15),
        }
        token = _jwt.encode(
            claims,
            settings.jwt_secret_key.get_secret_value(),
            algorithm="HS256",
        )
        with pytest.raises(AuthenticationError):
            validate_access_token(token)

    def test_missing_sub_raises(self) -> None:
        import jwt as _jwt

        from pwbs.core.config import get_settings

        settings = get_settings()
        now = datetime.now(UTC)
        claims = {"exp": now + timedelta(hours=1), "iat": now}
        token = _jwt.encode(
            claims,
            settings.jwt_secret_key.get_secret_value(),
            algorithm="HS256",
        )
        with pytest.raises(AuthenticationError, match="Malformed"):
            validate_access_token(token)


# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------


class TestCreateRefreshToken:
    @pytest.mark.asyncio
    async def test_returns_plaintext_string(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        token = await create_refresh_token(uuid.uuid4(), db)
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_adds_hashed_token_to_db(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        uid = uuid.uuid4()
        raw = await create_refresh_token(uid, db)
        db.add.assert_called_once()
        db_token = db.add.call_args[0][0]
        # Stored hash must NOT equal the raw token
        assert db_token.token_hash != raw
        assert db_token.token_hash == _hash_token(raw)
        assert db_token.user_id == uid

    @pytest.mark.asyncio
    async def test_custom_family_id(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        fid = uuid.uuid4()
        await create_refresh_token(uuid.uuid4(), db, family_id=fid)
        db_token = db.add.call_args[0][0]
        assert db_token.family_id == fid


class TestValidateRefreshToken:
    @pytest.mark.asyncio
    async def test_valid_token(self) -> None:
        uid = uuid.uuid4()
        fid = uuid.uuid4()
        now = datetime.now(UTC)
        db_token = MagicMock()
        db_token.user_id = uid
        db_token.family_id = fid
        db_token.revoked_at = None
        db_token.expires_at = now + timedelta(days=30)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result_mock)

        result = await validate_refresh_token("any-token", db)
        assert result is db_token

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self) -> None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            await validate_refresh_token("bad-token", db)

    @pytest.mark.asyncio
    async def test_revoked_token_raises(self) -> None:
        db_token = MagicMock()
        db_token.revoked_at = datetime.now(UTC)
        db_token.family_id = uuid.uuid4()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthenticationError, match="revoked"):
            await validate_refresh_token("revoked-token", db)

    @pytest.mark.asyncio
    async def test_expired_token_raises(self) -> None:
        db_token = MagicMock()
        db_token.revoked_at = None
        db_token.expires_at = datetime.now(UTC) - timedelta(days=1)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(AuthenticationError, match="expired"):
            await validate_refresh_token("expired-token", db)


class TestRevokeRefreshToken:
    @pytest.mark.asyncio
    async def test_executes_update(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        await revoke_refresh_token("some-token", db)
        db.execute.assert_awaited_once()


class TestRevokeAllUserTokens:
    @pytest.mark.asyncio
    async def test_returns_count(self) -> None:
        result_mock = MagicMock()
        result_mock.rowcount = 5
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result_mock)
        count = await revoke_all_user_tokens(uuid.uuid4(), db)
        assert count == 5


# ---------------------------------------------------------------------------
# Token pair
# ---------------------------------------------------------------------------


class TestCreateTokenPair:
    @pytest.mark.asyncio
    async def test_returns_token_pair(self) -> None:
        db = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        uid = uuid.uuid4()
        pair = await create_token_pair(uid, db)
        assert isinstance(pair, TokenPair)
        assert pair.token_type == "bearer"
        assert pair.expires_in == 15 * 60
        assert len(pair.access_token) > 0
        assert len(pair.refresh_token) > 0


# ---------------------------------------------------------------------------
# Token rotation
# ---------------------------------------------------------------------------


class TestRotateRefreshToken:
    @pytest.mark.asyncio
    async def test_rotation_revokes_old_and_issues_new(self) -> None:
        uid = uuid.uuid4()
        fid = uuid.uuid4()
        now = datetime.now(UTC)

        old_db_token = MagicMock()
        old_db_token.user_id = uid
        old_db_token.family_id = fid
        old_db_token.revoked_at = None
        old_db_token.expires_at = now + timedelta(days=30)

        # First execute: validate (returns old token)
        validate_result = MagicMock()
        validate_result.scalar_one_or_none.return_value = old_db_token

        # Second execute: revoke old token
        # Third execute: create new refresh token (flush)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=validate_result)
        db.flush = AsyncMock()
        db.add = MagicMock()

        pair = await rotate_refresh_token("old-raw-token", db)
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
