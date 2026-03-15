"""Unit tests for feedback endpoints (TASK-188)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_user(
    user_id: uuid.UUID | None = None,
    email: str = "user@test.com",
    is_admin: bool = False,
) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.is_admin = is_admin
    return user


class TestSubmitFeedback:
    @pytest.mark.asyncio
    async def test_creates_feedback(self) -> None:
        from pwbs.api.v1.routes.feedback import (
            ContextMeta,
            SubmitFeedbackRequest,
            submit_feedback,
        )

        user = _make_user()
        db = AsyncMock()

        # After refresh, feedback gets an id
        async def mock_refresh(obj: MagicMock) -> None:
            obj.id = uuid.uuid4()

        db.refresh = mock_refresh

        body = SubmitFeedbackRequest(
            feedback_type="bug",
            message="Something is broken",
            context=ContextMeta(
                url="http://app/dash",
                browser_info="Chrome",
                viewport_size="1920x1080",
            ),
        )

        result = await submit_feedback(body=body, current_user=user, db=db)

        assert result.message == "feedback_submitted"
        assert result.id is not None
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_empty_message(self) -> None:
        """Pydantic validation rejects empty messages."""
        from pydantic import ValidationError

        from pwbs.api.v1.routes.feedback import SubmitFeedbackRequest

        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(
                feedback_type="bug",
                message="",
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_type(self) -> None:
        """Pydantic validation rejects invalid feedback types."""
        from pydantic import ValidationError

        from pwbs.api.v1.routes.feedback import SubmitFeedbackRequest

        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(
                feedback_type="invalid",
                message="Test message",
            )


class TestListFeedbacksAdmin:
    @pytest.mark.asyncio
    async def test_requires_admin(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.feedback import list_feedbacks_admin

        user = _make_user(is_admin=False)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_feedbacks_admin(current_user=user, db=db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_paginated_feedbacks(self) -> None:
        from pwbs.api.v1.routes.feedback import list_feedbacks_admin

        admin = _make_user(is_admin=True)
        db = AsyncMock()

        # Mock feedback item
        fb = MagicMock()
        fb.id = uuid.uuid4()
        fb.feedback_type = "bug"
        fb.message = "Test"
        fb.context_meta = {"url": "/dash"}
        fb.created_at = MagicMock()
        fb.user = MagicMock()
        fb.user.email = "user@test.com"

        # First call: count
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 1

        # Second call: results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fb]

        db.execute = AsyncMock(side_effect=[mock_count, mock_result])

        result = await list_feedbacks_admin(current_user=admin, db=db)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].feedback_type == "bug"
        assert result.has_more is False
