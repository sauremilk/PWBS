"""Unit tests for user settings persistence (TASK-183)."""

from __future__ import annotations

import uuid
from datetime import time
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    user.display_name = "Test User"
    user.timezone = "Europe/Berlin"
    user.language = "de"
    user.briefing_auto_generate = True
    user.reminder_frequency = "daily"
    user.email_briefing_enabled = True
    user.briefing_email_time = time(6, 30)
    user.vertical_profile = "general"
    return user


class TestGetSettings:
    @pytest.mark.asyncio
    async def test_returns_all_settings_from_db(self) -> None:
        from pwbs.api.v1.routes.user import get_settings_endpoint

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        result = await get_settings_endpoint(response=response, user=user, db=db)

        assert result.timezone == "Europe/Berlin"
        assert result.language == "de"
        assert result.briefing_auto_generate is True
        assert result.reminder_frequency == "daily"
        assert result.email_briefing_enabled is True
        assert result.briefing_email_time == "06:30"


class TestUpdateSettings:
    @pytest.mark.asyncio
    async def test_persists_timezone(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        body = UserSettingsUpdate(timezone="Europe/Vienna")
        await update_settings(update=body, response=response, user=user, db=db)

        assert user.timezone == "Europe/Vienna"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persists_language(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        body = UserSettingsUpdate(language="en")
        await update_settings(update=body, response=response, user=user, db=db)

        assert user.language == "en"

    @pytest.mark.asyncio
    async def test_persists_briefing_auto_generate(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        body = UserSettingsUpdate(briefing_auto_generate=False)
        await update_settings(update=body, response=response, user=user, db=db)

        assert user.briefing_auto_generate is False

    @pytest.mark.asyncio
    async def test_persists_reminder_frequency(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        body = UserSettingsUpdate(reminder_frequency="weekly")
        await update_settings(update=body, response=response, user=user, db=db)

        assert user.reminder_frequency == "weekly"

    @pytest.mark.asyncio
    async def test_invalid_timezone_rejected(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        body = UserSettingsUpdate(timezone="Invalid/Zone")
        with pytest.raises(HTTPException) as exc_info:
            await update_settings(update=body, response=response, user=user, db=db)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_language_rejected(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()
        response = MagicMock()

        body = UserSettingsUpdate(language="xx")
        with pytest.raises(HTTPException) as exc_info:
            await update_settings(update=body, response=response, user=user, db=db)
        assert exc_info.value.status_code == 422
