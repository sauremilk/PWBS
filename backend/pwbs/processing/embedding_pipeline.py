"""Fehlerbehandlung und Retry-Logik fuer Embedding-Pipeline (TASK-060).

Pipeline handler wrapping `EmbeddingService` with:
- Batch-level retry with exponential backoff (1 min -> 5 min -> 25 min)
- Partial success tracking (persist successful chunks even if some fail)
- Document status updates (`processing_status` -> `done` / `error`)
- Audit logging of failures

D1 Section 3.2, AGENTS.md ProcessingAgent.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from pwbs.processing.chunking import TextChunk
from pwbs.processing.embedding import EmbeddingResult, EmbeddingService

logger = logging.getLogger(__name__)

__all__ = [
    "AuditLogger",
    "BatchResult",
    "DocumentStatusUpdater",
    "EmbeddingPipelineHandler",
    "PipelineConfig",
    "PipelineResult",
]


# ------------------------------------------------------------------
# Protocols for external dependencies
# ------------------------------------------------------------------


class DocumentStatusUpdater(Protocol):
    """Protocol for updating document processing status in DB."""

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None: ...


class AuditLogger(Protocol):
    """Protocol for writing audit log entries."""

    async def log(
        self,
        user_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        metadata: dict[str, Any],
    ) -> None: ...


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Configuration for the embedding pipeline handler.

    Parameters
    ----------
    max_batch_retries:
        Maximum retry attempts per failed batch.
    base_retry_delay:
        Base delay for exponential backoff (seconds).
    backoff_factor:
        Multiplier per retry (5 = 1min -> 5min -> 25min).
    save_partial:
        Whether to save successful embeddings from partially failed batches.
    """

    max_batch_retries: int = 3
    base_retry_delay: float = 60.0
    backoff_factor: float = 5.0
    save_partial: bool = True


# ------------------------------------------------------------------
# Result types
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a single batch."""

    batch_index: int
    total_chunks: int
    successful: list[EmbeddingResult]
    failed_indices: list[int]
    error: str | None = None
    retry_count: int = 0


@dataclass(slots=True)
class PipelineResult:
    """Aggregate result of the full embedding pipeline."""

    document_id: uuid.UUID
    total_chunks: int
    successful_embeddings: list[EmbeddingResult] = field(default_factory=list)
    failed_batch_count: int = 0
    total_batches: int = 0
    partial_success: bool = False
    final_status: str = "done"
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Fraction of chunks successfully embedded."""
        if self.total_chunks == 0:
            return 1.0
        return len(self.successful_embeddings) / self.total_chunks


# ------------------------------------------------------------------
# Pipeline Handler
# ------------------------------------------------------------------


