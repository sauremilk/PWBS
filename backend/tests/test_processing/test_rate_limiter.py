"""Tests for pwbs.core.rate_limiter  LLMRateLimiter (TASK-070)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from pwbs.core.rate_limiter import (
    CostRecord,
    InMemoryUsageStore,
    LLMRateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
)

_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_USER2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------


class TestConfig:
    def test_defaults(self) -> None:
        cfg = RateLimitConfig()
        assert cfg.max_daily_calls == 100
        assert cfg.max_daily_cost_usd == 5.0
        assert "briefing.morning" in cfg.token_budgets
        assert "search.answer" in cfg.token_budgets
        assert "entity.extraction" in cfg.token_budgets

    def test_custom_values(self) -> None:
        cfg = RateLimitConfig(max_daily_calls=50, max_daily_cost_usd=2.0)
        assert cfg.max_daily_calls == 50


# ---------------------------------------------------------------------------
# TokenBudget
# ---------------------------------------------------------------------------


class TestTokenBudget:
    def test_default_budgets(self) -> None:
        limiter = LLMRateLimiter()
        budget = limiter.get_token_budget("briefing.morning")
        assert budget is not None
        assert budget.max_context_tokens == 8000
        assert budget.max_output_tokens == 2000

    def test_entity_extraction_budget(self) -> None:
        limiter = LLMRateLimiter()
        budget = limiter.get_token_budget("entity.extraction")
        assert budget is not None
        assert budget.max_context_tokens == 2000
        assert budget.model == "claude-haiku"

    def test_unknown_use_case(self) -> None:
        limiter = LLMRateLimiter()
        assert limiter.get_token_budget("unknown") is None


# ---------------------------------------------------------------------------
# Daily call limit
# ---------------------------------------------------------------------------


class TestDailyCallLimit:
    @pytest.mark.asyncio
    async def test_under_limit_passes(self) -> None:
        limiter = LLMRateLimiter(config=RateLimitConfig(max_daily_calls=10))
        # Should not raise
        await limiter.check_limits(_USER, "briefing.morning")

    @pytest.mark.asyncio
    async def test_at_limit_raises(self) -> None:
        store = InMemoryUsageStore()
        cfg = RateLimitConfig(max_daily_calls=3)
        limiter = LLMRateLimiter(config=cfg, store=store)

        # Record 3 calls
        for _ in range(3):
            await limiter.record_usage(_USER, "briefing.morning", "claude", 100, 50, 0.001)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_limits(_USER, "briefing.morning")
        assert exc_info.value.user_id == _USER
        assert "3 calls/day" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_different_users_independent(self) -> None:
        store = InMemoryUsageStore()
        cfg = RateLimitConfig(max_daily_calls=2)
        limiter = LLMRateLimiter(config=cfg, store=store)

        for _ in range(2):
            await limiter.record_usage(_USER, "test", "claude", 100, 50, 0.001)

        # User1 should be blocked
        with pytest.raises(RateLimitExceededError):
            await limiter.check_limits(_USER, "test")

        # User2 should still pass
        await limiter.check_limits(_USER2, "test")


# ---------------------------------------------------------------------------
# Daily cost limit
# ---------------------------------------------------------------------------


class TestDailyCostLimit:
    @pytest.mark.asyncio
    async def test_under_cost_passes(self) -> None:
        cfg = RateLimitConfig(max_daily_cost_usd=10.0)
        limiter = LLMRateLimiter(config=cfg)
        await limiter.check_limits(_USER, "briefing.morning")

    @pytest.mark.asyncio
    async def test_cost_exceeded_raises(self) -> None:
        store = InMemoryUsageStore()
        cfg = RateLimitConfig(max_daily_cost_usd=0.01)
        limiter = LLMRateLimiter(config=cfg, store=store)

        await limiter.record_usage(_USER, "test", "claude", 1000, 500, 0.02)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_limits(_USER, "test")
        assert "cost limit" in exc_info.value.reason.lower()


# ---------------------------------------------------------------------------
# Token budget limits
# ---------------------------------------------------------------------------


class TestTokenBudgetLimits:
    @pytest.mark.asyncio
    async def test_within_budget_passes(self) -> None:
        limiter = LLMRateLimiter()
        await limiter.check_limits(_USER, "briefing.morning", input_tokens=5000)

    @pytest.mark.asyncio
    async def test_exceeds_context_tokens_raises(self) -> None:
        limiter = LLMRateLimiter()
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_limits(_USER, "briefing.morning", input_tokens=9000)
        assert "Input tokens" in exc_info.value.reason
        assert "8000" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_entity_extraction_context_limit(self) -> None:
        limiter = LLMRateLimiter()
        with pytest.raises(RateLimitExceededError):
            await limiter.check_limits(_USER, "entity.extraction", input_tokens=3000)

    @pytest.mark.asyncio
    async def test_unknown_use_case_no_token_check(self) -> None:
        limiter = LLMRateLimiter()
        # Should pass even with huge token count since no budget defined
        await limiter.check_limits(_USER, "custom.task", input_tokens=999999)


# ---------------------------------------------------------------------------
# Record usage
# ---------------------------------------------------------------------------


class TestRecordUsage:
    @pytest.mark.asyncio
    async def test_returns_cost_record(self) -> None:
        limiter = LLMRateLimiter()
        record = await limiter.record_usage(
            _USER,
            "briefing.morning",
            "claude-sonnet-4-20250514",
            500,
            200,
            0.0045,
        )
        assert isinstance(record, CostRecord)
        assert record.user_id == _USER
        assert record.use_case == "briefing.morning"
        assert record.input_tokens == 500
        assert record.output_tokens == 200
        assert record.estimated_cost_usd == 0.0045

    @pytest.mark.asyncio
    async def test_increments_daily_counter(self) -> None:
        store = InMemoryUsageStore()
        limiter = LLMRateLimiter(store=store)

        await limiter.record_usage(_USER, "test", "claude", 100, 50, 0.001)
        await limiter.record_usage(_USER, "test", "claude", 200, 100, 0.002)

        today = datetime.now(UTC).date()
        usage = await store.get_daily_usage(_USER, today)
        assert usage.call_count == 2
        assert usage.total_input_tokens == 300
        assert usage.total_output_tokens == 150
        assert usage.estimated_cost_usd == pytest.approx(0.003)

    @pytest.mark.asyncio
    async def test_timestamp_is_utc(self) -> None:
        limiter = LLMRateLimiter()
        record = await limiter.record_usage(_USER, "test", "claude", 10, 5, 0.0001)
        assert record.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Get remaining
# ---------------------------------------------------------------------------


class TestGetRemaining:
    @pytest.mark.asyncio
    async def test_fresh_user_full_quota(self) -> None:
        cfg = RateLimitConfig(max_daily_calls=100, max_daily_cost_usd=5.0)
        limiter = LLMRateLimiter(config=cfg)
        remaining = await limiter.get_remaining(_USER)
        assert remaining["calls_remaining"] == 100
        assert remaining["cost_remaining_usd"] == 5.0
        assert remaining["calls_used"] == 0

    @pytest.mark.asyncio
    async def test_after_usage(self) -> None:
        cfg = RateLimitConfig(max_daily_calls=10, max_daily_cost_usd=1.0)
        store = InMemoryUsageStore()
        limiter = LLMRateLimiter(config=cfg, store=store)

        await limiter.record_usage(_USER, "test", "claude", 100, 50, 0.3)
        remaining = await limiter.get_remaining(_USER)
        assert remaining["calls_remaining"] == 9
        assert remaining["calls_used"] == 1
        assert remaining["cost_remaining_usd"] == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_fully_exhausted(self) -> None:
        cfg = RateLimitConfig(max_daily_calls=1, max_daily_cost_usd=0.01)
        store = InMemoryUsageStore()
        limiter = LLMRateLimiter(config=cfg, store=store)

        await limiter.record_usage(_USER, "test", "claude", 100, 50, 0.02)
        remaining = await limiter.get_remaining(_USER)
        assert remaining["calls_remaining"] == 0
        assert remaining["cost_remaining_usd"] == 0.0


# ---------------------------------------------------------------------------
# InMemoryUsageStore
# ---------------------------------------------------------------------------


class TestInMemoryStore:
    @pytest.mark.asyncio
    async def test_fresh_user_returns_zero(self) -> None:
        store = InMemoryUsageStore()
        today = datetime.now(UTC).date()
        usage = await store.get_daily_usage(_USER, today)
        assert usage.call_count == 0
        assert usage.estimated_cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_different_days_isolated(self) -> None:
        store = InMemoryUsageStore()
        day1 = date(2026, 3, 14)
        day2 = date(2026, 3, 15)

        await store.increment_usage(_USER, day1, 100, 50, 0.01)
        usage1 = await store.get_daily_usage(_USER, day1)
        usage2 = await store.get_daily_usage(_USER, day2)

        assert usage1.call_count == 1
        assert usage2.call_count == 0

    @pytest.mark.asyncio
    async def test_increment_accumulates(self) -> None:
        store = InMemoryUsageStore()
        today = date(2026, 3, 14)

        await store.increment_usage(_USER, today, 100, 50, 0.01)
        await store.increment_usage(_USER, today, 200, 100, 0.02)

        usage = await store.get_daily_usage(_USER, today)
        assert usage.call_count == 2
        assert usage.total_input_tokens == 300
        assert usage.total_output_tokens == 150
        assert usage.estimated_cost_usd == pytest.approx(0.03)


# ---------------------------------------------------------------------------
# RateLimitExceededError
# ---------------------------------------------------------------------------


class TestRateLimitExceededError:
    def test_attributes(self) -> None:
        err = RateLimitExceededError(_USER, "too many calls")
        assert err.user_id == _USER
        assert err.reason == "too many calls"
        assert str(_USER) in str(err)

    def test_is_pwbs_error(self) -> None:
        from pwbs.core.exceptions import PWBSError

        err = RateLimitExceededError(_USER, "test")
        assert isinstance(err, PWBSError)
