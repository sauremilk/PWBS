"""LLM Gateway Retry-Logik mit Exponential Backoff (TASK-071).

Enhanced retry handler for LLM API calls with:
- Exponential backoff: 1 min -> 5 min -> 25 min (factor 5)
- Jitter to avoid thundering herd
- Configurable timeout per call (default 30s)
- Permanent error detection (401, 403) -> immediate switch
- Comprehensive logging of all retry attempts

D1 Section 3.4 (Fallback-Kaskade, Retry), AGENTS.md SchedulerAgent.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

__all__ = [
    "RetryConfig",
    "RetryHandler",
    "RetryResult",
    "RetryExhaustedError",
    "PermanentError",
    "ErrorCategory",
]

T = TypeVar("T")


# ------------------------------------------------------------------
# Error classification
# ------------------------------------------------------------------


class ErrorCategory(str, Enum):
    """Classification of an error for retry decisions."""

    TRANSIENT = "transient"      # 429, 500+, timeout, connection
    PERMANENT = "permanent"      # 401, 403, 404, invalid request
    UNKNOWN = "unknown"          # Unclassified


class PermanentError(Exception):
    """Raised when a permanent error is detected (no retry)."""

    def __init__(self, original: Exception, status_code: int | None = None) -> None:
        self.original = original
        self.status_code = status_code
        super().__init__(f"Permanent error (status={status_code}): {original}")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        attempts: int,
        last_error: Exception,
        duration_ms: float,
    ) -> None:
        self.attempts = attempts
        self.last_error = last_error
        self.duration_ms = duration_ms
        super().__init__(
            f"All {attempts} retry attempts exhausted after {duration_ms:.0f}ms: "
            f"{last_error}"
        )


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for the retry handler.

    Parameters
    ----------
    max_retries:
        Maximum number of retry attempts (3 = initial + 3 retries = 4 total).
    base_delay_seconds:
        Base delay before first retry (60s = 1 minute).
    backoff_factor:
        Multiplier for each subsequent retry (5 = 1m -> 5m -> 25m).
    jitter_fraction:
        Random jitter as fraction of delay (0.1 = +-10%).
    call_timeout_seconds:
        Timeout per individual API call (30s default).
    """

    max_retries: int = 3
    base_delay_seconds: float = 60.0
    backoff_factor: float = 5.0
    jitter_fraction: float = 0.1
    call_timeout_seconds: float = 30.0


# ------------------------------------------------------------------
# Result
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetryResult:
    """Result of a retry-wrapped operation."""

    value: Any
    attempts: int
    total_duration_ms: float
    retried: bool


# ------------------------------------------------------------------
# Handler
# ------------------------------------------------------------------


