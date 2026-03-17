"""Common API response schemas for OpenAPI documentation (TASK-119).

Provides a standard `ErrorResponse` model used in `responses=` parameters
across all API routers to produce consistent error documentation in the
OpenAPI schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response returned by all API error handlers."""

    code: str = Field(..., examples=["VALIDATION_ERROR"])
    message: str = Field(..., examples=["Request validation failed"])
    detail: str | None = Field(
        default=None,
        description="Additional detail (only in development mode)",
    )


#: Common error responses for authenticated endpoints.
#: Use as `responses={**AUTH_RESPONSES}` in router decorators.
AUTH_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Nicht authentifiziert -- fehlender oder ungültiger JWT",
    },
    403: {
        "model": ErrorResponse,
        "description": "Zugriff verweigert -- unzureichende Berechtigungen",
    },
}

#: Error responses common to all endpoints.
COMMON_RESPONSES: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Validierungsfehler -- ungültige Request-Daten",
    },
    429: {
        "model": ErrorResponse,
        "description": "Rate-Limit überschritten",
    },
    500: {
        "model": ErrorResponse,
        "description": "Interner Serverfehler",
    },
}
