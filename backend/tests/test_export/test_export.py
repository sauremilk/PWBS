"""Tests for briefing export (TASK-164).

Covers:
  - Pydantic schemas
  - Export strategies (Markdown, PDF HTML build, Confluence)
  - Strategy factory
  - Filename sanitization
  - API route registration and helpers
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Constants ─────────────────────────────────────────────────────────────────

OWNER_ID = uuid.uuid4()
BRIEFING_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _make_briefing(
    briefing_id: uuid.UUID = BRIEFING_ID,
    user_id: uuid.UUID = OWNER_ID,
    title: str = "Morning Briefing",
    content: str = "Today's summary.\n\nKey highlights here.",
    briefing_type: str = "morning",
) -> MagicMock:
    b = MagicMock()
    b.id = briefing_id
    b.user_id = user_id
    b.title = title
    b.content = content
    b.briefing_type = briefing_type
    b.generated_at = NOW
    b.source_chunks = [uuid.uuid4(), uuid.uuid4()]
    b.source_entities = [uuid.uuid4()]
    return b


# ═══════════════════════════════════════════════════════════════════════════════
# Schema Tests
# ═══════════════════════════════════════════════════════════════════════════════

from pwbs.export.schemas import (
    ConfluenceExportRequest,
    ExportMetadata,
    ExportResult,
)


class TestExportMetadata:
    def test_roundtrip(self) -> None:
        meta = ExportMetadata(
            generated_at=NOW,
            pwbs_version="0.2.0",
            briefing_id=BRIEFING_ID,
            briefing_type="morning",
            title="Test",
            source_count=3,
        )
        assert meta.source_count == 3
        assert meta.pwbs_version == "0.2.0"


class TestExportResult:
    def test_bytes_data(self) -> None:
        meta = ExportMetadata(
            generated_at=NOW,
            briefing_id=BRIEFING_ID,
            briefing_type="morning",
            title="T",
            source_count=0,
        )
        result = ExportResult(
            format="markdown",
            content_type="text/markdown",
            filename="test.md",
            data=b"# Hello",
            metadata=meta,
        )
        assert result.data == b"# Hello"


class TestConfluenceExportRequest:
    def test_valid(self) -> None:
        req = ConfluenceExportRequest(
            briefing_id=BRIEFING_ID,
            space_key="DEV",
        )
        assert req.space_key == "DEV"
        assert req.parent_page_id is None
        assert req.title is None

    def test_empty_space_key_rejected(self) -> None:
        with pytest.raises(Exception):
            ConfluenceExportRequest(
                briefing_id=BRIEFING_ID,
                space_key="",
            )

    def test_with_overrides(self) -> None:
        req = ConfluenceExportRequest(
            briefing_id=BRIEFING_ID,
            space_key="TEAM",
            parent_page_id="12345",
            title="Custom Title",
        )
        assert req.title == "Custom Title"


# ═══════════════════════════════════════════════════════════════════════════════
# Strategy Tests
# ═══════════════════════════════════════════════════════════════════════════════

from pwbs.export.strategies import (
    ConfluenceExportStrategy,
    MarkdownExportStrategy,
    PdfExportStrategy,
    _sanitize_filename,
    build_metadata,
    get_strategy,
)


def _meta() -> ExportMetadata:
    return ExportMetadata(
        generated_at=NOW,
        briefing_id=BRIEFING_ID,
        briefing_type="morning",
        title="Morning Briefing",
        source_count=2,
    )


class TestMarkdownExportStrategy:
    def test_basic_export(self) -> None:
        strategy = MarkdownExportStrategy()
        result = strategy.export(
            title="Morning Briefing",
            content="Good morning! Here is your briefing.",
            metadata=_meta(),
            sources=["Chunk: abc-123", "Entity: xyz-789"],
        )
        assert result.format == "markdown"
        assert result.content_type == "text/markdown; charset=utf-8"
        text = result.data.decode("utf-8")
        assert "# Morning Briefing" in text
        assert "Good morning!" in text
        assert "Quellenverzeichnis" in text
        assert "1. Chunk: abc-123" in text

    def test_no_sources(self) -> None:
        strategy = MarkdownExportStrategy()
        result = strategy.export(
            title="Briefing",
            content="Content here.",
            metadata=_meta(),
            sources=[],
        )
        text = result.data.decode("utf-8")
        assert "Quellenverzeichnis" not in text

    def test_filename_extension(self) -> None:
        strategy = MarkdownExportStrategy()
        result = strategy.export(
            title="Test Export",
            content="x",
            metadata=_meta(),
            sources=[],
        )
        assert result.filename.endswith(".md")


class TestPdfExportStrategy:
    def test_html_build(self) -> None:
        html_output = PdfExportStrategy._build_html(
            title="Test PDF",
            content="Line one.\n\nLine two.",
            metadata=_meta(),
            sources=["Source 1", "Source 2"],
        )
        assert "<title>Test PDF</title>" in html_output
        assert "Quellenverzeichnis" in html_output
        assert "<li>Source 1</li>" in html_output
        assert "</p><p>" in html_output  # paragraph separation

    def test_html_build_no_sources(self) -> None:
        html_output = PdfExportStrategy._build_html(
            title="No Sources",
            content="Just text.",
            metadata=_meta(),
            sources=[],
        )
        assert "Quellenverzeichnis" not in html_output

    def test_html_escaping(self) -> None:
        html_output = PdfExportStrategy._build_html(
            title="<script>alert('xss')</script>",
            content="Content with <b>html</b>",
            metadata=_meta(),
            sources=["<img src=x>"],
        )
        assert "<script>" not in html_output
        assert "&lt;script&gt;" in html_output
        assert "&lt;b&gt;html&lt;/b&gt;" in html_output


class TestConfluenceExportStrategy:
    def test_basic_export(self) -> None:
        strategy = ConfluenceExportStrategy()
        result = strategy.export(
            title="Confluence Page",
            content="Summary of the week.",
            metadata=_meta(),
            sources=["Source A"],
        )
        assert result.format == "confluence"
        assert result.content_type == "application/xhtml+xml; charset=utf-8"
        body = result.data.decode("utf-8")
        assert "<h1>Confluence Page</h1>" in body
        assert "Quellenverzeichnis" in body
        assert "<li>Source A</li>" in body

    def test_no_sources(self) -> None:
        strategy = ConfluenceExportStrategy()
        result = strategy.export(
            title="Title",
            content="Text",
            metadata=_meta(),
            sources=[],
        )
        body = result.data.decode("utf-8")
        assert "Quellenverzeichnis" not in body

    def test_filename(self) -> None:
        strategy = ConfluenceExportStrategy()
        result = strategy.export(
            title="My Page",
            content="x",
            metadata=_meta(),
            sources=[],
        )
        assert result.filename.endswith(".xhtml")


class TestGetStrategy:
    def test_markdown(self) -> None:
        s = get_strategy("markdown")
        assert isinstance(s, MarkdownExportStrategy)

    def test_pdf(self) -> None:
        s = get_strategy("pdf")
        assert isinstance(s, PdfExportStrategy)

    def test_confluence(self) -> None:
        s = get_strategy("confluence")
        assert isinstance(s, ConfluenceExportStrategy)

    def test_case_insensitive(self) -> None:
        s = get_strategy("Markdown")
        assert isinstance(s, MarkdownExportStrategy)

    def test_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported export format"):
            get_strategy("docx")


class TestBuildMetadata:
    def test_fields(self) -> None:
        meta = build_metadata(
            briefing_id=BRIEFING_ID,
            briefing_type="weekly",
            title="Weekly",
            generated_at=NOW,
            source_count=5,
        )
        assert meta.briefing_id == BRIEFING_ID
        assert meta.source_count == 5
        assert meta.briefing_type == "weekly"


class TestSanitizeFilename:
    def test_normal(self) -> None:
        assert _sanitize_filename("Hello World") == "Hello World"

    def test_special_chars(self) -> None:
        result = _sanitize_filename("Test/File:Name?")
        assert "/" not in result
        assert ":" not in result
        assert "?" not in result

    def test_empty_string(self) -> None:
        assert _sanitize_filename("") == "export"

    def test_long_name_truncated(self) -> None:
        result = _sanitize_filename("A" * 200)
        assert len(result) <= 100


# ═══════════════════════════════════════════════════════════════════════════════
# Router Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRouterRegistration:
    def test_export_router_has_routes(self) -> None:
        from pwbs.api.v1.routes.export import router

        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert "/api/v1/briefings/{briefing_id}/export" in paths
        assert "/api/v1/export/confluence" in paths

    def test_router_prefix(self) -> None:
        from pwbs.api.v1.routes.export import router

        assert router.prefix == "/api/v1"

    def test_router_tags(self) -> None:
        from pwbs.api.v1.routes.export import router

        assert "export" in router.tags


class TestBuildSourceList:
    def test_with_chunks_and_entities(self) -> None:
        from pwbs.api.v1.routes.export import _build_source_list

        briefing = _make_briefing()
        sources = _build_source_list(briefing)
        assert len(sources) == 3  # 2 chunks + 1 entity
        assert sources[0].startswith("Chunk:")
        assert sources[2].startswith("Entity:")

    def test_no_sources(self) -> None:
        from pwbs.api.v1.routes.export import _build_source_list

        briefing = _make_briefing()
        briefing.source_chunks = []
        briefing.source_entities = None
        sources = _build_source_list(briefing)
        assert sources == []


class TestGetBriefingForUser:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        from pwbs.api.v1.routes.export import _get_briefing_for_user

        db = AsyncMock()
        briefing = _make_briefing()
        db.get.return_value = briefing
        result = await _get_briefing_for_user(db, BRIEFING_ID, OWNER_ID)
        assert result is briefing

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.export import _get_briefing_for_user

        db = AsyncMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await _get_briefing_for_user(db, BRIEFING_ID, OWNER_ID)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_owner(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.export import _get_briefing_for_user

        db = AsyncMock()
        briefing = _make_briefing()
        db.get.return_value = briefing
        other_user = uuid.uuid4()
        with pytest.raises(HTTPException) as exc_info:
            await _get_briefing_for_user(db, BRIEFING_ID, other_user)
        assert exc_info.value.status_code == 404
