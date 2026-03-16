"""Pydantic schemas for knowledge snapshots (TASK-162)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Snapshot Data Schemas ─────────────────────────────────────────


class SnapshotEntity(BaseModel):
    """Entity captured in a snapshot."""

    id: str
    entity_type: str
    name: str
    normalized_name: str
    mention_count: int


class SnapshotRelationship(BaseModel):
    """Relationship between entities in a snapshot."""

    source_id: str
    target_id: str
    relation_type: str = "co_mentioned"
    weight: int = 1


class SnapshotTheme(BaseModel):
    """Top theme in a snapshot."""

    name: str
    mention_count: int


# ── API Request/Response Schemas ─────────────────────────────────


class SnapshotCreateRequest(BaseModel):
    """Request to create a manual snapshot."""

    label: str = Field(default="", max_length=200)


class SnapshotResponse(BaseModel):
    """Response for a single snapshot."""

    id: UUID
    label: str
    trigger: str
    entity_count: int
    relationship_count: int
    captured_at: datetime
    created_at: datetime


class SnapshotDetailResponse(SnapshotResponse):
    """Full snapshot with data."""

    entities: list[SnapshotEntity]
    relationships: list[SnapshotRelationship]
    top_themes: list[SnapshotTheme]


class SnapshotListResponse(BaseModel):
    """Response for listing snapshots."""

    snapshots: list[SnapshotResponse]
    total: int


# ── Diff Schemas ─────────────────────────────────────────────────


class EntityChange(BaseModel):
    """An entity that was added or removed between snapshots."""

    id: str
    entity_type: str
    name: str
    mention_count: int


class RelationshipChange(BaseModel):
    """A relationship that changed between snapshots."""

    source_id: str
    target_id: str
    relation_type: str
    old_weight: int | None = None
    new_weight: int | None = None
    change: str  # "added", "removed", "changed"


class ThemeShift(BaseModel):
    """A top theme shift between snapshots."""

    name: str
    old_count: int
    new_count: int
    delta: int


class SnapshotDiffResponse(BaseModel):
    """Structured diff between two snapshots."""

    snapshot_a_id: UUID
    snapshot_b_id: UUID
    snapshot_a_date: datetime
    snapshot_b_date: datetime
    added_entities: list[EntityChange]
    removed_entities: list[EntityChange]
    added_relationships: list[RelationshipChange]
    removed_relationships: list[RelationshipChange]
    top_theme_shifts: list[ThemeShift]
    stats: dict[str, object]
