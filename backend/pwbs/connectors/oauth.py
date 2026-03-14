"""OAuth Token Manager - encrypted token storage and refresh (TASK-043).

Handles:
- Fernet encryption/decryption of OAuth credentials (access + refresh tokens)
- Token refresh via provider-specific endpoints
- Encrypted persistence in the ``connections.credentials_enc`` column

Security:
- Tokens are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256).
- The Fernet key is derived from the application-level ``ENCRYPTION_MASTER_KEY``
  via HKDF (HMAC-based Key Derivation Function) with a per-user salt.
- Decrypted tokens are never logged. Only connection IDs appear in log output.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import TYPE_CHECKING

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from pwbs.core.config import get_settings
from pwbs.core.exceptions import (
    ConnectorError,
    TokenEncryptionError,
    TokenRefreshError,
)
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

# Token refresh endpoint mapping per provider
_REFRESH_ENDPOINTS: dict[SourceType, str] = {
    SourceType.GOOGLE_CALENDAR: "https://oauth2.googleapis.com/token",
    SourceType.NOTION: "https://api.notion.com/v1/oauth/token",
    SourceType.ZOOM: "https://zoom.us/oauth/token",
}

# SSRF protection: timeout for all external HTTP calls
_HTTP_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Token data model
# ---------------------------------------------------------------------------


class OAuthTokens(BaseModel):
    """Structured OAuth token data stored encrypted in the DB."""

    model_config = ConfigDict(str_strip_whitespace=True)

    access_token: SecretStr
    refresh_token: SecretStr | None = None
    token_type: str = "Bearer"
    expires_at: float | None = Field(
        default=None,
        description="Unix timestamp when the access token expires",
    )
    scope: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the access token has expired (with 60s safety margin)."""
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - 60)


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------


def _derive_fernet_key(owner_id: UUID) -> bytes:
    """Derive a per-user Fernet key from the master encryption key.

    Uses HKDF with the owner_id as salt to ensure each user's tokens
    are encrypted with a different key, even if the master key is shared.
    """
    settings = get_settings()
    master_key = settings.encryption_master_key.get_secret_value().encode("utf-8")

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=str(owner_id).encode("utf-8"),
        info=b"pwbs-oauth-tokens",
    )
    derived = hkdf.derive(master_key)
    return base64.urlsafe_b64encode(derived)


