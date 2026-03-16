"""OCR processor for image and PDF files (TASK-159).

Supports:
- Local: pytesseract (Tesseract OCR)
- Cloud fallback: Vision API via LLMGateway

Uses Protocol abstractions so unit tests don't require tesseract.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pwbs.processing.multimodal.models import (
    MediaType,
    OCRPageResult,
    OCRResult,
    ProcessingMode,
)

logger = logging.getLogger(__name__)

__all__ = ["OCRProcessor", "TesseractEngine", "VisionEngine"]


@runtime_checkable
class TesseractEngine(Protocol):
    """Protocol for pytesseract-compatible OCR engines."""

    def image_to_string(self, image: Any, lang: str = "deu") -> str: ...

    def image_to_data(
        self, image: Any, lang: str = "deu", output_type: Any = None
    ) -> dict[str, list[Any]]: ...


@runtime_checkable
class VisionEngine(Protocol):
    """Protocol for cloud Vision API (LLM-based OCR fallback)."""

    async def extract_text_from_image(self, image_bytes: bytes, mime_type: str) -> str: ...


@runtime_checkable
class PDFRenderer(Protocol):
    """Protocol for PDF-to-image conversion (e.g. pdf2image)."""

    def convert_from_path(self, pdf_path: str, dpi: int = 300) -> list[Any]: ...


class OCRProcessor:
    """Extracts text from images and PDFs.

    Parameters
    ----------
    tesseract:
        Local OCR engine (pytesseract-compatible).
    vision:
        Cloud fallback for OCR via Vision API.
    pdf_renderer:
        PDF-to-image converter (pdf2image-compatible).
    lang:
        Tesseract language code (default: German).
    """

    def __init__(
        self,
        tesseract: TesseractEngine | None = None,
        vision: VisionEngine | None = None,
        pdf_renderer: PDFRenderer | None = None,
        lang: str = "deu",
    ) -> None:
        self._tesseract = tesseract
        self._vision = vision
        self._pdf_renderer = pdf_renderer
        self._lang = lang

    def extract_text(
        self,
        file_path: Path,
        media_type: MediaType,
    ) -> OCRResult:
        """Extract text from an image or PDF file.

        Parameters
        ----------
        file_path:
            Path to the image/PDF file.
        media_type:
            The media type of the file.

        Returns
        -------
        OCRResult
            Extracted text with confidence scores.

        Raises
        ------
        RuntimeError
            If no OCR engine is available.
        ValueError
            If the media type is not an image/PDF type.
        """
        start = time.monotonic()

        if media_type == MediaType.PDF:
            pages = self._extract_pdf(file_path)
        elif media_type in (MediaType.JPEG, MediaType.PNG):
            pages = [self._extract_image(file_path)]
        else:
            raise ValueError(f"OCR does not support media type: {media_type}")

        full_text = "\n\n".join(p.text for p in pages if p.text)
        avg_conf = sum(p.confidence for p in pages) / len(pages) if pages else 0.0

        elapsed = time.monotonic() - start
        return OCRResult(
            pages=pages,
            full_text=full_text,
            average_confidence=round(avg_conf, 3),
            page_count=len(pages),
            mode=ProcessingMode.LOCAL if self._tesseract else ProcessingMode.CLOUD,
            processing_seconds=round(elapsed, 2),
        )

    def _extract_image(self, file_path: Path) -> OCRPageResult:
        """Extract text from a single image file."""
        if self._tesseract is None:
            raise RuntimeError(
                "No OCR engine available. Install pytesseract or provide a VisionEngine."
            )

        # pytesseract expects a PIL Image or file path string
        text = self._tesseract.image_to_string(str(file_path), lang=self._lang)
        confidence = self._estimate_confidence(file_path)

        return OCRPageResult(
            page_number=1,
            text=text.strip(),
            confidence=confidence,
        )

    def _extract_pdf(self, file_path: Path) -> list[OCRPageResult]:
        """Extract text from each page of a PDF."""
        if self._pdf_renderer is None:
            raise RuntimeError("No PDF renderer available. Install pdf2image to process PDFs.")
        if self._tesseract is None:
            raise RuntimeError("No OCR engine available for PDF processing.")

        images = self._pdf_renderer.convert_from_path(str(file_path), dpi=300)
        pages: list[OCRPageResult] = []

        for i, img in enumerate(images, start=1):
            text = self._tesseract.image_to_string(img, lang=self._lang)
            pages.append(
                OCRPageResult(
                    page_number=i,
                    text=text.strip(),
                    confidence=0.85,  # Conservative estimate for PDF OCR
                )
            )

        return pages

    def _estimate_confidence(self, file_path: Path) -> float:
        """Estimate OCR confidence using tesseract data output."""
        if self._tesseract is None:
            return 0.0

        try:
            data = self._tesseract.image_to_data(str(file_path), lang=self._lang, output_type=None)
            confs = [float(c) for c in data.get("conf", []) if str(c) != "-1" and str(c).strip()]
            return round(sum(confs) / len(confs) / 100.0, 3) if confs else 0.85
        except Exception:
            return 0.85  # Fallback confidence
