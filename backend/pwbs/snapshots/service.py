"""Knowledge Snapshot service (TASK-162).

Captures the current state of a user's knowledge graph from PostgreSQL,
computes diffs between snapshots, and manages the rolling window.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.entity import Entity, EntityMention
from pwbs.snapshots.models import KnowledgeSnapshot
from pwbs.snapshots.schemas import (
    EntityChange,
    RelationshipChange,
    SnapshotDiffResponse,
    ThemeShift,
)

logger = logging.getLogger(__name__)

MAX_SNAPSHOTS_PER_USER = 52  # 1-year rolling window


async def capture_snapshot(
    db: AsyncSession,
    *,
    user_id: UUID,
    label: str = "",
    trigger: str = "manual",
) -> KnowledgeSnapshot:
    """Capture a point-in-time snapshot of the user's knowledge graph.

    Queries PostgreSQL entities and entity_mentions to build the snapshot.
    Neo4j is not required (MVP-constraint: optional).
    """
    # 1. Fetch all entities for the user
    entity_stmt = (
        select(Entity).where(Entity.user_id == user_id).order_by(Entity.mention_count.desc())
    )
    entity_result = await db.execute(entity_stmt)
    entities = entity_result.scalars().all()

    entity_list: list[dict[str, Any]] = []
    entity_ids: set[str] = set()
    for e in entities:
        entity_list.append(
            {
                "id": str(e.id),
                "entity_type": e.entity_type,
                "name": e.name,
                "normalized_name": e.normalized_name,
                "mention_count": e.mention_count,
            }
        )
        entity_ids.add(str(e.id))

    # 2. Derive relationships from co-occurrences in entity_mentions
    # Two entities are "co_mentioned" if they share at least one chunk
    relationships: list[dict[str, Any]] = []
    if entity_ids:
        # Find pairs sharing chunks via self-join
        from sqlalchemy import and_
        from sqlalchemy.orm import aliased

        em1 = aliased(EntityMention)
        em2 = aliased(EntityMention)

        co_stmt = (
            select(
                em1.entity_id.label("source_id"),
                em2.entity_id.label("target_id"),
                func.count().label("weight"),
            )
            .join(em2, and_(em1.chunk_id == em2.chunk_id, em1.entity_id < em2.entity_id))
            .where(
                em1.entity_id.in_([e["id"] for e in entity_list]),
                em2.entity_id.in_([e["id"] for e in entity_list]),
            )
            .group_by(em1.entity_id, em2.entity_id)
            .order_by(func.count().desc())
            .limit(500)  # Cap relationships
        )
        co_result = await db.execute(co_stmt)
        for row in co_result.all():
            relationships.append(
                {
                    "source_id": str(row.source_id),
                    "target_id": str(row.target_id),
                    "relation_type": "co_mentioned",
                    "weight": row.weight,
                }
            )

    # 3. Top themes (entities with most mentions)
    top_themes = [
        {"name": e["name"], "mention_count": e["mention_count"]} for e in entity_list[:10]
    ]

    snapshot_data: dict[str, Any] = {
        "entities": entity_list,
        "relationships": relationships,
        "top_themes": top_themes,
    }

    snapshot = KnowledgeSnapshot(
        user_id=user_id,
        label=label,
        trigger=trigger,
        entity_count=len(entity_list),
        relationship_count=len(relationships),
        snapshot_data=snapshot_data,
        captured_at=datetime.now(tz=timezone.utc),
    )
    db.add(snapshot)
    await db.flush()

    # 4. Enforce rolling window
    await _enforce_rolling_window(db, user_id)

    return snapshot


async def _enforce_rolling_window(
    db: AsyncSession,
    user_id: UUID,
    max_count: int = MAX_SNAPSHOTS_PER_USER,
) -> int:
    """Delete oldest snapshots beyond the rolling window. Returns count deleted."""
    count_stmt = (
        select(func.count())
        .select_from(KnowledgeSnapshot)
        .where(KnowledgeSnapshot.user_id == user_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    if total <= max_count:
        return 0

    excess = total - max_count
    oldest_stmt = (
        select(KnowledgeSnapshot.id)
        .where(KnowledgeSnapshot.user_id == user_id)
        .order_by(KnowledgeSnapshot.captured_at.asc())
        .limit(excess)
    )
    oldest_ids = [row[0] for row in (await db.execute(oldest_stmt)).all()]

    if oldest_ids:
        await db.execute(delete(KnowledgeSnapshot).where(KnowledgeSnapshot.id.in_(oldest_ids)))

    return len(oldest_ids)


def compute_diff(
    snapshot_a: KnowledgeSnapshot,
    snapshot_b: KnowledgeSnapshot,
) -> SnapshotDiffResponse:
    """Compute a structured diff between two snapshots.

    Snapshot A is the older one, B is the newer one.
    """
    data_a = snapshot_a.snapshot_data
    data_b = snapshot_b.snapshot_data

    entities_a = {e["id"]: e for e in data_a.get("entities", [])}
    entities_b = {e["id"]: e for e in data_b.get("entities", [])}

    # Added / Removed entities
    added_ids = set(entities_b.keys()) - set(entities_a.keys())
    removed_ids = set(entities_a.keys()) - set(entities_b.keys())

    added_entities = [
        EntityChange(
            id=entities_b[eid]["id"],
            entity_type=entities_b[eid]["entity_type"],
            name=entities_b[eid]["name"],
            mention_count=entities_b[eid]["mention_count"],
        )
        for eid in added_ids
    ]
    removed_entities = [
        EntityChange(
            id=entities_a[eid]["id"],
            entity_type=entities_a[eid]["entity_type"],
            name=entities_a[eid]["name"],
            mention_count=entities_a[eid]["mention_count"],
        )
        for eid in removed_ids
    ]

    # Relationship changes
    def _rel_key(r: dict[str, Any]) -> str:
        return f"{r['source_id']}:{r['target_id']}"

    rels_a = {_rel_key(r): r for r in data_a.get("relationships", [])}
    rels_b = {_rel_key(r): r for r in data_b.get("relationships", [])}

    added_rels: list[RelationshipChange] = []
    removed_rels: list[RelationshipChange] = []

    for key in set(rels_b.keys()) - set(rels_a.keys()):
        r = rels_b[key]
        added_rels.append(
            RelationshipChange(
                source_id=r["source_id"],
                target_id=r["target_id"],
                relation_type=r.get("relation_type", "co_mentioned"),
                new_weight=r.get("weight"),
                change="added",
            )
        )

    for key in set(rels_a.keys()) - set(rels_b.keys()):
        r = rels_a[key]
        removed_rels.append(
            RelationshipChange(
                source_id=r["source_id"],
                target_id=r["target_id"],
                relation_type=r.get("relation_type", "co_mentioned"),
                old_weight=r.get("weight"),
                change="removed",
            )
        )

    # Top 5 theme shifts (entities present in both, ranked by |delta|)
    theme_shifts: list[ThemeShift] = []
    common_ids = set(entities_a.keys()) & set(entities_b.keys())
    deltas: list[tuple[str, int, int, int]] = []
    for eid in common_ids:
        old_count = entities_a[eid].get("mention_count", 0)
        new_count = entities_b[eid].get("mention_count", 0)
        delta = new_count - old_count
        if delta != 0:
            deltas.append((entities_b[eid]["name"], old_count, new_count, delta))

    deltas.sort(key=lambda x: abs(x[3]), reverse=True)
    for name, old_c, new_c, d in deltas[:5]:
        theme_shifts.append(
            ThemeShift(
                name=name,
                old_count=old_c,
                new_count=new_c,
                delta=d,
            )
        )

    stats: dict[str, object] = {
        "entities_added": len(added_entities),
        "entities_removed": len(removed_entities),
        "relationships_added": len(added_rels),
        "relationships_removed": len(removed_rels),
        "entity_count_a": snapshot_a.entity_count,
        "entity_count_b": snapshot_b.entity_count,
    }

    return SnapshotDiffResponse(
        snapshot_a_id=snapshot_a.id,
        snapshot_b_id=snapshot_b.id,
        snapshot_a_date=snapshot_a.captured_at,
        snapshot_b_date=snapshot_b.captured_at,
        added_entities=added_entities,
        removed_entities=removed_entities,
        added_relationships=added_rels,
        removed_relationships=removed_rels,
        top_theme_shifts=theme_shifts,
        stats=stats,
    )
