"""Per-user rate limiting and cost control for the LLM Gateway (TASK-070).

Provides:

- **Token budget limits** per use-case (briefing, search, entity extraction)
- **Daily call limits** (max 100 LLM-extraction calls per user/day)
- **Daily cost tracking** per user
- **Automatic daily reset** of counters

Counter storage: PostgreSQL in MVP, Redis in Phase 3.
Storage is abstracted via the `UsageStore` protocol.

D1 Section 3.4, D1 Section 3.2 (100 extraction calls/user/day).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

from pwbs.core.exceptions import PWBSError

logger = logging.getLogger(__name__)

__all__ = [
    "CostRecord",
    "DailyUsage",
    "LLMRateLimiter",
    "RateLimitConfig",
    "RateLimitExceededError",
    "TokenBudget",
    "UsageStore",
]


# ------------------------------------------------------------------
# Errors
# ------------------------------------------------------------------


class RateLimitExceededError(PWBSError):
    """Raised when a user exceeds their daily LLM usage limit."""

    def __init__(self, user_id: uuid.UUID, reason: str) -> None:
        self.user_id = user_id
        self.reason = reason
        super().__init__(f"Rate limit exceeded for user {user_id}: {reason}")


# ------------------------------------------------------------------
# Token budgets (D1 Section 3.4)
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenBudget:
    """Token limits for a specific use-case."""

    use_case: str
    max_context_tokens: int
    max_output_tokens: int
    model: str = "claude-sonnet-4-20250514"


# Default budgets from D1 Section 3.4
DEFAULT_TOKEN_BUDGETS: dict[str, TokenBudget] = {
    "briefing.morning": TokenBudget(
        use_case="briefing.morning",
        max_context_tokens=8000,
        max_output_tokens=2000,
    ),
    "search.answer": TokenBudget(
        use_case="search.answer",
        max_context_tokens=6000,
        max_output_tokens=1500,
    ),
    "entity.extraction": TokenBudget(
        use_case="entity.extraction",
        max_context_tokens=2000,
        max_output_tokens=1000,
        model="claude-haiku",
    ),
}


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Configuration for the LLM rate limiter.

    Parameters
    ----------
    max_daily_calls:
        Maximum LLM calls per user per day.
    max_daily_cost_usd:
        Maximum estimated cost per user per day (USD).
    token_budgets:
        Per-use-case token budgets.
    """

    max_daily_calls: int = 100
    max_daily_cost_usd: float = 5.0
    token_budgets: dict[str, TokenBudget] = field(
        default_factory=lambda: dict(DEFAULT_TOKEN_BUDGETS),
    )


# ------------------------------------------------------------------
# Usage data
# ------------------------------------------------------------------


@dataclass(slots=True)
class DailyUsage:
    """Tracks a user's daily LLM usage."""

    user_id: uuid.UUID
    date: date
    call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class CostRecord:
    """A single LLM call cost record for audit logging."""

    user_id: uuid.UUID
    use_case: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    timestamp: datetime


# ------------------------------------------------------------------
# Storage protocol
# ------------------------------------------------------------------


