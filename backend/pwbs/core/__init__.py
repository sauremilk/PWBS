"""PWBS core  shared configuration, exceptions, and base classes."""

from pwbs.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    EncryptionError,
    ExternalServiceError,
    IngestionError,
    NotFoundError,
    ProcessingError,
    PWBSError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "EncryptionError",
    "ExternalServiceError",
    "IngestionError",
    "NotFoundError",
    "ProcessingError",
    "PWBSError",
    "ValidationError",
]