def encrypt_tokens(tokens: OAuthTokens, *, owner_id: UUID) -> str:
    """Encrypt OAuth tokens for storage in the database.

    Returns a Fernet-encrypted, base64-encoded string suitable for the
    ``connections.credentials_enc`` column.

    Raises ``TokenEncryptionError`` on failure.
    """
    try:
        key = _derive_fernet_key(owner_id)
        f = Fernet(key)
        # SecretStr.model_dump_json() masks values; serialize explicitly
        data = {
            "access_token": tokens.access_token.get_secret_value(),
            "refresh_token": (
                tokens.refresh_token.get_secret_value() if tokens.refresh_token else None
            ),
            "token_type": tokens.token_type,
            "expires_at": tokens.expires_at,
            "scope": tokens.scope,
        }
        payload = json.dumps(data)
        return f.encrypt(payload.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise TokenEncryptionError(
            "Failed to encrypt OAuth tokens",
            code="TOKEN_ENCRYPT_FAILED",
        ) from exc


def decrypt_tokens(encrypted: str, *, owner_id: UUID) -> OAuthTokens:
    """Decrypt OAuth tokens retrieved from the database.

    Raises ``TokenEncryptionError`` if decryption fails (wrong key,
    corrupted data, or tampered ciphertext).
    """
    try:
        key = _derive_fernet_key(owner_id)
        f = Fernet(key)
        decrypted = f.decrypt(encrypted.encode("utf-8"))
        return OAuthTokens.model_validate_json(decrypted)
    except InvalidToken as exc:
        raise TokenEncryptionError(
            "Failed to decrypt OAuth tokens - invalid key or corrupted data",
            code="TOKEN_DECRYPT_FAILED",
        ) from exc
    except Exception as exc:
        raise TokenEncryptionError(
            "Failed to decrypt OAuth tokens",
            code="TOKEN_DECRYPT_FAILED",
        ) from exc


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


async def refresh_access_token(
    tokens: OAuthTokens,
    *,
    source_type: SourceType,
) -> OAuthTokens:
    """Refresh an expired access token using the refresh token.

    Makes an HTTP POST to the provider's token endpoint.
    Returns new ``OAuthTokens`` with updated access token and expiry.

    Raises:
        TokenRefreshError: If the refresh fails (network, auth, or missing refresh token).
        ConnectorError: If the source type has no known refresh endpoint.
    """
    if tokens.refresh_token is None:
        raise TokenRefreshError(
            "Cannot refresh: no refresh token available",
            code="NO_REFRESH_TOKEN",
        )

    endpoint = _REFRESH_ENDPOINTS.get(source_type)
    if endpoint is None:
        raise ConnectorError(
            f"No token refresh endpoint configured for {source_type.value}",
            code="NO_REFRESH_ENDPOINT",
        )

    settings = get_settings()
    client_id, client_secret = _get_client_credentials(source_type, settings)

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens.refresh_token.get_secret_value(),
        "client_id": client_id,
        "client_secret": client_secret,
    }

    logger.info("Refreshing access token: source_type=%s", source_type.value)

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(endpoint, data=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Token refresh HTTP error: source_type=%s status=%d",
            source_type.value,
            exc.response.status_code,
        )
        raise TokenRefreshError(
            f"Token refresh failed with HTTP {exc.response.status_code}",
            code="TOKEN_REFRESH_HTTP_ERROR",
        ) from exc
    except httpx.RequestError as exc:
        raise TokenRefreshError(
            f"Token refresh request failed: {exc}",
            code="TOKEN_REFRESH_NETWORK_ERROR",
        ) from exc

    # Build updated tokens - keep existing refresh token if provider didn't issue a new one
    new_refresh = data.get("refresh_token", tokens.refresh_token.get_secret_value())
    expires_in = data.get("expires_in")
    expires_at = time.time() + expires_in if expires_in else None

    return OAuthTokens(
        access_token=SecretStr(data["access_token"]),
        refresh_token=SecretStr(new_refresh),
        token_type=data.get("token_type", "Bearer"),
        expires_at=expires_at,
        scope=data.get("scope", tokens.scope),
    )


def _get_client_credentials(
    source_type: SourceType,
    settings: object,
) -> tuple[str, str]:
    """Extract client_id and client_secret for the given provider from settings."""
    credential_map: dict[SourceType, tuple[str, str]] = {
        SourceType.GOOGLE_CALENDAR: (
            getattr(settings, "google_client_id", ""),
            getattr(settings, "google_client_secret", SecretStr("")).get_secret_value(),
        ),
        SourceType.NOTION: (
            getattr(settings, "notion_client_id", ""),
            getattr(settings, "notion_client_secret", SecretStr("")).get_secret_value(),
        ),
        SourceType.ZOOM: (
            getattr(settings, "zoom_client_id", ""),
            getattr(settings, "zoom_client_secret", SecretStr("")).get_secret_value(),
        ),
    }

    client_id, client_secret = credential_map.get(source_type, ("", ""))
    if not client_id or not client_secret:
        raise ConnectorError(
            f"Missing OAuth client credentials for {source_type.value}",
            code="MISSING_CLIENT_CREDENTIALS",
        )
    return client_id, client_secret


# ---------------------------------------------------------------------------
# High-level token management
# ---------------------------------------------------------------------------


async def get_valid_access_token(
    encrypted_credentials: str,
    *,
    owner_id: UUID,
    source_type: SourceType,
) -> tuple[str, OAuthTokens | None]:
    """Retrieve a valid access token, refreshing if expired.

    Returns a tuple of:
    - The valid access token string
    - Updated ``OAuthTokens`` if a refresh occurred (caller must persist), or
      ``None`` if no refresh was needed.
    """
    tokens = decrypt_tokens(encrypted_credentials, owner_id=owner_id)

    if not tokens.is_expired:
        return tokens.access_token.get_secret_value(), None

    logger.info(
        "Access token expired, refreshing: source_type=%s",
        source_type.value,
    )
    new_tokens = await refresh_access_token(tokens, source_type=source_type)
    return new_tokens.access_token.get_secret_value(), new_tokens
