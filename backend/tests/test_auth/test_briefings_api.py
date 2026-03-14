"""Tests for Briefings API endpoints (TASK-089)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.api.v1.routes.briefings import (
    BriefingDetailResponse,
    BriefingListItem,
    BriefingListResponse,
    FeedbackRequest,
    FeedbackResponse,
    GenerateRequest,
    GenerateResponse,
    SourceRefResponse,
    _check_ownership,
    _orm_to_detail,
    _resolve_sources,
    router,
)
from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.models.user import User
from pwbs.schemas.enums import BriefingType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = user_id or USER_ID
    u.email = "test@example.com"
    u.display_name = "Test User"
    return u


def _make_briefing_orm(
    briefing_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    briefing_type: str = "morning",
    title: str = "Morning Briefing",
    content: str = "Your daily briefing content.",
    source_chunks: list[uuid.UUID] | None = None,
    source_entities: list[uuid.UUID] | None = None,
    trigger_context: dict | None = None,
    generated_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> BriefingORM:
    row = MagicMock(spec=BriefingORM)
    row.id = briefing_id or uuid.uuid4()
    row.user_id = user_id or USER_ID
    row.briefing_type = briefing_type
    row.title = title
    row.content = content
    row.source_chunks = source_chunks or []
    row.source_entities = source_entities
    row.trigger_context = trigger_context
    row.generated_at = generated_at or datetime(2026, 3, 14, 6, 30, tzinfo=timezone.utc)
    row.expires_at = expires_at
    return row


# ---------------------------------------------------------------------------
# Test: _check_ownership
# ---------------------------------------------------------------------------


class TestCheckOwnership:
    def test_passes_for_owner(self) -> None:
        row = _make_briefing_orm(user_id=USER_ID)
        _check_ownership(row, USER_ID)  # should not raise

    def test_raises_403_for_other_user(self) -> None:
        from fastapi import HTTPException

        row = _make_briefing_orm(user_id=USER_ID)
        with pytest.raises(HTTPException) as exc_info:
            _check_ownership(row, OTHER_USER_ID)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: _orm_to_detail
# ---------------------------------------------------------------------------


class TestOrmToDetail:
    def test_maps_all_fields(self) -> None:
        bid = uuid.uuid4()
        chunk_id = uuid.uuid4()
        gen_at = datetime(2026, 3, 14, 6, 30, tzinfo=timezone.utc)
        exp_at = datetime(2026, 3, 15, 6, 30, tzinfo=timezone.utc)

        row = _make_briefing_orm(
            briefing_id=bid,
            briefing_type="meeting_prep",
            title="Meeting Prep",
            content="Prepare for the meeting.",
            source_chunks=[chunk_id],
            source_entities=[],
            trigger_context={"event_id": "evt-1"},
            generated_at=gen_at,
            expires_at=exp_at,
        )

        sources = [
            SourceRefResponse(
                chunk_id=chunk_id,
                doc_title="Doc A",
                source_type="notion",
                date=gen_at,
                relevance=0.95,
            )
        ]

        result = _orm_to_detail(row, sources)

        assert result.id == bid
        assert result.briefing_type == "meeting_prep"
        assert result.title == "Meeting Prep"
        assert result.content == "Prepare for the meeting."
        assert result.source_chunks == [chunk_id]
        assert result.sources == sources
        assert result.generated_at == gen_at
        assert result.expires_at == exp_at

    def test_handles_none_collections(self) -> None:
        row = _make_briefing_orm(source_chunks=None, source_entities=None)
        result = _orm_to_detail(row, [])
        assert result.source_chunks == []
        assert result.source_entities == []


# ---------------------------------------------------------------------------
# Test: _resolve_sources
# ---------------------------------------------------------------------------


class TestResolveSources:
    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self) -> None:
        db = AsyncMock()
        result = await _resolve_sources([], USER_ID, db)
        assert result == []

    @pytest.mark.asyncio
    async def test_resolves_chunks_to_source_refs(self) -> None:
        chunk_id = uuid.uuid4()
        doc_created = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)

        mock_row = MagicMock()
        mock_row.id = chunk_id
        mock_row.title = "Test Document"
        mock_row.source_type = "notion"
        mock_row.created_at = doc_created

        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.all.return_value = [mock_row]
        db.execute.return_value = execute_result

        result = await _resolve_sources([chunk_id], USER_ID, db)

        assert len(result) == 1
        assert result[0].chunk_id == chunk_id
        assert result[0].doc_title == "Test Document"
        assert result[0].source_type == "notion"

    @pytest.mark.asyncio
    async def test_untitled_document_gets_default_title(self) -> None:
        chunk_id = uuid.uuid4()
        mock_row = MagicMock()
        mock_row.id = chunk_id
        mock_row.title = None
        mock_row.source_type = "obsidian"
        mock_row.created_at = datetime(2026, 3, 1, tzinfo=timezone.utc)

        db = AsyncMock()
        execute_result = MagicMock()
        execute_result.all.return_value = [mock_row]
        db.execute.return_value = execute_result

        result = await _resolve_sources([chunk_id], USER_ID, db)
        assert result[0].doc_title == "Untitled"


# ---------------------------------------------------------------------------
# Test: Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_generate_request_valid_morning(self) -> None:
        req = GenerateRequest(briefing_type=BriefingType.MORNING)
        assert req.briefing_type == BriefingType.MORNING
        assert req.trigger_context is None

    def test_generate_request_with_context(self) -> None:
        req = GenerateRequest(
            briefing_type=BriefingType.MEETING_PREP,
            trigger_context={"event_id": "evt-123"},
        )
        assert req.trigger_context == {"event_id": "evt-123"}

    def test_feedback_request_positive(self) -> None:
        req = FeedbackRequest(rating="positive", comment="Very helpful!")
        assert req.rating == "positive"
        assert req.comment == "Very helpful!"

    def test_feedback_request_negative(self) -> None:
        req = FeedbackRequest(rating="negative")
        assert req.rating == "negative"
        assert req.comment is None

    def test_feedback_request_invalid_rating(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FeedbackRequest(rating="neutral")

    def test_generate_response_defaults(self) -> None:
        bid = uuid.uuid4()
        resp = GenerateResponse(briefing_id=bid)
        assert resp.status == "generating"

    def test_briefing_list_response(self) -> None:
        resp = BriefingListResponse(briefings=[], total=0, has_more=False)
        assert resp.total == 0
        assert not resp.has_more


# ---------------------------------------------------------------------------
# Test: GET /api/v1/briefings/ (list)
# ---------------------------------------------------------------------------


class TestListBriefings:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        # Mock list query
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        list_result.scalars.return_value = scalars_mock

        db.execute.side_effect = [count_result, list_result]

        from pwbs.api.v1.routes.briefings import list_briefings

        result = await list_briefings(
            response=Response(),
            user=user,
            db=db,
        )

        assert result.total == 0
        assert result.briefings == []
        assert not result.has_more

    @pytest.mark.asyncio
    async def test_returns_paginated_results(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        row = _make_briefing_orm()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 25

        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [row]
        list_result.scalars.return_value = scalars_mock

        db.execute.side_effect = [count_result, list_result]

        from pwbs.api.v1.routes.briefings import list_briefings

        result = await list_briefings(
            response=Response(),
            user=user,
            db=db,
            limit=20,
            offset=0,
        )

        assert result.total == 25
        assert len(result.briefings) == 1
        assert result.has_more is True

    @pytest.mark.asyncio
    async def test_clamps_limit_to_50(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        list_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        list_result.scalars.return_value = scalars_mock
        db.execute.side_effect = [count_result, list_result]

        from pwbs.api.v1.routes.briefings import list_briefings

        result = await list_briefings(
            response=Response(),
            user=user,
            db=db,
            limit=100,
        )

        assert result.total == 0


# ---------------------------------------------------------------------------
# Test: GET /api/v1/briefings/latest
# ---------------------------------------------------------------------------


class TestLatestBriefings:
    @pytest.mark.asyncio
    async def test_returns_latest_per_type(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        morning_row = _make_briefing_orm(briefing_type="morning", title="AM")
        meeting_row = _make_briefing_orm(briefing_type="meeting_prep", title="MP")

        # Two queries, one per BriefingType
        morning_result = MagicMock()
        morning_result.scalar_one_or_none.return_value = morning_row
        meeting_result = MagicMock()
        meeting_result.scalar_one_or_none.return_value = meeting_row

        db.execute.side_effect = [morning_result, meeting_result]

        from pwbs.api.v1.routes.briefings import latest_briefings

        result = await latest_briefings(
            response=Response(),
            user=user,
            db=db,
        )

        assert len(result) == 2
        titles = {r.title for r in result}
        assert "AM" in titles
        assert "MP" in titles

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_briefings(self) -> None:
        from fastapi import Response

        user = _make_user()
        db = AsyncMock()

        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None

        db.execute.side_effect = [empty_result, empty_result]

        from pwbs.api.v1.routes.briefings import latest_briefings

        result = await latest_briefings(
            response=Response(),
            user=user,
            db=db,
        )

        assert result == []


# ---------------------------------------------------------------------------
# Test: GET /api/v1/briefings/{id}
# ---------------------------------------------------------------------------


class TestGetBriefing:
    @pytest.mark.asyncio
    async def test_returns_briefing_with_sources(self) -> None:
        from fastapi import Response

        bid = uuid.uuid4()
        user = _make_user()
        row = _make_briefing_orm(briefing_id=bid, user_id=USER_ID)

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.return_value = select_result

        from pwbs.api.v1.routes.briefings import get_briefing

        result = await get_briefing(
            briefing_id=bid,
            response=Response(),
            user=user,
            db=db,
        )

        assert result.id == bid

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self) -> None:
        from fastapi import HTTPException, Response

        user = _make_user()
        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute.return_value = select_result

        from pwbs.api.v1.routes.briefings import get_briefing

        with pytest.raises(HTTPException) as exc_info:
            await get_briefing(
                briefing_id=uuid.uuid4(),
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_for_other_user(self) -> None:
        from fastapi import HTTPException, Response

        bid = uuid.uuid4()
        user = _make_user(user_id=OTHER_USER_ID)
        row = _make_briefing_orm(briefing_id=bid, user_id=USER_ID)

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.return_value = select_result

        from pwbs.api.v1.routes.briefings import get_briefing

        with pytest.raises(HTTPException) as exc_info:
            await get_briefing(
                briefing_id=bid,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: POST /api/v1/briefings/generate
# ---------------------------------------------------------------------------


class TestGenerateBriefing:
    @pytest.mark.asyncio
    async def test_returns_202_with_briefing_id(self) -> None:
        from fastapi import BackgroundTasks, Response

        user = _make_user()
        db = AsyncMock()
        bg = BackgroundTasks()

        # No recent briefings → count = 0
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        db.execute.return_value = count_result

        body = GenerateRequest(briefing_type=BriefingType.MORNING)

        from pwbs.api.v1.routes.briefings import generate_briefing

        result = await generate_briefing(
            body=body,
            background_tasks=bg,
            response=Response(),
            user=user,
            db=db,
        )

        assert result.status == "generating"
        assert result.briefing_id is not None

    @pytest.mark.asyncio
    async def test_returns_429_when_rate_limited(self) -> None:
        from fastapi import BackgroundTasks, HTTPException, Response

        user = _make_user()
        db = AsyncMock()
        bg = BackgroundTasks()

        # Recent briefing exists → count = 1
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        db.execute.return_value = count_result

        body = GenerateRequest(briefing_type=BriefingType.MORNING)

        from pwbs.api.v1.routes.briefings import generate_briefing

        with pytest.raises(HTTPException) as exc_info:
            await generate_briefing(
                body=body,
                background_tasks=bg,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_meeting_prep_generation(self) -> None:
        from fastapi import BackgroundTasks, Response

        user = _make_user()
        db = AsyncMock()
        bg = BackgroundTasks()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        db.execute.return_value = count_result

        body = GenerateRequest(
            briefing_type=BriefingType.MEETING_PREP,
            trigger_context={"event_id": "evt-xyz"},
        )

        from pwbs.api.v1.routes.briefings import generate_briefing

        result = await generate_briefing(
            body=body,
            background_tasks=bg,
            response=Response(),
            user=user,
            db=db,
        )

        assert result.status == "generating"


# ---------------------------------------------------------------------------
# Test: POST /api/v1/briefings/{id}/feedback
# ---------------------------------------------------------------------------


class TestSubmitFeedback:
    @pytest.mark.asyncio
    async def test_stores_positive_feedback(self) -> None:
        from fastapi import Response

        bid = uuid.uuid4()
        user = _make_user()
        row = _make_briefing_orm(briefing_id=bid, user_id=USER_ID, trigger_context=None)

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.return_value = select_result

        body = FeedbackRequest(rating="positive", comment="Great!")

        from pwbs.api.v1.routes.briefings import submit_feedback

        result = await submit_feedback(
            briefing_id=bid,
            body=body,
            response=Response(),
            user=user,
            db=db,
        )

        assert result.briefing_id == bid
        assert result.rating == "positive"
        assert row.trigger_context["feedback"]["rating"] == "positive"
        assert row.trigger_context["feedback"]["comment"] == "Great!"
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stores_negative_feedback_without_comment(self) -> None:
        from fastapi import Response

        bid = uuid.uuid4()
        user = _make_user()
        row = _make_briefing_orm(
            briefing_id=bid,
            user_id=USER_ID,
            trigger_context={"existing_key": "value"},
        )

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.return_value = select_result

        body = FeedbackRequest(rating="negative")

        from pwbs.api.v1.routes.briefings import submit_feedback

        result = await submit_feedback(
            briefing_id=bid,
            body=body,
            response=Response(),
            user=user,
            db=db,
        )

        assert result.rating == "negative"
        assert row.trigger_context["feedback"]["comment"] is None
        # Existing context preserved
        assert row.trigger_context["existing_key"] == "value"

    @pytest.mark.asyncio
    async def test_raises_404_for_missing_briefing(self) -> None:
        from fastapi import HTTPException, Response

        user = _make_user()
        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute.return_value = select_result

        body = FeedbackRequest(rating="positive")

        from pwbs.api.v1.routes.briefings import submit_feedback

        with pytest.raises(HTTPException) as exc_info:
            await submit_feedback(
                briefing_id=uuid.uuid4(),
                body=body,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_briefing(self) -> None:
        from fastapi import HTTPException, Response

        bid = uuid.uuid4()
        user = _make_user(user_id=OTHER_USER_ID)
        row = _make_briefing_orm(briefing_id=bid, user_id=USER_ID)

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.return_value = select_result

        body = FeedbackRequest(rating="positive")

        from pwbs.api.v1.routes.briefings import submit_feedback

        with pytest.raises(HTTPException) as exc_info:
            await submit_feedback(
                briefing_id=bid,
                body=body,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: DELETE /api/v1/briefings/{id}
# ---------------------------------------------------------------------------


class TestDeleteBriefing:
    @pytest.mark.asyncio
    async def test_deletes_own_briefing(self) -> None:
        from fastapi import Response

        bid = uuid.uuid4()
        user = _make_user()
        row = _make_briefing_orm(briefing_id=bid, user_id=USER_ID)

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.side_effect = [select_result, MagicMock()]

        from pwbs.api.v1.routes.briefings import delete_briefing

        result = await delete_briefing(
            briefing_id=bid,
            response=Response(),
            user=user,
            db=db,
        )

        assert result is None
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_404_for_missing_briefing(self) -> None:
        from fastapi import HTTPException, Response

        user = _make_user()
        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute.return_value = select_result

        from pwbs.api.v1.routes.briefings import delete_briefing

        with pytest.raises(HTTPException) as exc_info:
            await delete_briefing(
                briefing_id=uuid.uuid4(),
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_for_other_users_briefing(self) -> None:
        from fastapi import HTTPException, Response

        bid = uuid.uuid4()
        user = _make_user(user_id=OTHER_USER_ID)
        row = _make_briefing_orm(briefing_id=bid, user_id=USER_ID)

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = row
        db.execute.return_value = select_result

        from pwbs.api.v1.routes.briefings import delete_briefing

        with pytest.raises(HTTPException) as exc_info:
            await delete_briefing(
                briefing_id=bid,
                response=Response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Test: Router metadata
# ---------------------------------------------------------------------------


class TestRouterMetadata:
    def test_prefix(self) -> None:
        assert router.prefix == "/api/v1/briefings"

    def test_tags(self) -> None:
        assert "briefings" in router.tags

    def test_route_count(self) -> None:
        paths = [r.path for r in router.routes]
        assert "/api/v1/briefings/" in paths
        assert "/api/v1/briefings/latest" in paths
        assert "/api/v1/briefings/generate" in paths
        assert "/api/v1/briefings/{briefing_id}" in paths
        assert "/api/v1/briefings/{briefing_id}/feedback" in paths
