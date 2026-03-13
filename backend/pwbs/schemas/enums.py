"""Shared enums for PWBS Pydantic schemas (TASK-032)."""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """Supported data-source types.

    Extensible: add new members as new connectors are implemented.
    """

    GOOGLE_CALENDAR = "google_calendar"
    NOTION = "notion"
    OBSIDIAN = "obsidian"
    ZOOM = "zoom"


class ContentType(str, Enum):
    """Content format of the normalised document body."""

    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"
    HTML = "html"
