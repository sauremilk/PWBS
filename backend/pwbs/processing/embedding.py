"""Embedding Generator for the PWBS Processing Pipeline (TASK-058).

Generates vector embeddings for document chunks using the OpenAI
``text-embedding-3-small`` API (1536 dimensions).  Supports batch
processing (max 64 chunks per API call) with exponential-backoff retry
for transient errors (429, 500, timeout).

The embedding model is configurable — only ``text-embedding-3-small`` is
used in the MVP; local models (Sentence Transformers) follow in Phase 3.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from openai import (
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from pwbs.processing.chunking import TextChunk

logger = logging.getLogger(__name__)

__all__ = [
    "EmbeddingConfig",
    "EmbeddingResult",
    "EmbeddingService",
]


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Configuration for the embedding service.

    Defaults from D1 §3.2: text-embedding-3-small, 1536 dimensions,
    batch size 64, per-input limit 8191 tokens.
    """

    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    max_batch_size: int = 64
    max_tokens_per_input: int = 8191
    max_retries: int = 3
    base_retry_delay: float = 1.0  # seconds; scales as base × 5^attempt


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Result of embedding a single chunk."""

    chunk_index: int
    embedding: list[float]
    token_count: int


class EmbeddingService:
    """Generates vector embeddings for :class:`TextChunk` objects.

    Chunks are sent to the OpenAI Embedding API in batches of up to
    ``max_batch_size`` (default 64).  Transient API errors (rate-limit,
    server errors, timeouts) are retried with exponential backoff.
    """

    def __init__(
        self,
        api_key: str,
        config: EmbeddingConfig | None = None,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._config = config or EmbeddingConfig()
        self._client = client or AsyncOpenAI(api_key=api_key)

    @property
    def config(self) -> EmbeddingConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_chunks(
        self,
        chunks: list[TextChunk],
    ) -> list[EmbeddingResult]:
        """Embed a list of chunks in batches.

        Chunks whose ``token_count`` exceeds the per-input limit are
        skipped with a warning log.

        Returns:
            One :class:`EmbeddingResult` per successfully embedded chunk,
            in the same order as the accepted input chunks.
        """
        if not chunks:
            return []

        # Validate per-input token limit
        valid_chunks: list[TextChunk] = []
        for chunk in chunks:
            if chunk.token_count > self._config.max_tokens_per_input:
                logger.warning(
                    "Chunk %d exceeds max token limit (%d > %d), skipping",
                    chunk.chunk_index,
                    chunk.token_count,
                    self._config.max_tokens_per_input,
                )
                continue
            valid_chunks.append(chunk)

        if not valid_chunks:
            return []

        results: list[EmbeddingResult] = []

        # Process in batches of max_batch_size
        for batch_start in range(0, len(valid_chunks), self._config.max_batch_size):
            batch = valid_chunks[batch_start : batch_start + self._config.max_batch_size]
            batch_results = await self._embed_batch(batch)
            results.extend(batch_results)

        return results

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.  Convenience method."""
        embeddings = await self._call_api([text])
        return embeddings[0]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _embed_batch(
        self,
        batch: list[TextChunk],
    ) -> list[EmbeddingResult]:
        """Embed a single batch of chunks with retry logic."""
        texts = [chunk.content for chunk in batch]
        embeddings = await self._call_api(texts)

        return [
            EmbeddingResult(
                chunk_index=chunk.chunk_index,
                embedding=embedding,
                token_count=chunk.token_count,
            )
            for chunk, embedding in zip(batch, embeddings, strict=True)
        ]

    async def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI Embedding API with exponential-backoff retry.

        Retries on:
        - 429 RateLimitError
        - 5xx server errors (APIStatusError with status >= 500)
        - API timeouts

        Client errors (4xx except 429) are raised immediately.
        """
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                response = await self._client.embeddings.create(
                    model=self._config.model,
                    input=texts,
                    dimensions=self._config.dimensions,
                )
                return [item.embedding for item in response.data]

            except (RateLimitError, APITimeoutError) as exc:
                last_error = exc
                if attempt < self._config.max_retries:
                    delay = self._config.base_retry_delay * (5**attempt)
                    logger.warning(
                        "OpenAI API error (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1,
                        self._config.max_retries + 1,
                        type(exc).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)

            except APIStatusError as exc:
                if exc.status_code >= 500:
                    last_error = exc
                    if attempt < self._config.max_retries:
                        delay = self._config.base_retry_delay * (5**attempt)
                        logger.warning(
                            "OpenAI server error %d (attempt %d/%d) — retrying in %.1fs",
                            exc.status_code,
                            attempt + 1,
                            self._config.max_retries + 1,
                            delay,
                        )
                        await asyncio.sleep(delay)
                else:
                    # Client errors (4xx except 429) are not retried
                    raise

        assert last_error is not None
        raise last_error
