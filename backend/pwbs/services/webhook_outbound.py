"""Outbound Webhook delivery service (TASK-189).

Delivers signed HTTP POST payloads to registered webhook URLs.
Failed deliveries are retried up to 3 times with exponential backoff
(10 s → 30 s → 90 s).

Signature: ``X-PWBS-Signature: sha256=<hex-digest>`` computed via
HMAC-SHA256 over the raw JSON body using the webhook's secret.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

__all__ = [
    "DeliveryResult",
    "deliver_webhook",
    "sign_payload",
]

# Supported event types
SUPPORTED_EVENTS: frozenset[str] = frozenset(
    {
        "briefing.generated",
        "document.ingested",
        "connector.error",
        "connector.synced",
        "export.ready",
    }
)

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 10
_TIMEOUT_SECONDS = 10.0
_MAX_RESPONSE_BODY = 1024  # store at most 1 KiB of response


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Outcome of a single delivery attempt."""

    success: bool
    status_code: int | None
    response_body: str | None
    error_message: str | None
    duration_ms: int
    attempt: int


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute ``sha256=<hex>`` HMAC signature for *payload_bytes*."""
    mac = hmac.new(secret.encode(), payload_bytes, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


async def deliver_webhook(
    url: str,
    secret: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    max_attempts: int = _MAX_ATTEMPTS,
    timeout: float = _TIMEOUT_SECONDS,
) -> list[DeliveryResult]:
    """Deliver a signed payload to *url* with retries.

    Args:
        url: Target webhook URL.
        secret: HMAC secret for signing.
        event_type: The event type header.
        payload: JSON-serialisable body.
        max_attempts: Maximum delivery attempts (default 3).
        timeout: Per-request timeout in seconds.

    Returns:
        List of :class:`DeliveryResult` – one per attempt.
    """
    body = json.dumps(payload, default=str).encode()
    signature = sign_payload(body, secret)
    headers = {
        "Content-Type": "application/json",
        "X-PWBS-Signature": signature,
        "X-PWBS-Event": event_type,
        "User-Agent": "PWBS-Webhook/1.0",
    }

    results: list[DeliveryResult] = []

    for attempt in range(1, max_attempts + 1):
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, content=body, headers=headers)

            duration_ms = int((time.monotonic() - start) * 1000)
            resp_body = resp.text[:_MAX_RESPONSE_BODY] if resp.text else None
            success = 200 <= resp.status_code < 300

            results.append(
                DeliveryResult(
                    success=success,
                    status_code=resp.status_code,
                    response_body=resp_body,
                    error_message=None if success else f"HTTP {resp.status_code}",
                    duration_ms=duration_ms,
                    attempt=attempt,
                )
            )

            if success:
                return results

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            results.append(
                DeliveryResult(
                    success=False,
                    status_code=None,
                    response_body=None,
                    error_message=str(exc)[:256],
                    duration_ms=duration_ms,
                    attempt=attempt,
                )
            )

        if attempt < max_attempts:
            import asyncio

            backoff = _BACKOFF_BASE_SECONDS * (3 ** (attempt - 1))
            logger.info(
                "Webhook delivery attempt %d failed for %s, retrying in %ds",
                attempt,
                url,
                backoff,
            )
            await asyncio.sleep(backoff)

    return results