class EmbeddingPipelineHandler:
    """Orchestrates embedding generation with error handling.

    Wraps `EmbeddingService.embed_chunks()` with:
    - Per-batch retry with exponential backoff
    - Partial success preservation
    - Document status updates via `DocumentStatusUpdater` protocol
    - Audit logging via `AuditLogger` protocol

    Parameters
    ----------
    embedding_service:
        The underlying embedding service.
    config:
        Pipeline configuration.
    status_updater:
        Optional DB status updater.
    audit_logger:
        Optional audit logger.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        config: PipelineConfig | None = None,
        status_updater: DocumentStatusUpdater | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._embedding = embedding_service
        self._config = config or PipelineConfig()
        self._status_updater = status_updater
        self._audit_logger = audit_logger

    @property
    def config(self) -> PipelineConfig:
        """Current pipeline configuration."""
        return self._config

    async def process_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        chunks: list[TextChunk],
    ) -> PipelineResult:
        """Process all chunks for a document with error handling.

        Parameters
        ----------
        document_id:
            Document being processed.
        user_id:
            Owner ID for audit logging.
        chunks:
            Chunks to embed.

        Returns
        -------
        PipelineResult
            Contains successful embeddings and error details.
        """
        result = PipelineResult(
            document_id=document_id,
            total_chunks=len(chunks),
        )

        if not chunks:
            result.final_status = "done"
            await self._update_status(document_id, "done")
            return result

        # Split into batches (using embedding service's batch size)
        batch_size = self._embedding.config.max_batch_size
        batches = [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]
        result.total_batches = len(batches)

        for batch_idx, batch in enumerate(batches):
            batch_result = await self._process_batch_with_retry(
                batch,
                batch_idx,
            )

            result.successful_embeddings.extend(batch_result.successful)

            if batch_result.error is not None:
                result.failed_batch_count += 1
                result.errors.append(f"Batch {batch_idx}: {batch_result.error}")

        # Determine final status
        if result.failed_batch_count == 0:
            result.final_status = "done"
        elif result.successful_embeddings:
            result.final_status = "done" if self._config.save_partial else "error"
            result.partial_success = True
        else:
            result.final_status = "error"

        # Update document status
        error_msg = "; ".join(result.errors) if result.errors else None
        await self._update_status(document_id, result.final_status, error_msg)

        # Audit log failures
        if result.errors:
            await self._log_failure(
                user_id=user_id,
                document_id=document_id,
                errors=result.errors,
                success_rate=result.success_rate,
            )

        logger.info(
            "Embedding pipeline complete: doc=%s chunks=%d/%d batches_failed=%d status=%s",
            document_id,
            len(result.successful_embeddings),
            result.total_chunks,
            result.failed_batch_count,
            result.final_status,
        )

        return result

    # ------------------------------------------------------------------
    # Batch processing with retry
    # ------------------------------------------------------------------

    async def _process_batch_with_retry(
        self,
        batch: list[TextChunk],
        batch_index: int,
    ) -> BatchResult:
        """Process a single batch with exponential backoff retry.

        Returns partial results on failure if possible.
        """
        import asyncio

        last_error: str | None = None
        retry_count = 0

        for attempt in range(self._config.max_batch_retries + 1):
            try:
                embeddings = await self._embedding.embed_chunks(batch)
                return BatchResult(
                    batch_index=batch_index,
                    total_chunks=len(batch),
                    successful=embeddings,
                    failed_indices=[],
                    retry_count=attempt,
                )

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                retry_count = attempt + 1

                if attempt < self._config.max_batch_retries:
                    delay = self._config.base_retry_delay * (self._config.backoff_factor**attempt)
                    logger.warning(
                        "Batch %d failed (attempt %d/%d): %s  retrying in %.0fs",
                        batch_index,
                        attempt + 1,
                        self._config.max_batch_retries + 1,
                        last_error,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Batch %d permanently failed after %d attempts: %s",
                        batch_index,
                        self._config.max_batch_retries + 1,
                        last_error,
                    )

        return BatchResult(
            batch_index=batch_index,
            total_chunks=len(batch),
            successful=[],
            failed_indices=list(range(len(batch))),
            error=last_error,
            retry_count=retry_count,
        )

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    async def _update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update document processing status if updater is available."""
        if self._status_updater is not None:
            try:
                await self._status_updater.update_status(
                    document_id,
                    status,
                    error_message,
                )
            except Exception as exc:
                logger.error(
                    "Failed to update document status: doc=%s status=%s: %s",
                    document_id,
                    status,
                    exc,
                )

    async def _log_failure(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        errors: list[str],
        success_rate: float,
    ) -> None:
        """Log embedding failures to audit log."""
        if self._audit_logger is not None:
            try:
                await self._audit_logger.log(
                    user_id=user_id,
                    action="embedding_pipeline_error",
                    resource_type="document",
                    resource_id=document_id,
                    metadata={
                        "errors": errors,
                        "success_rate": round(success_rate, 3),
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
            except Exception as exc:
                logger.error("Failed to write audit log: %s", exc)
