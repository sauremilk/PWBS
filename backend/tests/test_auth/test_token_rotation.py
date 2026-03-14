"""Tests for token rotation and refresh endpoint (TASK-084)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.core.config import get_settings
from pwbs.core.exceptions import AuthenticationError
from pwbs.models.refresh_token import RefreshToken
from pwbs.services.auth import (
    TokenPair,
    _hash_token,
    create_token_pair,
    rotate_refresh_token,
    validate_access_token,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def family_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture()
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# rotate_refresh_token
# ---------------------------------------------------------------------------


class TestRotateRefreshToken:
    @pytest.mark.asyncio
    async def test_successful_rotation(
        self, user_id: uuid.UUID, family_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        """Valid token -> revoke old, issue new pair in same family."""
        old_token = "old-valid-token"
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(old_token),
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked_at=None,
        )
        # validate_refresh_token queries DB -> return the token
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        pair = await rotate_refresh_token(old_token, mock_db)

        # Old token should be revoked
        assert db_token.revoked_at is not None
        # New pair should be valid
        assert isinstance(pair, TokenPair)
        assert pair.access_token
        assert pair.refresh_token
        assert pair.refresh_token != old_token
        # Access token should decode to same user
        payload = validate_access_token(pair.access_token)
        assert payload.user_id == user_id

    @pytest.mark.asyncio
    async def test_rotation_preserves_family(
        self, user_id: uuid.UUID, family_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        """New refresh token should be in the same family."""
        old_token = "family-token"
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(old_token),
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked_at=None,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        await rotate_refresh_token(old_token, mock_db)

        # The new refresh token saved to DB should use the same family_id
        saved = mock_db.add.call_args[0][0]
        assert isinstance(saved, RefreshToken)
        assert saved.family_id == family_id

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_db: AsyncMock) -> None:
        """Non-existent token -> AuthenticationError."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            await rotate_refresh_token("nonexistent-token", mock_db)

    @pytest.mark.asyncio
    async def test_revoked_token_triggers_family_revocation(
        self, user_id: uuid.UUID, family_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        """Already-revoked token -> replay detection -> revoke family."""
        old_token = "revoked-token"
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(old_token),
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="revoked"):
            await rotate_refresh_token(old_token, mock_db)

    @pytest.mark.asyncio
    async def test_expired_token_raises(
        self, user_id: uuid.UUID, family_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        """Expired token -> AuthenticationError."""
        old_token = "expired-token"
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(old_token),
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            revoked_at=None,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        with pytest.raises(AuthenticationError, match="expired"):
            await rotate_refresh_token(old_token, mock_db)

    @pytest.mark.asyncio
    async def test_new_token_has_30_day_expiry(
        self, user_id: uuid.UUID, family_id: uuid.UUID, mock_db: AsyncMock
    ) -> None:
        """New refresh token should expire in 30 days."""
        old_token = "valid-for-expiry-test"
        db_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=_hash_token(old_token),
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            revoked_at=None,
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = db_token
        mock_db.execute.return_value = result_mock

        await rotate_refresh_token(old_token, mock_db)

        saved = mock_db.add.call_args[0][0]
        expected_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        delta = abs((saved.expires_at - expected_expiry).total_seconds())
        assert delta < 5  # within 5 seconds tolerance
