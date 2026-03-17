"""Tests for Project Briefing (TASK-133).

Tests covering:
- ProjectContextAssembler (context building, token budget, document fetch)
- BriefingGenerator with PROJECT type
- BriefingPersistenceService with PROJECT expiry
- BriefingType.PROJECT in schemas
- Prompt template existence
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.generator import (
    BriefingGenerator,
    BriefingGeneratorConfig,
    BriefingLLMResult,
)
from pwbs.briefing.generator import BriefingType as GenBriefingType
from pwbs.briefing.persistence import (
    PersistenceConfig,
)
from pwbs.briefing.project_context import (
    NullProjectGraphService,
    ProjectBriefingConfig,
    ProjectBriefingContext,
    ProjectContextAssembler,
    ProjectDecision,
    ProjectMilestone,
    ProjectParticipant,
)
from pwbs.core.llm_gateway import LLMProvider, LLMResponse, LLMUsage
from pwbs.schemas.enums import BriefingType

USER_ID = uuid.uuid4()
PROJECT_NAME = "PWBS Phase 2"

MOCK_USAGE = LLMUsage(
    provider=LLMProvider.CLAUDE,
    model="claude-sonnet-4-20250514",
    input_tokens=800,
    output_tokens=600,
    duration_ms=2000.0,
    estimated_cost_usd=0.008,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _mock_session_with_documents(
    documents: list[dict] | None = None,
) -> AsyncMock:
    """Create a mock async session that returns documents."""
    docs = (
        documents
        if documents is not None
        else [
            {
                "doc_id": str(uuid.uuid4()),
                "title": "PWBS Phase 2 Sprint Planning",
                "source_type": "notion",
                "created_at": datetime(2025, 6, 13, 10, 0, tzinfo=UTC),
            },
            {
                "doc_id": str(uuid.uuid4()),
                "title": "PWBS Phase 2 Architecture Review",
                "source_type": "google_docs",
                "created_at": datetime(2025, 6, 12, 14, 0, tzinfo=UTC),
            },
            {
                "doc_id": str(uuid.uuid4()),
                "title": "PWBS Phase 2 Meeting Notes",
                "source_type": "zoom",
                "created_at": datetime(2025, 6, 11, 16, 0, tzinfo=UTC),
            },
        ]
    )

    mock_rows = []
    for d in docs:
        row = MagicMock()
        row.doc_id = d["doc_id"]
        row.title = d["title"]
        row.source_type = d["source_type"]
        row.created_at = d["created_at"]
        mock_rows.append(row)

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows
    session.execute = AsyncMock(return_value=mock_result)
    session.add = MagicMock()
    session.flush = AsyncMock()

    return session


def _mock_search_service() -> MagicMock:
    """Create a mock SemanticSearchService."""
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[])
    return svc


def _make_template() -> MagicMock:
    tpl = MagicMock()
    tpl.id = "briefing_project.v1"
    tpl.system_prompt = "Du bist ein Briefing-Assistent."
    tpl.template = "## Projektbriefing: {{ project_name }}"
    tpl.required_context = [
        "project_name",
        "decisions",
        "timeline",
        "participants",
        "open_items",
        "recent_documents",
        "summary_stats",
    ]
    tpl.temperature = 0.3
    tpl.max_output_tokens = 3000
    return tpl


def _make_registry(template: MagicMock | None = None) -> MagicMock:
    tpl = template or _make_template()
    registry = MagicMock()
    registry.get.return_value = tpl
    registry.render.return_value = "## Projektbriefing: PWBS Phase 2"
    return registry


def _make_gateway(
    content: str = "# Projektbriefing\n\nDas Projekt ist auf Kurs. [Quelle: Sprint Notes, 13.06.2025]",
) -> AsyncMock:
    gw = AsyncMock()
    gw.generate = AsyncMock(
        return_value=LLMResponse(
            content=content,
            usage=MOCK_USAGE,
            provider=LLMProvider.CLAUDE,
            model="claude-sonnet-4-20250514",
        )
    )
    return gw


class _MockGraphService:
    """Graph service with configurable return values for testing."""

    def __init__(
        self,
        decisions: list[ProjectDecision] | None = None,
        participants: list[ProjectParticipant] | None = None,
        timeline: list[ProjectMilestone] | None = None,
        open_items: list[str] | None = None,
    ) -> None:
        self._decisions = decisions or []
        self._participants = participants or []
        self._timeline = timeline or []
        self._open_items = open_items or []

    async def get_project_decisions(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[ProjectDecision]:
        return self._decisions

    async def get_project_participants(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 15,
    ) -> list[ProjectParticipant]:
        return self._participants

    async def get_project_timeline(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[ProjectMilestone]:
        return self._timeline

    async def get_project_open_items(
        self,
        owner_id: uuid.UUID,
        project_name: str,
        limit: int = 10,
    ) -> list[str]:
        return self._open_items


# ------------------------------------------------------------------
# BriefingType enum
# ------------------------------------------------------------------


class TestProjectBriefingType:
    """Verify PROJECT exists in both BriefingType enums."""

    def test_schema_enum_has_project(self) -> None:
        assert BriefingType.PROJECT.value == "project"

    def test_generator_enum_has_project(self) -> None:
        assert GenBriefingType.PROJECT.value == "project"

    def test_schema_project_roundtrip(self) -> None:
        assert BriefingType("project") == BriefingType.PROJECT

    def test_generator_project_roundtrip(self) -> None:
        assert GenBriefingType("project") == GenBriefingType.PROJECT


# ------------------------------------------------------------------
# ProjectContextAssembler
# ------------------------------------------------------------------


class TestProjectContextAssembler:
    """Tests for the project context assembler."""

    @pytest.mark.asyncio
    async def test_assemble_returns_context(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
            graph_service=NullProjectGraphService(),
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        assert isinstance(ctx, ProjectBriefingContext)
        assert ctx.project_name == PROJECT_NAME
        assert isinstance(ctx.recent_documents, list)
        assert isinstance(ctx.decisions, list)
        assert isinstance(ctx.participants, list)

    @pytest.mark.asyncio
    async def test_assemble_fetches_documents(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        session.execute.assert_called_once()
        assert len(ctx.recent_documents) == 3

    @pytest.mark.asyncio
    async def test_assemble_empty_documents(self) -> None:
        session = _mock_session_with_documents(documents=[])
        search = _mock_search_service()
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        assert ctx.recent_documents == []
        assert ctx.document_count == 0

    @pytest.mark.asyncio
    async def test_assemble_with_graph_data(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        graph = _MockGraphService(
            decisions=[
                ProjectDecision(title="Weaviate als Vektordatenbank", status="resolved"),
                ProjectDecision(title="API-Rate-Limiting", status="pending"),
            ],
            participants=[
                ProjectParticipant(name="Alice", role="Tech Lead", contribution_count=15),
                ProjectParticipant(name="Bob", role="Backend Dev", contribution_count=8),
            ],
            timeline=[
                ProjectMilestone(title="Kickoff", date="01.01.2025"),
                ProjectMilestone(title="MVP Release", date="15.03.2025"),
            ],
            open_items=["CI/CD Pipeline einrichten", "Load-Tests schreiben"],
        )
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
            graph_service=graph,
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        assert len(ctx.decisions) == 2
        assert ctx.decisions[0]["title"] == "Weaviate als Vektordatenbank"
        assert len(ctx.participants) == 2
        assert ctx.participants[0]["name"] == "Alice"
        assert len(ctx.timeline) == 2
        assert len(ctx.open_items) == 2

    @pytest.mark.asyncio
    async def test_assemble_summary_stats(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        graph = _MockGraphService(
            decisions=[ProjectDecision(title="Test")],
            participants=[ProjectParticipant(name="Alice")],
            open_items=["Item 1", "Item 2"],
        )
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
            graph_service=graph,
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        assert ctx.summary_stats["document_count"] == 3
        assert ctx.summary_stats["decision_count"] == 1
        assert ctx.summary_stats["participant_count"] == 1
        assert ctx.summary_stats["open_item_count"] == 2

    @pytest.mark.asyncio
    async def test_assemble_with_project_id(self) -> None:
        session = _mock_session_with_documents()
        search = _mock_search_service()
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
        )

        ctx = await assembler.assemble(
            user_id=USER_ID,
            project_name=PROJECT_NAME,
            project_id="entity-123",
        )

        assert ctx.project_id == "entity-123"


class TestProjectContextTokenBudget:
    """Tests for token budget enforcement."""

    @pytest.mark.asyncio
    async def test_context_without_truncation(self) -> None:
        session = _mock_session_with_documents(documents=[])
        search = _mock_search_service()
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
            config=ProjectBriefingConfig(token_budget=8000),
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        assert not ctx.truncated
        assert ctx.token_count <= 8000

    @pytest.mark.asyncio
    async def test_context_truncation_under_tight_budget(self) -> None:
        # Many documents to force truncation
        many_docs = [
            {
                "doc_id": str(uuid.uuid4()),
                "title": f"Dokument {i} mit einem langen Titel über das Projekt ABC und viele Details",
                "source_type": "notion",
                "created_at": datetime(2025, 6, 13, 10, 0, tzinfo=UTC),
            }
            for i in range(30)
        ]
        session = _mock_session_with_documents(documents=many_docs)
        search = _mock_search_service()
        graph = _MockGraphService(
            open_items=[f"Open item {i}" for i in range(20)],
            participants=[ProjectParticipant(name=f"Person {i}") for i in range(15)],
        )
        assembler = ProjectContextAssembler(
            session=session,
            search_service=search,
            graph_service=graph,
            config=ProjectBriefingConfig(token_budget=50),
        )

        ctx = await assembler.assemble(user_id=USER_ID, project_name=PROJECT_NAME)

        assert ctx.truncated
        assert ctx.token_count <= 50


class TestNullProjectGraphService:
    """Tests for the NullProjectGraphService fallback."""

    @pytest.mark.asyncio
    async def test_decisions_empty(self) -> None:
        svc = NullProjectGraphService()
        result = await svc.get_project_decisions(USER_ID, PROJECT_NAME)
        assert result == []

    @pytest.mark.asyncio
    async def test_participants_empty(self) -> None:
        svc = NullProjectGraphService()
        result = await svc.get_project_participants(USER_ID, PROJECT_NAME)
        assert result == []

    @pytest.mark.asyncio
    async def test_timeline_empty(self) -> None:
        svc = NullProjectGraphService()
        result = await svc.get_project_timeline(USER_ID, PROJECT_NAME)
        assert result == []

    @pytest.mark.asyncio
    async def test_open_items_empty(self) -> None:
        svc = NullProjectGraphService()
        result = await svc.get_project_open_items(USER_ID, PROJECT_NAME)
        assert result == []


# ------------------------------------------------------------------
# BriefingGenerator with PROJECT
# ------------------------------------------------------------------


class TestProjectBriefingGenerator:
    """Tests for BriefingGenerator with PROJECT type."""

    @pytest.mark.asyncio
    async def test_generate_project_briefing(self) -> None:
        gateway = _make_gateway()
        registry = _make_registry()

        config = BriefingGeneratorConfig(project_max_output_tokens=3000)
        generator = BriefingGenerator(gateway, registry, config)

        result = await generator.generate(
            briefing_type=GenBriefingType.PROJECT,
            context={
                "project_name": PROJECT_NAME,
                "decisions": [],
                "timeline": [],
                "participants": [],
                "open_items": [],
                "recent_documents": [],
                "summary_stats": {"document_count": 0},
            },
            user_id=USER_ID,
        )

        assert isinstance(result, BriefingLLMResult)
        assert result.briefing_type == GenBriefingType.PROJECT
        registry.get.assert_called_once_with("briefing_project")
        gateway.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_max_output_tokens(self) -> None:
        gateway = _make_gateway()
        tpl = _make_template()
        tpl.max_output_tokens = None
        registry = _make_registry(tpl)

        config = BriefingGeneratorConfig(project_max_output_tokens=3000)
        generator = BriefingGenerator(gateway, registry, config)

        await generator.generate(
            briefing_type=GenBriefingType.PROJECT,
            context={"project_name": PROJECT_NAME},
            user_id=USER_ID,
        )

        call_args = gateway.generate.call_args
        request = call_args.args[0] if call_args.args else call_args.kwargs.get("request")
        assert request.max_tokens == 3000

    @pytest.mark.asyncio
    async def test_project_max_words_1200(self) -> None:
        from pwbs.briefing.generator import _MAX_WORDS

        assert _MAX_WORDS[GenBriefingType.PROJECT] == 1200


# ------------------------------------------------------------------
# Persistence with PROJECT
# ------------------------------------------------------------------


class TestProjectBriefingPersistence:
    """Tests for BriefingPersistenceService with PROJECT type."""

    def test_project_expiry_is_7_days(self) -> None:
        from pwbs.briefing.persistence import _EXPIRY_DURATIONS

        assert _EXPIRY_DURATIONS[BriefingType.PROJECT] == timedelta(days=7)

    def test_persistence_config_has_project_expiry(self) -> None:
        config = PersistenceConfig()
        assert config.project_expiry_hours == 168


# ------------------------------------------------------------------
# Prompt template file
# ------------------------------------------------------------------


class TestProjectPromptTemplate:
    """Verify the prompt template file exists and is valid."""

    def test_template_file_exists(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[2] / "pwbs" / "prompts" / "briefing_project.v1.j2"
        )
        assert template_path.exists(), f"Template not found: {template_path}"

    def test_template_has_required_context(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[2] / "pwbs" / "prompts" / "briefing_project.v1.j2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "project_name" in content
        assert "decisions" in content
        assert "timeline" in content
        assert "participants" in content
        assert "open_items" in content
        assert "recent_documents" in content
        assert "summary_stats" in content

    def test_template_has_front_matter(self) -> None:
        template_path = (
            Path(__file__).resolve().parents[2] / "pwbs" / "prompts" / "briefing_project.v1.j2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "max_output_tokens: 3000" in content
        assert "temperature: 0.3" in content
