"""Export strategies – Strategy pattern for briefing exports (TASK-164).

Each strategy converts a Briefing + metadata into a specific output format.
"""

from __future__ import annotations

import html
import io
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from pwbs.export.schemas import ExportMetadata, ExportResult

logger = logging.getLogger(__name__)

_PWBS_VERSION = "0.2.0"


class ExportStrategy(ABC):
    """Base class for export format strategies."""

    @abstractmethod
    def export(
        self,
        title: str,
        content: str,
        metadata: ExportMetadata,
        sources: list[str],
    ) -> ExportResult:
        """Convert briefing data into the target format."""
        ...


# ── Markdown ──────────────────────────────────────────────────────────────────


class MarkdownExportStrategy(ExportStrategy):
    """Export briefing as Markdown with source references as links."""

    def export(
        self,
        title: str,
        content: str,
        metadata: ExportMetadata,
        sources: list[str],
    ) -> ExportResult:
        lines: list[str] = [
            f"# {title}",
            "",
            f"*Generiert: {metadata.generated_at.isoformat()} | "
            f"PWBS {metadata.pwbs_version} | "
            f"Typ: {metadata.briefing_type}*",
            "",
            "---",
            "",
            content,
            "",
        ]

        if sources:
            lines.append("---")
            lines.append("")
            lines.append("## Quellenverzeichnis")
            lines.append("")
            for i, src in enumerate(sources, 1):
                lines.append(f"{i}. {src}")
            lines.append("")

        md_text = "\n".join(lines)

        return ExportResult(
            format="markdown",
            content_type="text/markdown; charset=utf-8",
            filename=f"{_sanitize_filename(title)}.md",
            data=md_text.encode("utf-8"),
            metadata=metadata,
        )


# ── PDF ───────────────────────────────────────────────────────────────────────


class PdfExportStrategy(ExportStrategy):
    """Export briefing as PDF.

    Uses a lightweight HTML→PDF approach. Requires `weasyprint` at
    runtime; raises ImportError with a clear message if missing.
    """

    def export(
        self,
        title: str,
        content: str,
        metadata: ExportMetadata,
        sources: list[str],
    ) -> ExportResult:
        html_content = self._build_html(title, content, metadata, sources)
        pdf_bytes = self._render_pdf(html_content)

        return ExportResult(
            format="pdf",
            content_type="application/pdf",
            filename=f"{_sanitize_filename(title)}.pdf",
            data=pdf_bytes,
            metadata=metadata,
        )

    @staticmethod
    def _build_html(
        title: str,
        content: str,
        metadata: ExportMetadata,
        sources: list[str],
    ) -> str:
        escaped_title = html.escape(title)
        escaped_content = html.escape(content)
        # Convert newlines to <br> for basic formatting
        formatted_content = escaped_content.replace("\n\n", "</p><p>").replace("\n", "<br>")

        sources_html = ""
        if sources:
            items = "".join(f"<li>{html.escape(s)}</li>" for s in sources)
            sources_html = f"<hr><h2>Quellenverzeichnis</h2><ol>{items}</ol>"

        return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{escaped_title}</title>
<style>
  body {{ font-family: 'Helvetica', 'Arial', sans-serif; margin: 2cm; font-size: 11pt; line-height: 1.5; }}
  h1 {{ color: #1a1a2e; border-bottom: 2px solid #0f3460; padding-bottom: 0.3em; }}
  h2 {{ color: #0f3460; }}
  .meta {{ color: #666; font-size: 9pt; margin-bottom: 1.5em; }}
  ol {{ padding-left: 1.5em; }}
  li {{ margin-bottom: 0.3em; }}
</style>
</head>
<body>
<h1>{escaped_title}</h1>
<div class="meta">Generiert: {metadata.generated_at.isoformat()} | PWBS {metadata.pwbs_version} | Typ: {metadata.briefing_type}</div>
<p>{formatted_content}</p>
{sources_html}
</body>
</html>"""

    @staticmethod
    def _render_pdf(html_content: str) -> bytes:
        try:
            from weasyprint import HTML  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "PDF export requires 'weasyprint'. Install it with: pip install weasyprint"
            )
        buf = io.BytesIO()
        HTML(string=html_content).write_pdf(buf)
        return buf.getvalue()


# ── Confluence Wiki Markup ────────────────────────────────────────────────────


class ConfluenceExportStrategy(ExportStrategy):
    """Export briefing as Confluence Storage Format (XHTML).

    Returns the storage-format body ready to be posted via Confluence REST API.
    """

    def export(
        self,
        title: str,
        content: str,
        metadata: ExportMetadata,
        sources: list[str],
    ) -> ExportResult:
        escaped_content = html.escape(content)
        body_parts: list[str] = [
            f"<h1>{html.escape(title)}</h1>",
            f"<p><em>Generiert: {metadata.generated_at.isoformat()} | "
            f"PWBS {metadata.pwbs_version} | "
            f"Typ: {metadata.briefing_type}</em></p>",
            "<hr/>",
        ]

        # Convert paragraphs
        paragraphs = escaped_content.split("\n\n")
        for para in paragraphs:
            body_parts.append(f"<p>{para.replace(chr(10), '<br/>')}</p>")

        if sources:
            body_parts.append("<hr/>")
            body_parts.append("<h2>Quellenverzeichnis</h2>")
            body_parts.append("<ol>")
            for src in sources:
                body_parts.append(f"<li>{html.escape(src)}</li>")
            body_parts.append("</ol>")

        storage_body = "\n".join(body_parts)

        return ExportResult(
            format="confluence",
            content_type="application/xhtml+xml; charset=utf-8",
            filename=f"{_sanitize_filename(title)}.xhtml",
            data=storage_body.encode("utf-8"),
            metadata=metadata,
        )


# ── Factory ───────────────────────────────────────────────────────────────────

_STRATEGIES: dict[str, type[ExportStrategy]] = {
    "markdown": MarkdownExportStrategy,
    "pdf": PdfExportStrategy,
    "confluence": ConfluenceExportStrategy,
}


def get_strategy(format_name: str) -> ExportStrategy:
    """Return the export strategy for the given format name.

    Raises ValueError if format is unsupported.
    """
    cls = _STRATEGIES.get(format_name.lower())
    if cls is None:
        supported = ", ".join(sorted(_STRATEGIES.keys()))
        raise ValueError(f"Unsupported export format: '{format_name}'. Supported: {supported}")
    return cls()


def build_metadata(
    briefing_id: object,
    briefing_type: str,
    title: str,
    generated_at: datetime,
    source_count: int,
) -> ExportMetadata:
    """Build ExportMetadata from briefing fields."""
    return ExportMetadata(
        generated_at=generated_at,
        pwbs_version=_PWBS_VERSION,
        briefing_id=briefing_id,  # type: ignore[arg-type]
        briefing_type=briefing_type,
        title=title,
        source_count=source_count,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Replace unsafe chars with underscore
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
    return safe.strip()[:100] or "export"
