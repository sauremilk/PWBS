"""Multi-modal processing pipeline orchestrator (TASK-159).

Routes files to the correct processor (OCR or Audio) based on media type,
creates UnifiedDocuments from results, and tracks progress.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pwbs.processing.multimodal.audio import AudioTranscriber
from pwbs.processing.multimodal.models import (
    AUDIO_MEDIA_TYPES,
    IMAGE_MEDIA_TYPES,
    JobStatus,
    MediaType,
    ProcessingJob,
    classify_media,
)
from pwbs.processing.multimodal.ocr import OCRProcessor

logger = logging.getLogger(__name__)

__all__ = ["MultiModalPipeline", "MultiModalResult"]


class MultiModalResult:
    """Result of multi-modal processing."""

    __slots__ = (
        "source_type",
        "content",
        "metadata",
        "title",
    )

    def __init__(
        self,
        source_type: str,
        content: str,
        metadata: dict[str, Any],
        title: str,
    ) -> None:
        self.source_type = source_type
        self.content = content
        self.metadata = metadata
        self.title = title


class MultiModalPipeline:
    """Orchestrates multi-modal file processing.

    Parameters
    ----------
    ocr_processor:
        OCR handler for images and PDFs.
    audio_transcriber:
        Audio transcription handler.
    """

    def __init__(
        self,
        ocr_processor: OCRProcessor,
        audio_transcriber: AudioTranscriber,
    ) -> None:
        self._ocr = ocr_processor
        self._audio = audio_transcriber
        self._jobs: dict[uuid.UUID, ProcessingJob] = {}

    def create_job(
        self,
        owner_id: uuid.UUID,
        file_name: str,
        media_type: MediaType,
    ) -> ProcessingJob:
        """Create a new processing job for tracking."""
        job = ProcessingJob(
            owner_id=owner_id,
            file_name=file_name,
            media_type=media_type,
        )
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: uuid.UUID) -> ProcessingJob | None:
        """Get job status by ID."""
        return self._jobs.get(job_id)

    def process_file(
        self,
        file_path: Path,
        media_type: MediaType,
        job_id: uuid.UUID | None = None,
    ) -> MultiModalResult:
        """Process a file and return extracted content.

        Parameters
        ----------
        file_path:
            Path to the file to process.
        media_type:
            MIME type of the file.
        job_id:
            Optional job ID for progress tracking.

        Returns
        -------
        MultiModalResult
            Extracted content ready for UDF normalization.
        """
        job = self._jobs.get(job_id) if job_id else None
        if job:
            job.status = JobStatus.PROCESSING
            job.progress_percent = 10

        try:
            category = classify_media(media_type.value)

            if category == "image":
                return self._process_image(file_path, media_type, job)
            else:
                return self._process_audio(file_path, media_type, job)
        except Exception as exc:
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
            raise

    def _process_image(
        self,
        file_path: Path,
        media_type: MediaType,
        job: ProcessingJob | None,
    ) -> MultiModalResult:
        """Process an image/PDF file via OCR."""
        if job:
            job.progress_percent = 30

        result = self._ocr.extract_text(file_path, media_type)

        if job:
            job.progress_percent = 90
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100
            job.completed_at = datetime.now(tz=timezone.utc)

        return MultiModalResult(
            source_type="ocr",
            content=result.full_text,
            metadata={
                "page_count": result.page_count,
                "average_confidence": result.average_confidence,
                "processing_mode": result.mode.value,
                "processing_seconds": result.processing_seconds,
                "original_file": file_path.name,
                "media_type": media_type.value,
            },
            title=f"OCR: {file_path.stem}",
        )

    def _process_audio(
        self,
        file_path: Path,
        media_type: MediaType,
        job: ProcessingJob | None,
    ) -> MultiModalResult:
        """Process an audio file via transcription."""
        if job:
            job.progress_percent = 30

        result = self._audio.transcribe(file_path, media_type)

        if job:
            job.progress_percent = 90
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100
            job.completed_at = datetime.now(tz=timezone.utc)

        # Build timestamped transcript text
        timestamped_lines: list[str] = []
        for seg in result.segments:
            ts = f"[{_format_time(seg.start_seconds)} - {_format_time(seg.end_seconds)}]"
            speaker = f" ({seg.speaker})" if seg.speaker else ""
            timestamped_lines.append(f"{ts}{speaker} {seg.text}")

        content = "\n".join(timestamped_lines) if timestamped_lines else result.full_text

        return MultiModalResult(
            source_type="audio_transcript",
            content=content,
            metadata={
                "duration_seconds": result.duration_seconds,
                "segment_count": len(result.segments),
                "language": result.language,
                "processing_mode": result.mode.value,
                "processing_seconds": result.processing_seconds,
                "original_file": file_path.name,
                "media_type": media_type.value,
                "full_text_plain": result.full_text,
            },
            title=f"Transkript: {file_path.stem}",
        )


def _format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
