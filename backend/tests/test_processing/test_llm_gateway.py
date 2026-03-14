"""Tests for pwbs.core.llm_gateway – LLMGateway (TASK-066)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pwbs.core.llm_gateway import (
    BaseLLMProvider,
    LLMConfig,
    LLMGateway,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeProvider(BaseLLMProvider):
    """Fake provider for testing that returns configurable results."""

    def __init__(
        self,
        provider_type: LLMProvider,
        content: str = "test response",
        input_tokens: int = 10,
        output_tokens: int = 20,
        error: Exception | None = None,
        fail_times: int = 0,
    ) -> None:
        self._provider_type = provider_type
        self._content = content
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._error = error
        self._fail_times = fail_times
        self._call_count = 0

    @property
    def provider_type(self) -> LLMProvider:
        return self._provider_type

    @property
    def call_count(self) -> int:
        return self._call_count

    async def generate(
        self,
        request: LLMRequest,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        self._call_count += 1
        if self._error and self._call_count <= self._fail_times:
            raise self._error
        return self._content, self._input_tokens, self._output_tokens


def _make_request(
    system: str = "You are a helper.",
    user: str = "Hello",
    preference: LLMProvider | None = None,
) -> LLMRequest:
    return LLMRequest(
        system_prompt=system,
        user_prompt=user,
        model_preference=preference,
    )


def _make_config(**overrides: object) -> LLMConfig:
    defaults = {
        "claude_api_key": "test-claude-key",
        "openai_api_key": "test-openai-key",
        "max_retries": 2,
        "base_retry_delay": 0.001,  # fast for tests
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)  # type: ignore[arg-type]


def _make_gateway(
    config: LLMConfig | None = None,
    claude: FakeProvider | None = None,
    gpt4: FakeProvider | None = None,
) -> LLMGateway:
    cfg = config or _make_config()
    providers: dict[LLMProvider, BaseLLMProvider] = {}
    if claude is not None:
        providers[LLMProvider.CLAUDE] = claude
    if gpt4 is not None:
        providers[LLMProvider.GPT4] = gpt4
    return LLMGateway(cfg, providers=providers)


# ---------------------------------------------------------------------------
# AC: Claude API (primär) und GPT-4 (Fallback) als Provider implementiert
# ---------------------------------------------------------------------------


class TestProviders:
    @pytest.mark.asyncio
    async def test_claude_primary(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE, content="claude answer")
        gpt4 = FakeProvider(LLMProvider.GPT4, content="gpt4 answer")
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        resp = await gw.generate(_make_request())
        assert resp.content == "claude answer"
        assert resp.provider == LLMProvider.CLAUDE
        assert claude.call_count == 1
        assert gpt4.call_count == 0

    @pytest.mark.asyncio
    async def test_gpt4_used_when_preferred(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE, content="claude")
        gpt4 = FakeProvider(LLMProvider.GPT4, content="gpt4")
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        resp = await gw.generate(_make_request(preference=LLMProvider.GPT4))
        assert resp.content == "gpt4"
        assert resp.provider == LLMProvider.GPT4


# ---------------------------------------------------------------------------
# AC: Fallback-Kaskade
# ---------------------------------------------------------------------------


class TestFallbackCascade:
    @pytest.mark.asyncio
    async def test_fallback_to_gpt4_when_claude_fails(self) -> None:
        claude = FakeProvider(
            LLMProvider.CLAUDE,
            error=ConnectionError("API down"),
            fail_times=999,
        )
        gpt4 = FakeProvider(LLMProvider.GPT4, content="gpt4 fallback")
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        resp = await gw.generate(_make_request())
        assert resp.content == "gpt4 fallback"
        assert resp.provider == LLMProvider.GPT4

    @pytest.mark.asyncio
    async def test_fallback_to_cache_when_all_fail(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE, content="cached")
        gpt4 = FakeProvider(LLMProvider.GPT4)
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        req = _make_request()
        # First call succeeds → caches
        await gw.generate(req)

        # Now make both providers fail
        claude_fail = FakeProvider(
            LLMProvider.CLAUDE,
            error=ConnectionError("down"),
            fail_times=999,
        )
        gpt4_fail = FakeProvider(
            LLMProvider.GPT4,
            error=ConnectionError("down"),
            fail_times=999,
        )
        gw2 = LLMGateway(
            _make_config(),
            providers={
                LLMProvider.CLAUDE: claude_fail,
                LLMProvider.GPT4: gpt4_fail,
            },
            cache=gw._cache,  # share the cache
        )

        resp = await gw2.generate(req)
        assert resp.content == "cached"
        assert resp.from_cache is True

    @pytest.mark.asyncio
    async def test_provider_error_when_all_fail_no_cache(self) -> None:
        claude = FakeProvider(
            LLMProvider.CLAUDE,
            error=ConnectionError("down"),
            fail_times=999,
        )
        gpt4 = FakeProvider(
            LLMProvider.GPT4,
            error=ConnectionError("down"),
            fail_times=999,
        )
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        with pytest.raises(ProviderError) as exc_info:
            await gw.generate(_make_request())

        assert LLMProvider.CLAUDE in exc_info.value.errors
        assert LLMProvider.GPT4 in exc_info.value.errors


# ---------------------------------------------------------------------------
# AC: Retry-Logik mit Exponential Backoff
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_transient_errors(self) -> None:
        claude = FakeProvider(
            LLMProvider.CLAUDE,
            content="success after retry",
            error=ConnectionError("timeout"),
            fail_times=2,  # fail first 2 calls, succeed on 3rd
        )
        gw = _make_gateway(
            config=_make_config(max_retries=3),
            claude=claude,
        )

        resp = await gw.generate(_make_request())
        assert resp.content == "success after retry"
        assert claude.call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_non_transient_error_not_retried(self) -> None:
        """ValueError is not transient — should fail immediately."""
        claude = FakeProvider(
            LLMProvider.CLAUDE,
            error=ValueError("bad input"),
            fail_times=999,
        )
        gpt4 = FakeProvider(LLMProvider.GPT4, content="fallback")
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        resp = await gw.generate(_make_request())
        # Should fallback to GPT4 after non-transient error (no retry)
        assert resp.content == "fallback"
        assert claude.call_count == 1  # only 1 attempt, no retry


# ---------------------------------------------------------------------------
# AC: Cost & Latency Logging
# ---------------------------------------------------------------------------


class TestUsageTracking:
    @pytest.mark.asyncio
    async def test_usage_fields_populated(self) -> None:
        claude = FakeProvider(
            LLMProvider.CLAUDE, input_tokens=100, output_tokens=50
        )
        gw = _make_gateway(claude=claude)

        resp = await gw.generate(_make_request())
        assert resp.usage.input_tokens == 100
        assert resp.usage.output_tokens == 50
        assert resp.usage.provider == LLMProvider.CLAUDE
        assert resp.usage.duration_ms >= 0
        assert resp.usage.estimated_cost_usd >= 0

    @pytest.mark.asyncio
    async def test_model_name_in_response(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE)
        gw = _make_gateway(claude=claude)

        resp = await gw.generate(_make_request())
        assert resp.model == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# AC: Provider Router selektiert anhand model_preference
# ---------------------------------------------------------------------------


class TestProviderRouting:
    @pytest.mark.asyncio
    async def test_preference_claude(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE, content="claude")
        gpt4 = FakeProvider(LLMProvider.GPT4, content="gpt4")
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        resp = await gw.generate(_make_request(preference=LLMProvider.CLAUDE))
        assert resp.provider == LLMProvider.CLAUDE

    @pytest.mark.asyncio
    async def test_preference_gpt4(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE, content="claude")
        gpt4 = FakeProvider(LLMProvider.GPT4, content="gpt4")
        gw = _make_gateway(claude=claude, gpt4=gpt4)

        resp = await gw.generate(_make_request(preference=LLMProvider.GPT4))
        assert resp.provider == LLMProvider.GPT4

    def test_available_providers(self) -> None:
        claude = FakeProvider(LLMProvider.CLAUDE)
        gw = _make_gateway(claude=claude)
        assert LLMProvider.CLAUDE in gw.available_providers


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_temperature(self) -> None:
        config = LLMConfig()
        assert config.default_temperature == 0.3

    def test_default_provider(self) -> None:
        config = LLMConfig()
        assert config.default_provider == LLMProvider.CLAUDE
