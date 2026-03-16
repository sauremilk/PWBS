"""Data models for multi-modal processing results (TASK-159)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Supported multi-modal media types."""

    # Image / OCR
    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"

    # Audio
    MP3 = "audio/mpeg"
    WAV = "audio/wav"
    M4A = "audio/mp4"
    WEBM = "audio/webm"


class ProcessingMode(str, Enum):
    """Which backend was used for processing."""

    LOCAL = "local"
    CLOUD = "cloud"


class JobStatus(str, Enum):
    """Status of an async multi-modal processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── OCR ──────────────────────────────────────────────────────────────


class OCRPageResult(BaseModel):
    """OCR result for a single page (PDF) or a single image."""

    page_number: int = 1
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class OCRResult(BaseModel):
    """Aggregated OCR result for a file."""

    pages: list[OCRPageResult]
    full_text: str
    average_confidence: float = Field(ge=0.0, le=1.0)
    page_count: int
    mode: ProcessingMode
    processing_seconds: float


# ── Audio ────────────────────────────────────────────────────────────


class TranscriptSegment(BaseModel):
    """A timestamped segment of an audio transcription."""

    start_seconds: float
    end_seconds: float
    text: str
    speaker: str | None = None


class TranscriptionResult(BaseModel):
    """Full audio transcription result."""

    segments: list[TranscriptSegment]
    full_text: str
    duration_seconds: float
    language: str = "de"
    mode: ProcessingMode
    processing_seconds: float


# ── Job progress ─────────────────────────────────────────────────────


class ProcessingJob(BaseModel):
    """Tracks progress of an async multi-modal processing job."""

    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    owner_id: uuid.UUID
    file_name: str
    media_type: MediaType
    status: JobStatus = JobStatus.PENDING
    progress_percent: int = Field(default=0, ge=0, le=100)
    document_id: uuid.UUID | None = None
    error_message: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=__import__("datetime").timezone.utc)
    )
    completed_at: datetime | None = None


# ── Helpers ──────────────────────────────────────────────────────────

IMAGE_MEDIA_TYPES = frozenset({MediaType.JPEG, MediaType.PNG, MediaType.PDF})
AUDIO_MEDIA_TYPES = frozenset({MediaType.MP3, MediaType.WAV, MediaType.M4A, MediaType.WEBM})

MIME_TO_MEDIA_TYPE: dict[str, MediaType] = {m.value: m for m in MediaType}


def classify_media(mime_type: str) -> str:
    """Return 'image', 'audio', or raise ValueError for unsupported types."""
    media = MIME_TO_MEDIA_TYPE.get(mime_type)
    if media is None:
        raise ValueError(f"Unsupported media type: {mime_type}")
    if media in IMAGE_MEDIA_TYPES:
        return "image"
    return "audio"
