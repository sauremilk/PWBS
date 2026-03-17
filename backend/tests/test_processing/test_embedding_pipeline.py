"""Tests for pwbs.processing.embedding_pipeline (TASK-060)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.processing.chunking import TextChunk
from pwbs.processing.embedding import EmbeddingConfig, EmbeddingResult, EmbeddingService
from pwbs.processing.embedding_pipeline import (
    AuditLogger,
    DocumentStatusUpdater,
    EmbeddingPipelineHandler,
    PipelineConfig,
    PipelineResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DOC_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_chunk(index: int, content: str = "test", token_count: int = 5) -> TextChunk:
    return TextChunk(content=content, chunk_index=index, token_count=token_count)


def _make_result(index: int, dim: int = 1536) -> EmbeddingResult:
    return EmbeddingResult(chunk_index=index, embedding=[0.1] * dim, token_count=5)


def _make_embedding_service(
    embed_chunks_side_effect: Any = None,
    batch_size: int = 64,
) -> EmbeddingService:
    """Create a mock EmbeddingService with controlled behavior."""
    svc = MagicMock(spec=EmbeddingService)
    svc.config = EmbeddingConfig(max_batch_size=batch_size)
    if embed_chunks_side_effect is not None:
        svc.embed_chunks = AsyncMock(side_effect=embed_chunks_side_effect)
    else:
        svc.embed_chunks = AsyncMock(return_value=[])
    return svc


def _make_status_updater() -> AsyncMock:
    updater = AsyncMock(spec=DocumentStatusUpdater)
    updater.update_status = AsyncMock()
    return updater


def _make_audit_logger() -> AsyncMock:
    logger = AsyncMock(spec=AuditLogger)
    logger.log = AsyncMock()
    return logger


# ---------------------------------------------------------------------------
# PipelineConfig
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    def test_defaults(self) -> None:
        cfg = PipelineConfig()
        assert cfg.max_batch_retries == 3
        assert cfg.base_retry_delay == 60.0
        assert cfg.backoff_factor == 5.0
        assert cfg.save_partial is True

    def test_custom_values(self) -> None:
        cfg = PipelineConfig(
            max_batch_retries=5, base_retry_delay=10.0, backoff_factor=2.0, save_partial=False
        )
        assert cfg.max_batch_retries == 5
        assert cfg.base_retry_delay == 10.0
        assert cfg.backoff_factor == 2.0
        assert cfg.save_partial is False


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_success_rate_empty(self) -> None:
        r = PipelineResult(document_id=_DOC_ID, total_chunks=0)
        assert r.success_rate == 1.0

    def test_success_rate_partial(self) -> None:
        r = PipelineResult(
            document_id=_DOC_ID,
            total_chunks=10,
            successful_embeddings=[_make_result(i) for i in range(6)],
        )
        assert r.success_rate == pytest.approx(0.6)

    def test_success_rate_all(self) -> None:
        r = PipelineResult(
            document_id=_DOC_ID,
            total_chunks=5,
            successful_embeddings=[_make_result(i) for i in range(5)],
        )
        assert r.success_rate == 1.0


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


class TestEmptyInput:
    @pytest.mark.asyncio
    async def test_empty_chunks_returns_done(self) -> None:
        svc = _make_embedding_service()
        updater = _make_status_updater()
        handler = EmbeddingPipelineHandler(svc, status_updater=updater)

        result = await handler.process_document(_DOC_ID, _USER_ID, [])

        assert result.final_status == "done"
        assert result.total_chunks == 0
        assert result.successful_embeddings == []
        updater.update_status.assert_awaited_once_with(_DOC_ID, "done", None)


# ---------------------------------------------------------------------------
# Successful processing
# ---------------------------------------------------------------------------


class TestSuccessfulProcessing:
    @pytest.mark.asyncio
    async def test_single_batch_success(self) -> None:
        chunks = [_make_chunk(i) for i in range(10)]
        results = [_make_result(i) for i in range(10)]
        svc = _make_embedding_service(embed_chunks_side_effect=[results])
        updater = _make_status_updater()

        handler = EmbeddingPipelineHandler(svc, status_updater=updater)
        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.final_status == "done"
        assert len(result.successful_embeddings) == 10
        assert result.failed_batch_count == 0
        assert result.total_batches == 1
        updater.update_status.assert_awaited_once_with(_DOC_ID, "done", None)

    @pytest.mark.asyncio
    async def test_multiple_batches_success(self) -> None:
        chunks = [_make_chunk(i) for i in range(10)]
        batch1 = [_make_result(i) for i in range(4)]
        batch2 = [_make_result(i) for i in range(4, 8)]
        batch3 = [_make_result(i) for i in range(8, 10)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=[batch1, batch2, batch3],
            batch_size=4,
        )
        updater = _make_status_updater()

        handler = EmbeddingPipelineHandler(svc, status_updater=updater)
        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.final_status == "done"
        assert len(result.successful_embeddings) == 10
        assert result.total_batches == 3
        assert result.failed_batch_count == 0


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------


class TestRetryBehavior:
    @pytest.mark.asyncio
    async def test_transient_failure_retries_and_succeeds(self) -> None:
        chunks = [_make_chunk(i) for i in range(3)]
        results = [_make_result(i) for i in range(3)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=[RuntimeError("transient"), results],
        )
        config = PipelineConfig(max_batch_retries=3, base_retry_delay=0.0)
        handler = EmbeddingPipelineHandler(svc, config=config)
        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.final_status == "done"
        assert len(result.successful_embeddings) == 3
        assert result.failed_batch_count == 0
        assert svc.embed_chunks.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        chunks = [_make_chunk(i) for i in range(3)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=RuntimeError("persistent failure"),
        )
        config = PipelineConfig(max_batch_retries=3, base_retry_delay=0.0)
        updater = _make_status_updater()
        audit = _make_audit_logger()
        handler = EmbeddingPipelineHandler(
            svc, config=config, status_updater=updater, audit_logger=audit
        )

        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.final_status == "error"
        assert result.failed_batch_count == 1
        assert len(result.errors) == 1
        assert "persistent failure" in result.errors[0]
        # 1 initial + 3 retries = 4 calls
        assert svc.embed_chunks.call_count == 4
        updater.update_status.assert_awaited()
        audit.log.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_uses_exponential_backoff(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=RuntimeError("fail"),
        )
        config = PipelineConfig(max_batch_retries=2, base_retry_delay=0.01, backoff_factor=5.0)
        handler = EmbeddingPipelineHandler(svc, config=config)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await handler.process_document(_DOC_ID, _USER_ID, chunks)

            # attempt 0 delay: 0.01 * 5^0 = 0.01
            # attempt 1 delay: 0.01 * 5^1 = 0.05
            assert mock_sleep.call_count == 2
            delays = [c.args[0] for c in mock_sleep.call_args_list]
            assert delays[0] == pytest.approx(0.01)
            assert delays[1] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Partial success
# ---------------------------------------------------------------------------


class TestPartialSuccess:
    @pytest.mark.asyncio
    async def test_partial_success_saves_good_batches(self) -> None:
        """Batch 0 succeeds, batch 1 fails permanently."""
        chunks = [_make_chunk(i) for i in range(8)]
        batch1_results = [_make_result(i) for i in range(4)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=[
                batch1_results,
                RuntimeError("fail"),
                RuntimeError("fail"),
                RuntimeError("fail"),
                RuntimeError("fail"),
            ],
            batch_size=4,
        )
        config = PipelineConfig(max_batch_retries=3, base_retry_delay=0.0, save_partial=True)
        updater = _make_status_updater()
        handler = EmbeddingPipelineHandler(svc, config=config, status_updater=updater)

        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.partial_success is True
        assert len(result.successful_embeddings) == 4
        assert result.failed_batch_count == 1
        # save_partial=True  status should be "done"
        assert result.final_status == "done"

    @pytest.mark.asyncio
    async def test_partial_success_save_partial_false(self) -> None:
        """With save_partial=False, partial success  error status."""
        chunks = [_make_chunk(i) for i in range(8)]
        batch1_results = [_make_result(i) for i in range(4)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=[
                batch1_results,
                RuntimeError("fail"),
                RuntimeError("fail"),
                RuntimeError("fail"),
                RuntimeError("fail"),
            ],
            batch_size=4,
        )
        config = PipelineConfig(max_batch_retries=3, base_retry_delay=0.0, save_partial=False)
        handler = EmbeddingPipelineHandler(svc, config=config)

        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.partial_success is True
        assert result.final_status == "error"

    @pytest.mark.asyncio
    async def test_all_batches_fail(self) -> None:
        chunks = [_make_chunk(i) for i in range(8)]
        svc = _make_embedding_service(
            embed_chunks_side_effect=RuntimeError("total failure"),
            batch_size=4,
        )
        config = PipelineConfig(max_batch_retries=3, base_retry_delay=0.0)
        updater = _make_status_updater()
        handler = EmbeddingPipelineHandler(svc, config=config, status_updater=updater)

        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)

        assert result.final_status == "error"
        assert len(result.successful_embeddings) == 0
        assert result.failed_batch_count == 2
        assert result.partial_success is False


# ---------------------------------------------------------------------------
# Document status updates
# ---------------------------------------------------------------------------


class TestDocumentStatusUpdates:
    @pytest.mark.asyncio
    async def test_status_updated_to_done_on_success(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=[[_make_result(0)]])
        updater = _make_status_updater()
        handler = EmbeddingPipelineHandler(svc, status_updater=updater)

        await handler.process_document(_DOC_ID, _USER_ID, chunks)
        updater.update_status.assert_awaited_once_with(_DOC_ID, "done", None)

    @pytest.mark.asyncio
    async def test_status_updated_to_error_on_failure(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=RuntimeError("boom"))
        config = PipelineConfig(max_batch_retries=0, base_retry_delay=0.0)
        updater = _make_status_updater()
        handler = EmbeddingPipelineHandler(svc, config=config, status_updater=updater)

        await handler.process_document(_DOC_ID, _USER_ID, chunks)
        call_args = updater.update_status.call_args
        assert call_args[0][1] == "error"
        assert "boom" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_status_updater_failure_does_not_crash(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=[[_make_result(0)]])
        updater = _make_status_updater()
        updater.update_status.side_effect = RuntimeError("db connection lost")
        handler = EmbeddingPipelineHandler(svc, status_updater=updater)

        # Should not raise
        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)
        assert result.final_status == "done"

    @pytest.mark.asyncio
    async def test_no_status_updater(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=[[_make_result(0)]])
        handler = EmbeddingPipelineHandler(svc)

        # Should not raise even without updater
        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)
        assert result.final_status == "done"


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_audit_logged_on_failure(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=RuntimeError("fail"))
        config = PipelineConfig(max_batch_retries=0, base_retry_delay=0.0)
        audit = _make_audit_logger()
        handler = EmbeddingPipelineHandler(svc, config=config, audit_logger=audit)

        await handler.process_document(_DOC_ID, _USER_ID, chunks)

        audit.log.assert_awaited_once()
        kwargs = audit.log.call_args.kwargs
        assert kwargs["user_id"] == _USER_ID
        assert kwargs["action"] == "embedding_pipeline_error"
        assert kwargs["resource_type"] == "document"
        assert kwargs["resource_id"] == _DOC_ID
        assert "errors" in kwargs["metadata"]
        assert "success_rate" in kwargs["metadata"]

    @pytest.mark.asyncio
    async def test_no_audit_on_success(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=[[_make_result(0)]])
        audit = _make_audit_logger()
        handler = EmbeddingPipelineHandler(svc, audit_logger=audit)

        await handler.process_document(_DOC_ID, _USER_ID, chunks)
        audit.log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_audit_logger_failure_does_not_crash(self) -> None:
        chunks = [_make_chunk(0)]
        svc = _make_embedding_service(embed_chunks_side_effect=RuntimeError("fail"))
        config = PipelineConfig(max_batch_retries=0, base_retry_delay=0.0)
        audit = _make_audit_logger()
        audit.log.side_effect = RuntimeError("logging broken")
        handler = EmbeddingPipelineHandler(svc, config=config, audit_logger=audit)

        result = await handler.process_document(_DOC_ID, _USER_ID, chunks)
        assert result.final_status == "error"


# ---------------------------------------------------------------------------
# Config property
# ---------------------------------------------------------------------------


class TestConfigProperty:
    def test_default_config(self) -> None:
        svc = _make_embedding_service()
        handler = EmbeddingPipelineHandler(svc)
        assert handler.config.max_batch_retries == 3

    def test_custom_config(self) -> None:
        svc = _make_embedding_service()
        cfg = PipelineConfig(max_batch_retries=5)
        handler = EmbeddingPipelineHandler(svc, config=cfg)
        assert handler.config.max_batch_retries == 5
