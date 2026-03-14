"""Sentry error-tracking integration (TASK-115).

Initialises the Sentry SDK for FastAPI with:
- PII scrubbing in `before_send` (no emails, passwords, content)
- Request-ID and pseudonymised user-ID as Sentry context
- Environment tag from `Settings.environment`
- Performance tracing (`traces_sample_rate`)

The SDK is only initialised when `SENTRY_DSN` is set to a non-empty value.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# PII keys to strip from Sentry event data (aligned with logging.py)
_PII_KEYS = frozenset({
    "email",
    "password",
    "password_hash",
    "display_name",
    "name",
    "content",
    "body",
    "text",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "phone",
    "address",
    "embedding",
    "embeddings",
    "metadata",
})


def _pseudonymise_user_id(user_id: str) -> str:
    """Return a SHA-256 hex digest prefix (16 chars) so Sentry can group
    issues by user without storing the raw UUID."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def _scrub_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove PII keys from a dictionary."""
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _PII_KEYS:
            cleaned[key] = "[Filtered]"
        elif isinstance(value, dict):
            cleaned[key] = _scrub_dict(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _scrub_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Sentry `before_send` hook -- strip PII from event data."""
    # Scrub request data
    request_data = event.get("request", {})
    if "data" in request_data and isinstance(request_data["data"], dict):
        request_data["data"] = _scrub_dict(request_data["data"])
    if "headers" in request_data and isinstance(request_data["headers"], dict):
        # Strip Authorization header
        headers = request_data["headers"]
        if "Authorization" in headers:
            headers["Authorization"] = "[Filtered]"
        if "authorization" in headers:
            headers["authorization"] = "[Filtered]"
        if "Cookie" in headers:
            headers["Cookie"] = "[Filtered]"
        if "cookie" in headers:
            headers["cookie"] = "[Filtered]"

    # Scrub exception local variables
    for exc_info in event.get("exception", {}).get("values", []):
        for frame in exc_info.get("stacktrace", {}).get("frames", []):
            if "vars" in frame and isinstance(frame["vars"], dict):
                frame["vars"] = _scrub_dict(frame["vars"])

    # Scrub breadcrumbs
    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if "data" in breadcrumb and isinstance(breadcrumb["data"], dict):
            breadcrumb["data"] = _scrub_dict(breadcrumb["data"])

    # Attach request-ID and pseudonymised user-ID from context vars
    from pwbs.core.logging import request_id_var, user_id_var

    request_id = request_id_var.get(None)
    user_id = user_id_var.get(None)

    if request_id:
        event.setdefault("tags", {})["request_id"] = request_id

    if user_id:
        event.setdefault("user", {})["id"] = _pseudonymise_user_id(user_id)

    return event


def init_sentry(
    dsn: str,
    environment: str,
    traces_sample_rate: float = 1.0,
) -> None:
    """Initialise Sentry SDK if *dsn* is non-empty.

    Call once at application startup (in `create_app`).
    """
    if not dsn:
        logger.info("SENTRY_DSN not set -- Sentry error-tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning(
            "sentry-sdk not installed -- skipping Sentry initialisation. "
            "Install with: pip install sentry-sdk[fastapi]"
        )
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        before_send=before_send,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
    logger.info(
        "Sentry initialised (environment=%s, traces_sample_rate=%s)",
        environment,
        traces_sample_rate,
    )
