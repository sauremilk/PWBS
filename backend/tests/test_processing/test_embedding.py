"""Tests for pwbs.processing.embedding – EmbeddingService (TASK-058)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.processing.chunking import TextChunk
from pwbs.processing.embedding import (
    EmbeddingConfig,
    EmbeddingResult,
    EmbeddingService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(index: int, content: str = "test", token_count: int = 5) -> TextChunk:
    return TextChunk(content=content, chunk_index=index, token_count=token_count)


def _fake_embedding(dim: int = 1536) -> list[float]:
    return [0.1] * dim


def _make_embedding_response(n: int, dim: int = 1536) -> MagicMock:
    """Build a mock that mimics openai.types.CreateEmbeddingResponse."""
    items = []
    for i in range(n):
        item = MagicMock()
        item.embedding = _fake_embedding(dim)
        items.append(item)
    resp = MagicMock()
    resp.data = items
    return resp


def _make_service(
    config: EmbeddingConfig | None = None,
    client: Any = None,
) -> EmbeddingService:
    mock_client = client or AsyncMock()
    return EmbeddingService(api_key="test-key", config=config, client=mock_client)


# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------


class TestEmbedChunks:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self) -> None:
        svc = _make_service()
        result = await svc.embed_chunks([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_chunk(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(1))
        svc = _make_service(client=mock_client)

        chunks = [_make_chunk(0, "hello world", 2)]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 1
        assert results[0].chunk_index == 0
        assert len(results[0].embedding) == 1536
        assert results[0].token_count == 2

    @pytest.mark.asyncio
    async def test_result_is_embedding_result(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(1))
        svc = _make_service(client=mock_client)

        chunks = [_make_chunk(0)]
        results = await svc.embed_chunks(chunks)
        assert isinstance(results[0], EmbeddingResult)


# ---------------------------------------------------------------------------
# AC: Batches of max 64
# ---------------------------------------------------------------------------


class TestBatching:
    @pytest.mark.asyncio
    async def test_chunks_split_into_batches(self) -> None:
        """70 chunks → 2 API calls (64 + 6)."""
        mock_client = AsyncMock()
        # First call: 64 chunks, second: 6 chunks
        mock_client.embeddings.create = AsyncMock(
            side_effect=[
                _make_embedding_response(64),
                _make_embedding_response(6),
            ]
        )
        svc = _make_service(client=mock_client)

        chunks = [_make_chunk(i) for i in range(70)]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 70
        assert mock_client.embeddings.create.call_count == 2

    @pytest.mark.asyncio
    async def test_exactly_64_chunks_single_batch(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(64))
        svc = _make_service(client=mock_client)

        chunks = [_make_chunk(i) for i in range(64)]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 64
        assert mock_client.embeddings.create.call_count == 1


# ---------------------------------------------------------------------------
# AC: Token-Count pro Batch geprüft (max 8191 per input)
# ---------------------------------------------------------------------------


class TestTokenLimits:
    @pytest.mark.asyncio
    async def test_oversized_chunks_skipped(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(2))
        svc = _make_service(client=mock_client)

        chunks = [
            _make_chunk(0, "ok", 100),
            _make_chunk(1, "too large", 9000),  # exceeds 8191
            _make_chunk(2, "ok too", 200),
        ]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 2
        assert results[0].chunk_index == 0
        assert results[1].chunk_index == 2

    @pytest.mark.asyncio
    async def test_all_chunks_oversized_returns_empty(self) -> None:
        svc = _make_service()
        chunks = [_make_chunk(0, "big", 9000), _make_chunk(1, "bigger", 10000)]
        results = await svc.embed_chunks(chunks)
        assert results == []


# ---------------------------------------------------------------------------
# AC: Retry-Logik bei API-Fehlern (429, 500, Timeout)
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(self) -> None:
        from httpx import Request, Response
        from openai import RateLimitError

        mock_client = AsyncMock()
        mock_request = Request("POST", "https://api.openai.com/v1/embeddings")
        mock_response = Response(status_code=429, request=mock_request)
        error = RateLimitError(
            message="rate limited",
            response=mock_response,
            body=None,
        )
        # Fail twice, succeed on third
        mock_client.embeddings.create = AsyncMock(
            side_effect=[error, error, _make_embedding_response(1)]
        )

        config = EmbeddingConfig(base_retry_delay=0.01)  # fast retries for tests
        svc = _make_service(config=config, client=mock_client)

        chunks = [_make_chunk(0)]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 1
        assert mock_client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self) -> None:
        from httpx import Request
        from openai import APITimeoutError

        mock_client = AsyncMock()
        error = APITimeoutError(request=Request("POST", "https://api.openai.com"))
        mock_client.embeddings.create = AsyncMock(side_effect=[error, _make_embedding_response(1)])

        config = EmbeddingConfig(base_retry_delay=0.01)
        svc = _make_service(config=config, client=mock_client)

        chunks = [_make_chunk(0)]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 1
        assert mock_client.embeddings.create.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_server_error(self) -> None:
        from httpx import Request, Response
        from openai import APIStatusError

        mock_client = AsyncMock()
        mock_request = Request("POST", "https://api.openai.com/v1/embeddings")
        mock_response = Response(status_code=500, request=mock_request)
        error = APIStatusError(
            message="server error",
            response=mock_response,
            body=None,
        )
        mock_client.embeddings.create = AsyncMock(side_effect=[error, _make_embedding_response(1)])

        config = EmbeddingConfig(base_retry_delay=0.01)
        svc = _make_service(config=config, client=mock_client)

        chunks = [_make_chunk(0)]
        results = await svc.embed_chunks(chunks)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        from httpx import Request, Response
        from openai import RateLimitError

        mock_client = AsyncMock()
        mock_request = Request("POST", "https://api.openai.com/v1/embeddings")
        mock_response = Response(status_code=429, request=mock_request)
        error = RateLimitError(
            message="rate limited",
            response=mock_response,
            body=None,
        )
        mock_client.embeddings.create = AsyncMock(side_effect=error)

        config = EmbeddingConfig(max_retries=2, base_retry_delay=0.01)
        svc = _make_service(config=config, client=mock_client)

        chunks = [_make_chunk(0)]
        with pytest.raises(RateLimitError):
            await svc.embed_chunks(chunks)

        # 1 initial + 2 retries = 3 calls
        assert mock_client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_client_error_not_retried(self) -> None:
        from httpx import Request, Response
        from openai import APIStatusError

        mock_client = AsyncMock()
        mock_request = Request("POST", "https://api.openai.com/v1/embeddings")
        mock_response = Response(status_code=400, request=mock_request)
        error = APIStatusError(
            message="bad request",
            response=mock_response,
            body=None,
        )
        mock_client.embeddings.create = AsyncMock(side_effect=error)

        config = EmbeddingConfig(base_retry_delay=0.01)
        svc = _make_service(config=config, client=mock_client)

        chunks = [_make_chunk(0)]
        with pytest.raises(APIStatusError):
            await svc.embed_chunks(chunks)

        # Should NOT retry – just 1 call
        assert mock_client.embeddings.create.call_count == 1


# ---------------------------------------------------------------------------
# AC: Modellname konfigurierbar
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_model(self) -> None:
        svc = _make_service()
        assert svc.config.model == "text-embedding-3-small"

    def test_default_dimensions(self) -> None:
        svc = _make_service()
        assert svc.config.dimensions == 1536

    def test_custom_model(self) -> None:
        config = EmbeddingConfig(model="text-embedding-3-large", dimensions=3072)
        svc = _make_service(config=config)
        assert svc.config.model == "text-embedding-3-large"
        assert svc.config.dimensions == 3072

    @pytest.mark.asyncio
    async def test_model_passed_to_api(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(1))

        config = EmbeddingConfig(model="custom-model")
        svc = _make_service(config=config, client=mock_client)

        await svc.embed_chunks([_make_chunk(0)])

        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert call_kwargs["model"] == "custom-model"


# ---------------------------------------------------------------------------
# AC: 1536-dimensionale Float-Vektoren
# ---------------------------------------------------------------------------


class TestEmbeddingDimensions:
    @pytest.mark.asyncio
    async def test_embeddings_have_correct_dimensions(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(1, 1536))
        svc = _make_service(client=mock_client)

        results = await svc.embed_chunks([_make_chunk(0)])
        assert len(results[0].embedding) == 1536

    @pytest.mark.asyncio
    async def test_embed_text_convenience(self) -> None:
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=_make_embedding_response(1))
        svc = _make_service(client=mock_client)

        embedding = await svc.embed_text("hello world")
        assert len(embedding) == 1536
