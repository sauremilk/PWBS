"""Tests for Morning Briefing Context Assembly (TASK-076)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.context import (
    CalendarEvent,
    MorningBriefingConfig,
    MorningBriefingContext,
    MorningContextAssembler,
    NullGraphService,
    ParticipantHistory,
    PendingDecision,
)
from pwbs.search.service import SemanticSearchResult

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()
TODAY = date(2026, 3, 14)
NOW = datetime(2026, 3, 14, 10, 0, 0, tzinfo=UTC)


def _make_event(
    event_id: str = "evt-1",
    title: str = "Sprint Planning",
    start_time: datetime = NOW,
    participants: list[str] | None = None,
    notes: str | None = None,
) -> CalendarEvent:
    return CalendarEvent(
        event_id=event_id,
        title=title,
        start_time=start_time,
        participants=participants or [],
        notes=notes,
    )


def _make_search_result(
    content: str = "Some doc content",
    title: str = "Doc Title",
    score: float = 0.9,
) -> SemanticSearchResult:
    return SemanticSearchResult(
        chunk_id=uuid.uuid4(),
        content=content,
        title=title,
        source_type="notion",
        created_at="2026-03-10",
        score=score,
        chunk_index=0,
    )


def _make_db_row(
    event_id: str = "evt-1",
    title: str = "Sprint Planning",
    created_at: datetime = NOW,
    content: str | None = None,
):
    row = MagicMock()
    row.event_id = event_id
    row.title = title
    row.created_at = created_at
    row.content = content
    return row


def _make_session(rows: list | None = None) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.fetchall.return_value = rows or []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)
    return session


def _make_search_service(results: list[SemanticSearchResult] | None = None) -> AsyncMock:
    svc = AsyncMock()
    svc.search = AsyncMock(return_value=results or [])
    return svc


def _make_graph_service(
    histories: list[ParticipantHistory] | None = None,
    decisions: list[PendingDecision] | None = None,
) -> AsyncMock:
    svc = AsyncMock()
    svc.get_participant_history = AsyncMock(return_value=histories or [])
    svc.get_pending_decisions = AsyncMock(return_value=decisions or [])
    return svc


# ------------------------------------------------------------------
# CalendarEvent tests
# ------------------------------------------------------------------


class TestCalendarEvent:
    def test_create_basic(self) -> None:
        ev = _make_event()
        assert ev.event_id == "evt-1"
        assert ev.title == "Sprint Planning"

    def test_default_participants_empty(self) -> None:
        ev = CalendarEvent(event_id="x", title="Test", start_time=NOW)
        assert ev.participants == []


# ------------------------------------------------------------------
# NullGraphService tests
# ------------------------------------------------------------------


class TestNullGraphService:
    @pytest.mark.asyncio
    async def test_returns_empty_histories(self) -> None:
        svc = NullGraphService()
        result = await svc.get_participant_history(["Alice"], USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_decisions(self) -> None:
        svc = NullGraphService()
        result = await svc.get_pending_decisions(USER_ID)
        assert result == []


# ------------------------------------------------------------------
# Participant extraction
# ------------------------------------------------------------------


class TestParticipantExtraction:
    def test_extract_german_format(self) -> None:
        content = "Thema: Sprint\nTeilnehmer: Alice, Bob, Charlie\nNotizen: ..."
        result = MorningContextAssembler._extract_participants(content)
        assert result == ["Alice", "Bob", "Charlie"]

    def test_extract_english_format(self) -> None:
        content = "Participants: Alice, Bob"
        result = MorningContextAssembler._extract_participants(content)
        assert result == ["Alice", "Bob"]

    def test_no_participants_line(self) -> None:
        content = "Just some meeting notes"
        result = MorningContextAssembler._extract_participants(content)
        assert result == []

    def test_empty_content(self) -> None:
        result = MorningContextAssembler._extract_participants("")
        assert result == []

    def test_case_insensitive(self) -> None:
        content = "teilnehmer: Alice"
        result = MorningContextAssembler._extract_participants(content)
        assert result == ["Alice"]


# ------------------------------------------------------------------
# Search query construction
# ------------------------------------------------------------------


class TestBuildSearchQuery:
    def test_from_events(self) -> None:
        events = [
            _make_event(title="Sprint Planning"),
            _make_event(title="Design Review"),
        ]
        query = MorningContextAssembler._build_search_query(events, TODAY)
        assert "Sprint Planning" in query
        assert "Design Review" in query

    def test_no_events_uses_date(self) -> None:
        query = MorningContextAssembler._build_search_query([], TODAY)
        assert "2026-03-14" in query

    def test_caps_at_10_events(self) -> None:
        events = [_make_event(title=f"Event {i}") for i in range(15)]
        query = MorningContextAssembler._build_search_query(events, TODAY)
        parts = query.split()
        # Should have at most 10 event titles
        assert len(parts) <= 20  # max 2 words per title * 10


# ------------------------------------------------------------------
# Token counting
# ------------------------------------------------------------------


class TestTokenCounting:
    def test_counts_tokens(self) -> None:
        ctx = MorningBriefingContext(
            date="2026-03-14",
            calendar_events=[{"title": "Sprint", "time": "10:00", "participants": []}],
            participant_histories={},
            recent_documents=[],
            pending_decisions=[],
        )
        tokens = MorningContextAssembler._count_tokens(ctx)
        assert tokens > 0

    def test_more_content_more_tokens(self) -> None:
        ctx_small = MorningBriefingContext(
            date="2026-03-14",
            calendar_events=[],
            participant_histories={},
            recent_documents=[],
            pending_decisions=[],
        )
        ctx_large = MorningBriefingContext(
            date="2026-03-14",
            calendar_events=[
                {"title": f"Event {i}", "time": "10:00", "participants": []} for i in range(10)
            ],
            participant_histories={},
            recent_documents=[
                {
                    "title": f"Doc {i}",
                    "content": f"Long content {i} " * 50,
                    "source": "notion",
                    "date": "2026-03-10",
                    "score": 0.9,
                }
                for i in range(10)
            ],
            pending_decisions=[],
        )
        small_tokens = MorningContextAssembler._count_tokens(ctx_small)
        large_tokens = MorningContextAssembler._count_tokens(ctx_large)
        assert large_tokens > small_tokens


# ------------------------------------------------------------------
# Token budget enforcement
# ------------------------------------------------------------------


class TestTokenBudget:
    def test_within_budget_unchanged(self) -> None:
        session = _make_session()
        search = _make_search_service()
        config = MorningBriefingConfig(token_budget=10000)
        assembler = MorningContextAssembler(session, search, config=config)

        ctx = MorningBriefingContext(
            date="2026-03-14",
            calendar_events=[{"title": "Short", "time": "10:00", "participants": []}],
            participant_histories={},
            recent_documents=[
                {"title": "D", "content": "C", "source": "x", "date": "d", "score": 0.1}
            ],
            pending_decisions=[],
        )
        result = assembler._enforce_token_budget(ctx)
        assert not result.truncated
        assert len(result.recent_documents) == 1

    def test_over_budget_trims_documents_first(self) -> None:
        session = _make_session()
        search = _make_search_service()
        config = MorningBriefingConfig(token_budget=10)  # Very small
        assembler = MorningContextAssembler(session, search, config=config)

        ctx = MorningBriefingContext(
            date="2026-03-14",
            calendar_events=[{"title": "Meeting", "time": "10:00", "participants": []}],
            participant_histories={},
            recent_documents=[
                {
                    "title": f"Doc {i}",
                    "content": "x " * 100,
                    "source": "n",
                    "date": "d",
                    "score": 0.1,
                }
                for i in range(5)
            ],
            pending_decisions=[
                {"title": "Dec 1", "project": "P", "created": "d", "context": "c " * 50}
            ],
        )
        result = assembler._enforce_token_budget(ctx)
        assert result.truncated
        # Documents should be trimmed before decisions
        assert len(result.recent_documents) < 5

    def test_calendar_events_never_trimmed(self) -> None:
        session = _make_session()
        search = _make_search_service()
        config = MorningBriefingConfig(token_budget=10)
        assembler = MorningContextAssembler(session, search, config=config)

        ctx = MorningBriefingContext(
            date="2026-03-14",
            calendar_events=[
                {"title": f"Event {i}", "time": "10:00", "participants": []} for i in range(5)
            ],
            participant_histories={},
            recent_documents=[],
            pending_decisions=[],
        )
        result = assembler._enforce_token_budget(ctx)
        # Events are never removed
        assert len(result.calendar_events) == 5


# ------------------------------------------------------------------
# Full assembly
# ------------------------------------------------------------------


class TestAssemble:
    @pytest.mark.asyncio
    async def test_basic_assembly(self) -> None:
        rows = [_make_db_row(event_id="e1", title="Standup")]
        session = _make_session(rows)
        search = _make_search_service([_make_search_result()])
        graph = _make_graph_service()

        assembler = MorningContextAssembler(session, search, graph)
        ctx = await assembler.assemble(USER_ID, target_date=TODAY)

        assert ctx.date == "2026-03-14"
        assert len(ctx.calendar_events) == 1
        assert ctx.calendar_events[0]["title"] == "Standup"

    @pytest.mark.asyncio
    async def test_no_events_still_works(self) -> None:
        session = _make_session([])
        search = _make_search_service([_make_search_result()])
        graph = _make_graph_service()

        assembler = MorningContextAssembler(session, search, graph)
        ctx = await assembler.assemble(USER_ID, target_date=TODAY)

        assert ctx.calendar_events == []
        assert len(ctx.recent_documents) == 1

    @pytest.mark.asyncio
    async def test_graph_service_called_with_participants(self) -> None:
        rows = [
            _make_db_row(
                event_id="e1",
                title="Meeting",
                content="Teilnehmer: Alice, Bob",
            )
        ]
        session = _make_session(rows)
        search = _make_search_service()
        graph = _make_graph_service(
            histories=[
                ParticipantHistory(name="Alice", last_meetings=["Sprint"]),
            ]
        )

        assembler = MorningContextAssembler(session, search, graph)
        ctx = await assembler.assemble(USER_ID, target_date=TODAY)

        graph.get_participant_history.assert_called_once()
        call_args = graph.get_participant_history.call_args
        assert "Alice" in call_args[0][0]
        assert "Bob" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_pending_decisions_included(self) -> None:
        session = _make_session([])
        search = _make_search_service()
        graph = _make_graph_service(
            decisions=[
                PendingDecision(title="API Design", project="PWBS"),
            ]
        )

        assembler = MorningContextAssembler(session, search, graph)
        ctx = await assembler.assemble(USER_ID, target_date=TODAY)

        assert len(ctx.pending_decisions) == 1
        assert ctx.pending_decisions[0]["title"] == "API Design"

    @pytest.mark.asyncio
    async def test_user_id_passed_to_session(self) -> None:
        session = _make_session([])
        search = _make_search_service()
        graph = _make_graph_service()

        uid = uuid.uuid4()
        assembler = MorningContextAssembler(session, search, graph)
        await assembler.assemble(uid, target_date=TODAY)

        session.execute.assert_called_once()
        params = session.execute.call_args[0][1]
        assert params["user_id"] == str(uid)

    @pytest.mark.asyncio
    async def test_search_called_with_event_topics(self) -> None:
        rows = [
            _make_db_row(event_id="e1", title="API Review"),
            _make_db_row(event_id="e2", title="Sprint Demo"),
        ]
        session = _make_session(rows)
        search = _make_search_service()
        graph = _make_graph_service()

        assembler = MorningContextAssembler(session, search, graph)
        await assembler.assemble(USER_ID, target_date=TODAY)

        search.search.assert_called_once()
        query = search.search.call_args.kwargs.get("query") or search.search.call_args[0][0]
        assert "API Review" in query
        assert "Sprint Demo" in query

    @pytest.mark.asyncio
    async def test_null_graph_service_default(self) -> None:
        """If no graph service provided, NullGraphService is used."""
        session = _make_session([])
        search = _make_search_service()

        assembler = MorningContextAssembler(session, search)
        ctx = await assembler.assemble(USER_ID, target_date=TODAY)

        # Should work without errors
        assert ctx.pending_decisions == []

    @pytest.mark.asyncio
    async def test_token_count_set(self) -> None:
        session = _make_session([_make_db_row()])
        search = _make_search_service([_make_search_result()])
        graph = _make_graph_service()

        assembler = MorningContextAssembler(session, search, graph)
        ctx = await assembler.assemble(USER_ID, target_date=TODAY)

        assert ctx.token_count > 0


# ------------------------------------------------------------------
# Config defaults
# ------------------------------------------------------------------


class TestConfig:
    def test_default_values(self) -> None:
        config = MorningBriefingConfig()
        assert config.token_budget == 8000
        assert config.lookback_days == 7
        assert config.max_events == 20
        assert config.max_decisions == 10
        assert config.max_documents == 20
