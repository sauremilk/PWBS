"""Tests for pwbs.connectors.resilience  CircuitBreaker (TASK-195).

At least 8 scenarios as required by acceptance criteria:
1. success  call succeeds, circuit stays closed
2. retry-success  first call fails, retry succeeds
3. circuit-open  3 consecutive failures open the circuit
4. circuit-open-rejects  open circuit rejects calls immediately
5. half-open-success  after recovery timeout, probe succeeds -> closed
6. half-open-failure  probe fails -> circuit re-opens
7. partial-failure  non-tracked exception passes through
8. reset  force-reset returns circuit to closed
9. backoff-delays  verify exponential backoff timing
10. idempotent-success-reset  success after failures resets counter
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from pwbs.connectors.resilience import CircuitBreaker, CircuitState
from pwbs.core.exceptions import CircuitOpenError, ConnectorError

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_breaker(**kwargs: object) -> CircuitBreaker:
    """Create a breaker with fast retry delays for testing."""
    defaults = {
        "name": "test",
        "failure_threshold": 3,
        "recovery_timeout": 0.1,  # 100ms for fast tests
        "retry_delays": (0.0, 0.0, 0.0),  # No actual waiting
        "exc_types": (ConnectorError,),
    }
    defaults.update(kwargs)
    return CircuitBreaker(**defaults)  # type: ignore[arg-type]


async def _success_func() -> str:
    return "ok"


async def _fail_func() -> str:
    raise ConnectorError("API error", code="TEST_ERROR")


# ---------------------------------------------------------------------------
# 1. Success  circuit stays closed
# ---------------------------------------------------------------------------


class TestSuccessCall:
    async def test_success_returns_result(self) -> None:
        cb = _make_breaker()
        result = await cb.call(_success_func)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_multiple_successes_keep_closed(self) -> None:
        cb = _make_breaker()
        for _ in range(5):
            result = await cb.call(_success_func)
            assert result == "ok"
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# 2. Retry-success  first fails, retry succeeds
# ---------------------------------------------------------------------------


class TestRetrySuccess:
    async def test_retry_then_success(self) -> None:
        call_count = 0

        async def _flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectorError("transient", code="TRANSIENT")
            return "recovered"

        cb = _make_breaker()
        result = await cb.call(_flaky)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert call_count == 3


# ---------------------------------------------------------------------------
# 3. Circuit-open  3 consecutive failures open circuit
# ---------------------------------------------------------------------------


class TestCircuitOpen:
    async def test_opens_after_threshold_failures(self) -> None:
        cb = _make_breaker()
        with pytest.raises((ConnectorError, CircuitOpenError)):
            await cb.call(_fail_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count >= 3

    async def test_failure_count_tracks_consecutive(self) -> None:
        cb = _make_breaker(retry_delays=())  # no retries
        # Each call is one attempt
        for _ in range(2):
            with pytest.raises(ConnectorError):
                await cb.call(_fail_func)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 2

        with pytest.raises((ConnectorError, CircuitOpenError)):
            await cb.call(_fail_func)
        assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# 4. Open circuit rejects immediately
# ---------------------------------------------------------------------------


class TestCircuitOpenRejects:
    async def test_open_circuit_raises_immediately(self) -> None:
        cb = _make_breaker()
        # Force open
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        call_count = 0

        async def _should_not_be_called() -> str:
            nonlocal call_count
            call_count += 1
            return "should not reach"

        with pytest.raises(CircuitOpenError):
            await cb.call(_should_not_be_called)

        assert call_count == 0, "Function should not be called when circuit is open"


# ---------------------------------------------------------------------------
# 5. Half-open success  probe succeeds, circuit closes
# ---------------------------------------------------------------------------


class TestHalfOpenSuccess:
    async def test_probe_success_closes_circuit(self) -> None:
        cb = _make_breaker(recovery_timeout=0.05)  # 50ms
        # Open the circuit
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

        # Probe succeeds
        result = await cb.call(_success_func)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# 6. Half-open failure  probe fails, circuit re-opens
# ---------------------------------------------------------------------------


class TestHalfOpenFailure:
    async def test_probe_failure_reopens_circuit(self) -> None:
        cb = _make_breaker(recovery_timeout=0.05)
        # Open the circuit
        for _ in range(3):
            cb.record_failure()

        # Wait for recovery
        await asyncio.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

        # Probe fails
        with pytest.raises(CircuitOpenError):
            await cb.call(_fail_func)

        assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# 7. Non-tracked exception passes through
# ---------------------------------------------------------------------------


class TestNonTrackedExceptions:
    async def test_non_tracked_exception_passes_through(self) -> None:
        cb = _make_breaker(exc_types=(ConnectorError,))

        async def _value_error() -> str:
            raise ValueError("not a connector error")

        with pytest.raises(ValueError, match="not a connector error"):
            await cb.call(_value_error)

        # Circuit should still be closed  non-tracked errors don't trip it
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# 8. Reset  force-reset returns circuit to closed
# ---------------------------------------------------------------------------


class TestReset:
    async def test_reset_clears_state(self) -> None:
        cb = _make_breaker()
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

        # Should work again
        result = await cb.call(_success_func)
        assert result == "ok"


# ---------------------------------------------------------------------------
# 9. Exponential backoff timing
# ---------------------------------------------------------------------------


class TestBackoffDelays:
    async def test_retry_delays_are_applied(self) -> None:
        sleep_durations: list[float] = []
        original_sleep = asyncio.sleep

        async def _mock_sleep(duration: float) -> None:
            sleep_durations.append(duration)

        cb = CircuitBreaker(
            name="backoff-test",
            failure_threshold=10,  # high threshold so we see all retries
            recovery_timeout=1800.0,
            retry_delays=(60.0, 300.0, 1500.0),
            exc_types=(ConnectorError,),
        )

        with patch("pwbs.connectors.resilience.asyncio.sleep", side_effect=_mock_sleep):
            with pytest.raises(ConnectorError):
                await cb.call(_fail_func)

        # Should have slept 3 times (one per retry_delay)
        assert sleep_durations == [60.0, 300.0, 1500.0]


# ---------------------------------------------------------------------------
# 10. Success after failures resets counter
# ---------------------------------------------------------------------------


class TestSuccessResetsCounter:
    async def test_success_resets_failure_count(self) -> None:
        cb = _make_breaker(retry_delays=())
        # Record 2 failures (below threshold)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        # Success resets
        result = await cb.call(_success_func)
        assert result == "ok"
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# 11. Partial failure  successful docs persist, cursor at last success
# ---------------------------------------------------------------------------


class TestPartialFailure:
    async def test_partial_batch_failure(self) -> None:
        """Simulate a batch of 10 docs where doc 7 fails.

        Documents 1-6 should be 'persisted' (accumulated) and only
        that partial result returned. This tests the pattern where
        the caller catches the error and keeps partial results.
        """
        processed: list[int] = []

        async def _process_batch(docs: list[int]) -> list[int]:
            results = []
            for doc in docs:
                if doc == 7:
                    raise ConnectorError(
                        f"Failed processing doc {doc}",
                        code="DOC_ERROR",
                    )
                results.append(doc)
                processed.append(doc)
            return results

        cb = _make_breaker(retry_delays=())  # no retries for this test

        docs = list(range(1, 11))  # docs 1-10

        # The caller handles partial failure by processing one at a time
        successful: list[int] = []
        cursor_position = 0

        for i, doc_id in enumerate(docs):
            try:
                result = await cb.call(_process_batch, [doc_id])
                successful.extend(result)
                cursor_position = i + 1
            except ConnectorError:
                break

        assert successful == [1, 2, 3, 4, 5, 6]
        assert cursor_position == 6