class UsageStore(Protocol):
    """Protocol for persisting daily usage counters.

    MVP: PostgreSQL implementation.
    Phase 3: Redis with automatic TTL.
    """

    async def get_daily_usage(
        self,
        user_id: uuid.UUID,
        day: date,
    ) -> DailyUsage: ...

    async def increment_usage(
        self,
        user_id: uuid.UUID,
        day: date,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> DailyUsage: ...


# ------------------------------------------------------------------
# In-memory store (MVP default)
# ------------------------------------------------------------------


class InMemoryUsageStore:
    """Simple in-memory usage store for MVP / testing."""

    def __init__(self) -> None:
        self._data: dict[tuple[uuid.UUID, date], DailyUsage] = {}

    async def get_daily_usage(
        self,
        user_id: uuid.UUID,
        day: date,
    ) -> DailyUsage:
        key = (user_id, day)
        if key not in self._data:
            self._data[key] = DailyUsage(user_id=user_id, date=day)
        return self._data[key]

    async def increment_usage(
        self,
        user_id: uuid.UUID,
        day: date,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> DailyUsage:
        usage = await self.get_daily_usage(user_id, day)
        usage.call_count += 1
        usage.total_input_tokens += input_tokens
        usage.total_output_tokens += output_tokens
        usage.estimated_cost_usd += cost_usd
        return usage


# ------------------------------------------------------------------
# Rate Limiter
# ------------------------------------------------------------------


class LLMRateLimiter:
    """Per-user rate limiting and cost control for LLM calls.

    Parameters
    ----------
    config:
        Rate limit configuration.
    store:
        Usage counter store. Defaults to in-memory.
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        store: UsageStore | None = None,
    ) -> None:
        self._config = config or RateLimitConfig()
        self._store = store or InMemoryUsageStore()

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    def get_token_budget(self, use_case: str) -> TokenBudget | None:
        """Get the token budget for a use-case, or None if unconstrained."""
        return self._config.token_budgets.get(use_case)

    async def check_limits(
        self,
        user_id: uuid.UUID,
        use_case: str,
        input_tokens: int = 0,
    ) -> None:
        """Check whether a user may make an LLM call.

        Parameters
        ----------
        user_id:
            The requesting user.
        use_case:
            The use-case key (e.g. `'briefing.morning'`).
        input_tokens:
            Number of context/input tokens for the upcoming call.

        Raises
        ------
        RateLimitExceededError
            If any limit is exceeded.
        """
        today = datetime.now(UTC).date()
        usage = await self._store.get_daily_usage(user_id, today)

        # 1. Daily call limit
        if usage.call_count >= self._config.max_daily_calls:
            raise RateLimitExceededError(
                user_id,
                f"Daily call limit reached ({self._config.max_daily_calls} calls/day). "
                f"Current: {usage.call_count}.",
            )

        # 2. Daily cost cap
        if usage.estimated_cost_usd >= self._config.max_daily_cost_usd:
            raise RateLimitExceededError(
                user_id,
                "Daily cost limit reached (/day). Current: .",
            )

        # 3. Token budget for use-case
        budget = self._config.token_budgets.get(use_case)
        if budget and input_tokens > budget.max_context_tokens:
            raise RateLimitExceededError(
                user_id,
                f"Input tokens ({input_tokens}) exceed budget for '{use_case}' "
                f"(max: {budget.max_context_tokens}).",
            )

    async def record_usage(
        self,
        user_id: uuid.UUID,
        use_case: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
    ) -> CostRecord:
        """Record a completed LLM call and return a cost record.

        Parameters
        ----------
        user_id:
            The user who made the call.
        use_case:
            The use-case key.
        model:
            The LLM model used.
        input_tokens:
            Input/prompt tokens consumed.
        output_tokens:
            Output/completion tokens consumed.
        estimated_cost_usd:
            Estimated cost in USD.

        Returns
        -------
        CostRecord
            The logged cost record.
        """
        today = datetime.now(UTC).date()
        usage = await self._store.increment_usage(
            user_id,
            today,
            input_tokens,
            output_tokens,
            estimated_cost_usd,
        )

        record = CostRecord(
            user_id=user_id,
            use_case=use_case,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            timestamp=datetime.now(UTC),
        )

        logger.info(
            "LLM usage recorded: user=%s case=%s model=%s"
            " in=%d out=%d cost=$%.4f daily_total=$%.4f calls=%d",
            user_id,
            use_case,
            model,
            input_tokens,
            output_tokens,
            estimated_cost_usd,
            usage.estimated_cost_usd,
            usage.call_count,
        )

        return record

    async def get_remaining(
        self,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get remaining daily limits for a user.

        Returns
        -------
        dict
            Keys: `calls_remaining`, `cost_remaining_usd`.
        """
        today = datetime.now(UTC).date()
        usage = await self._store.get_daily_usage(user_id, today)

        return {
            "calls_remaining": max(0, self._config.max_daily_calls - usage.call_count),
            "cost_remaining_usd": max(
                0.0,
                self._config.max_daily_cost_usd - usage.estimated_cost_usd,
            ),
            "calls_used": usage.call_count,
            "cost_used_usd": round(usage.estimated_cost_usd, 4),
        }
