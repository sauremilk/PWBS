"""PWBS core  shared configuration, exceptions, and base classes."""

from pwbs.core.config import Settings, get_settings
from pwbs.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ConnectorError,
    EncryptionError,
    ExternalServiceError,
    IngestionError,
    NotFoundError,
    ProcessingError,
    PWBSError,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "Settings",
    "get_settings",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "ConnectorError",
    "EncryptionError",
    "ExternalServiceError",
    "IngestionError",
    "NotFoundError",
    "ProcessingError",
    "PWBSError",
    "RateLimitError",
    "ValidationError",
]
