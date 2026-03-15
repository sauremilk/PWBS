"""Pydantic v2 schemas for search API contracts (TASK-035, TASK-182)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from pwbs.schemas.briefing import SourceRef
from pwbs.schemas.enums import SourceType


class SearchFilters(BaseModel):
    """Optional filters for search requests."""

    source_types: list[SourceType] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    entity_ids: list[UUID] | None = None


class SearchResult(BaseModel):
    """A single search hit."""

    chunk_id: UUID
    doc_title: str
    source_type: SourceType
    date: datetime
    content: str
    score: float = Field(ge=0.0, le=1.0)
    entities: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    """Incoming search query payload."""

    query: str = Field(min_length=1)
    filters: SearchFilters | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResponse(BaseModel):
    """Search response including optional RAG answer."""

    results: list[SearchResult]
    answer: str | None = None
    sources: list[SourceRef] = Field(default_factory=list)
    confidence: float | None = None


# ---------------------------------------------------------------------------
# Auto-Complete (TASK-182)
# ---------------------------------------------------------------------------


class AutoCompleteItem(BaseModel):
    """A single auto-complete suggestion."""

    entity_id: UUID
    name: str
    entity_type: str


class AutoCompleteResponse(BaseModel):
    """Auto-complete response."""

    suggestions: list[AutoCompleteItem]


# ---------------------------------------------------------------------------
# Saved Searches (TASK-182)
# ---------------------------------------------------------------------------


class SavedSearchCreate(BaseModel):
    """Create a saved search."""

    name: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1)
    filters: SearchFilters | None = None


class SavedSearchOut(BaseModel):
    """Saved search response item."""

    id: UUID
    name: str
    query: str
    filters_json: dict | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Search History (TASK-182)
# ---------------------------------------------------------------------------


class SearchHistoryItem(BaseModel):
    """A single search history entry."""

    id: UUID
    query: str
    result_count: int
    created_at: datetime


class SearchHistoryResponse(BaseModel):
    """Search history response."""

    items: list[SearchHistoryItem]
