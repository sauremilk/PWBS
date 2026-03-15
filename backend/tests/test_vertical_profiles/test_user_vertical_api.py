"""Tests for vertical_profile in user settings API (TASK-154)."""

from __future__ import annotations

import uuid
from datetime import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.api.v1.routes.user import (
    UserSettingsUpdate,
    get_settings_endpoint,
    update_settings,
)

USER_ID = uuid.uuid4()


def _make_user(
    user_id: uuid.UUID = USER_ID,
    vertical_profile: str = "general",
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.email = "alice@example.com"
    u.display_name = "Alice"
    u.email_briefing_enabled = False
    u.briefing_email_time = time(6, 30)
    u.vertical_profile = vertical_profile
    return u


# ---------------------------------------------------------------------------
# GET /settings — vertical_profile field
# ---------------------------------------------------------------------------


class TestGetSettingsVerticalProfile:
    @pytest.mark.asyncio
    async def test_returns_default_general(self) -> None:
        user = _make_user()
        resp = await get_settings_endpoint(
            response=MagicMock(), user=user, db=AsyncMock()
        )
        assert resp.vertical_profile == "general"

    @pytest.mark.asyncio
    async def test_returns_researcher(self) -> None:
        user = _make_user(vertical_profile="researcher")
        resp = await get_settings_endpoint(
            response=MagicMock(), user=user, db=AsyncMock()
        )
        assert resp.vertical_profile == "researcher"

    @pytest.mark.asyncio
    async def test_returns_consultant(self) -> None:
        user = _make_user(vertical_profile="consultant")
        resp = await get_settings_endpoint(
            response=MagicMock(), user=user, db=AsyncMock()
        )
        assert resp.vertical_profile == "consultant"

    @pytest.mark.asyncio
    async def test_returns_developer(self) -> None:
        user = _make_user(vertical_profile="developer")
        resp = await get_settings_endpoint(
            response=MagicMock(), user=user, db=AsyncMock()
        )
        assert resp.vertical_profile == "developer"


# ---------------------------------------------------------------------------
# PATCH /settings — vertical_profile update
# ---------------------------------------------------------------------------


class TestUpdateSettingsVerticalProfile:
    @pytest.mark.asyncio
    async def test_update_to_researcher(self) -> None:
        user = _make_user()
        db = AsyncMock()
        update = UserSettingsUpdate(vertical_profile="researcher")
        resp = await update_settings(
            update=update, response=MagicMock(), user=user, db=db
        )
        assert user.vertical_profile == "researcher"
        assert resp.vertical_profile == "researcher"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_to_consultant(self) -> None:
        user = _make_user()
        db = AsyncMock()
        update = UserSettingsUpdate(vertical_profile="consultant")
        resp = await update_settings(
            update=update, response=MagicMock(), user=user, db=db
        )
        assert user.vertical_profile == "consultant"

    @pytest.mark.asyncio
    async def test_update_to_developer(self) -> None:
        user = _make_user()
        db = AsyncMock()
        update = UserSettingsUpdate(vertical_profile="developer")
        resp = await update_settings(
            update=update, response=MagicMock(), user=user, db=db
        )
        assert user.vertical_profile == "developer"

    @pytest.mark.asyncio
    async def test_update_to_general(self) -> None:
        user = _make_user(vertical_profile="researcher")
        db = AsyncMock()
        update = UserSettingsUpdate(vertical_profile="general")
        resp = await update_settings(
            update=update, response=MagicMock(), user=user, db=db
        )
        assert user.vertical_profile == "general"

    @pytest.mark.asyncio
    async def test_invalid_profile_rejected(self) -> None:
        user = _make_user()
        db = AsyncMock()
        update = UserSettingsUpdate(vertical_profile="astronaut")
        with pytest.raises(Exception) as exc_info:
            await update_settings(
                update=update, response=MagicMock(), user=user, db=db
            )
        assert exc_info.value.status_code == 422  # type: ignore[union-attr]
        assert "INVALID_VERTICAL_PROFILE" in str(exc_info.value.detail)  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_empty_profile_rejected(self) -> None:
        user = _make_user()
        db = AsyncMock()
        update = UserSettingsUpdate(vertical_profile="")
        with pytest.raises(Exception) as exc_info:
            await update_settings(
                update=update, response=MagicMock(), user=user, db=db
            )
        assert exc_info.value.status_code == 422  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_none_profile_skips_update(self) -> None:
        user = _make_user(vertical_profile="researcher")
        db = AsyncMock()
        update = UserSettingsUpdate()  # vertical_profile=None
        resp = await update_settings(
            update=update, response=MagicMock(), user=user, db=db
        )
        # Should remain researcher (not overwritten)
        assert resp.vertical_profile == "researcher"

    @pytest.mark.asyncio
    async def test_profile_combined_with_other_updates(self) -> None:
        user = _make_user()
        db = AsyncMock()
        update = UserSettingsUpdate(
            vertical_profile="developer",
            display_name="Bob",
        )
        resp = await update_settings(
            update=update, response=MagicMock(), user=user, db=db
        )
        assert user.vertical_profile == "developer"
        assert user.display_name == "Bob"
        assert resp.vertical_profile == "developer"