class RetryHandler:
    """Retry handler with exponential backoff and jitter.

    Classifies errors as transient (retryable) or permanent (immediate fail).
    Logs all retry attempts with delay and error details.

    Parameters
    ----------
    config:
        Retry configuration. Uses safe defaults if None.
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()

    @property
    def config(self) -> RetryConfig:
        """Current retry configuration."""
        return self._config

    async def execute(
        self,
        operation: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> RetryResult:
        """Execute an async operation with retry logic.

        Parameters
        ----------
        operation:
            Async callable to execute.
        *args, **kwargs:
            Arguments passed to the operation.

        Returns
        -------
        RetryResult
            Contains the operation result and retry metadata.

        Raises
        ------
        PermanentError
            If a permanent error (401, 403) is detected.
        RetryExhaustedError
            If all retry attempts are exhausted.
        """
        start = time.monotonic()
        last_error: Exception | None = None
        total_attempts = self._config.max_retries + 1

        for attempt in range(total_attempts):
            try:
                result = await self._call_with_timeout(operation, *args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000

                if attempt > 0:
                    logger.info(
                        "Retry succeeded on attempt %d/%d after %.0fms",
                        attempt + 1,
                        total_attempts,
                        duration_ms,
                    )

                return RetryResult(
                    value=result,
                    attempts=attempt + 1,
                    total_duration_ms=round(duration_ms, 1),
                    retried=attempt > 0,
                )

            except Exception as exc:
                last_error = exc
                category = self.classify_error(exc)

                if category == ErrorCategory.PERMANENT:
                    status = self._extract_status_code(exc)
                    logger.warning(
                        "Permanent error on attempt %d/%d (status=%s): %s",
                        attempt + 1,
                        total_attempts,
                        status,
                        exc,
                    )
                    raise PermanentError(exc, status) from exc

                if attempt < self._config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        "Transient error on attempt %d/%d: %s  retrying in %.1fs",
                        attempt + 1,
                        total_attempts,
                        type(exc).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "All %d retry attempts exhausted: %s",
                        total_attempts,
                        exc,
                    )

        assert last_error is not None  # noqa: S101
        duration_ms = (time.monotonic() - start) * 1000
        raise RetryExhaustedError(total_attempts, last_error, duration_ms)

    # ------------------------------------------------------------------
    # Timeout wrapper
    # ------------------------------------------------------------------

    async def _call_with_timeout(
        self,
        operation: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Call operation with configurable timeout."""
        try:
            return await asyncio.wait_for(
                operation(*args, **kwargs),
                timeout=self._config.call_timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"LLM call timed out after {self._config.call_timeout_seconds}s"
            ) from None

    # ------------------------------------------------------------------
    # Delay calculation
    # ------------------------------------------------------------------

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter.

        attempt=0: base_delay (60s)
        attempt=1: base_delay * factor (300s = 5min)
        attempt=2: base_delay * factor^2 (1500s = 25min)
        """
        base = self._config.base_delay_seconds * (
            self._config.backoff_factor ** attempt
        )
        # Add jitter: +/- jitter_fraction of the base delay
        jitter_range = base * self._config.jitter_fraction
        jitter = random.uniform(-jitter_range, jitter_range)  # noqa: S311
        return max(0.0, base + jitter)

    # ------------------------------------------------------------------
    # Error classification
    # ------------------------------------------------------------------

    @staticmethod
    def classify_error(exc: Exception) -> ErrorCategory:
        """Classify an exception as transient, permanent, or unknown.

        Transient (retryable):
        - HTTP 429 (Rate Limit)
        - HTTP 500+ (Server Error)
        - Timeout errors
        - Connection errors

        Permanent (no retry):
        - HTTP 401 (Unauthorized)
        - HTTP 403 (Forbidden)
        - HTTP 404 (Not Found)
        - HTTP 400 (Bad Request)
        """
        status = RetryHandler._extract_status_code(exc)

        if status is not None:
            if status == 429 or status >= 500:
                return ErrorCategory.TRANSIENT
            if status in (401, 403, 404, 400):
                return ErrorCategory.PERMANENT

        # Check by exception type
        if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            return ErrorCategory.TRANSIENT

        # Anthropic-specific
        try:
            from anthropic import (
                APITimeoutError as AnthropicTimeout,
            )
            from anthropic import (
                AuthenticationError as AnthropicAuth,
            )
            from anthropic import (
                PermissionDeniedError as AnthropicPermission,
            )
            from anthropic import (
                RateLimitError as AnthropicRateLimit,
            )
            if isinstance(exc, (AnthropicTimeout, AnthropicRateLimit)):
                return ErrorCategory.TRANSIENT
            if isinstance(exc, (AnthropicAuth, AnthropicPermission)):
                return ErrorCategory.PERMANENT
        except ImportError:
            pass

        # OpenAI-specific
        try:
            from openai import (
                APITimeoutError as OpenAITimeout,
            )
            from openai import (
                AuthenticationError as OpenAIAuth,
            )
            from openai import (
                PermissionDeniedError as OpenAIPermission,
            )
            from openai import (
                RateLimitError as OpenAIRateLimit,
            )
            if isinstance(exc, (OpenAITimeout, OpenAIRateLimit)):
                return ErrorCategory.TRANSIENT
            if isinstance(exc, (OpenAIAuth, OpenAIPermission)):
                return ErrorCategory.PERMANENT
        except ImportError:
            pass

        return ErrorCategory.UNKNOWN

    @staticmethod
    def _extract_status_code(exc: Exception) -> int | None:
        """Extract HTTP status code from an API exception."""
        # anthropic / openai API errors have .status_code
        status = getattr(exc, "status_code", None)
        if isinstance(status, int):
            return status
        # Some exceptions have .response.status_code
        response = getattr(exc, "response", None)
        if response is not None:
            status = getattr(response, "status_code", None)
            if isinstance(status, int):
                return status
        return None
