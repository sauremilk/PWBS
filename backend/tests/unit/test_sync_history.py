"""Unit tests for connector sync history endpoint (TASK-184)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    return user


def _make_connection(
    user_id: uuid.UUID,
    source_type: str = "google_calendar",
) -> MagicMock:
    conn = MagicMock()
    conn.id = uuid.uuid4()
    conn.user_id = user_id
    conn.source_type = source_type
    return conn


def _make_sync_run(
    connection_id: uuid.UUID,
    status: str = "success",
    doc_count: int = 5,
    error_count: int = 0,
) -> MagicMock:
    run = MagicMock()
    run.id = uuid.uuid4()
    run.connection_id = connection_id
    run.status = status
    run.started_at = datetime.now(UTC) - timedelta(minutes=10)
    run.completed_at = datetime.now(UTC)
    run.document_count = doc_count
    run.error_count = error_count
    run.errors_json = None
    return run


class TestGetSyncHistory:
    @pytest.mark.asyncio
    async def test_returns_history(self) -> None:
        from pwbs.api.v1.routes.connectors import get_sync_history

        user = _make_user()
        conn = _make_connection(user.id)
        run = _make_sync_run(conn.id)
        db = AsyncMock()

        # Call 1: find connection
        mock_conn_result = MagicMock()
        mock_conn_result.scalar_one_or_none.return_value = conn

        # Call 2: count
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        # Call 3: paginated runs
        mock_runs_result = MagicMock()
        mock_runs_result.scalars.return_value.all.return_value = [run]

        db.execute = AsyncMock(
            side_effect=[mock_conn_result, mock_count_result, mock_runs_result]
        )

        result = await get_sync_history(
            type="google_calendar",
            current_user=user,
            db=db,
        )

        assert result.total == 1
        assert len(result.runs) == 1
        assert result.runs[0].status == "success"
        assert result.runs[0].document_count == 5
        assert result.runs[0].duration_seconds is not None

    @pytest.mark.asyncio
    async def test_returns_empty_state(self) -> None:
        from pwbs.api.v1.routes.connectors import get_sync_history

        user = _make_user()
        conn = _make_connection(user.id)
        db = AsyncMock()

        mock_conn_result = MagicMock()
        mock_conn_result.scalar_one_or_none.return_value = conn

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_runs_result = MagicMock()
        mock_runs_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[mock_conn_result, mock_count_result, mock_runs_result]
        )

        result = await get_sync_history(
            type="google_calendar",
            current_user=user,
            db=db,
        )

        assert result.total == 0
        assert len(result.runs) == 0
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_rejects_missing_connection(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.connectors import get_sync_history

        user = _make_user()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_sync_history(
                type="google_calendar",
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404
