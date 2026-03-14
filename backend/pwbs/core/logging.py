"""Structured JSON-Logging configuration (TASK-113).

Configures stdlib logging to emit JSON-formatted log entries via structlog's
ProcessorFormatter. Each entry contains: timestamp, level, logger (module),
message, request_id, user_id, and extra fields like duration_ms.

PII keys are stripped from all log events (DSGVO compliance).
Log level is configurable via the `log_level` setting (env: LOG_LEVEL
or PWBS_LOG_LEVEL).
"""

from __future__ import annotations

import contextvars
import logging
import sys
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Context variables -- set by middleware, read by structlog processors
# ---------------------------------------------------------------------------

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id",
    default=None,
)

# ---------------------------------------------------------------------------
# PII prevention -- keys that MUST NOT appear in log output
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# structlog processors
# ---------------------------------------------------------------------------


def _add_request_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject request_id and user_id from context vars into every log entry."""
    event_dict.setdefault("request_id", request_id_var.get())
    event_dict.setdefault("user_id", user_id_var.get())
    return event_dict


def _sanitize_pii(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Remove PII keys from log events (DSGVO compliance)."""
    for key in _PII_KEYS:
        event_dict.pop(key, None)
    return event_dict


def _rename_event_to_message(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Rename structlog's `event` key to `message` for spec conformance."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging for the PWBS backend.

    Must be called once at application startup (before any log calls).
    After this, all `logging.getLogger()` calls automatically produce
    JSON-formatted output with request context and PII sanitisation.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure structlog for direct structlog.get_logger() usage
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # JSON formatter -- processes both structlog and stdlib log records
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.ExtraAdder(),
        ],
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            _add_request_context,
            _sanitize_pii,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            _rename_event_to_message,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Prevent noisy third-party loggers from flooding output
    for noisy in ("uvicorn.access", "httpcore", "httpx", "hpack"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, level))
