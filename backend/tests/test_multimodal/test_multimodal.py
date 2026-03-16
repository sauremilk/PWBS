"""Tests for Multi-Modal Ingestion Pipeline (TASK-159).

Covers:
- AC1: OCR extracts text from JPEG/PNG/PDF with confidence scoring
- AC2: Audio transcription with Whisper produces timestamped segments
- AC3: Results normalize to UnifiedDocument with correct source_type
- AC4: Async job tracking with progress and status polling
- Models: MediaType, ProcessingJob, OCRResult, TranscriptionResult
- Pipeline: routing, progress tracking, error handling
- Queue: Celery task registration and routing
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pwbs.processing.multimodal.models import (
    AUDIO_MEDIA_TYPES,
    IMAGE_MEDIA_TYPES,
    MIME_TO_MEDIA_TYPE,
    JobStatus,
    MediaType,
    OCRPageResult,
    OCRResult,
    ProcessingJob,
    ProcessingMode,
    TranscriptionResult,
    TranscriptSegment,
    classify_media,
)

# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1: Models & Enums
# ═══════════════════════════════════════════════════════════════════════


class TestMediaType:
    def test_image_types(self) -> None:
        assert MediaType.JPEG.value == "image/jpeg"
        assert MediaType.PNG.value == "image/png"
        assert MediaType.PDF.value == "application/pdf"

    def test_audio_types(self) -> None:
        assert MediaType.MP3.value == "audio/mpeg"
        assert MediaType.WAV.value == "audio/wav"
        assert MediaType.M4A.value == "audio/mp4"
        assert MediaType.WEBM.value == "audio/webm"

    def test_image_set(self) -> None:
        assert MediaType.JPEG in IMAGE_MEDIA_TYPES
        assert MediaType.PNG in IMAGE_MEDIA_TYPES
        assert MediaType.PDF in IMAGE_MEDIA_TYPES
        assert MediaType.MP3 not in IMAGE_MEDIA_TYPES

    def test_audio_set(self) -> None:
        assert MediaType.MP3 in AUDIO_MEDIA_TYPES
        assert MediaType.WAV in AUDIO_MEDIA_TYPES
        assert MediaType.M4A in AUDIO_MEDIA_TYPES
        assert MediaType.WEBM in AUDIO_MEDIA_TYPES
        assert MediaType.JPEG not in AUDIO_MEDIA_TYPES


class TestClassifyMedia:
    def test_image_classification(self) -> None:
        assert classify_media("image/jpeg") == "image"
        assert classify_media("image/png") == "image"
        assert classify_media("application/pdf") == "image"

    def test_audio_classification(self) -> None:
        assert classify_media("audio/mpeg") == "audio"
        assert classify_media("audio/wav") == "audio"
        assert classify_media("audio/mp4") == "audio"
        assert classify_media("audio/webm") == "audio"

    def test_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported media type"):
            classify_media("text/plain")


class TestMimeToMediaType:
    def test_all_media_types_mapped(self) -> None:
        for mt in MediaType:
            assert mt.value in MIME_TO_MEDIA_TYPE
            assert MIME_TO_MEDIA_TYPE[mt.value] == mt


class TestOCRModels:
    def test_ocr_page_result(self) -> None:
        page = OCRPageResult(page_number=1, text="Hello World", confidence=0.95)
        assert page.confidence == 0.95
        assert page.text == "Hello World"

    def test_ocr_result_aggregation(self) -> None:
        result = OCRResult(
            pages=[
                OCRPageResult(page_number=1, text="Page 1", confidence=0.9),
                OCRPageResult(page_number=2, text="Page 2", confidence=0.8),
            ],
            full_text="Page 1\n\nPage 2",
            average_confidence=0.85,
            page_count=2,
            mode=ProcessingMode.LOCAL,
            processing_seconds=1.5,
        )
        assert result.page_count == 2
        assert result.average_confidence == 0.85

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):
            OCRPageResult(page_number=1, text="", confidence=1.5)
        with pytest.raises(Exception):
            OCRPageResult(page_number=1, text="", confidence=-0.1)


class TestTranscriptionModels:
    def test_transcript_segment(self) -> None:
        seg = TranscriptSegment(
            start_seconds=0.0,
            end_seconds=5.5,
            text="Hallo zusammen",
            speaker="Alice",
        )
        assert seg.start_seconds == 0.0
        assert seg.speaker == "Alice"

    def test_transcription_result(self) -> None:
        result = TranscriptionResult(
            segments=[
                TranscriptSegment(start_seconds=0.0, end_seconds=3.0, text="Eins"),
                TranscriptSegment(start_seconds=3.0, end_seconds=6.0, text="Zwei"),
            ],
            full_text="Eins Zwei",
            duration_seconds=6.0,
            language="de",
            mode=ProcessingMode.LOCAL,
            processing_seconds=2.1,
        )
        assert len(result.segments) == 2
        assert result.duration_seconds == 6.0


class TestProcessingJob:
    def test_default_values(self) -> None:
        job = ProcessingJob(
            owner_id=uuid.uuid4(),
            file_name="test.jpg",
            media_type=MediaType.JPEG,
        )
        assert job.status == JobStatus.PENDING
        assert job.progress_percent == 0
        assert job.document_id is None
        assert job.error_message is None

    def test_job_id_auto_generated(self) -> None:
        job = ProcessingJob(
            owner_id=uuid.uuid4(),
            file_name="audio.mp3",
            media_type=MediaType.MP3,
        )
        assert isinstance(job.job_id, uuid.UUID)


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2: OCR Processor (AC1)
# ═══════════════════════════════════════════════════════════════════════


class TestOCRProcessor:
    def _make_tesseract(self) -> MagicMock:
        engine = MagicMock()
        engine.image_to_string.return_value = "Extracted text from image"
        engine.image_to_data.return_value = {"conf": ["95", "90", "85"]}
        return engine

    def _make_pdf_renderer(self, page_count: int = 2) -> MagicMock:
        renderer = MagicMock()
        renderer.convert_from_path.return_value = [MagicMock() for _ in range(page_count)]
        return renderer

    def test_extract_jpeg(self) -> None:
        """AC1: OCR extracts text from JPEG."""
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        proc = OCRProcessor(tesseract=tess)
        result = proc.extract_text(Path("/tmp/test.jpg"), MediaType.JPEG)

        assert result.full_text == "Extracted text from image"
        assert result.page_count == 1
        assert result.mode == ProcessingMode.LOCAL
        tess.image_to_string.assert_called_once()

    def test_extract_png(self) -> None:
        """AC1: OCR extracts text from PNG."""
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        proc = OCRProcessor(tesseract=tess)
        result = proc.extract_text(Path("/tmp/test.png"), MediaType.PNG)

        assert result.page_count == 1
        assert result.full_text == "Extracted text from image"

    def test_extract_pdf_multiple_pages(self) -> None:
        """AC1: OCR processes multi-page PDFs."""
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        pdf = self._make_pdf_renderer(page_count=3)
        proc = OCRProcessor(tesseract=tess, pdf_renderer=pdf)
        result = proc.extract_text(Path("/tmp/doc.pdf"), MediaType.PDF)

        assert result.page_count == 3
        assert tess.image_to_string.call_count == 3
        pdf.convert_from_path.assert_called_once()

    def test_no_engine_raises(self) -> None:
        from pwbs.processing.multimodal.ocr import OCRProcessor

        proc = OCRProcessor()
        with pytest.raises(RuntimeError, match="No OCR engine"):
            proc.extract_text(Path("/tmp/test.jpg"), MediaType.JPEG)

    def test_pdf_without_renderer_raises(self) -> None:
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        proc = OCRProcessor(tesseract=tess)
        with pytest.raises(RuntimeError, match="No PDF renderer"):
            proc.extract_text(Path("/tmp/doc.pdf"), MediaType.PDF)

    def test_unsupported_media_type_raises(self) -> None:
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        proc = OCRProcessor(tesseract=tess)
        with pytest.raises(ValueError, match="does not support"):
            proc.extract_text(Path("/tmp/audio.mp3"), MediaType.MP3)

    def test_confidence_estimation(self) -> None:
        """AC1: Confidence scoring from tesseract data."""
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        proc = OCRProcessor(tesseract=tess)
        result = proc.extract_text(Path("/tmp/test.jpg"), MediaType.JPEG)

        # Confidence from mock data: (95+90+85)/3/100 = 0.9
        assert result.pages[0].confidence == 0.9

    def test_processing_seconds_tracked(self) -> None:
        from pwbs.processing.multimodal.ocr import OCRProcessor

        tess = self._make_tesseract()
        proc = OCRProcessor(tesseract=tess)
        result = proc.extract_text(Path("/tmp/test.jpg"), MediaType.JPEG)

        assert result.processing_seconds >= 0


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3: Audio Transcriber (AC2)
# ═══════════════════════════════════════════════════════════════════════


class TestAudioTranscriber:
    def _make_whisper(self) -> MagicMock:
        engine = MagicMock()
        engine.transcribe.return_value = {
            "text": "Hallo, das ist ein Test.",
            "language": "de",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hallo,"},
                {"start": 2.5, "end": 5.0, "text": " das ist ein Test."},
            ],
        }
        return engine

    def test_transcribe_mp3(self) -> None:
        """AC2: Transcribe MP3 with Whisper."""
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        result = transcriber.transcribe(Path("/tmp/audio.mp3"), MediaType.MP3)

        assert result.full_text == "Hallo, das ist ein Test."
        assert len(result.segments) == 2
        assert result.language == "de"
        assert result.mode == ProcessingMode.LOCAL
        whisper.transcribe.assert_called_once()

    def test_transcribe_wav(self) -> None:
        """AC2: Transcribe WAV."""
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        result = transcriber.transcribe(Path("/tmp/audio.wav"), MediaType.WAV)

        assert result.full_text == "Hallo, das ist ein Test."

    def test_transcribe_m4a(self) -> None:
        """AC2: Transcribe M4A."""
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        result = transcriber.transcribe(Path("/tmp/audio.m4a"), MediaType.M4A)

        assert len(result.segments) == 2

    def test_timestamped_segments(self) -> None:
        """AC2: Timestamps in segments."""
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        result = transcriber.transcribe(Path("/tmp/audio.mp3"), MediaType.MP3)

        assert result.segments[0].start_seconds == 0.0
        assert result.segments[0].end_seconds == 2.5
        assert result.segments[1].start_seconds == 2.5

    def test_duration_from_last_segment(self) -> None:
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        result = transcriber.transcribe(Path("/tmp/audio.mp3"), MediaType.MP3)

        assert result.duration_seconds == 5.0

    def test_no_engine_raises(self) -> None:
        from pwbs.processing.multimodal.audio import AudioTranscriber

        transcriber = AudioTranscriber()
        with pytest.raises(RuntimeError, match="No transcription engine"):
            transcriber.transcribe(Path("/tmp/audio.mp3"), MediaType.MP3)

    def test_unsupported_media_type_raises(self) -> None:
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        with pytest.raises(ValueError, match="does not support"):
            transcriber.transcribe(Path("/tmp/doc.pdf"), MediaType.PDF)

    def test_processing_seconds_tracked(self) -> None:
        from pwbs.processing.multimodal.audio import AudioTranscriber

        whisper = self._make_whisper()
        transcriber = AudioTranscriber(whisper=whisper)
        result = transcriber.transcribe(Path("/tmp/audio.mp3"), MediaType.MP3)

        assert result.processing_seconds >= 0


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 4: Pipeline (AC3 + AC4)
# ═══════════════════════════════════════════════════════════════════════


class TestMultiModalPipeline:
    def _make_pipeline(self) -> tuple:
        from pwbs.processing.multimodal.pipeline import MultiModalPipeline

        tess = MagicMock()
        tess.image_to_string.return_value = "OCR text"
        tess.image_to_data.return_value = {"conf": ["90"]}

        whisper = MagicMock()
        whisper.transcribe.return_value = {
            "text": "Audio text",
            "language": "de",
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "Audio text"},
            ],
        }

        from pwbs.processing.multimodal.audio import AudioTranscriber
        from pwbs.processing.multimodal.ocr import OCRProcessor

        ocr = OCRProcessor(tesseract=tess)
        audio = AudioTranscriber(whisper=whisper)
        pipeline = MultiModalPipeline(ocr_processor=ocr, audio_transcriber=audio)
        return pipeline, tess, whisper

    def test_route_image_to_ocr(self) -> None:
        """AC3: Images routed to OCR, source_type='ocr'."""
        pipeline, tess, _ = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/test.jpg"), MediaType.JPEG)

        assert result.source_type == "ocr"
        assert result.content == "OCR text"
        tess.image_to_string.assert_called()

    def test_route_audio_to_transcriber(self) -> None:
        """AC3: Audio routed to transcriber, source_type='audio_transcript'."""
        pipeline, _, whisper = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/audio.mp3"), MediaType.MP3)

        assert result.source_type == "audio_transcript"
        assert "Audio text" in result.content
        whisper.transcribe.assert_called()

    def test_ocr_metadata_includes_confidence(self) -> None:
        """AC1: Metadata includes confidence score."""
        pipeline, _, _ = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/test.png"), MediaType.PNG)

        assert "average_confidence" in result.metadata
        assert "page_count" in result.metadata
        assert result.metadata["media_type"] == "image/png"

    def test_audio_metadata_includes_duration(self) -> None:
        """AC2: Metadata includes duration and segment count."""
        pipeline, _, _ = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/audio.wav"), MediaType.WAV)

        assert "duration_seconds" in result.metadata
        assert "segment_count" in result.metadata
        assert result.metadata["language"] == "de"

    def test_audio_content_is_timestamped(self) -> None:
        """AC2: Audio content contains timestamps."""
        pipeline, _, _ = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/audio.mp3"), MediaType.MP3)

        # Should contain time markers like [00:00 - 00:03]
        assert "[00:00" in result.content

    def test_create_and_track_job(self) -> None:
        """AC4: Job creation and progress tracking."""
        pipeline, _, _ = self._make_pipeline()
        owner_id = uuid.uuid4()

        job = pipeline.create_job(owner_id, "test.jpg", MediaType.JPEG)
        assert job.status == JobStatus.PENDING
        assert job.progress_percent == 0

        retrieved = pipeline.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_job_completes_on_success(self) -> None:
        """AC4: Job status updates to COMPLETED on success."""
        pipeline, _, _ = self._make_pipeline()
        owner_id = uuid.uuid4()

        job = pipeline.create_job(owner_id, "test.jpg", MediaType.JPEG)
        pipeline.process_file(Path("/tmp/test.jpg"), MediaType.JPEG, job_id=job.job_id)

        updated = pipeline.get_job(job.job_id)
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED
        assert updated.progress_percent == 100
        assert updated.completed_at is not None

    def test_job_fails_on_error(self) -> None:
        """AC4: Job status updates to FAILED on error."""
        from pwbs.processing.multimodal.audio import AudioTranscriber
        from pwbs.processing.multimodal.ocr import OCRProcessor
        from pwbs.processing.multimodal.pipeline import MultiModalPipeline

        # OCR processor without engine -> will fail
        ocr = OCRProcessor()
        audio = AudioTranscriber()
        pipeline = MultiModalPipeline(ocr_processor=ocr, audio_transcriber=audio)

        owner_id = uuid.uuid4()
        job = pipeline.create_job(owner_id, "test.jpg", MediaType.JPEG)

        with pytest.raises(RuntimeError):
            pipeline.process_file(Path("/tmp/test.jpg"), MediaType.JPEG, job_id=job.job_id)

        updated = pipeline.get_job(job.job_id)
        assert updated is not None
        assert updated.status == JobStatus.FAILED
        assert updated.error_message is not None

    def test_unknown_job_returns_none(self) -> None:
        pipeline, _, _ = self._make_pipeline()
        assert pipeline.get_job(uuid.uuid4()) is None

    def test_ocr_title_contains_filename(self) -> None:
        """AC3: Title derived from filename."""
        pipeline, _, _ = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/meeting_notes.jpg"), MediaType.JPEG)

        assert "meeting_notes" in result.title

    def test_audio_title_contains_filename(self) -> None:
        pipeline, _, _ = self._make_pipeline()
        result = pipeline.process_file(Path("/tmp/interview_recording.mp3"), MediaType.MP3)

        assert "interview_recording" in result.title


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 5: Source Type Enum (AC3)
# ═══════════════════════════════════════════════════════════════════════


class TestSourceTypeEnum:
    def test_ocr_source_type_exists(self) -> None:
        """AC3: source_type 'ocr' available."""
        from pwbs.schemas.enums import SourceType

        assert hasattr(SourceType, "OCR")
        assert SourceType.OCR.value == "ocr"

    def test_audio_transcript_source_type_exists(self) -> None:
        """AC3: source_type 'audio_transcript' available."""
        from pwbs.schemas.enums import SourceType

        assert hasattr(SourceType, "AUDIO_TRANSCRIPT")
        assert SourceType.AUDIO_TRANSCRIPT.value == "audio_transcript"


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 6: Queue Task Registration (AC4)
# ═══════════════════════════════════════════════════════════════════════


class TestCeleryTask:
    def test_multimodal_task_registered(self) -> None:
        """AC4: Celery task is registered."""
        from pwbs.queue.tasks.multimodal import process_multimodal_file

        assert process_multimodal_file.name == "pwbs.queue.tasks.multimodal.process_multimodal_file"

    def test_multimodal_route_configured(self) -> None:
        """AC4: Queue route for multimodal tasks."""
        from pwbs.queue.celery_app import app

        routes = app.conf.task_routes
        assert "pwbs.queue.tasks.multimodal.*" in routes
        assert routes["pwbs.queue.tasks.multimodal.*"]["queue"] == "processing.embed"


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 7: Time Formatting
# ═══════════════════════════════════════════════════════════════════════


class TestFormatTime:
    def test_zero(self) -> None:
        from pwbs.processing.multimodal.pipeline import _format_time

        assert _format_time(0) == "00:00"

    def test_seconds_only(self) -> None:
        from pwbs.processing.multimodal.pipeline import _format_time

        assert _format_time(45) == "00:45"

    def test_minutes_and_seconds(self) -> None:
        from pwbs.processing.multimodal.pipeline import _format_time

        assert _format_time(125) == "02:05"

    def test_fractional_seconds(self) -> None:
        from pwbs.processing.multimodal.pipeline import _format_time

        assert _format_time(3.7) == "00:03"


# ═══════════════════════════════════════════════════════════════════
#  SECTION 8: Celery Task Processing Logic (AC3+AC4)
# ═══════════════════════════════════════════════════════════════════


class TestCeleryTaskProcessing:
    """Tests for the complete Celery task processing (not just registration)."""

    def test_unsupported_mime_returns_failed(self) -> None:
        """Unsupported MIME types are rejected without processing."""
        from pwbs.queue.tasks.multimodal import process_multimodal_file

        result = process_multimodal_file.apply(  # type: ignore[attr-defined]
            args=[
                "/tmp/test.txt",
                "text/plain",
                str(uuid.uuid4()),
                "test.txt",
            ]
        ).result
        assert result["status"] == "failed"
        assert "Unsupported" in str(result["error"])

    def test_task_has_acks_late(self) -> None:
        """Task configured with acks_late for reliability."""
        from pwbs.queue.tasks.multimodal import process_multimodal_file

        assert process_multimodal_file.acks_late is True  # type: ignore[attr-defined]

    def test_task_max_retries(self) -> None:
        """Task retries up to 2 times."""
        from pwbs.queue.tasks.multimodal import process_multimodal_file

        assert process_multimodal_file.max_retries == 2  # type: ignore[attr-defined]


# ═══════════════════════════════════════════════════════════════════
#  SECTION 9: API Endpoint (AC4 – Upload + Polling)
# ═══════════════════════════════════════════════════════════════════


class TestMultimodalAPIRouter:
    """Tests for the multimodal API router configuration."""

    def test_router_prefix(self) -> None:
        from pwbs.api.v1.routes.multimodal import router

        assert router.prefix == "/api/v1/multimodal"

    def test_router_tags(self) -> None:
        from pwbs.api.v1.routes.multimodal import router

        assert "multimodal" in router.tags

    def test_upload_endpoint_exists(self) -> None:
        from pwbs.api.v1.routes.multimodal import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/api/v1/multimodal/upload" in paths

    def test_job_status_endpoint_exists(self) -> None:
        from pwbs.api.v1.routes.multimodal import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/api/v1/multimodal/jobs/{job_id}" in paths

    def test_allowed_content_types(self) -> None:
        from pwbs.api.v1.routes.multimodal import ALLOWED_CONTENT_TYPES

        assert "image/jpeg" in ALLOWED_CONTENT_TYPES
        assert "image/png" in ALLOWED_CONTENT_TYPES
        assert "application/pdf" in ALLOWED_CONTENT_TYPES
        assert "audio/mpeg" in ALLOWED_CONTENT_TYPES
        assert "audio/wav" in ALLOWED_CONTENT_TYPES
        assert "audio/mp4" in ALLOWED_CONTENT_TYPES
        assert "audio/webm" in ALLOWED_CONTENT_TYPES
        assert "text/plain" not in ALLOWED_CONTENT_TYPES

    def test_max_file_size(self) -> None:
        from pwbs.api.v1.routes.multimodal import MAX_FILE_SIZE

        assert MAX_FILE_SIZE == 100 * 1024 * 1024

    def test_upload_response_schema(self) -> None:
        from pwbs.api.v1.routes.multimodal import UploadResponse

        resp = UploadResponse(
            job_id="abc-123",
            file_name="test.jpg",
            media_type="image/jpeg",
        )
        assert resp.status == "pending"

    def test_job_status_response_schema(self) -> None:
        from pwbs.api.v1.routes.multimodal import JobStatusResponse

        resp = JobStatusResponse(
            job_id="abc-123",
            status="completed",
            document_id="doc-456",
        )
        assert resp.document_id == "doc-456"
        assert resp.error is None

    def test_router_registered_in_app(self) -> None:
        """Multimodal router is included in the main app."""
        pytest.importorskip("prometheus_client")
        from unittest.mock import patch

        with patch("pwbs.db.postgres.get_engine"):
            from pwbs.api.main import create_app

            app = create_app()
            routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
            assert any("/api/v1/multimodal" in r for r in routes)
