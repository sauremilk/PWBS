"""LLM Gateway Service with Provider Abstraction (TASK-066).

Central abstraction over Claude API (primary) and GPT-4 (fallback).
Implements the request pipeline from D1 §3.4:

  Prompt Assembly → Token Budget Check → Provider Selection →
  API Call with Retry → Response Validation → Cost Logging

Fallback cascade: Claude → GPT-4 → Cached Response → Structured Error.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "LLMGateway",
    "LLMProvider",
    "LLMConfig",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
    "ProviderError",
]


# ------------------------------------------------------------------
# Data types
# ------------------------------------------------------------------


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    CLAUDE = "claude"
    GPT4 = "gpt4"


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Configuration for the LLM Gateway."""

    claude_api_key: str = ""
    openai_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    gpt4_model: str = "gpt-4-turbo"
    default_provider: LLMProvider = LLMProvider.CLAUDE
    max_retries: int = 3
    base_retry_delay: float = 1.0
    default_temperature: float = 0.3
    default_max_tokens: int = 4096


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """A request to the LLM Gateway."""

    system_prompt: str
    user_prompt: str
    temperature: float | None = None
    max_tokens: int | None = None
    model_preference: LLMProvider | None = None
    json_mode: bool = False


@dataclass(frozen=True, slots=True)
class LLMUsage:
    """Token usage and cost information for an LLM call."""

    provider: LLMProvider
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    estimated_cost_usd: float


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Response from the LLM Gateway."""

    content: str
    usage: LLMUsage
    provider: LLMProvider
    model: str
    from_cache: bool = False


class ProviderError(Exception):
    """Raised when all providers in the fallback cascade fail."""

    def __init__(self, message: str, errors: dict[LLMProvider, Exception]) -> None:
        super().__init__(message)
        self.errors = errors


# ------------------------------------------------------------------
# Provider interface
# ------------------------------------------------------------------


class BaseLLMProvider(ABC):
    """Abstract base for LLM provider implementations."""

    @abstractmethod
    async def generate(
        self,
        request: LLMRequest,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        """Generate a completion.

        Returns:
            Tuple of (content, input_tokens, output_tokens).
        """
        ...

    @property
    @abstractmethod
    def provider_type(self) -> LLMProvider: ...


# ------------------------------------------------------------------
# Claude provider
# ------------------------------------------------------------------


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def provider_type(self) -> LLMProvider:
        return LLMProvider.CLAUDE

    async def generate(
        self,
        request: LLMRequest,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        response = await self._client.messages.create(
            model=model or self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=request.system_prompt,
            messages=[{"role": "user", "content": request.user_prompt}],
        )
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text  # type: ignore[union-attr]
                break
        return content, response.usage.input_tokens, response.usage.output_tokens


# ------------------------------------------------------------------
# GPT-4 provider
# ------------------------------------------------------------------


class GPT4Provider(BaseLLMProvider):
    """OpenAI GPT-4 API provider."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def provider_type(self) -> LLMProvider:
        return LLMProvider.GPT4

    async def generate(
        self,
        request: LLMRequest,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int, int]:
        kwargs: dict[str, Any] = {
            "model": model or self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        if request.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "" if response.choices else ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        return content, input_tokens, output_tokens


# ------------------------------------------------------------------
# Cost estimation
# ------------------------------------------------------------------

# Approximate pricing per 1M tokens (USD) as of 2025-Q1
_COST_PER_1M: dict[str, tuple[float, float]] = {
    # (input, output) per 1M tokens
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-3-5-sonnet-20241022": (3.0, 15.0),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-4o": (2.5, 10.0),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_1M.get(model, (5.0, 15.0))  # conservative default
    return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000


# ------------------------------------------------------------------
# Gateway
# ------------------------------------------------------------------


class LLMGateway:
    """Central LLM Gateway with provider routing and fallback cascade.

    Fallback order: Claude → GPT-4 → Cached Response → ProviderError.
    Each provider call uses exponential-backoff retry for transient errors.

    Cost and latency are logged for every successful call.
    """

    def __init__(
        self,
        config: LLMConfig,
        *,
        providers: dict[LLMProvider, BaseLLMProvider] | None = None,
        cache: dict[str, LLMResponse] | None = None,
    ) -> None:
        self._config = config
        self._cache: dict[str, LLMResponse] = cache if cache is not None else {}

        if providers is not None:
            self._providers = providers
        else:
            self._providers = {}
            if config.claude_api_key:
                self._providers[LLMProvider.CLAUDE] = ClaudeProvider(
                    api_key=config.claude_api_key,
                    model=config.claude_model,
                )
            if config.openai_api_key:
                self._providers[LLMProvider.GPT4] = GPT4Provider(
                    api_key=config.openai_api_key,
                    model=config.gpt4_model,
                )

    @property
    def config(self) -> LLMConfig:
        return self._config

    @property
    def available_providers(self) -> list[LLMProvider]:
        return list(self._providers.keys())

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate an LLM response with provider routing and fallback.

        Args:
            request: The LLM request with prompt and configuration.

        Returns:
            :class:`LLMResponse` from the first successful provider.

        Raises:
            ProviderError: If all providers fail and no cached response exists.
        """
        temperature = (
            request.temperature
            if request.temperature is not None
            else self._config.default_temperature
        )
        max_tokens = (
            request.max_tokens
            if request.max_tokens is not None
            else self._config.default_max_tokens
        )

        # Build provider cascade
        cascade = self._build_cascade(request.model_preference)
        errors: dict[LLMProvider, Exception] = {}

        for provider_type in cascade:
            provider = self._providers.get(provider_type)
            if provider is None:
                continue

            model = (
                self._config.claude_model
                if provider_type == LLMProvider.CLAUDE
                else self._config.gpt4_model
            )

            try:
                response = await self._call_with_retry(
                    provider=provider,
                    request=request,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                # Cache successful response
                cache_key = self._cache_key(request)
                self._cache[cache_key] = response

                return response

            except Exception as exc:
                errors[provider_type] = exc
                logger.warning(
                    "Provider %s failed: %s — trying fallback",
                    provider_type.value,
                    exc,
                )

        # Try cache as last resort
        cache_key = self._cache_key(request)
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("All providers failed; returning cached response")
            return LLMResponse(
                content=cached.content,
                usage=cached.usage,
                provider=cached.provider,
                model=cached.model,
                from_cache=True,
            )

        raise ProviderError(
            "All LLM providers failed and no cached response available",
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_cascade(
        self,
        preference: LLMProvider | None,
    ) -> list[LLMProvider]:
        """Build the provider fallback cascade.

        If *preference* is set: preference → other providers.
        Default: Claude → GPT-4.
        """
        default_order = [LLMProvider.CLAUDE, LLMProvider.GPT4]

        if preference is not None:
            rest = [p for p in default_order if p != preference]
            return [preference] + rest

        if self._config.default_provider != LLMProvider.CLAUDE:
            return [self._config.default_provider] + [
                p for p in default_order if p != self._config.default_provider
            ]

        return default_order

    async def _call_with_retry(
        self,
        provider: BaseLLMProvider,
        request: LLMRequest,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Call a provider with exponential-backoff retry."""
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                start = time.monotonic()
                content, input_tokens, output_tokens = await provider.generate(
                    request=request,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                duration_ms = (time.monotonic() - start) * 1000

                usage = LLMUsage(
                    provider=provider.provider_type,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_ms=round(duration_ms, 1),
                    estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
                )

                logger.info(
                    "LLM call: provider=%s model=%s in=%d out=%d duration=%.0fms cost=$%.6f",
                    provider.provider_type.value,
                    model,
                    input_tokens,
                    output_tokens,
                    duration_ms,
                    usage.estimated_cost_usd,
                )

                return LLMResponse(
                    content=content,
                    usage=usage,
                    provider=provider.provider_type,
                    model=model,
                )

            except Exception as exc:
                last_error = exc
                if attempt < self._config.max_retries and self._is_transient(exc):
                    delay = self._config.base_retry_delay * (5**attempt)
                    logger.warning(
                        "LLM %s attempt %d/%d failed (%s) — retrying in %.1fs",
                        provider.provider_type.value,
                        attempt + 1,
                        self._config.max_retries + 1,
                        type(exc).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
                elif not self._is_transient(exc):
                    raise

        assert last_error is not None  # noqa: S101
        raise last_error

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        """Check if an exception is transient (worth retrying)."""
        # Anthropic
        try:
            from anthropic import APIStatusError as AnthropicStatusError
            from anthropic import APITimeoutError as AnthropicTimeout
            from anthropic import RateLimitError as AnthropicRateLimit

            if isinstance(exc, (AnthropicTimeout, AnthropicRateLimit)):
                return True
            if isinstance(exc, AnthropicStatusError) and exc.status_code >= 500:
                return True
        except ImportError:
            pass

        # OpenAI
        try:
            from openai import APIStatusError as OpenAIStatusError
            from openai import APITimeoutError as OpenAITimeout
            from openai import RateLimitError as OpenAIRateLimit

            if isinstance(exc, (OpenAITimeout, OpenAIRateLimit)):
                return True
            if isinstance(exc, OpenAIStatusError) and exc.status_code >= 500:
                return True
        except ImportError:
            pass

        # Generic timeout / connection errors
        if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            return True

        return False

    @staticmethod
    def _cache_key(request: LLMRequest) -> str:
        """Generate a simple cache key from the request prompts."""
        return f"{request.system_prompt}::{request.user_prompt}"
