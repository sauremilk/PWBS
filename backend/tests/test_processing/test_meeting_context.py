"""Tests for Meeting-Vorbereitung Kontextassemblierung (TASK-077)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.meeting_context import (
    MeetingContextAssembler,
    MeetingContextConfig,
    MeetingGraphService,
    MeetingPrepContext,
    NullMeetingGraphService,
    ParticipantContext,
)
from pwbs.search.service import SemanticSearchResult

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EVENT_ID = "evt-001"
NOW = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_session(
    row: dict[str, Any] | None = None,
) -> AsyncMock:
    """Mock AsyncSession returning a single row from execute."""
    session = AsyncMock()
    result = MagicMock()
    mappings = MagicMock()

    if row is None:
        mappings.first.return_value = None
    else:
        mappings.first.return_value = row

    result.mappings.return_value = mappings
    session.execute.return_value = result
    return session


def _make_event_row(
    title: str = "Sprint Retro",
    participants: list[dict[str, str]] | None = None,
    start_time: str = "2026-06-01T10:00:00Z",
    location: str | None = "Room A",
) -> dict[str, Any]:
    if participants is None:
        participants = [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
        ]
    return {
        "title": title,
        "content": "Sprint retro discussion",
        "metadata": {
            "start_time": start_time,
            "location": location,
            "participants": participants,
        },
    }


def _make_search_result(
    title: str = "Related Doc",
    content: str = "Some related content here",
    source_type: str = "notion",
    score: float = 0.85,
) -> SemanticSearchResult:
    return SemanticSearchResult(
        chunk_id=uuid.uuid4(),
        content=content,
        title=title,
        source_type=source_type,
        created_at="2026-05-28T10:00:00Z",
        score=score,
        chunk_index=0,
    )


def _make_graph_service(
    known_participants: dict[str, ParticipantContext] | None = None,
) -> AsyncMock:
    """Graph service mock returning participant contexts."""
    known = known_participants or {}
    svc = AsyncMock(spec=MeetingGraphService)

    async def _get_ctx(
        participant_name: str,
        owner_id: uuid.UUID,
        limit: int = 5,
    ) -> ParticipantContext:
        if participant_name in known:
            return known[participant_name]
        return ParticipantContext(name=participant_name, known=False)

    svc.get_participant_context = AsyncMock(side_effect=_get_ctx)
    return svc


def _make_assembler(
    session: AsyncMock | None = None,
    search_results: list[SemanticSearchResult] | None = None,
    graph_service: AsyncMock | None = None,
    config: MeetingContextConfig | None = None,
) -> MeetingContextAssembler:
    sess = session or _make_session(_make_event_row())
    search_svc = AsyncMock()
    search_svc.search = AsyncMock(return_value=search_results or [])
    return MeetingContextAssembler(
        session=sess,
        search_service=search_svc,
        graph_service=graph_service,
        config=config,
    )


# ===================================================================
# Config
# ===================================================================


class TestMeetingContextConfig:
    def test_defaults(self) -> None:
        cfg = MeetingContextConfig()
        assert cfg.token_budget == 6000
        assert cfg.lookback_days == 14
        assert cfg.max_documents == 15
        assert cfg.min_participants == 2

    def test_custom(self) -> None:
        cfg = MeetingContextConfig(token_budget=3000, max_documents=5)
        assert cfg.token_budget == 3000
        assert cfg.max_documents == 5


# ===================================================================
# NullMeetingGraphService
# ===================================================================


class TestNullMeetingGraphService:
    @pytest.mark.asyncio
    async def test_returns_unknown_participant(self) -> None:
        svc = NullMeetingGraphService()
        ctx = await svc.get_participant_context("Alice", USER_ID)
        assert ctx.name == "Alice"
        assert ctx.known is False
        assert ctx.last_meetings == []
        assert ctx.shared_projects == []
        assert ctx.open_items == []


# ===================================================================
# Event Loading
# ===================================================================


class TestLoadEvent:
    @pytest.mark.asyncio
    async def test_event_found(self) -> None:
        session = _make_session(_make_event_row(title="Kickoff"))
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.meeting_title == "Kickoff"

    @pytest.mark.asyncio
    async def test_event_not_found(self) -> None:
        session = _make_session(row=None)
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.meeting_title == "Unbekannter Termin"
        assert ctx.participants == []
        assert ctx.relevant_documents == []

    @pytest.mark.asyncio
    async def test_event_with_location(self) -> None:
        session = _make_session(_make_event_row(location="Room B"))
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.meeting_location == "Room B"

    @pytest.mark.asyncio
    async def test_event_without_location(self) -> None:
        session = _make_session(_make_event_row(location=None))
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.meeting_location is None

    @pytest.mark.asyncio
    async def test_start_time_preserved(self) -> None:
        session = _make_session(
            _make_event_row(start_time="2026-06-01T14:00:00Z"),
        )
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert "14:00" in ctx.meeting_time


# ===================================================================
# Participant Extraction
# ===================================================================


class TestParticipantExtraction:
    @pytest.mark.asyncio
    async def test_dict_participants(self) -> None:
        session = _make_session(
            _make_event_row(
                participants=[
                    {"name": "Alice", "email": "a@x.com"},
                    {"name": "Bob", "email": "b@x.com"},
                ],
            ),
        )
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        names = [p["name"] for p in ctx.participants]
        assert "Alice" in names
        assert "Bob" in names

    @pytest.mark.asyncio
    async def test_string_participants(self) -> None:
        session = _make_session(
            _make_event_row(participants=["Carol", "Dave"]),
        )
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        names = [p["name"] for p in ctx.participants]
        assert "Carol" in names
        assert "Dave" in names

    @pytest.mark.asyncio
    async def test_empty_participants(self) -> None:
        session = _make_session(_make_event_row(participants=[]))
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.participants == []

    @pytest.mark.asyncio
    async def test_blank_name_skipped(self) -> None:
        session = _make_session(
            _make_event_row(participants=[{"name": "", "email": "x@x.com"}]),
        )
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.participants == []


# ===================================================================
# Graph Integration
# ===================================================================


class TestGraphIntegration:
    @pytest.mark.asyncio
    async def test_known_participant_has_history(self) -> None:
        alice_ctx = ParticipantContext(
            name="Alice",
            known=True,
            last_meetings=["Sprint Retro (May 15)"],
            shared_projects=["Project Phoenix"],
            open_items=["Finalize API spec"],
        )
        graph = _make_graph_service(known_participants={"Alice": alice_ctx})
        session = _make_session(
            _make_event_row(participants=[{"name": "Alice", "email": "a@x.com"}]),
        )
        asm = _make_assembler(session=session, graph_service=graph)
        ctx = await asm.assemble(USER_ID, EVENT_ID)

        alice = ctx.participants[0]
        assert alice["known"] is True
        assert "Sprint Retro (May 15)" in alice["last_meetings"]
        assert "Project Phoenix" in alice["shared_projects"]
        assert "Finalize API spec" in alice["open_items"]

    @pytest.mark.asyncio
    async def test_unknown_participant_flagged(self) -> None:
        graph = _make_graph_service(known_participants={})
        session = _make_session(
            _make_event_row(participants=[{"name": "NewPerson", "email": "n@x.com"}]),
        )
        asm = _make_assembler(session=session, graph_service=graph)
        ctx = await asm.assemble(USER_ID, EVENT_ID)

        p = ctx.participants[0]
        assert p["known"] is False
        assert "Neu im System" in p.get("note", "")

    @pytest.mark.asyncio
    async def test_null_graph_service_used_as_default(self) -> None:
        session = _make_session(
            _make_event_row(participants=[{"name": "X", "email": "x@x.com"}]),
        )
        asm = MeetingContextAssembler(
            session=session,
            search_service=AsyncMock(search=AsyncMock(return_value=[])),
        )
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.participants[0]["known"] is False


# ===================================================================
# Semantic Search
# ===================================================================


class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_documents_returned(self) -> None:
        results = [_make_search_result(title="Design Doc")]
        asm = _make_assembler(search_results=results)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert len(ctx.relevant_documents) == 1
        assert ctx.relevant_documents[0]["title"] == "Design Doc"

    @pytest.mark.asyncio
    async def test_documents_have_required_fields(self) -> None:
        results = [_make_search_result()]
        asm = _make_assembler(search_results=results)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        doc = ctx.relevant_documents[0]
        assert "title" in doc
        assert "content" in doc
        assert "source" in doc
        assert "score" in doc
        assert "chunk_id" in doc

    @pytest.mark.asyncio
    async def test_search_failure_returns_empty(self) -> None:
        search_svc = AsyncMock()
        search_svc.search = AsyncMock(side_effect=RuntimeError("connection"))
        session = _make_session(_make_event_row())
        asm = MeetingContextAssembler(
            session=session,
            search_service=search_svc,
        )
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.relevant_documents == []

    @pytest.mark.asyncio
    async def test_content_truncated_to_500(self) -> None:
        long_content = "x" * 1000
        results = [_make_search_result(content=long_content)]
        asm = _make_assembler(search_results=results)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert len(ctx.relevant_documents[0]["content"]) == 500

    @pytest.mark.asyncio
    async def test_search_query_includes_title_and_participants(self) -> None:
        session = _make_session(
            _make_event_row(
                title="Architecture Review",
                participants=[{"name": "Alice", "email": "a@x.com"}],
            ),
        )
        search_svc = AsyncMock()
        search_svc.search = AsyncMock(return_value=[])
        asm = MeetingContextAssembler(
            session=session,
            search_service=search_svc,
        )
        await asm.assemble(USER_ID, EVENT_ID)

        call_args = search_svc.search.call_args
        query = call_args.kwargs.get("query") or call_args[1].get("query", call_args[0][0] if call_args[0] else "")
        assert "Architecture Review" in query
        assert "Alice" in query


# ===================================================================
# Open Items
# ===================================================================


class TestOpenItems:
    @pytest.mark.asyncio
    async def test_open_items_aggregated(self) -> None:
        alice_ctx = ParticipantContext(
            name="Alice", known=True, open_items=["Item A"],
        )
        bob_ctx = ParticipantContext(
            name="Bob", known=True, open_items=["Item B"],
        )
        graph = _make_graph_service(
            known_participants={"Alice": alice_ctx, "Bob": bob_ctx},
        )
        session = _make_session(
            _make_event_row(
                participants=[
                    {"name": "Alice", "email": "a@x.com"},
                    {"name": "Bob", "email": "b@x.com"},
                ],
            ),
        )
        asm = _make_assembler(session=session, graph_service=graph)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert "Item A" in ctx.open_items_summary
        assert "Item B" in ctx.open_items_summary

    @pytest.mark.asyncio
    async def test_duplicate_open_items_deduplicated(self) -> None:
        alice_ctx = ParticipantContext(
            name="Alice", known=True, open_items=["Shared Item"],
        )
        bob_ctx = ParticipantContext(
            name="Bob", known=True, open_items=["Shared Item"],
        )
        graph = _make_graph_service(
            known_participants={"Alice": alice_ctx, "Bob": bob_ctx},
        )
        session = _make_session(
            _make_event_row(
                participants=[
                    {"name": "Alice", "email": "a@x.com"},
                    {"name": "Bob", "email": "b@x.com"},
                ],
            ),
        )
        asm = _make_assembler(session=session, graph_service=graph)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.open_items_summary.count("Shared Item") == 1


# ===================================================================
# Token Budget
# ===================================================================


class TestTokenBudget:
    @pytest.mark.asyncio
    async def test_small_context_not_truncated(self) -> None:
        asm = _make_assembler()
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.truncated is False
        assert ctx.token_count > 0

    @pytest.mark.asyncio
    async def test_large_context_trimmed(self) -> None:
        many_docs = [
            _make_search_result(content="x " * 300, title=f"Doc {i}")
            for i in range(30)
        ]
        asm = _make_assembler(
            search_results=many_docs,
            config=MeetingContextConfig(token_budget=500),
        )
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.truncated is True
        assert ctx.token_count <= 500

    @pytest.mark.asyncio
    async def test_documents_trimmed_before_open_items(self) -> None:
        alice_ctx = ParticipantContext(
            name="Alice", known=True, open_items=["Important item"],
        )
        graph = _make_graph_service(known_participants={"Alice": alice_ctx})
        many_docs = [
            _make_search_result(content="y " * 200, title=f"Doc {i}")
            for i in range(20)
        ]
        session = _make_session(
            _make_event_row(
                participants=[{"name": "Alice", "email": "a@x.com"}],
            ),
        )
        asm = _make_assembler(
            session=session,
            search_results=many_docs,
            graph_service=graph,
            config=MeetingContextConfig(token_budget=800),
        )
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        # Open items survive trimming (participants > open items > documents)
        assert "Important item" in ctx.open_items_summary

    @pytest.mark.asyncio
    async def test_token_count_set(self) -> None:
        asm = _make_assembler()
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.token_count > 0


# ===================================================================
# Edge Cases
# ===================================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_metadata_none(self) -> None:
        session = _make_session(
            {"title": "Test", "content": "content", "metadata": None},
        )
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.meeting_title == "Test"
        assert ctx.participants == []

    @pytest.mark.asyncio
    async def test_metadata_empty(self) -> None:
        session = _make_session(
            {"title": "Test", "content": "content", "metadata": {}},
        )
        asm = _make_assembler(session=session)
        ctx = await asm.assemble(USER_ID, EVENT_ID)
        assert ctx.meeting_title == "Test"
        assert ctx.participants == []

    @pytest.mark.asyncio
    async def test_config_property(self) -> None:
        cfg = MeetingContextConfig(token_budget=4000)
        asm = _make_assembler(config=cfg)
        assert asm.config.token_budget == 4000

    @pytest.mark.asyncio
    async def test_user_id_passed_to_graph(self) -> None:
        graph = _make_graph_service({})
        session = _make_session(
            _make_event_row(participants=[{"name": "Alice", "email": "a@x.com"}]),
        )
        asm = _make_assembler(session=session, graph_service=graph)
        await asm.assemble(USER_ID, EVENT_ID)
        call_args = graph.get_participant_context.call_args
        assert call_args[0][1] == USER_ID

    @pytest.mark.asyncio
    async def test_user_id_passed_to_search(self) -> None:
        search_svc = AsyncMock()
        search_svc.search = AsyncMock(return_value=[])
        session = _make_session(_make_event_row())
        asm = MeetingContextAssembler(
            session=session,
            search_service=search_svc,
        )
        await asm.assemble(USER_ID, EVENT_ID)
        call_args = search_svc.search.call_args
        assert call_args.kwargs.get("user_id") == USER_ID
