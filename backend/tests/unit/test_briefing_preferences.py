"""Unit tests for TASK-186: Briefing Personalisation - preferences API + generator integration."""

from __future__ import annotations

import uuid
from datetime import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.api.v1.routes.user import (
    BriefingPreferencesResponse,
    BriefingPreferencesUpdate,
    get_briefing_preferences,
    update_briefing_preferences,
)
from pwbs.briefing.generator import (
    BriefingGenerator,
    BriefingLLMResult,
    BriefingType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(preferences: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.display_name = "Test"
    user.timezone = "Europe/Berlin"
    user.language = "de"
    user.briefing_auto_generate = True
    user.reminder_frequency = "daily"
    user.email_briefing_enabled = False
    user.briefing_email_time = time(6, 30)
    user.vertical_profile = "general"
    user.briefing_preferences = preferences
    return user


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_response() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# GET /api/v1/user/briefing-preferences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_briefing_preferences_default() -> None:
    """No preferences set → empty lists returned."""
    user = _make_user(preferences=None)
    result = await get_briefing_preferences(
        response=_make_response(), user=user, db=_make_db()
    )
    assert isinstance(result, BriefingPreferencesResponse)
    assert result.focus_projects == []
    assert result.excluded_sources == []
    assert result.priority_topics == []


@pytest.mark.asyncio
async def test_get_briefing_preferences_with_data() -> None:
    """Existing preferences are returned correctly."""
    prefs = {
        "focus_projects": ["Project Alpha"],
        "excluded_sources": ["slack"],
        "priority_topics": ["AI", "ML"],
    }
    user = _make_user(preferences=prefs)
    result = await get_briefing_preferences(
        response=_make_response(), user=user, db=_make_db()
    )
    assert result.focus_projects == ["Project Alpha"]
    assert result.excluded_sources == ["slack"]
    assert result.priority_topics == ["AI", "ML"]


# ---------------------------------------------------------------------------
# PATCH /api/v1/user/briefing-preferences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_briefing_preferences_creates_new() -> None:
    """First-time set of preferences (user.briefing_preferences is None)."""
    user = _make_user(preferences=None)
    db = _make_db()
    db.refresh = AsyncMock(side_effect=lambda u: None)

    update = BriefingPreferencesUpdate(
        focus_projects=["Alpha", "Beta"],
        priority_topics=["AI"],
    )
    result = await update_briefing_preferences(
        update=update, response=_make_response(), user=user, db=db
    )
    db.commit.assert_awaited_once()
    assert result.focus_projects == ["Alpha", "Beta"]
    assert user.briefing_preferences["priority_topics"] == ["AI"]
    assert user.briefing_preferences.get("excluded_sources") is None


@pytest.mark.asyncio
async def test_update_briefing_preferences_merges() -> None:
    """Partial update merges with existing preferences."""
    existing = {
        "focus_projects": ["Old"],
        "excluded_sources": ["gmail"],
        "priority_topics": ["Old Topic"],
    }
    user = _make_user(preferences=existing)
    db = _make_db()
    db.refresh = AsyncMock(side_effect=lambda u: None)

    update = BriefingPreferencesUpdate(priority_topics=["New Topic"])
    await update_briefing_preferences(
        update=update, response=_make_response(), user=user, db=db
    )
    # focus_projects and excluded_sources kept, priority_topics overwritten
    assert user.briefing_preferences["focus_projects"] == ["Old"]
    assert user.briefing_preferences["excluded_sources"] == ["gmail"]
    assert user.briefing_preferences["priority_topics"] == ["New Topic"]


@pytest.mark.asyncio
async def test_update_strips_whitespace() -> None:
    """Leading/trailing whitespace in tags is stripped; empty tags removed."""
    user = _make_user(preferences=None)
    db = _make_db()
    db.refresh = AsyncMock(side_effect=lambda u: None)

    update = BriefingPreferencesUpdate(
        focus_projects=["  Alpha  ", "", "  "],
    )
    await update_briefing_preferences(
        update=update, response=_make_response(), user=user, db=db
    )
    assert user.briefing_preferences["focus_projects"] == ["Alpha"]


# ---------------------------------------------------------------------------
# BriefingGenerator - preference injection into system prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generator_injects_preferences_into_system_prompt() -> None:
    """Briefing preferences are appended to the system prompt."""
    # Setup mocks
    mock_template = MagicMock()
    mock_template.id = "briefing_morning"
    mock_template.system_prompt = "Du bist ein Briefing-Assistent."
    mock_template.temperature = 0.3
    mock_template.max_output_tokens = None

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_template
    mock_registry.render.return_value = "Rendered prompt text"

    mock_response = MagicMock()
    mock_response.content = "Hier ist dein Briefing."
    mock_response.usage = None
    mock_response.model = "test-model"

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = mock_response

    generator = BriefingGenerator(
        llm_gateway=mock_llm,
        prompt_registry=mock_registry,
        config=MagicMock(
            enable_grounding=False,
            default_temperature=0.3,
            morning_max_output_tokens=2000,
        ),
    )

    prefs = {
        "focus_projects": ["Project X"],
        "priority_topics": ["AI", "ML"],
        "excluded_sources": ["slack"],
    }

    result = await generator.generate(
        briefing_type=BriefingType.MORNING,
        context={"date": "2026-03-15"},
        user_id=uuid.uuid4(),
        briefing_preferences=prefs,
    )

    assert isinstance(result, BriefingLLMResult)

    # Verify the system prompt sent to LLM includes preferences
    call_args = mock_llm.generate.call_args
    request = call_args[0][0] if call_args[0] else call_args[1].get("request")
    system_prompt = request.system_prompt

    assert "Nutzer-Präferenzen" in system_prompt
    assert "Project X" in system_prompt
    assert "AI" in system_prompt
    assert "slack" in system_prompt


@pytest.mark.asyncio
async def test_generator_no_preferences_no_extra_prompt() -> None:
    """Without preferences, no personalisation instructions are added."""
    mock_template = MagicMock()
    mock_template.id = "briefing_morning"
    mock_template.system_prompt = "Du bist ein Briefing-Assistent."
    mock_template.temperature = 0.3
    mock_template.max_output_tokens = None

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_template
    mock_registry.render.return_value = "Rendered prompt text"

    mock_response = MagicMock()
    mock_response.content = "Briefing output."
    mock_response.usage = None
    mock_response.model = "test-model"

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = mock_response

    generator = BriefingGenerator(
        llm_gateway=mock_llm,
        prompt_registry=mock_registry,
        config=MagicMock(
            enable_grounding=False,
            default_temperature=0.3,
            morning_max_output_tokens=2000,
        ),
    )

    await generator.generate(
        briefing_type=BriefingType.MORNING,
        context={"date": "2026-03-15"},
        user_id=uuid.uuid4(),
        briefing_preferences=None,
    )

    call_args = mock_llm.generate.call_args
    request = call_args[0][0] if call_args[0] else call_args[1].get("request")
    assert "Nutzer-Präferenzen" not in request.system_prompt
