"""Audit Log Service (TASK-106).

Append-only audit logging for all security-relevant actions.
No UPDATE/DELETE on audit_log entries (except retention cleanup).

Metadata must not contain PII (no email, no content -- only IDs,
counts, and error codes).
"""

from __future__ import annotations

import enum
import logging
import uuid
from typing import Any

from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.audit_log import AuditLog

logger = logging.getLogger("pwbs.audit")


class AuditAction(str, enum.Enum):
    """All auditable domain actions in the PWBS system."""

    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGIN_FAILED = "user.login_failed"
    CONNECTION_CREATED = "connection.created"
    CONNECTION_DELETED = "connection.deleted"
    DATA_INGESTED = "data.ingested"
    BRIEFING_GENERATED = "briefing.generated"
    SEARCH_EXECUTED = "search.executed"
    DATA_EXPORTED = "data.exported"
    USER_DELETED = "user.deleted"


# Keys that must never appear in audit metadata (PII prevention).
_PII_KEYS = frozenset({
    "email", "password", "password_hash", "display_name", "name",
    "content", "body", "text", "token", "access_token", "refresh_token",
    "secret", "api_key", "phone", "address",
})


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Strip PII keys from metadata.  Only IDs, counts, and error codes allowed."""
    if not metadata:
        return {}
    return {k: v for k, v in metadata.items() if k.lower() not in _PII_KEYS}


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from the request (respects X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def log_event(
    db: AsyncSession,
    *,
    action: AuditAction,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an audit log entry.  Never raises -- logs errors instead.

    This is append-only: no UPDATE/DELETE operations are provided.
    The caller is responsible for committing the session.
    """
    safe_metadata = sanitize_metadata(metadata)
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            metadata_=safe_metadata,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        logger.exception(
            "Failed to write audit event action=%s user_id=%s",
            action.value,
            user_id,
        )
