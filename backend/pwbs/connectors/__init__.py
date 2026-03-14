"""PWBS data-source connectors package.

Public API:
- ``BaseConnector``, ``ConnectorConfig``, ``SyncResult`` - connector interface
- ``register_connector``, ``get_connector_class``, ``create_connector`` - registry
- ``OAuthTokens``, ``encrypt_tokens``, ``decrypt_tokens`` - OAuth token management
- ``normalize_document``, ``compute_content_hash`` - document normalisation
"""

from pwbs.connectors.base import BaseConnector, ConnectorConfig, JsonValue, SyncError, SyncResult
from pwbs.connectors.normalizer import (
    compute_content_hash,
    compute_expiry,
    has_content_changed,
    normalize_document,
)
from pwbs.connectors.oauth import (
    OAuthTokens,
    decrypt_tokens,
    encrypt_tokens,
    get_valid_access_token,
    refresh_access_token,
)
from pwbs.connectors.registry import (
    clear_registry,
    create_connector,
    get_connector_class,
    list_registered_types,
    register_connector,
)

__all__ = [
    # base
    "BaseConnector",
    "ConnectorConfig",
    "JsonValue",
    "SyncError",
    "SyncResult",
    # registry
    "clear_registry",
    "create_connector",
    "get_connector_class",
    "list_registered_types",
    "register_connector",
    # oauth
    "OAuthTokens",
    "decrypt_tokens",
    "encrypt_tokens",
    "get_valid_access_token",
    "refresh_access_token",
    # normalizer
    "compute_content_hash",
    "compute_expiry",
    "has_content_changed",
    "normalize_document",
]
