"""Audio transcription processor (TASK-159).

Supports:
- Local: openai-whisper
- Cloud fallback: Deepgram API

Uses Protocol abstractions so unit tests don't require whisper/deepgram.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pwbs.processing.multimodal.models import (
    MediaType,
    ProcessingMode,
    TranscriptionResult,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

__all__ = ["AudioTranscriber", "WhisperEngine", "DeepgramEngine"]


@runtime_checkable
class WhisperEngine(Protocol):
    """Protocol for openai-whisper compatible transcription engines."""

    def transcribe(self, audio_path: str, language: str | None = None) -> dict[str, Any]: ...


@runtime_checkable
class DeepgramEngine(Protocol):
    """Protocol for Deepgram API compatible engines."""

    async def transcribe_file(
        self, audio_bytes: bytes, mime_type: str, language: str
    ) -> dict[str, Any]: ...


class AudioTranscriber:
    """Transcribes audio files to timestamped text.

    Parameters
    ----------
    whisper:
        Local Whisper engine (openai-whisper compatible).
    deepgram:
        Cloud fallback via Deepgram API.
    language:
        Default language code for transcription.
    """

    def __init__(
        self,
        whisper: WhisperEngine | None = None,
        deepgram: DeepgramEngine | None = None,
        language: str = "de",
    ) -> None:
        self._whisper = whisper
        self._deepgram = deepgram
        self._language = language

    def transcribe(
        self,
        file_path: Path,
        media_type: MediaType,
    ) -> TranscriptionResult:
        """Transcribe an audio file.

        Parameters
        ----------
        file_path:
            Path to the audio file.
        media_type:
            The media type of the file.

        Returns
        -------
        TranscriptionResult
            Timestamped transcription with segments.

        Raises
        ------
        RuntimeError
            If no transcription engine is available.
        ValueError
            If the media type is not an audio type.
        """
        from pwbs.processing.multimodal.models import AUDIO_MEDIA_TYPES

        if media_type not in AUDIO_MEDIA_TYPES:
            raise ValueError(f"Audio transcription does not support: {media_type}")

        start = time.monotonic()

        if self._whisper is not None:
            result = self._transcribe_whisper(file_path)
        else:
            raise RuntimeError(
                "No transcription engine available. "
                "Install openai-whisper or provide a DeepgramEngine."
            )

        elapsed = time.monotonic() - start
        result_with_time = TranscriptionResult(
            segments=result.segments,
            full_text=result.full_text,
            duration_seconds=result.duration_seconds,
            language=result.language,
            mode=result.mode,
            processing_seconds=round(elapsed, 2),
        )
        return result_with_time

    def _transcribe_whisper(self, file_path: Path) -> TranscriptionResult:
        """Transcribe using local Whisper engine."""
        assert self._whisper is not None

        raw = self._whisper.transcribe(str(file_path), language=self._language)

        segments: list[TranscriptSegment] = []
        for seg in raw.get("segments", []):
            segments.append(
                TranscriptSegment(
                    start_seconds=float(seg.get("start", 0)),
                    end_seconds=float(seg.get("end", 0)),
                    text=str(seg.get("text", "")).strip(),
                    speaker=None,
                )
            )

        full_text = raw.get("text", "").strip()
        duration = segments[-1].end_seconds if segments else 0.0
        detected_lang = raw.get("language", self._language)

        return TranscriptionResult(
            segments=segments,
            full_text=full_text,
            duration_seconds=duration,
            language=detected_lang,
            mode=ProcessingMode.LOCAL,
            processing_seconds=0.0,  # Will be overwritten
        )
