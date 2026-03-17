"""PostHog product analytics integration (LAUNCH-ANA-001).

Initialises the PostHog Python SDK for server-side event tracking.
IP anonymisation is enabled by default for DSGVO compliance.

The SDK is only initialised when ``POSTHOG_API_KEY`` is set to a non-empty value.
"""

from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)

_client: object | None = None


def _pseudonymise(user_id: str) -> str:
    """SHA-256 prefix so PostHog can group by user without storing raw UUIDs."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def init_posthog(api_key: str, host: str = "http://localhost:8200") -> None:
    """Initialise PostHog SDK if *api_key* is non-empty.

    Call once at application startup (in ``create_app``).
    """
    global _client

    if not api_key:
        logger.info("POSTHOG_API_KEY not set -- PostHog analytics disabled")
        return

    try:
        from posthog import Posthog
    except ImportError:
        logger.warning(
            "posthog package not installed -- skipping PostHog initialisation. "
            "Install with: pip install posthog"
        )
        return

    _client = Posthog(api_key, host=host)
    logger.info("PostHog initialised (host=%s)", host)


def capture(
    user_id: str,
    event: str,
    properties: dict[str, object] | None = None,
) -> None:
    """Send an analytics event to PostHog.

    ``user_id`` is pseudonymised before sending.  No-op if PostHog is disabled.
    """
    if _client is None:
        return

    _client.capture(  # type: ignore[union-attr]
        distinct_id=_pseudonymise(user_id),
        event=event,
        properties=properties or {},
    )


def shutdown() -> None:
    """Flush pending events and shut down the PostHog client."""
    if _client is None:
        return
    _client.shutdown()  # type: ignore[union-attr]
    logger.info("PostHog client shut down")
