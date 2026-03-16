"""Tests for Knowledge Snapshots – TASK-162.

Sections:
  1. Schema validation (SnapshotEntity, SnapshotRelationship, create request, diff)
  2. Service: capture_snapshot, compute_diff, _enforce_rolling_window
  3. Celery task registration & beat schedule
  4. API router configuration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# ── Section 1: Schema Validation ─────────────────────────────────────────────


class TestSnapshotEntitySchema:
    """Pydantic schema validation for SnapshotEntity."""

    def test_valid_entity(self) -> None:
        from pwbs.snapshots.schemas import SnapshotEntity

        e = SnapshotEntity(
            id="abc-123",
            entity_type="Person",
            name="Alice",
            normalized_name="alice",
            mention_count=5,
        )
        assert e.id == "abc-123"
        assert e.entity_type == "Person"
        assert e.mention_count == 5

    def test_entity_requires_all_fields(self) -> None:
        from pwbs.snapshots.schemas import SnapshotEntity

        with pytest.raises(ValidationError):
            SnapshotEntity(id="x", entity_type="Person")  # type: ignore[call-arg]


class TestSnapshotRelationshipSchema:
    """Pydantic schema validation for SnapshotRelationship."""

    def test_defaults(self) -> None:
        from pwbs.snapshots.schemas import SnapshotRelationship

        r = SnapshotRelationship(source_id="a", target_id="b")
        assert r.relation_type == "co_mentioned"
        assert r.weight == 1

    def test_custom_values(self) -> None:
        from pwbs.snapshots.schemas import SnapshotRelationship

        r = SnapshotRelationship(
            source_id="a", target_id="b", relation_type="discussed_in", weight=3
        )
        assert r.relation_type == "discussed_in"
        assert r.weight == 3


class TestSnapshotThemeSchema:
    def test_valid(self) -> None:
        from pwbs.snapshots.schemas import SnapshotTheme

        t = SnapshotTheme(name="AI", mention_count=42)
        assert t.name == "AI"
        assert t.mention_count == 42


class TestSnapshotCreateRequestSchema:
    def test_defaults(self) -> None:
        from pwbs.snapshots.schemas import SnapshotCreateRequest

        req = SnapshotCreateRequest()
        assert req.label == ""

    def test_label_max_length(self) -> None:
        from pwbs.snapshots.schemas import SnapshotCreateRequest

        # max_length=200
        with pytest.raises(ValidationError):
            SnapshotCreateRequest(label="x" * 201)

    def test_valid_label(self) -> None:
        from pwbs.snapshots.schemas import SnapshotCreateRequest

        req = SnapshotCreateRequest(label="Sprint 42 Review")
        assert req.label == "Sprint 42 Review"


class TestSnapshotResponseSchema:
    def test_all_fields(self) -> None:
        from pwbs.snapshots.schemas import SnapshotResponse

        now = datetime.now(timezone.utc)
        uid = uuid.uuid4()
        resp = SnapshotResponse(
            id=uid,
            label="test",
            trigger="manual",
            entity_count=10,
            relationship_count=5,
            captured_at=now,
            created_at=now,
        )
        assert resp.id == uid
        assert resp.trigger == "manual"


class TestSnapshotDetailResponseSchema:
    def test_includes_data(self) -> None:
        from pwbs.snapshots.schemas import (
            SnapshotDetailResponse,
            SnapshotEntity,
            SnapshotRelationship,
            SnapshotTheme,
        )

        now = datetime.now(timezone.utc)
        detail = SnapshotDetailResponse(
            id=uuid.uuid4(),
            label="v1",
            trigger="weekly_auto",
            entity_count=1,
            relationship_count=0,
            captured_at=now,
            created_at=now,
            entities=[
                SnapshotEntity(
                    id="e1",
                    entity_type="Topic",
                    name="ML",
                    normalized_name="ml",
                    mention_count=3,
                )
            ],
            relationships=[],
            top_themes=[SnapshotTheme(name="ML", mention_count=3)],
        )
        assert len(detail.entities) == 1
        assert detail.top_themes[0].name == "ML"


class TestSnapshotListResponseSchema:
    def test_empty_list(self) -> None:
        from pwbs.snapshots.schemas import SnapshotListResponse

        resp = SnapshotListResponse(snapshots=[], total=0)
        assert resp.total == 0
        assert resp.snapshots == []


class TestSnapshotDiffSchemas:
    def test_entity_change(self) -> None:
        from pwbs.snapshots.schemas import EntityChange

        ec = EntityChange(id="e1", entity_type="Person", name="Alice", mention_count=5)
        assert ec.name == "Alice"

    def test_relationship_change(self) -> None:
        from pwbs.snapshots.schemas import RelationshipChange

        rc = RelationshipChange(
            source_id="a",
            target_id="b",
            relation_type="co_mentioned",
            new_weight=3,
            change="added",
        )
        assert rc.change == "added"
        assert rc.old_weight is None

    def test_theme_shift(self) -> None:
        from pwbs.snapshots.schemas import ThemeShift

        ts = ThemeShift(name="AI", old_count=10, new_count=25, delta=15)
        assert ts.delta == 15

    def test_diff_response(self) -> None:
        from pwbs.snapshots.schemas import SnapshotDiffResponse

        now = datetime.now(timezone.utc)
        diff = SnapshotDiffResponse(
            snapshot_a_id=uuid.uuid4(),
            snapshot_b_id=uuid.uuid4(),
            snapshot_a_date=now,
            snapshot_b_date=now,
            added_entities=[],
            removed_entities=[],
            added_relationships=[],
            removed_relationships=[],
            top_theme_shifts=[],
            stats={"entity_delta": 0},
        )
        assert diff.stats["entity_delta"] == 0


# ── Section 2: Service ───────────────────────────────────────────────────────


class TestComputeDiff:
    """Tests for the compute_diff function."""

    def _make_snapshot(
        self,
        *,
        user_id: uuid.UUID | None = None,
        entities: list[dict[str, Any]] | None = None,
        relationships: list[dict[str, Any]] | None = None,
        top_themes: list[dict[str, Any]] | None = None,
        entity_count: int = 0,
        relationship_count: int = 0,
    ) -> MagicMock:
        uid = user_id or uuid.uuid4()
        snap = MagicMock()
        snap.id = uuid.uuid4()
        snap.user_id = uid
        snap.label = "test"
        snap.trigger = "manual"
        snap.entity_count = entity_count
        snap.relationship_count = relationship_count
        snap.captured_at = datetime.now(timezone.utc)
        snap.created_at = datetime.now(timezone.utc)
        snap.snapshot_data = {
            "entities": entities or [],
            "relationships": relationships or [],
            "top_themes": top_themes or [],
        }
        return snap

    def test_identical_snapshots(self) -> None:
        from pwbs.snapshots.service import compute_diff

        entities = [
            {
                "id": "e1",
                "entity_type": "Person",
                "name": "Alice",
                "normalized_name": "alice",
                "mention_count": 3,
            }
        ]
        a = self._make_snapshot(entities=entities, entity_count=1)
        b = self._make_snapshot(entities=entities, entity_count=1)

        diff = compute_diff(a, b)
        assert len(diff.added_entities) == 0
        assert len(diff.removed_entities) == 0
        assert diff.stats["entities_added"] == 0
        assert diff.stats["entities_removed"] == 0

    def test_added_entity(self) -> None:
        from pwbs.snapshots.service import compute_diff

        e1 = {
            "id": "e1",
            "entity_type": "Person",
            "name": "Alice",
            "normalized_name": "alice",
            "mention_count": 3,
        }
        e2 = {
            "id": "e2",
            "entity_type": "Topic",
            "name": "ML",
            "normalized_name": "ml",
            "mention_count": 5,
        }
        a = self._make_snapshot(entities=[e1], entity_count=1)
        b = self._make_snapshot(entities=[e1, e2], entity_count=2)

        diff = compute_diff(a, b)
        assert len(diff.added_entities) == 1
        assert diff.added_entities[0].id == "e2"
        assert len(diff.removed_entities) == 0

    def test_removed_entity(self) -> None:
        from pwbs.snapshots.service import compute_diff

        e1 = {
            "id": "e1",
            "entity_type": "Person",
            "name": "Alice",
            "normalized_name": "alice",
            "mention_count": 3,
        }
        a = self._make_snapshot(entities=[e1], entity_count=1)
        b = self._make_snapshot(entities=[], entity_count=0)

        diff = compute_diff(a, b)
        assert len(diff.removed_entities) == 1
        assert diff.removed_entities[0].id == "e1"

    def test_added_relationship(self) -> None:
        from pwbs.snapshots.service import compute_diff

        r1 = {
            "source_id": "e1",
            "target_id": "e2",
            "relation_type": "co_mentioned",
            "weight": 2,
        }
        a = self._make_snapshot(relationships=[], relationship_count=0)
        b = self._make_snapshot(relationships=[r1], relationship_count=1)

        diff = compute_diff(a, b)
        assert len(diff.added_relationships) == 1
        assert diff.added_relationships[0].source_id == "e1"

    def test_removed_relationship(self) -> None:
        from pwbs.snapshots.service import compute_diff

        r1 = {
            "source_id": "e1",
            "target_id": "e2",
            "relation_type": "co_mentioned",
            "weight": 2,
        }
        a = self._make_snapshot(relationships=[r1], relationship_count=1)
        b = self._make_snapshot(relationships=[], relationship_count=0)

        diff = compute_diff(a, b)
        assert len(diff.removed_relationships) == 1

    def test_theme_shifts_sorted_by_abs_delta(self) -> None:
        from pwbs.snapshots.service import compute_diff

        # Theme shifts come from common entity IDs with changed mention_count
        entities_a = [
            {
                "id": "e1",
                "entity_type": "Topic",
                "name": "AI",
                "normalized_name": "ai",
                "mention_count": 10,
            },
            {
                "id": "e2",
                "entity_type": "Topic",
                "name": "Cloud",
                "normalized_name": "cloud",
                "mention_count": 20,
            },
            {
                "id": "e3",
                "entity_type": "Topic",
                "name": "Security",
                "normalized_name": "security",
                "mention_count": 5,
            },
        ]
        entities_b = [
            {
                "id": "e1",
                "entity_type": "Topic",
                "name": "AI",
                "normalized_name": "ai",
                "mention_count": 25,
            },  # +15
            {
                "id": "e2",
                "entity_type": "Topic",
                "name": "Cloud",
                "normalized_name": "cloud",
                "mention_count": 18,
            },  # -2
            {
                "id": "e3",
                "entity_type": "Topic",
                "name": "Security",
                "normalized_name": "security",
                "mention_count": 5,
            },  # 0
        ]
        a = self._make_snapshot(entities=entities_a)
        b = self._make_snapshot(entities=entities_b)

        diff = compute_diff(a, b)
        non_zero_shifts = [s for s in diff.top_theme_shifts if s.delta != 0]
        assert len(non_zero_shifts) >= 1
        # First shift should be the largest absolute delta
        assert non_zero_shifts[0].name == "AI"
        assert non_zero_shifts[0].delta == 15

    def test_empty_snapshots(self) -> None:
        from pwbs.snapshots.service import compute_diff

        a = self._make_snapshot()
        b = self._make_snapshot()

        diff = compute_diff(a, b)
        assert len(diff.added_entities) == 0
        assert len(diff.removed_entities) == 0
        assert len(diff.added_relationships) == 0
        assert len(diff.removed_relationships) == 0
        assert len(diff.top_theme_shifts) == 0

    def test_stats_contains_entity_counts(self) -> None:
        from pwbs.snapshots.service import compute_diff

        a = self._make_snapshot(entity_count=5, relationship_count=3)
        b = self._make_snapshot(entity_count=8, relationship_count=2)

        diff = compute_diff(a, b)
        assert diff.stats["entity_count_a"] == 5
        assert diff.stats["entity_count_b"] == 8
        assert diff.stats["entities_added"] == 0
        assert diff.stats["entities_removed"] == 0

    def test_common_entity_mention_increase_appears_as_shift(self) -> None:
        from pwbs.snapshots.service import compute_diff

        # Theme shifts come from common entities with changed mention_count
        entities_a = [
            {
                "id": "e1",
                "entity_type": "Topic",
                "name": "NewTopic",
                "normalized_name": "newtopic",
                "mention_count": 2,
            },
        ]
        entities_b = [
            {
                "id": "e1",
                "entity_type": "Topic",
                "name": "NewTopic",
                "normalized_name": "newtopic",
                "mention_count": 12,
            },
        ]
        a = self._make_snapshot(entities=entities_a)
        b = self._make_snapshot(entities=entities_b)

        diff = compute_diff(a, b)
        shifts = [s for s in diff.top_theme_shifts if s.name == "NewTopic"]
        assert len(shifts) == 1
        assert shifts[0].old_count == 2
        assert shifts[0].new_count == 12
        assert shifts[0].delta == 10

    def test_common_entity_mention_decrease_appears_as_shift(self) -> None:
        from pwbs.snapshots.service import compute_diff

        entities_a = [
            {
                "id": "e1",
                "entity_type": "Topic",
                "name": "OldTopic",
                "normalized_name": "oldtopic",
                "mention_count": 15,
            },
        ]
        entities_b = [
            {
                "id": "e1",
                "entity_type": "Topic",
                "name": "OldTopic",
                "normalized_name": "oldtopic",
                "mention_count": 7,
            },
        ]
        a = self._make_snapshot(entities=entities_a)
        b = self._make_snapshot(entities=entities_b)

        diff = compute_diff(a, b)
        shifts = [s for s in diff.top_theme_shifts if s.name == "OldTopic"]
        assert len(shifts) == 1
        assert shifts[0].delta == -8


class TestCaptureSnapshot:
    """Tests for capture_snapshot service function."""

    @pytest.mark.asyncio
    async def test_capture_creates_snapshot(self) -> None:
        from pwbs.snapshots.service import capture_snapshot

        user_id = uuid.uuid4()
        entity_id = uuid.uuid4()
        mock_db = AsyncMock()

        # 1st execute: entity query → .scalars().all()
        mock_entity = MagicMock()
        mock_entity.id = entity_id
        mock_entity.entity_type = "Person"
        mock_entity.name = "Alice"
        mock_entity.normalized_name = "alice"
        mock_entity.mention_count = 5

        mock_entity_result = MagicMock()
        mock_entity_result.scalars.return_value.all.return_value = [mock_entity]

        # 2nd execute: co-occurrence query → .all()
        mock_co_result = MagicMock()
        mock_co_result.all.return_value = []

        # 3rd execute: _enforce_rolling_window count → .scalar_one()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_db.execute.side_effect = [
            mock_entity_result,
            mock_co_result,
            mock_count_result,
        ]

        snapshot = await capture_snapshot(mock_db, user_id=user_id, label="test", trigger="manual")

        assert snapshot.user_id == user_id
        assert snapshot.label == "test"
        assert snapshot.trigger == "manual"
        assert snapshot.entity_count == 1
        assert snapshot.snapshot_data["entities"][0]["name"] == "Alice"
        mock_db.add.assert_called_once_with(snapshot)

    @pytest.mark.asyncio
    async def test_capture_with_no_entities(self) -> None:
        from pwbs.snapshots.service import capture_snapshot

        user_id = uuid.uuid4()
        mock_db = AsyncMock()

        # 1st execute: entity query → empty list
        mock_entity_result = MagicMock()
        mock_entity_result.scalars.return_value.all.return_value = []

        # 2nd execute: _enforce_rolling_window count (co-occurrence skipped)
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_db.execute.side_effect = [
            mock_entity_result,
            mock_count_result,
        ]

        snapshot = await capture_snapshot(
            mock_db, user_id=user_id, label="empty", trigger="weekly_auto"
        )

        assert snapshot.entity_count == 0
        assert snapshot.relationship_count == 0
        assert snapshot.snapshot_data["entities"] == []


class TestEnforceRollingWindow:
    """Tests for _enforce_rolling_window."""

    @pytest.mark.asyncio
    async def test_no_deletion_when_under_limit(self) -> None:
        from pwbs.snapshots.service import _enforce_rolling_window

        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 10  # well under 52

        mock_db.execute.return_value = mock_count_result

        await _enforce_rolling_window(mock_db, uuid.uuid4(), max_count=52)

        # Only 1 execute call (the count) - no deletion
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_deletion_when_over_limit(self) -> None:
        from pwbs.snapshots.service import _enforce_rolling_window

        mock_db = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 55  # 3 over limit of 52

        mock_ids_result = MagicMock()
        old_ids = [MagicMock(id=uuid.uuid4()) for _ in range(3)]
        mock_ids_result.all.return_value = old_ids

        mock_db.execute.side_effect = [
            mock_count_result,  # count query
            mock_ids_result,  # oldest IDs query
            MagicMock(),  # delete query
        ]

        await _enforce_rolling_window(mock_db, uuid.uuid4(), max_count=52)

        # count + select oldest + delete = 3 execute calls
        assert mock_db.execute.call_count == 3


# ── Section 3: Celery Task Registration & Beat Schedule ──────────────────────


class TestCelerySnapshotTask:
    """Tests for the Celery snapshot task."""

    def test_task_is_registered(self) -> None:
        # Import triggers task registration
        import pwbs.queue.tasks.snapshots  # noqa: F401
        from pwbs.queue.celery_app import app

        task_name = "pwbs.queue.tasks.snapshots.create_weekly_snapshots"
        assert task_name in app.tasks

    def test_task_config(self) -> None:
        from pwbs.queue.tasks.snapshots import create_weekly_snapshots

        assert create_weekly_snapshots.max_retries == 3
        assert create_weekly_snapshots.queue == "briefing.generate"

    def test_beat_schedule_has_snapshot_entry(self) -> None:
        from pwbs.queue.celery_app import app

        assert "weekly-snapshots" in app.conf.beat_schedule

    def test_beat_schedule_sunday_2am(self) -> None:
        from pwbs.queue.celery_app import app

        schedule = app.conf.beat_schedule["weekly-snapshots"]
        assert schedule["schedule"]["hour"] == "2"
        assert schedule["schedule"]["minute"] == "0"
        assert schedule["schedule"]["day_of_week"] == "0"

    def test_beat_schedule_task_name(self) -> None:
        from pwbs.queue.celery_app import app

        schedule = app.conf.beat_schedule["weekly-snapshots"]
        assert schedule["task"] == "pwbs.queue.tasks.snapshots.create_weekly_snapshots"

    def test_beat_schedule_queue(self) -> None:
        from pwbs.queue.celery_app import app

        schedule = app.conf.beat_schedule["weekly-snapshots"]
        assert schedule["options"]["queue"] == "briefing.generate"


# ── Section 4: API Router Configuration ──────────────────────────────────────


class TestSnapshotsAPIRouter:
    """Tests for the snapshots API router configuration."""

    def test_router_prefix(self) -> None:
        from pwbs.api.v1.routes.snapshots import router

        assert router.prefix == "/api/v1/snapshots"

    def test_router_tags(self) -> None:
        from pwbs.api.v1.routes.snapshots import router

        assert "snapshots" in router.tags

    def test_endpoints_exist(self) -> None:
        from pwbs.api.v1.routes.snapshots import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/api/v1/snapshots/" in paths
        assert "/api/v1/snapshots/{snapshot_id}" in paths
        assert "/api/v1/snapshots/{snapshot_a_id}/diff/{snapshot_b_id}" in paths

    def test_endpoint_methods(self) -> None:
        from pwbs.api.v1.routes.snapshots import router

        method_map: dict[str, set[str]] = {}
        for route in router.routes:  # type: ignore[attr-defined]
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if path not in method_map:
                method_map[path] = set()
            method_map[path].update(methods)

        assert "POST" in method_map.get("/api/v1/snapshots/", set())
        assert "GET" in method_map.get("/api/v1/snapshots/", set())
        assert "GET" in method_map.get("/api/v1/snapshots/{snapshot_id}", set())
        assert "DELETE" in method_map.get("/api/v1/snapshots/{snapshot_id}", set())
        assert "GET" in method_map.get(
            "/api/v1/snapshots/{snapshot_a_id}/diff/{snapshot_b_id}", set()
        )

    def test_router_registered_in_app(self) -> None:
        """Snapshots router is included in the main app."""
        pytest.importorskip("prometheus_client")
        from unittest.mock import patch as mock_patch

        with mock_patch("pwbs.db.postgres.get_engine"):
            from pwbs.api.main import create_app

            app = create_app()
            routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
            assert any("/api/v1/snapshots" in r for r in routes)
