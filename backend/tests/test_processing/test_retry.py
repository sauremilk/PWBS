"""Tests for RetryHandler (TASK-071)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.core.retry import (
    ErrorCategory,
    PermanentError,
    RetryConfig,
    RetryExhaustedError,
    RetryHandler,
    RetryResult,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


class FakeAPIError(Exception):
    """Fake API error with status_code."""

    def __init__(self, status_code: int, message: str = "error") -> None:
        self.status_code = status_code
        super().__init__(message)


def _make_failing_fn(
    fail_times: int,
    error: Exception,
    result: str = "success",
):
    """Create an async fn that fails N times then succeeds."""
    call_count = 0

    async def fn():
        nonlocal call_count
        call_count += 1
        if call_count <= fail_times:
            raise error
        return result

    return fn


# ------------------------------------------------------------------
# RetryConfig
# ------------------------------------------------------------------


class TestRetryConfig:
    """Tests for retry configuration."""

    def test_defaults(self) -> None:
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.base_delay_seconds == 60.0
        assert cfg.backoff_factor == 5.0
        assert cfg.jitter_fraction == 0.1
        assert cfg.call_timeout_seconds == 30.0

    def test_custom(self) -> None:
        cfg = RetryConfig(
            max_retries=5,
            base_delay_seconds=10.0,
            backoff_factor=2.0,
            jitter_fraction=0.0,
            call_timeout_seconds=60.0,
        )
        assert cfg.max_retries == 5
        assert cfg.base_delay_seconds == 10.0


# ------------------------------------------------------------------
# Delay Calculation
# ------------------------------------------------------------------


class TestDelayCalculation:
    """Tests for exponential backoff delay calculation."""

    def test_first_retry_base_delay(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                base_delay_seconds=60.0,
                backoff_factor=5.0,
                jitter_fraction=0.0,
            )
        )
        delay = handler._calculate_delay(0)
        assert delay == 60.0

    def test_second_retry_5x(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                base_delay_seconds=60.0,
                backoff_factor=5.0,
                jitter_fraction=0.0,
            )
        )
        delay = handler._calculate_delay(1)
        assert delay == 300.0  # 5 min

    def test_third_retry_25x(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                base_delay_seconds=60.0,
                backoff_factor=5.0,
                jitter_fraction=0.0,
            )
        )
        delay = handler._calculate_delay(2)
        assert delay == 1500.0  # 25 min

    def test_jitter_within_range(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                base_delay_seconds=60.0,
                backoff_factor=5.0,
                jitter_fraction=0.1,
            )
        )
        delays = [handler._calculate_delay(0) for _ in range(100)]
        assert all(54.0 <= d <= 66.0 for d in delays)

    def test_no_negative_delay(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                base_delay_seconds=0.01,
                jitter_fraction=0.5,
            )
        )
        delays = [handler._calculate_delay(0) for _ in range(100)]
        assert all(d >= 0.0 for d in delays)


# ------------------------------------------------------------------
# Error Classification
# ------------------------------------------------------------------


class TestErrorClassification:
    """Tests for error classification."""

    def test_429_is_transient(self) -> None:
        exc = FakeAPIError(429)
        assert RetryHandler.classify_error(exc) == ErrorCategory.TRANSIENT

    def test_500_is_transient(self) -> None:
        exc = FakeAPIError(500)
        assert RetryHandler.classify_error(exc) == ErrorCategory.TRANSIENT

    def test_502_is_transient(self) -> None:
        exc = FakeAPIError(502)
        assert RetryHandler.classify_error(exc) == ErrorCategory.TRANSIENT

    def test_503_is_transient(self) -> None:
        exc = FakeAPIError(503)
        assert RetryHandler.classify_error(exc) == ErrorCategory.TRANSIENT

    def test_401_is_permanent(self) -> None:
        exc = FakeAPIError(401)
        assert RetryHandler.classify_error(exc) == ErrorCategory.PERMANENT

    def test_403_is_permanent(self) -> None:
        exc = FakeAPIError(403)
        assert RetryHandler.classify_error(exc) == ErrorCategory.PERMANENT

    def test_404_is_permanent(self) -> None:
        exc = FakeAPIError(404)
        assert RetryHandler.classify_error(exc) == ErrorCategory.PERMANENT

    def test_400_is_permanent(self) -> None:
        exc = FakeAPIError(400)
        assert RetryHandler.classify_error(exc) == ErrorCategory.PERMANENT

    def test_timeout_is_transient(self) -> None:
        assert RetryHandler.classify_error(TimeoutError()) == ErrorCategory.TRANSIENT

    def test_connection_error_is_transient(self) -> None:
        assert RetryHandler.classify_error(ConnectionError()) == ErrorCategory.TRANSIENT

    def test_os_error_is_transient(self) -> None:
        assert RetryHandler.classify_error(OSError()) == ErrorCategory.TRANSIENT

    def test_unknown_error(self) -> None:
        assert RetryHandler.classify_error(ValueError("bad")) == ErrorCategory.UNKNOWN


# ------------------------------------------------------------------
# Status Code Extraction
# ------------------------------------------------------------------


class TestStatusCodeExtraction:
    """Tests for _extract_status_code."""

    def test_direct_attribute(self) -> None:
        exc = FakeAPIError(429)
        assert RetryHandler._extract_status_code(exc) == 429

    def test_response_attribute(self) -> None:
        exc = Exception("error")
        exc.response = MagicMock()
        exc.response.status_code = 503
        assert RetryHandler._extract_status_code(exc) == 503

    def test_no_status_code(self) -> None:
        assert RetryHandler._extract_status_code(ValueError("x")) is None


# ------------------------------------------------------------------
# Execute - Success
# ------------------------------------------------------------------


class TestExecuteSuccess:
    """Tests for successful execution."""

    @pytest.mark.asyncio
    async def test_immediate_success(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                base_delay_seconds=0.01,
                jitter_fraction=0.0,
            )
        )
        fn = AsyncMock(return_value="ok")

        result = await handler.execute(fn)

        assert result.value == "ok"
        assert result.attempts == 1
        assert result.retried is False
        fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_after_retries(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                max_retries=3,
                base_delay_seconds=0.001,
                jitter_fraction=0.0,
            )
        )
        fn = _make_failing_fn(2, ConnectionError("fail"))

        result = await handler.execute(fn)

        assert result.value == "success"
        assert result.attempts == 3
        assert result.retried is True

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self) -> None:
        handler = RetryHandler(RetryConfig(base_delay_seconds=0.001))
        fn = AsyncMock(return_value="result")

        await handler.execute(fn, "arg1", key="val")

        fn.assert_called_once_with("arg1", key="val")


# ------------------------------------------------------------------
# Execute - Permanent Errors
# ------------------------------------------------------------------


class TestExecutePermanent:
    """Tests for permanent error handling."""

    @pytest.mark.asyncio
    async def test_401_raises_immediately(self) -> None:
        handler = RetryHandler(RetryConfig(base_delay_seconds=0.001))
        fn = AsyncMock(side_effect=FakeAPIError(401, "unauthorized"))

        with pytest.raises(PermanentError) as exc_info:
            await handler.execute(fn)

        assert exc_info.value.status_code == 401
        fn.assert_called_once()  # No retries

    @pytest.mark.asyncio
    async def test_403_raises_immediately(self) -> None:
        handler = RetryHandler(RetryConfig(base_delay_seconds=0.001))
        fn = AsyncMock(side_effect=FakeAPIError(403, "forbidden"))

        with pytest.raises(PermanentError):
            await handler.execute(fn)

        fn.assert_called_once()


# ------------------------------------------------------------------
# Execute - Exhausted Retries
# ------------------------------------------------------------------


class TestExecuteExhausted:
    """Tests for retry exhaustion."""

    @pytest.mark.asyncio
    async def test_exhausted_raises(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                max_retries=2,
                base_delay_seconds=0.001,
                jitter_fraction=0.0,
            )
        )
        fn = AsyncMock(side_effect=ConnectionError("down"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.execute(fn)

        assert exc_info.value.attempts == 3  # 1 initial + 2 retries
        assert fn.call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_carries_last_error(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                max_retries=1,
                base_delay_seconds=0.001,
                jitter_fraction=0.0,
            )
        )
        err = FakeAPIError(500, "server error")
        fn = AsyncMock(side_effect=err)

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.execute(fn)

        assert exc_info.value.last_error is err


# ------------------------------------------------------------------
# Timeout
# ------------------------------------------------------------------


class TestTimeout:
    """Tests for per-call timeout."""

    @pytest.mark.asyncio
    async def test_timeout_triggers(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                max_retries=0,
                call_timeout_seconds=0.05,
            )
        )

        async def slow_fn():
            await asyncio.sleep(10)

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.execute(slow_fn)

        # The timeout converts to a TimeoutError which is transient
        assert isinstance(exc_info.value.last_error, TimeoutError)

    @pytest.mark.asyncio
    async def test_timeout_retried_as_transient(self) -> None:
        handler = RetryHandler(
            RetryConfig(
                max_retries=1,
                call_timeout_seconds=0.05,
                base_delay_seconds=0.001,
                jitter_fraction=0.0,
            )
        )
        call_count = 0

        async def sometimes_slow():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(10)  # timeout
            return "fast"

        result = await handler.execute(sometimes_slow)

        assert result.value == "fast"
        assert result.attempts == 2
        assert call_count == 2


# ------------------------------------------------------------------
# RetryResult
# ------------------------------------------------------------------


class TestRetryResult:
    """Tests for RetryResult dataclass."""

    def test_frozen(self) -> None:
        r = RetryResult(value="x", attempts=1, total_duration_ms=100.0, retried=False)
        with pytest.raises(AttributeError):
            r.value = "y"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = RetryResult(value=42, attempts=3, total_duration_ms=5000.0, retried=True)
        assert r.value == 42
        assert r.attempts == 3
        assert r.retried is True


# ------------------------------------------------------------------
# PermanentError
# ------------------------------------------------------------------


class TestPermanentError:
    """Tests for PermanentError."""

    def test_carries_original(self) -> None:
        orig = FakeAPIError(401)
        pe = PermanentError(orig, 401)
        assert pe.original is orig
        assert pe.status_code == 401

    def test_str(self) -> None:
        pe = PermanentError(ValueError("bad"), None)
        assert "Permanent error" in str(pe)
