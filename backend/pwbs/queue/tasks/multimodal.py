"""Celery tasks for multi-modal processing (TASK-159).

Dispatches OCR and audio transcription jobs asynchronously,
creating UnifiedDocuments from the results.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from pathlib import Path

from pwbs.queue.celery_app import app

logger = logging.getLogger(__name__)


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(
    name="pwbs.queue.tasks.multimodal.process_multimodal_file",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="processing.embed",
    acks_late=True,
)
def process_multimodal_file(
    self: object,
    file_path: str,
    mime_type: str,
    owner_id: str,
    file_name: str,
    job_id: str | None = None,
) -> dict[str, object]:
    """Process a multi-modal file (image OCR or audio transcription).

    This task runs on the processing.embed queue and creates a
    UnifiedDocument from the extracted content.

    Parameters
    ----------
    file_path:
        Absolute path to the uploaded file.
    mime_type:
        MIME type of the file.
    owner_id:
        UUID of the file owner.
    file_name:
        Original file name.
    job_id:
        Optional UUID for progress tracking.
    """
    from pwbs.processing.multimodal.models import MIME_TO_MEDIA_TYPE

    media_type = MIME_TO_MEDIA_TYPE.get(mime_type)
    if media_type is None:
        return {
            "status": "failed",
            "error": f"Unsupported media type: {mime_type}",
        }

    start = time.monotonic()
    logger.info(
        "Processing multi-modal file: name=%s type=%s owner=%s",
        file_name,
        mime_type,
        owner_id,
    )

    try:
        result = _run_async(
            _process_and_persist(
                file_path=file_path,
                media_type=media_type,
                owner_id=owner_id,
                file_name=file_name,
            )
        )
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "process_multimodal_file completed: file=%s doc_id=%s duration=%.0fms",
            file_name,
            result.get("document_id"),
            duration_ms,
        )
        return result
    except Exception as exc:
        logger.error("process_multimodal_file failed: %s", exc)
        raise self.retry(exc=exc)  # type: ignore[attr-defined]


async def _process_and_persist(
    file_path: str,
    media_type: object,
    owner_id: str,
    file_name: str,
) -> dict[str, object]:
    """Run multimodal processing and persist result as Document (async)."""
    from pwbs.db.postgres import get_session_factory
    from pwbs.models.document import Document
    from pwbs.processing.multimodal.audio import AudioTranscriber
    from pwbs.processing.multimodal.models import (
        MediaType,
    )
    from pwbs.processing.multimodal.ocr import OCRProcessor
    from pwbs.processing.multimodal.pipeline import MultiModalPipeline

    assert isinstance(media_type, MediaType)
    owner_uuid = uuid.UUID(owner_id)
    path = Path(file_path)

    # Build pipeline with available engines (graceful: no engine = error at runtime)
    ocr_processor = OCRProcessor()
    audio_transcriber = AudioTranscriber()

    # Try to load local engines if available
    try:
        import pytesseract  # type: ignore[import-untyped]

        ocr_processor = OCRProcessor(
            tesseract=pytesseract,  # type: ignore[arg-type]  # runtime protocol match
        )
    except ImportError:
        pass

    try:
        import whisper  # type: ignore[import-untyped]

        model = whisper.load_model("base")
        audio_transcriber = AudioTranscriber(
            whisper=model,  # type: ignore[arg-type]  # runtime protocol match
        )
    except ImportError:
        pass

    pipeline = MultiModalPipeline(
        ocr_processor=ocr_processor,
        audio_transcriber=audio_transcriber,
    )

    result = pipeline.process_file(path, media_type)

    content_hash = hashlib.sha256(result.content.encode("utf-8")).hexdigest()
    source_id = f"multimodal:{uuid.uuid4().hex[:12]}"

    factory = get_session_factory()
    async with factory() as db:
        doc = Document(
            user_id=owner_uuid,
            source_type=result.source_type,
            source_id=source_id,
            title=result.title,
            content_hash=content_hash,
            processing_status="completed",
        )
        db.add(doc)
        await db.flush()
        doc_id = str(doc.id)
        await db.commit()

    return {
        "status": "completed",
        "document_id": doc_id,
        "source_type": result.source_type,
        "file_name": file_name,
        "content_length": len(result.content),
        "metadata": result.metadata,
    }
