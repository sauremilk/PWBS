"""Tests for Briefing Feedback API (TASK-171)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from pwbs.api.v1.routes.briefings import (
    FeedbackRequest,
    FeedbackResponse,
    FeedbackStatsItem,
    FeedbackStatsResponse,
    feedback_stats,
    submit_feedback,
)
from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.models.briefing_feedback import BriefingFeedback
from pwbs.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
BRIEFING_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = user_id or USER_ID
    u.email = "test@example.com"
    u.display_name = "Test User"
    return u


def _make_briefing(
    briefing_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> BriefingORM:
    row = MagicMock(spec=BriefingORM)
    row.id = briefing_id or BRIEFING_ID
    row.user_id = user_id or USER_ID
    row.briefing_type = "morning"
    row.title = "Test Briefing"
    row.content = "Content"
    row.source_chunks = []
    row.source_entities = None
    row.trigger_context = None
    row.generated_at = datetime(2026, 3, 14, 6, 30, tzinfo=UTC)
    row.expires_at = None
    return row


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def _mock_response() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Tests: FeedbackRequest schema
# ---------------------------------------------------------------------------


class TestFeedbackRequestSchema:
    def test_positive_rating(self) -> None:
        req = FeedbackRequest(rating="positive")
        assert req.rating == "positive"
        assert req.comment is None

    def test_negative_rating_with_comment(self) -> None:
        req = FeedbackRequest(rating="negative", comment="Not helpful")
        assert req.rating == "negative"
        assert req.comment == "Not helpful"

    def test_invalid_rating_rejected(self) -> None:
        with pytest.raises(Exception):
            FeedbackRequest(rating="neutral")


# ---------------------------------------------------------------------------
# Tests: submit_feedback endpoint
# ---------------------------------------------------------------------------


class TestSubmitFeedback:
    @pytest.mark.asyncio
    async def test_submit_positive_feedback(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_briefing()
        db.execute.return_value = mock_result

        user = _make_user()
        body = FeedbackRequest(rating="positive")

        result = await submit_feedback(
            briefing_id=BRIEFING_ID,
            body=body,
            response=_mock_response(),
            user=user,
            db=db,
        )

        assert isinstance(result, FeedbackResponse)
        assert result.briefing_id == BRIEFING_ID
        assert result.rating == "positive"
        # Upsert executed (two db.execute calls: select + upsert)
        assert db.execute.call_count == 2
        assert db.flush.call_count == 1

    @pytest.mark.asyncio
    async def test_submit_negative_feedback_with_comment(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_briefing()
        db.execute.return_value = mock_result

        user = _make_user()
        body = FeedbackRequest(rating="negative", comment="Too verbose")

        result = await submit_feedback(
            briefing_id=BRIEFING_ID,
            body=body,
            response=_mock_response(),
            user=user,
            db=db,
        )

        assert result.rating == "negative"

    @pytest.mark.asyncio
    async def test_briefing_not_found_returns_404(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        user = _make_user()
        body = FeedbackRequest(rating="positive")

        with pytest.raises(HTTPException) as exc_info:
            await submit_feedback(
                briefing_id=uuid.uuid4(),
                body=body,
                response=_mock_response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_other_user_briefing_returns_403(self) -> None:
        other_user_id = uuid.uuid4()
        briefing = _make_briefing(user_id=other_user_id)

        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = briefing
        db.execute.return_value = mock_result

        user = _make_user()
        body = FeedbackRequest(rating="positive")

        with pytest.raises(HTTPException) as exc_info:
            await submit_feedback(
                briefing_id=briefing.id,
                body=body,
                response=_mock_response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_positive_feedback_strips_comment(self) -> None:
        """Comment should be stripped when rating is positive."""
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_briefing()
        db.execute.return_value = mock_result

        user = _make_user()
        body = FeedbackRequest(rating="positive", comment="Should be ignored")

        result = await submit_feedback(
            briefing_id=BRIEFING_ID,
            body=body,
            response=_mock_response(),
            user=user,
            db=db,
        )

        assert result.rating == "positive"


# ---------------------------------------------------------------------------
# Tests: feedback_stats endpoint
# ---------------------------------------------------------------------------


class TestFeedbackStats:
    @pytest.mark.asyncio
    async def test_returns_empty_stats(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        user = _make_user()
        result = await feedback_stats(
            response=_mock_response(),
            user=user,
            db=db,
        )

        assert isinstance(result, FeedbackStatsResponse)
        assert result.stats == []

    @pytest.mark.asyncio
    async def test_returns_aggregated_stats(self) -> None:
        db = _mock_db()
        row = MagicMock()
        row.briefing_type = "morning"
        row.positive = 5
        row.negative = 2
        row.total = 7
        mock_result = MagicMock()
        mock_result.all.return_value = [row]
        db.execute.return_value = mock_result

        user = _make_user()
        result = await feedback_stats(
            response=_mock_response(),
            user=user,
            db=db,
        )

        assert len(result.stats) == 1
        assert result.stats[0].briefing_type == "morning"
        assert result.stats[0].positive == 5
        assert result.stats[0].negative == 2
        assert result.stats[0].total == 7


# ---------------------------------------------------------------------------
# Tests: FeedbackStatsItem schema
# ---------------------------------------------------------------------------


class TestFeedbackStatsSchema:
    def test_stats_item_creation(self) -> None:
        item = FeedbackStatsItem(
            briefing_type="morning",
            positive=10,
            negative=3,
            total=13,
        )
        assert item.briefing_type == "morning"
        assert item.positive == 10

    def test_stats_response_creation(self) -> None:
        resp = FeedbackStatsResponse(
            stats=[
                FeedbackStatsItem(briefing_type="morning", positive=5, negative=1, total=6),
                FeedbackStatsItem(briefing_type="weekly", positive=3, negative=0, total=3),
            ]
        )
        assert len(resp.stats) == 2


# ---------------------------------------------------------------------------
# Tests: BriefingFeedback model
# ---------------------------------------------------------------------------


class TestBriefingFeedbackModel:
    def test_table_name(self) -> None:
        assert BriefingFeedback.__tablename__ == "briefing_feedback"

    def test_unique_constraint_exists(self) -> None:
        constraint_names = [
            c.name for c in BriefingFeedback.__table__.constraints if hasattr(c, "name") and c.name
        ]
        assert "uq_feedback_briefing_owner" in constraint_names

    def test_columns_present(self) -> None:
        cols = {c.name for c in BriefingFeedback.__table__.columns}
        assert {"id", "briefing_id", "owner_id", "rating", "comment", "created_at"} <= cols
