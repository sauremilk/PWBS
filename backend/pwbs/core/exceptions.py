"""PWBS base exceptions.

All domain exceptions inherit from PWBSError.
HTTP-level exceptions use FastAPI HTTPException with structured detail dicts.
"""

from __future__ import annotations


class PWBSError(Exception):
    """Base exception for all PWBS domain errors."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ConfigurationError(PWBSError):
    """Raised when application configuration is invalid or missing."""


class AuthenticationError(PWBSError):
    """Raised when authentication fails."""


class AuthorizationError(PWBSError):
    """Raised when a user lacks permission for the requested operation."""


class NotFoundError(PWBSError):
    """Raised when a requested resource does not exist."""


class ValidationError(PWBSError):
    """Raised when input data fails domain validation."""


class ExternalServiceError(PWBSError):
    """Raised when an external service (LLM, DB, API) fails."""


class IngestionError(PWBSError):
    """Raised when data ingestion fails."""


class ProcessingError(PWBSError):
    """Raised when document processing (chunking, embedding, NER) fails."""


class EncryptionError(PWBSError):
    """Raised when encryption or decryption operations fail."""