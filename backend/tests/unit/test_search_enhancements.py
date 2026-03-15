"""Unit tests for search enhancements (TASK-182): autocomplete, saved searches, history."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    return user


def _make_entity(user_id: uuid.UUID, name: str, entity_type: str = "Person") -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.user_id = user_id
    e.name = name
    e.normalized_name = name.lower()
    e.entity_type = entity_type
    e.mention_count = 5
    return e


def _make_saved_search(user_id: uuid.UUID, name: str, query: str) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.name = name
    s.query = query
    s.filters_json = None
    s.created_at = datetime.now(UTC)
    return s


def _make_history_entry(user_id: uuid.UUID, query: str, result_count: int = 3) -> MagicMock:
    h = MagicMock()
    h.id = uuid.uuid4()
    h.user_id = user_id
    h.query = query
    h.result_count = result_count
    h.created_at = datetime.now(UTC)
    return h


class TestAutoComplete:
    @pytest.mark.asyncio
    async def test_returns_entity_suggestions(self) -> None:
        from pwbs.api.v1.routes.search import autocomplete

        user = _make_user()
        entity = _make_entity(user.id, "Max Mustermann")
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entity]
        db.execute.return_value = mock_result

        resp = await autocomplete(q="max", limit=10, user=user, session=db)

        assert len(resp.suggestions) == 1
        assert resp.suggestions[0].name == "Max Mustermann"
        assert resp.suggestions[0].entity_type == "Person"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_match(self) -> None:
        from pwbs.api.v1.routes.search import autocomplete

        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        resp = await autocomplete(q="xyz", limit=10, user=user, session=db)

        assert len(resp.suggestions) == 0


class TestSavedSearches:
    @pytest.mark.asyncio
    async def test_create_saved_search(self) -> None:
        from pwbs.api.v1.routes.search import create_saved_search
        from pwbs.schemas.search import SavedSearchCreate

        user = _make_user()
        db = AsyncMock()

        body = SavedSearchCreate(name="My Search", query="project alpha")

        async def fake_refresh(obj: object) -> None:
            obj.id = uuid.uuid4()  # type: ignore[attr-defined]
            obj.created_at = datetime.now(UTC)  # type: ignore[attr-defined]

        db.refresh = fake_refresh

        resp = await create_saved_search(body=body, user=user, session=db)

        assert resp.name == "My Search"
        assert resp.query == "project alpha"
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_saved_searches(self) -> None:
        from pwbs.api.v1.routes.search import list_saved_searches

        user = _make_user()
        saved = _make_saved_search(user.id, "Test", "alpha")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [saved]
        db.execute.return_value = mock_result

        resp = await list_saved_searches(user=user, session=db)

        assert len(resp) == 1
        assert resp[0].name == "Test"

    @pytest.mark.asyncio
    async def test_delete_saved_search(self) -> None:
        from pwbs.api.v1.routes.search import delete_saved_search

        user = _make_user()
        saved = _make_saved_search(user.id, "Del", "remove")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = saved
        db.execute.return_value = mock_result

        await delete_saved_search(search_id=saved.id, user=user, session=db)

        db.delete.assert_awaited_once_with(saved)
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found_raises_404(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.search import delete_saved_search

        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_saved_search(search_id=uuid.uuid4(), user=user, session=db)

        assert exc_info.value.status_code == 404


class TestSearchHistory:
    @pytest.mark.asyncio
    async def test_returns_history_items(self) -> None:
        from pwbs.api.v1.routes.search import get_search_history

        user = _make_user()
        entry = _make_history_entry(user.id, "test query", 7)
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entry]
        db.execute.return_value = mock_result

        resp = await get_search_history(user=user, session=db)

        assert len(resp.items) == 1
        assert resp.items[0].query == "test query"
        assert resp.items[0].result_count == 7

    @pytest.mark.asyncio
    async def test_returns_empty_history(self) -> None:
        from pwbs.api.v1.routes.search import get_search_history

        user = _make_user()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        resp = await get_search_history(user=user, session=db)

        assert len(resp.items) == 0
