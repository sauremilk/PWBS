"""Tests for Work Pattern Analysis Service (TASK-134)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.analytics.work_patterns import (
    ThemeInfo,
    WorkPatternAnalyzer,
    WorkPatternConfig,
    WorkPatternProfile,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()
NOW = datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc)


def _make_theme_row(name: str = "Architektur", entity_type: str = "topic", mention_count: int = 10):
    row = MagicMock()
    row.name = name
    row.entity_type = entity_type
    row.mention_count = mention_count
    return row


def _make_hour_row(hour: int = 9, doc_count: int = 5):
    row = MagicMock()
    row.hour = hour
    row.doc_count = doc_count
    return row


def _make_decision_row(
    created_at: datetime = NOW - timedelta(days=5),
    decided_at: datetime = NOW,
):
    row = MagicMock()
    row.created_at = created_at
    row.decided_at = decided_at
    return row


def _mock_session_with_results(results_sequence: list) -> AsyncMock:
    """Create a mock async session that returns different results per call."""
    session = AsyncMock()
    mock_results = []
    for result_data in results_sequence:
        mock_result = MagicMock()
        if isinstance(result_data, list):
            mock_result.all.return_value = result_data
            mock_result.scalar_one.return_value = len(result_data)
        elif isinstance(result_data, (int, float)):
            mock_result.scalar_one.return_value = result_data
            mock_result.all.return_value = []
        else:
            mock_result.scalar_one.return_value = result_data
            mock_result.all.return_value = []
        mock_results.append(mock_result)

    session.execute = AsyncMock(side_effect=mock_results)
    return session


def _mock_session_single(rows: list | None = None, scalar: int | float | None = None) -> AsyncMock:
    """Create a mock session returning a single result set."""
    session = AsyncMock()
    mock_result = MagicMock()
    if rows is not None:
        mock_result.all.return_value = rows
    if scalar is not None:
        mock_result.scalar_one.return_value = scalar
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ------------------------------------------------------------------
# WorkPatternConfig
# ------------------------------------------------------------------


class TestWorkPatternConfig:
    def test_defaults(self) -> None:
        cfg = WorkPatternConfig()
        assert cfg.lookback_days == 30
        assert cfg.top_themes_count == 5
        assert cfg.min_theme_mentions == 2
        assert cfg.profile_expiry_days == 90

    def test_custom(self) -> None:
        cfg = WorkPatternConfig(lookback_days=60, top_themes_count=10)
        assert cfg.lookback_days == 60
        assert cfg.top_themes_count == 10


# ------------------------------------------------------------------
# ThemeInfo
# ------------------------------------------------------------------


class TestThemeInfo:
    def test_create(self) -> None:
        t = ThemeInfo(name="DSGVO", mention_count=8, entity_type="topic")
        assert t.name == "DSGVO"
        assert t.mention_count == 8
        assert t.entity_type == "topic"


# ------------------------------------------------------------------
# WorkPatternProfile
# ------------------------------------------------------------------


class TestWorkPatternProfile:
    def test_defaults(self) -> None:
        p = WorkPatternProfile()
        assert p.top_themes == []
        assert p.avg_meetings_per_week == 0.0
        assert p.preferred_hours == {}
        assert p.decision_speed_avg_days is None
        assert p.analysis_date is not None

    def test_with_data(self) -> None:
        theme = ThemeInfo("AI", 12, "topic")
        p = WorkPatternProfile(
            top_themes=[theme],
            avg_meetings_per_week=3.5,
            preferred_hours={"hours": {"9": 5}, "peak_start": 9, "peak_end": 12},
            decision_speed_avg_days=2.5,
        )
        assert len(p.top_themes) == 1
        assert p.avg_meetings_per_week == 3.5


# ------------------------------------------------------------------
# extract_top_themes
# ------------------------------------------------------------------


class TestExtractTopThemes:
    @pytest.mark.asyncio
    async def test_returns_top_themes(self) -> None:
        rows = [
            _make_theme_row("Architektur", "topic", 15),
            _make_theme_row("DSGVO", "topic", 10),
            _make_theme_row("Alice", "person", 8),
        ]
        session = _mock_session_single(rows=rows)
        analyzer = WorkPatternAnalyzer(session)

        themes = await analyzer.extract_top_themes(USER_ID)

        assert len(themes) == 3
        assert themes[0].name == "Architektur"
        assert themes[0].mention_count == 15
        assert themes[1].name == "DSGVO"

    @pytest.mark.asyncio
    async def test_empty_when_no_entities(self) -> None:
        session = _mock_session_single(rows=[])
        analyzer = WorkPatternAnalyzer(session)

        themes = await analyzer.extract_top_themes(USER_ID)
        assert themes == []

    @pytest.mark.asyncio
    async def test_respects_config_count(self) -> None:
        rows = [_make_theme_row(f"Theme-{i}", "topic", 10 - i) for i in range(3)]
        session = _mock_session_single(rows=rows)
        cfg = WorkPatternConfig(top_themes_count=3)
        analyzer = WorkPatternAnalyzer(session, config=cfg)

        themes = await analyzer.extract_top_themes(USER_ID)
        assert len(themes) == 3


# ------------------------------------------------------------------
# extract_meeting_load
# ------------------------------------------------------------------


class TestExtractMeetingLoad:
    @pytest.mark.asyncio
    async def test_calculates_weekly_avg(self) -> None:
        # 21 meetings in 30 days = 21 / (30/7) = 21 / 4.29 = ~4.9
        session = _mock_session_single(scalar=21)
        analyzer = WorkPatternAnalyzer(session)

        avg = await analyzer.extract_meeting_load(USER_ID)

        assert avg == 4.9

    @pytest.mark.asyncio
    async def test_zero_meetings(self) -> None:
        session = _mock_session_single(scalar=0)
        analyzer = WorkPatternAnalyzer(session)

        avg = await analyzer.extract_meeting_load(USER_ID)
        assert avg == 0.0

    @pytest.mark.asyncio
    async def test_custom_lookback(self) -> None:
        session = _mock_session_single(scalar=14)
        cfg = WorkPatternConfig(lookback_days=14)
        analyzer = WorkPatternAnalyzer(session, config=cfg)

        avg = await analyzer.extract_meeting_load(USER_ID)
        # 14 meetings / 2 weeks = 7.0
        assert avg == 7.0


# ------------------------------------------------------------------
# extract_preferred_hours
# ------------------------------------------------------------------


class TestExtractPreferredHours:
    @pytest.mark.asyncio
    async def test_finds_peak_hours(self) -> None:
        rows = [
            _make_hour_row(8, 2),
            _make_hour_row(9, 8),
            _make_hour_row(10, 10),
            _make_hour_row(11, 7),
            _make_hour_row(14, 3),
        ]
        session = _mock_session_single(rows=rows)
        analyzer = WorkPatternAnalyzer(session)

        hours = await analyzer.extract_preferred_hours(USER_ID)

        assert hours["peak_start"] == 9
        assert hours["peak_end"] == 12
        assert "9" in hours["hours"]
        assert hours["hours"]["10"] == 10

    @pytest.mark.asyncio
    async def test_empty_when_no_documents(self) -> None:
        session = _mock_session_single(rows=[])
        analyzer = WorkPatternAnalyzer(session)

        hours = await analyzer.extract_preferred_hours(USER_ID)
        assert hours["peak_start"] is None
        assert hours["peak_end"] is None
        assert hours["hours"] == {}

    @pytest.mark.asyncio
    async def test_single_hour(self) -> None:
        rows = [_make_hour_row(14, 20)]
        session = _mock_session_single(rows=rows)
        analyzer = WorkPatternAnalyzer(session)

        hours = await analyzer.extract_preferred_hours(USER_ID)
        # Earliest 3-hour window containing hour 14 is [12,13,14]
        assert hours["peak_start"] == 12
        assert hours["peak_end"] == 15


# ------------------------------------------------------------------
# extract_decision_speed
# ------------------------------------------------------------------


class TestExtractDecisionSpeed:
    @pytest.mark.asyncio
    async def test_calculates_average_speed(self) -> None:
        rows = [
            _make_decision_row(NOW - timedelta(days=3), NOW),
            _make_decision_row(NOW - timedelta(days=7), NOW),
        ]
        session = _mock_session_single(rows=rows)
        analyzer = WorkPatternAnalyzer(session)

        speed = await analyzer.extract_decision_speed(USER_ID)

        # (3 + 7) / 2 = 5.0
        assert speed == 5.0

    @pytest.mark.asyncio
    async def test_none_when_no_decisions(self) -> None:
        session = _mock_session_single(rows=[])
        analyzer = WorkPatternAnalyzer(session)

        speed = await analyzer.extract_decision_speed(USER_ID)
        assert speed is None

    @pytest.mark.asyncio
    async def test_single_decision(self) -> None:
        rows = [_make_decision_row(NOW - timedelta(days=2), NOW)]
        session = _mock_session_single(rows=rows)
        analyzer = WorkPatternAnalyzer(session)

        speed = await analyzer.extract_decision_speed(USER_ID)
        assert speed == 2.0


# ------------------------------------------------------------------
# analyze (full pipeline)
# ------------------------------------------------------------------


class TestAnalyze:
    @pytest.mark.asyncio
    async def test_full_analysis(self) -> None:
        theme_rows = [_make_theme_row("AI", "topic", 12)]
        meeting_scalar = 14
        hour_rows = [_make_hour_row(10, 15)]
        decision_rows = [_make_decision_row(NOW - timedelta(days=4), NOW)]

        results = [
            theme_rows,       # extract_top_themes
            meeting_scalar,   # extract_meeting_load
            hour_rows,        # extract_preferred_hours
            decision_rows,    # extract_decision_speed
        ]

        # Build mock - each call returns next result
        session = AsyncMock()
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            r = results[call_count]
            call_count += 1
            mock_r = MagicMock()
            if isinstance(r, list):
                mock_r.all.return_value = r
                mock_r.scalar_one.return_value = len(r)
            else:
                mock_r.scalar_one.return_value = r
                mock_r.all.return_value = []
            return mock_r

        session.execute = AsyncMock(side_effect=_execute)
        analyzer = WorkPatternAnalyzer(session)

        profile = await analyzer.analyze(USER_ID)

        assert len(profile.top_themes) == 1
        assert profile.top_themes[0].name == "AI"
        assert profile.avg_meetings_per_week > 0
        assert profile.preferred_hours["peak_start"] == 8
        assert profile.decision_speed_avg_days == 4.0


# ------------------------------------------------------------------
# analyze_and_persist
# ------------------------------------------------------------------


class TestAnalyzeAndPersist:
    @pytest.mark.asyncio
    async def test_persists_profile(self) -> None:
        # Build mock session that returns sequential results
        results = [
            [],    # themes (empty)
            0,     # meeting count
            [],    # hours (empty)
            [],    # decisions (empty)
            0,     # max version query -> 0 means first profile
        ]

        session = AsyncMock()
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            r = results[call_count]
            call_count += 1
            mock_r = MagicMock()
            if isinstance(r, list):
                mock_r.all.return_value = r
                mock_r.scalar_one.return_value = len(r)
            else:
                mock_r.scalar_one.return_value = r
                mock_r.all.return_value = []
            return mock_r

        session.execute = AsyncMock(side_effect=_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        analyzer = WorkPatternAnalyzer(session)
        db_profile = await analyzer.analyze_and_persist(USER_ID)

        assert db_profile.version == 1
        assert db_profile.user_id == USER_ID
        assert db_profile.expires_at is not None
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increments_version(self) -> None:
        results = [
            [],    # themes
            0,     # meetings
            [],    # hours
            [],    # decisions
            3,     # existing max version = 3
        ]

        session = AsyncMock()
        call_count = 0

        async def _execute(stmt):
            nonlocal call_count
            r = results[call_count]
            call_count += 1
            mock_r = MagicMock()
            if isinstance(r, list):
                mock_r.all.return_value = r
                mock_r.scalar_one.return_value = len(r)
            else:
                mock_r.scalar_one.return_value = r
                mock_r.all.return_value = []
            return mock_r

        session.execute = AsyncMock(side_effect=_execute)
        session.add = MagicMock()
        session.flush = AsyncMock()

        analyzer = WorkPatternAnalyzer(session)
        db_profile = await analyzer.analyze_and_persist(USER_ID)

        assert db_profile.version == 4


# ------------------------------------------------------------------
# Config property
# ------------------------------------------------------------------


class TestConfigProperty:
    def test_default_config(self) -> None:
        analyzer = WorkPatternAnalyzer(AsyncMock())
        assert analyzer.config.lookback_days == 30

    def test_custom_config(self) -> None:
        cfg = WorkPatternConfig(lookback_days=60)
        analyzer = WorkPatternAnalyzer(AsyncMock(), config=cfg)
        assert analyzer.config.lookback_days == 60