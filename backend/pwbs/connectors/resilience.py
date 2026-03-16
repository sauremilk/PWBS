"""Circuit Breaker for connector API resilience (TASK-195).

Provides a ``CircuitBreaker`` that wraps async callables with three-state
fault tolerance:

- **closed**: Normal operation. Failures increment a counter.
- **open**: All calls are immediately rejected with ``CircuitOpenError``.
  Transitions to half-open after ``recovery_timeout`` seconds.
- **half_open**: One probe call is allowed. On success -> closed.
  On failure -> open (timer resets).

Exponential backoff delays (1 min -> 5 min -> 25 min) are applied between
retries before the circuit opens.  After ``failure_threshold`` consecutive
failures the circuit opens for ``recovery_timeout`` seconds (default 30 min).

State is kept in-memory for the MVP.  Redis-backed state follows in Phase 3.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from pwbs.core.exceptions import CircuitOpenError

logger = logging.getLogger(__name__)

__all__ = [
    "CircuitBreaker",
    "CircuitState",
]

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """In-memory circuit breaker for connector API calls.

    Parameters
    ----------
    name:
        Human-readable identifier (e.g. connector name) for logging.
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds the circuit stays open before transitioning to half-open.
    retry_delays:
        Exponential backoff delays (seconds) applied before each retry
        within the closed state.  Length determines max retries.
    exc_types:
        Exception types that count as failures.  Defaults to all
        ``Exception`` subclasses.  Narrowing this allows certain
        errors (e.g. validation) to pass through without tripping
        the breaker.
    """

    def __init__(
        self,
        name: str = "default",
        *,
        failure_threshold: int = 3,
        recovery_timeout: float = 1800.0,
        retry_delays: tuple[float, ...] = (60.0, 300.0, 1500.0),
        exc_types: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._retry_delays = retry_delays
        self._exc_types = exc_types

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._opened_at: float = 0.0

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current state, accounting for automatic open -> half-open transition."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit '%s' transitioned to HALF_OPEN after %.0fs recovery timeout",
                    self._name,
                    self._recovery_timeout,
                )
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def name(self) -> str:
        return self._name

    # ------------------------------------------------------------------
    # Core call wrapper
    # ------------------------------------------------------------------

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute *func* through the circuit breaker.

        In **closed** state, retries with exponential backoff on tracked
        exception types.  After ``failure_threshold`` consecutive failures
        the circuit opens.

        In **open** state, raises ``CircuitOpenError`` immediately.

        In **half_open** state, allows exactly one probe call.
        Success -> closed.  Failure -> open.

        Returns the result of *func* on success.
        """
        current = self.state

        if current == CircuitState.OPEN:
            recovery_at = self._opened_at + self._recovery_timeout
            raise CircuitOpenError(
                f"Circuit '{self._name}' is OPEN (recovery in "
                f"{recovery_at - time.monotonic():.0f}s)",
                recovery_at=recovery_at,
            )

        if current == CircuitState.HALF_OPEN:
            return await self._probe_call(func, *args, **kwargs)

        # CLOSED state: call with retry
        return await self._closed_call(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def record_success(self) -> None:
        """Record a successful call.  Resets failure count and closes circuit."""
        self._failure_count = 0
        if self._state != CircuitState.CLOSED:
            logger.info("Circuit '%s' closed after successful call", self._name)
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call.  May open the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self._failure_threshold:
            self._open_circuit()

    def reset(self) -> None:
        """Force-reset the circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_circuit(self) -> None:
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        logger.warning(
            "Circuit '%s' OPENED after %d consecutive failures. "
            "Recovery in %.0fs.",
            self._name,
            self._failure_count,
            self._recovery_timeout,
        )

    async def _closed_call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute with retry in CLOSED state."""
        max_attempts = len(self._retry_delays) + 1
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except self._exc_types as exc:
                last_error = exc
                self.record_failure()

                if self._state == CircuitState.OPEN:
                    # Circuit just opened -- stop retrying
                    raise CircuitOpenError(
                        f"Circuit '{self._name}' opened after {self._failure_count} failures",
                        recovery_at=self._opened_at + self._recovery_timeout,
                    ) from exc

                if attempt < len(self._retry_delays):
                    delay = self._retry_delays[attempt]
                    logger.warning(
                        "Circuit '%s' call failed (attempt %d/%d), "
                        "retrying in %.0fs: %s",
                        self._name,
                        attempt + 1,
                        max_attempts,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
            except Exception:
                # Non-tracked exceptions pass through without affecting circuit
                raise

        # All retries exhausted -- circuit should be open now
        assert last_error is not None
        raise last_error

    async def _probe_call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute a single probe call in HALF_OPEN state."""
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            logger.info(
                "Circuit '%s' probe succeeded -- transitioning to CLOSED",
                self._name,
            )
            return result
        except self._exc_types as exc:
            self._failure_count += 1
            self._open_circuit()
            raise CircuitOpenError(
                f"Circuit '{self._name}' probe failed -- re-opening circuit",
                recovery_at=self._opened_at + self._recovery_timeout,
            ) from exc