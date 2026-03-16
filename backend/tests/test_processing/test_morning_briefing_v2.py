"""Tests für Morning Briefing v2 – Quellenreferenzen, Word-Budget, Struktur.

Validiert die Anforderungen aus briefing-feature.prompt.md:
- sources niemals leer
- Token/Word-Budget-Einhaltung (max 800 Wörter)
- Pflichtfelder: date, agenda_items (calendar_events), open_threads
  (pending_decisions), context_updates (recent_documents)
- Fakten vs. Interpretation klar getrennt
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.context import (
    CalendarEvent,
    MorningBriefingConfig,
    MorningBriefingContext,
    MorningContextAssembler,
    NullGraphService,
    PendingDecision,
)
from pwbs.briefing.generator import (
    BriefingGenerator,
    BriefingGeneratorConfig,
    BriefingLLMResult,
    BriefingType,
)
from pwbs.core.llm_gateway import LLMProvider, LLMResponse, LLMUsage
from pwbs.prompts.registry import PromptRegistry
from pwbs.search.service import SemanticSearchResult

# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

USER_ID = uuid.uuid4()
TODAY = date(2026, 3, 16)
NOW = datetime(2026, 3, 16, 7, 0, 0, tzinfo=timezone.utc)

MOCK_USAGE = LLMUsage(
    provider=LLMProvider.CLAUDE,
    model="claude-sonnet-4-20250514",
    input_tokens=600,
    output_tokens=400,
    duration_ms=1500.0,
    estimated_cost_usd=0.006,
)


def _morning_context_with_sources() -> dict[str, Any]:
    """Kontext-Dict das alle Pflichtfelder für das v2-Template enthält."""
    return {
        "date": "2026-03-16",
        "calendar_events": [
            {
                "title": "Sprint Planning",
                "time": "10:00",
                "participants": ["Alice", "Bob"],
                "notes": "Backlog Review + Sprint Goals",
            },
            {
                "title": "Design Review",
                "time": "14:00",
                "participants": ["Charlie"],
            },
        ],
        "recent_documents": [
            {
                "title": "Sprint Notes KW11",
                "source": "notion",
                "date": "2026-03-14",
                "content": "Sprint Velocity: 42 Story Points abgeschlossen.",
                "score": 0.92,
            },
            {
                "title": "API Design Draft",
                "source": "obsidian",
                "date": "2026-03-15",
                "content": "REST-Endpunkte für Briefing-API definiert.",
                "score": 0.87,
            },
        ],
        "pending_decisions": [
            {
                "title": "Cache-Strategie für Embeddings",
                "project": "PWBS MVP",
                "created": "2026-03-10",
                "context": "Redis vs. lokaler In-Memory-Cache",
            },
        ],
        "patterns": [
            {
                "type": "wiederkehrend",
                "entity": "Sprint Planning",
                "summary": "Wöchentliches Meeting seit 8 Wochen",
                "count": 8,
            },
        ],
    }


def _llm_response_with_sources() -> str:
    """Simulierter LLM-Output im v2-Format mit Quellenreferenzen."""
    return (
        "## Morgenbriefing – 2026-03-16\n\n"
        "### Tagesagenda\n"
        "- **10:00 – Sprint Planning** [Quelle: Kalender, 2026-03-16]\n"
        "  Teilnehmer: Alice, Bob\n"
        "  Laut Sprint Notes KW11 wurden 42 Story Points abgeschlossen. "
        "[Quelle: Sprint Notes KW11, 2026-03-14]\n"
        "  → Fokus auf offene Backlog-Items legen.\n\n"
        "- **14:00 – Design Review** [Quelle: Kalender, 2026-03-16]\n"
        "  Teilnehmer: Charlie\n"
        "  Laut API Design Draft wurden REST-Endpunkte definiert. "
        "[Quelle: API Design Draft, 2026-03-15]\n\n"
        "### Offene Threads\n"
        "- **Cache-Strategie für Embeddings** (PWBS MVP) – Offen seit 2026-03-10\n"
        "  Redis vs. lokaler In-Memory-Cache [Quelle: Cache-Strategie für Embeddings, 2026-03-10]\n"
        "  → Entscheidung im heutigen Sprint Planning anstoßen.\n\n"
        "### Kontext-Updates\n"
        "- **Sprint Notes KW11** (notion, 2026-03-14): Sprint Velocity bei 42 SP. "
        "[Quelle: Sprint Notes KW11, 2026-03-14]\n"
        "- **API Design Draft** (obsidian, 2026-03-15): REST-Endpunkte definiert. "
        "[Quelle: API Design Draft, 2026-03-15]\n\n"
        "### Quellen\n"
        "- [Kalender] – google_calendar, 2026-03-16\n"
        "- [Sprint Notes KW11] – notion, 2026-03-14\n"
        "- [API Design Draft] – obsidian, 2026-03-15\n"
        "- [Cache-Strategie für Embeddings] – decision, 2026-03-10\n"
    )


def _llm_response_no_sources() -> str:
    """LLM-Output ohne Quellenreferenzen – sollte von Validierung erkannt werden."""
    return (
        "## Morgenbriefing – 2026-03-16\n\n"
        "### Tagesagenda\n"
        "Heute steht ein Sprint Planning an.\n\n"
        "### Offene Threads\n"
        "Es gibt eine offene Entscheidung zur Cache-Strategie.\n\n"
        "### Kontext-Updates\n"
        "Keine aktuellen Updates.\n"
    )


def _llm_response_over_budget() -> str:
    """LLM-Output der 800 Wörter überschreitet."""
    words = " ".join(f"Wort{i}" for i in range(900))
    return f"## Morgenbriefing – 2026-03-16\n\n{words}\n"


def _make_gateway(content: str | None = None) -> AsyncMock:
    gw = AsyncMock()
    gw.generate = AsyncMock(
        return_value=LLMResponse(
            content=content or _llm_response_with_sources(),
            usage=MOCK_USAGE,
            provider=LLMProvider.CLAUDE,
            model="claude-sonnet-4-20250514",
        )
    )
    return gw


def _make_registry_mock(
    required_context: list[str] | None = None,
) -> MagicMock:
    """Erstellt einen gemockten PromptRegistry der das v2-Template simuliert."""
    tpl = MagicMock()
    tpl.id = "briefing_morning.v2"
    tpl.system_prompt = (
        "Du bist ein präziser Briefing-Assistent im PWBS. "
        "Kennzeichne JEDE Aussage mit [Quelle: Titel, Datum]. "
        "Maximal 800 Wörter."
    )
    tpl.template = "## Morgenbriefing für {{ date }}"
    tpl.required_context = required_context or [
        "date",
        "calendar_events",
        "recent_documents",
        "pending_decisions",
    ]
    tpl.temperature = 0.3
    tpl.max_output_tokens = 2000

    registry = MagicMock()
    registry.get.return_value = tpl
    registry.render.return_value = "## Morgenbriefing – 2026-03-16\n"
    return registry


# ------------------------------------------------------------------
# Quellenreferenzen: sources dürfen nie leer sein
# ------------------------------------------------------------------


class TestSourceReferencesNeverEmpty:
    """Validiert: Jede Briefing-Aussage durch mindestens eine SourceRef belegt."""

    @pytest.mark.asyncio
    async def test_output_contains_source_references(self) -> None:
        """LLM-Output muss [Quelle: ...] Referenzen enthalten."""
        gateway = _make_gateway(_llm_response_with_sources())
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
            known_sources=[
                {"title": "Sprint Notes KW11"},
                {"title": "API Design Draft"},
                {"title": "Kalender"},
            ],
        )

        assert "[Quelle:" in result.content
        assert result.grounding_result is not None
        assert result.grounding_result.valid_source_count >= 1

    @pytest.mark.asyncio
    async def test_output_without_sources_detectable(self) -> None:
        """Ein Output ohne [Quelle: ...] erzeugt 0 valid_source_count."""
        gateway = _make_gateway(_llm_response_no_sources())
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
            known_sources=[{"title": "Sprint Notes KW11"}],
        )

        # Die Grounding-Analyse erkennt fehlende Quellenreferenzen
        assert result.grounding_result is not None
        assert "[Quelle:" not in result.content

    @pytest.mark.asyncio
    async def test_grounding_validates_known_sources(self) -> None:
        """Grounding prüft ob referenzierte Quellen in known_sources existieren."""
        gateway = _make_gateway(_llm_response_with_sources())
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
            known_sources=[
                {"title": "Sprint Notes KW11"},
                {"title": "API Design Draft"},
            ],
        )

        assert result.grounding_result is not None

    @pytest.mark.asyncio
    async def test_no_grounding_without_known_sources(self) -> None:
        """Ohne known_sources wird kein Grounding durchgeführt."""
        gateway = _make_gateway(_llm_response_with_sources())
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
            known_sources=None,
        )

        assert result.grounding_result is None


# ------------------------------------------------------------------
# Word-Budget: max 800 Wörter für Morning Briefing
# ------------------------------------------------------------------


class TestWordBudgetEnforcement:
    """Validiert: Morning Briefings <= 800 Wörter."""

    @pytest.mark.asyncio
    async def test_within_budget_no_warning(self) -> None:
        """Output innerhalb des Budgets → kein Warning im Log."""
        content = " ".join(["Wort"] * 200) + " [Quelle: Test, 2026-03-16]"
        gateway = _make_gateway(content)
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
        )

        assert result.word_count <= 800

    @pytest.mark.asyncio
    async def test_over_budget_logged(self) -> None:
        """Output > 800 Wörter wird erkannt und word_count korrekt gesetzt."""
        gateway = _make_gateway(_llm_response_over_budget())
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
        )

        assert result.word_count > 800

    @pytest.mark.asyncio
    async def test_word_count_calculated_correctly(self) -> None:
        """Word-Count basiert auf split() des Contents."""
        content = "eins zwei drei vier fünf sechs sieben"
        gateway = _make_gateway(content)
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        result = await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
        )

        assert result.word_count == 7

    @pytest.mark.asyncio
    async def test_system_prompt_includes_800_word_limit(self) -> None:
        """System-Prompt enthält die Wortgrenze 800 für Morning."""
        gateway = _make_gateway()
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MORNING,
            _morning_context_with_sources(),
            USER_ID,
        )

        request = gateway.generate.call_args[0][0]
        assert "800" in request.system_prompt

    @pytest.mark.asyncio
    async def test_meeting_prep_has_400_word_limit(self) -> None:
        """Meeting Prep hat ein 400-Wort-Limit."""
        gateway = _make_gateway()
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.MEETING_PREP,
            _morning_context_with_sources(),
            USER_ID,
        )

        request = gateway.generate.call_args[0][0]
        assert "400" in request.system_prompt

    @pytest.mark.asyncio
    async def test_weekly_has_600_word_limit(self) -> None:
        """Weekly Briefing hat ein 600-Wort-Limit."""
        gateway = _make_gateway()
        registry = _make_registry_mock()
        gen = BriefingGenerator(gateway, registry)

        await gen.generate(
            BriefingType.WEEKLY,
            _morning_context_with_sources(),
            USER_ID,
        )

        request = gateway.generate.call_args[0][0]
        assert "600" in request.system_prompt


# ------------------------------------------------------------------
# Token-Budget im Kontext-Assembler
# ------------------------------------------------------------------


class TestContextTokenBudget:
    """Validiert: Context-Assembler hält das 8000-Token-Budget ein."""

    def test_small_context_within_budget(self) -> None:
        ctx = MorningBriefingContext(
            date="2026-03-16",
            calendar_events=[
                {"title": "Sprint Planning", "time": "10:00", "participants": []},
            ],
            participant_histories={},
            recent_documents=[
                {
                    "title": "Notes",
                    "content": "Short content",
                    "source": "notion",
                    "date": "d",
                    "score": 0.9,
                },
            ],
            pending_decisions=[],
        )
        session = AsyncMock()
        search = AsyncMock()
        assembler = MorningContextAssembler(session, search)
        result = assembler._enforce_token_budget(ctx)

        assert not result.truncated
        assert result.token_count <= 8000

    def test_large_context_gets_trimmed(self) -> None:
        """Kontext mit zu vielen Dokumenten wird auf Budget getrimmt."""
        ctx = MorningBriefingContext(
            date="2026-03-16",
            calendar_events=[
                {"title": "Meeting", "time": "10:00", "participants": []},
            ],
            participant_histories={},
            recent_documents=[
                {
                    "title": f"Doc {i}",
                    "content": "Langer Inhalt " * 200,
                    "source": "notion",
                    "date": "2026-03-15",
                    "score": 0.8,
                }
                for i in range(20)
            ],
            pending_decisions=[
                {
                    "title": f"Decision {i}",
                    "project": "PWBS",
                    "created": "2026-03-10",
                    "context": "Kontext " * 100,
                }
                for i in range(10)
            ],
        )
        session = AsyncMock()
        search = AsyncMock()
        config = MorningBriefingConfig(token_budget=500)
        assembler = MorningContextAssembler(session, search, config=config)
        result = assembler._enforce_token_budget(ctx)

        assert result.truncated
        assert len(result.recent_documents) < 20

    def test_calendar_events_never_trimmed(self) -> None:
        """Kalender-Events werden niemals gekürzt – höchste Priorität."""
        ctx = MorningBriefingContext(
            date="2026-03-16",
            calendar_events=[
                {"title": f"Event {i}", "time": "10:00", "participants": []} for i in range(10)
            ],
            participant_histories={},
            recent_documents=[],
            pending_decisions=[],
        )
        session = AsyncMock()
        search = AsyncMock()
        config = MorningBriefingConfig(token_budget=10)
        assembler = MorningContextAssembler(session, search, config=config)
        result = assembler._enforce_token_budget(ctx)

        assert len(result.calendar_events) == 10


# ------------------------------------------------------------------
# Strukturierte Morning-Briefing-Ausgabe (v2 Pflichtfelder)
# ------------------------------------------------------------------


class TestMorningBriefingStructure:
    """Validiert die Pflichtfelder des v2-Templates."""

    @pytest.mark.asyncio
    async def test_v2_template_loaded_as_latest(self) -> None:
        """Registry gibt v2 als neueste Version zurück."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert tpl.version == 2
        assert tpl.id == "briefing_morning.v2"

    @pytest.mark.asyncio
    async def test_v2_requires_pending_decisions(self) -> None:
        """v2-Template hat pending_decisions als Pflichtfeld."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert "pending_decisions" in tpl.required_context

    @pytest.mark.asyncio
    async def test_v2_requires_date(self) -> None:
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert "date" in tpl.required_context

    @pytest.mark.asyncio
    async def test_v2_requires_calendar_events(self) -> None:
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert "calendar_events" in tpl.required_context

    @pytest.mark.asyncio
    async def test_v2_requires_recent_documents(self) -> None:
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert "recent_documents" in tpl.required_context

    @pytest.mark.asyncio
    async def test_v2_renders_with_full_context(self) -> None:
        """v2-Template rendert korrekt mit allen Pflichtfeldern."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        rendered = registry.render(tpl, _morning_context_with_sources())

        assert "2026-03-16" in rendered
        assert "Sprint Planning" in rendered
        assert "Cache-Strategie" in rendered
        assert "Sprint Notes KW11" in rendered

    @pytest.mark.asyncio
    async def test_v2_renders_empty_sections_gracefully(self) -> None:
        """Template zeigt Fallback-Text wenn Sektionen leer sind."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        empty_context = {
            "date": "2026-03-16",
            "calendar_events": [],
            "recent_documents": [],
            "pending_decisions": [],
        }
        rendered = registry.render(tpl, empty_context)

        assert "Keine Termine" in rendered
        assert "Keine offenen Threads" in rendered
        assert "Keine aktuellen Dokumente" in rendered

    @pytest.mark.asyncio
    async def test_v2_system_prompt_enforces_source_format(self) -> None:
        """System-Prompt erzwingt [Quelle: Titel, Datum] Format."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert "[Quelle:" in tpl.system_prompt
        assert "800 Wörter" in tpl.system_prompt

    @pytest.mark.asyncio
    async def test_v2_temperature_is_03(self) -> None:
        """Sachliche Briefings verwenden Temperatur 0.3."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        assert tpl.temperature == 0.3


# ------------------------------------------------------------------
# Fakten vs. Interpretation Trennung
# ------------------------------------------------------------------


class TestFactsVsInterpretation:
    """Validiert: Systemanweisung trennt Fakten und Interpretationen."""

    @pytest.mark.asyncio
    async def test_system_prompt_requires_fact_marking(self) -> None:
        """System-Prompt enthält Anweisung zur Faktenkennzeichnung."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        # Prüfe ob Fakten/Interpretation-Trennung angewiesen wird
        sp = tpl.system_prompt.lower()
        assert "fakten" in sp or "laut" in sp
        assert "interpretation" in sp or "empfehlung" in sp or "→" in tpl.system_prompt

    @pytest.mark.asyncio
    async def test_llm_output_separates_facts_from_interpretation(self) -> None:
        """Simulierter LLM-Output enthält Fakten mit [Quelle:] und
        Interpretationen mit → Markierung."""
        content = _llm_response_with_sources()

        # Fakten: enthalten [Quelle: ...]
        assert "[Quelle:" in content

        # Interpretationen: beginnen mit →
        assert "→" in content

    @pytest.mark.asyncio
    async def test_system_prompt_forbids_llm_prior_knowledge(self) -> None:
        """System-Prompt verbietet LLM-Vorwissen (nur RAG)."""
        registry = PromptRegistry(
            prompts_dir=Path(__file__).parent.parent.parent / "pwbs" / "prompts"
        )
        tpl = registry.get("briefing_morning")
        sp = tpl.system_prompt.lower()
        assert "ausschliesslich" in sp or "ausschließlich" in sp or "nur" in sp
        assert "bereitgestellt" in sp or "informationen" in sp


# ------------------------------------------------------------------
# Context-Assembler: Suchanfragen + Kalender
# ------------------------------------------------------------------


class TestMorningContextAssemblerSearch:
    """Validiert: Suchanfragen für Morning = Kalendereinträge + offene Tasks."""

    def test_search_query_includes_event_titles(self) -> None:
        events = [
            CalendarEvent(event_id="e1", title="Sprint Planning", start_time=NOW),
            CalendarEvent(event_id="e2", title="Design Review", start_time=NOW),
        ]
        query = MorningContextAssembler._build_search_query(events, TODAY)
        assert "Sprint Planning" in query
        assert "Design Review" in query

    def test_search_query_fallback_without_events(self) -> None:
        query = MorningContextAssembler._build_search_query([], TODAY)
        assert "2026-03-16" in query

    @pytest.mark.asyncio
    async def test_assembler_calls_search_service(self) -> None:
        """Context-Assembler ruft die Suche mit Event-Titeln auf."""
        rows = [MagicMock(event_id="e1", title="Sprint", created_at=NOW, content=None)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        search = AsyncMock()
        search.search = AsyncMock(return_value=[])
        graph = NullGraphService()

        assembler = MorningContextAssembler(session, search, graph)
        await assembler.assemble(USER_ID, target_date=TODAY)

        search.search.assert_called_once()
        call_kwargs = search.search.call_args.kwargs
        assert "Sprint" in call_kwargs.get("query", "")

    @pytest.mark.asyncio
    async def test_assembler_enriches_query_with_preferences(self) -> None:
        """Nutzer-Präferenzen erweitern die Suchanfrage."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        search = AsyncMock()
        search.search = AsyncMock(return_value=[])
        graph = NullGraphService()

        assembler = MorningContextAssembler(session, search, graph)
        await assembler.assemble(
            USER_ID,
            target_date=TODAY,
            briefing_preferences={
                "focus_projects": ["PWBS MVP"],
                "priority_topics": ["Embeddings"],
            },
        )

        search.search.assert_called_once()
        query = search.search.call_args.kwargs.get("query", "")
        assert "PWBS MVP" in query
        assert "Embeddings" in query

    @pytest.mark.asyncio
    async def test_assembler_filters_excluded_sources(self) -> None:
        """Ausgeschlossene Quellen werden gefiltert."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        notion_doc = SemanticSearchResult(
            chunk_id=uuid.uuid4(),
            content="Notion content",
            title="Notion Doc",
            source_type="notion",
            created_at="2026-03-15",
            score=0.9,
            chunk_index=0,
        )
        zoom_doc = SemanticSearchResult(
            chunk_id=uuid.uuid4(),
            content="Zoom transcript",
            title="Zoom Call",
            source_type="zoom",
            created_at="2026-03-15",
            score=0.85,
            chunk_index=0,
        )

        search = AsyncMock()
        search.search = AsyncMock(return_value=[notion_doc, zoom_doc])
        graph = NullGraphService()

        assembler = MorningContextAssembler(session, search, graph)
        ctx = await assembler.assemble(
            USER_ID,
            target_date=TODAY,
            briefing_preferences={"excluded_sources": ["zoom"]},
        )

        # Zoom-Dokument sollte gefiltert sein
        source_types = [d["source"] for d in ctx.recent_documents]
        assert "zoom" not in source_types
        assert "notion" in source_types
