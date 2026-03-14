"""Tests for OAuth Token Manager (TASK-043)."""

from __future__ import annotations

import time
import uuid

import httpx
import pytest
from pydantic import SecretStr

from pwbs.connectors.oauth import (
    OAuthTokens,
    _derive_fernet_key,
    decrypt_tokens,
    encrypt_tokens,
    get_valid_access_token,
    refresh_access_token,
)
from pwbs.core.exceptions import TokenEncryptionError, TokenRefreshError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def owner_id() -> uuid.UUID:
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture()
def tokens() -> OAuthTokens:
    return OAuthTokens(
        access_token=SecretStr("access-token-123"),
        refresh_token=SecretStr("refresh-token-456"),
        token_type="Bearer",
        expires_at=time.time() + 3600,
        scope="calendar.readonly",
    )


@pytest.fixture()
def expired_tokens() -> OAuthTokens:
    return OAuthTokens(
        access_token=SecretStr("expired-access"),
        refresh_token=SecretStr("refresh-token-456"),
        token_type="Bearer",
        expires_at=time.time() - 100,
    )


# ---------------------------------------------------------------------------
# OAuthTokens model tests
# ---------------------------------------------------------------------------


class TestOAuthTokens:
    def test_not_expired(self, tokens: OAuthTokens) -> None:
        assert tokens.is_expired is False

    def test_expired(self, expired_tokens: OAuthTokens) -> None:
        assert expired_tokens.is_expired is True

    def test_no_expiry_never_expired(self) -> None:
        t = OAuthTokens(access_token=SecretStr("abc"))
        assert t.is_expired is False

    def test_expired_within_safety_margin(self) -> None:
        """Token within 60s of expiry is considered expired."""
        t = OAuthTokens(
            access_token=SecretStr("abc"),
            expires_at=time.time() + 30,  # 30s left < 60s margin
        )
        assert t.is_expired is True


# ---------------------------------------------------------------------------
# Encryption / Decryption tests
# ---------------------------------------------------------------------------


class TestEncryptDecrypt:
    def test_roundtrip(self, tokens: OAuthTokens, owner_id: uuid.UUID) -> None:
        encrypted = encrypt_tokens(tokens, owner_id=owner_id)
        assert isinstance(encrypted, str)
        assert encrypted != tokens.access_token.get_secret_value()

        decrypted = decrypt_tokens(encrypted, owner_id=owner_id)
        assert decrypted.access_token.get_secret_value() == "access-token-123"
        assert decrypted.refresh_token is not None
        assert decrypted.refresh_token.get_secret_value() == "refresh-token-456"
        assert decrypted.scope == "calendar.readonly"

    def test_different_owners_different_ciphertexts(
        self,
        tokens: OAuthTokens,
    ) -> None:
        owner_a = uuid.uuid4()
        owner_b = uuid.uuid4()
        enc_a = encrypt_tokens(tokens, owner_id=owner_a)
        enc_b = encrypt_tokens(tokens, owner_id=owner_b)
        assert enc_a != enc_b

    def test_wrong_owner_cannot_decrypt(
        self,
        tokens: OAuthTokens,
        owner_id: uuid.UUID,
    ) -> None:
        encrypted = encrypt_tokens(tokens, owner_id=owner_id)
        wrong_owner = uuid.uuid4()
        with pytest.raises(TokenEncryptionError, match="invalid key"):
            decrypt_tokens(encrypted, owner_id=wrong_owner)

    def test_corrupted_data_raises(self, owner_id: uuid.UUID) -> None:
        with pytest.raises(TokenEncryptionError):
            decrypt_tokens("corrupted-garbage-data", owner_id=owner_id)

    def test_key_derivation_deterministic(self, owner_id: uuid.UUID) -> None:
        key1 = _derive_fernet_key(owner_id)
        key2 = _derive_fernet_key(owner_id)
        assert key1 == key2


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


class TestRefreshAccessToken:
    async def test_no_refresh_token_raises(self) -> None:
        tokens = OAuthTokens(access_token=SecretStr("abc"))
        with pytest.raises(TokenRefreshError, match="no refresh token"):
            await refresh_access_token(tokens, source_type=SourceType.GOOGLE_CALENDAR)

    async def test_successful_refresh(
        self, expired_tokens: OAuthTokens, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mock the HTTP call to simulate a successful token refresh."""
        monkeypatch.setattr(
            "pwbs.connectors.oauth._get_client_credentials",
            lambda source_type, settings: ("test-client-id", "test-client-secret"),
        )

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        result = await refresh_access_token(expired_tokens, source_type=SourceType.GOOGLE_CALENDAR)
        assert result.access_token.get_secret_value() == "new-access-token"
        assert result.refresh_token is not None
        assert result.refresh_token.get_secret_value() == "new-refresh-token"
        assert result.expires_at is not None
        assert result.expires_at > time.time()

    async def test_http_error_raises(
        self, expired_tokens: OAuthTokens, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "pwbs.connectors.oauth._get_client_credentials",
            lambda source_type, settings: ("test-client-id", "test-client-secret"),
        )

        async def mock_post(self: httpx.AsyncClient, url: str, **kwargs: object) -> httpx.Response:
            resp = httpx.Response(
                401,
                json={"error": "invalid_grant"},
                request=httpx.Request("POST", url),
            )
            resp.raise_for_status()
            return resp  # unreachable

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        with pytest.raises(TokenRefreshError, match="HTTP 401"):
            await refresh_access_token(expired_tokens, source_type=SourceType.GOOGLE_CALENDAR)

    async def test_unsupported_source_type_raises(self) -> None:
        tokens = OAuthTokens(
            access_token=SecretStr("abc"),
            refresh_token=SecretStr("def"),
        )
        with pytest.raises(Exception, match="No token refresh endpoint"):
            await refresh_access_token(tokens, source_type=SourceType.OBSIDIAN)


# ---------------------------------------------------------------------------
# get_valid_access_token tests
# ---------------------------------------------------------------------------


class TestGetValidAccessToken:
    async def test_valid_token_returns_directly(
        self, tokens: OAuthTokens, owner_id: uuid.UUID
    ) -> None:
        encrypted = encrypt_tokens(tokens, owner_id=owner_id)
        access_token, updated = await get_valid_access_token(
            encrypted,
            owner_id=owner_id,
            source_type=SourceType.GOOGLE_CALENDAR,
        )
        assert access_token == "access-token-123"
        assert updated is None  # no refresh needed
