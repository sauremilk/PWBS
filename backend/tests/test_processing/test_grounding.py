"""Tests für Halluzinations-Mitigation mit Quellenreferenz-Pflicht (TASK-069)."""

from __future__ import annotations

import pytest

from pwbs.core.grounding import (
    Confidence,
    GroundingConfig,
    GroundingResult,
    GroundingService,
    GroundedStatement,
    SourceReference,
    build_grounding_system_prompt,
    build_structured_prompt,
)


# ------------------------------------------------------------------
# Prompt builder tests
# ------------------------------------------------------------------


class TestBuildGroundingSystemPrompt:
    """Tests for grounding system prompt augmentation."""

    def test_contains_grounding_instruction(self) -> None:
        result = build_grounding_system_prompt("Du bist ein Assistent.")
        assert "ausschließlich basierend auf den bereitgestellten Quellen" in result
        assert "Du bist ein Assistent." in result

    def test_contains_source_format_instruction(self) -> None:
        result = build_grounding_system_prompt("")
        assert "[Quelle: Dokumenttitel, Datum]" in result

    def test_contains_no_prior_knowledge_instruction(self) -> None:
        result = build_grounding_system_prompt("")
        assert "KEIN Vorwissen" in result

    def test_base_prompt_preserved(self) -> None:
        base = "Spezielle Instruktion für Briefings."
        result = build_grounding_system_prompt(base)
        assert base in result


class TestBuildStructuredPrompt:
    """Tests for structured user prompt with sources."""

    def test_includes_sources(self) -> None:
        sources = [
            {"title": "Meeting Notes", "date": "2026-03-14", "content": "Discussion about X."},
            {"title": "Project Plan", "date": "2026-03-10", "content": "Timeline details."},
        ]
        result = build_structured_prompt("Was wurde besprochen?", sources)
        assert "Meeting Notes" in result
        assert "Project Plan" in result
        assert "Discussion about X." in result
        assert "Was wurde besprochen?" in result

    def test_includes_section_structure(self) -> None:
        result = build_structured_prompt("Frage", [])
        assert "Fakten" in result
        assert "Zusammenhänge" in result
        assert "Empfehlungen" in result

    def test_empty_sources(self) -> None:
        result = build_structured_prompt("Frage", [])
        assert "Aufgabe" in result
        assert "Frage" in result


# ------------------------------------------------------------------
# Source extraction tests
# ------------------------------------------------------------------


class TestSourceExtraction:
    """Tests for parsing [Quelle: ...] references."""

    def test_single_reference(self) -> None:
        text = "Das Meeting war produktiv. [Quelle: Meeting Notes, 2026-03-14]"
        refs = GroundingService._extract_sources(text)
        assert len(refs) == 1
        assert refs[0].title == "Meeting Notes"
        assert refs[0].date == "2026-03-14"

    def test_multiple_references(self) -> None:
        text = (
            "Punkt A. [Quelle: Doc A, 2026-03-14] "
            "Punkt B. [Quelle: Doc B, März 2026]"
        )
        refs = GroundingService._extract_sources(text)
        assert len(refs) == 2
        assert refs[0].title == "Doc A"
        assert refs[1].title == "Doc B"
        assert refs[1].date == "März 2026"

    def test_no_references(self) -> None:
        refs = GroundingService._extract_sources("Kein Verweis hier.")
        assert refs == []

    def test_reference_with_spaces(self) -> None:
        text = "[Quelle:  Langer Titel mit Leerzeichen ,  14. März 2026 ]"
        refs = GroundingService._extract_sources(text)
        assert len(refs) == 1
        assert refs[0].title == "Langer Titel mit Leerzeichen"
        assert refs[0].date == "14. März 2026"

    def test_raw_preserved(self) -> None:
        text = "Text [Quelle: Test, 2026-01-01] mehr."
        refs = GroundingService._extract_sources(text)
        assert refs[0].raw == "[Quelle: Test, 2026-01-01]"


# ------------------------------------------------------------------
# Confidence scoring tests
# ------------------------------------------------------------------


class TestConfidenceScoring:
    """Tests for confidence level assignment."""

    def test_high_with_valid_source(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Meeting Notes"}])
        result = svc.analyze("Das Ergebnis war gut. [Quelle: Meeting Notes, 2026-03-14]")
        stmt = [s for s in result.statements if "Ergebnis" in s.text][0]
        assert stmt.confidence == Confidence.HIGH

    def test_low_without_any_source(self) -> None:
        svc = GroundingService(known_sources=[{"title": "X"}])
        result = svc.analyze("Eine Aussage ohne Quellenangabe.")
        stmt = [s for s in result.statements if "Aussage" in s.text][0]
        assert stmt.confidence == Confidence.LOW

    def test_medium_with_invalid_source(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Real Doc"}])
        result = svc.analyze("Etwas passierte. [Quelle: Halluziniertes Dokument, 2026-01-01]")
        stmt = [s for s in result.statements if "passierte" in s.text][0]
        assert stmt.confidence == Confidence.MEDIUM

    def test_heading_is_high_confidence(self) -> None:
        svc = GroundingService()
        result = svc.analyze("# Fakten\nText hier.")
        heading = [s for s in result.statements if s.text.strip().startswith("#")][0]
        assert heading.confidence == Confidence.HIGH

    def test_no_known_sources_all_valid(self) -> None:
        """Without known sources, all references are considered valid."""
        svc = GroundingService()  # no known sources
        result = svc.analyze("Fakt. [Quelle: Irgendwas, 2026-01-01]")
        stmt = [s for s in result.statements if "Fakt" in s.text][0]
        assert stmt.confidence == Confidence.HIGH


# ------------------------------------------------------------------
# Source validation tests
# ------------------------------------------------------------------


class TestSourceValidation:
    """Tests for validating source references against known sources."""

    def test_exact_match(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Sprint Planning Notes"}])
        result = svc.analyze("Ergebnis. [Quelle: Sprint Planning Notes, 2026-03-14]")
        assert result.valid_source_count == 1
        assert result.invalid_source_count == 0

    def test_case_insensitive_match(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Meeting Notes"}])
        result = svc.analyze("X. [Quelle: meeting notes, 2026-03-14]")
        assert result.valid_source_count == 1

    def test_substring_fuzzy_match(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Sprint Planning Meeting Notes Q1"}])
        # LLM might abbreviate title
        result = svc.analyze("Y. [Quelle: Sprint Planning Meeting Notes, 2026-03-14]")
        assert result.valid_source_count == 1

    def test_invalid_source_detected(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Real Document"}])
        result = svc.analyze("Z. [Quelle: Erfundenes Dokument, 2026-03-14]")
        assert result.invalid_source_count == 1
        assert result.valid_source_count == 0

    def test_mixed_valid_and_invalid(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Doc A"}])
        text = (
            "Punkt 1. [Quelle: Doc A, 2026-03-14]\n"
            "Punkt 2. [Quelle: Fake Doc, 2026-03-14]"
        )
        result = svc.analyze(text)
        assert result.valid_source_count == 1
        assert result.invalid_source_count == 1

    def test_add_known_source(self) -> None:
        svc = GroundingService(known_sources=[{"title": "Doc A"}])
        svc.add_known_source("Doc B")
        result = svc.analyze("X. [Quelle: Doc B, 2026-01-01]")
        assert result.valid_source_count == 1


# ------------------------------------------------------------------
# Cleaned text tests
# ------------------------------------------------------------------


class TestCleanedText:
    """Tests for cleaned output text generation."""

    def test_invalid_refs_removed(self) -> None:
        svc = GroundingService(
            config=GroundingConfig(remove_invalid_refs=True),
            known_sources=[{"title": "Valid"}],
        )
        text = "Aussage. [Quelle: Halluziniert, 2026-01-01]"
        result = svc.analyze(text)
        assert "[Quelle: Halluziniert" not in result.cleaned_text

    def test_valid_refs_preserved(self) -> None:
        svc = GroundingService(
            config=GroundingConfig(remove_invalid_refs=True),
            known_sources=[{"title": "Real Doc"}],
        )
        text = "Fakt. [Quelle: Real Doc, 2026-03-14]"
        result = svc.analyze(text)
        assert "[Quelle: Real Doc, 2026-03-14]" in result.cleaned_text

    def test_low_confidence_marked(self) -> None:
        svc = GroundingService(
            config=GroundingConfig(mark_low_confidence=True),
            known_sources=[{"title": "Doc"}],
        )
        text = "Unbelegte Aussage hier."
        result = svc.analyze(text)
        assert "⚠️" in result.cleaned_text

    def test_custom_low_confidence_marker(self) -> None:
        svc = GroundingService(
            config=GroundingConfig(
                mark_low_confidence=True,
                low_confidence_marker=" [UNBELEGT]",
            ),
            known_sources=[{"title": "Doc"}],
        )
        result = svc.analyze("Keine Quelle angegeben.")
        assert "[UNBELEGT]" in result.cleaned_text

    def test_no_marking_when_disabled(self) -> None:
        svc = GroundingService(
            config=GroundingConfig(mark_low_confidence=False),
            known_sources=[{"title": "Doc"}],
        )
        result = svc.analyze("Ohne Quelle.")
        assert "⚠️" not in result.cleaned_text


# ------------------------------------------------------------------
# Full analysis integration test
# ------------------------------------------------------------------


class TestFullAnalysis:
    """Integration tests for the full grounding analysis pipeline."""

    def test_structured_output_analysis(self) -> None:
        svc = GroundingService(
            known_sources=[
                {"title": "Sprint Planning"},
                {"title": "Projekt Alpha Status"},
            ],
        )

        llm_output = (
            "# Fakten\n\n"
            "Das Sprint Planning fand am Montag statt. [Quelle: Sprint Planning, 2026-03-10]\n"
            "Projekt Alpha ist im Zeitplan. [Quelle: Projekt Alpha Status, 2026-03-12]\n\n"
            "# Zusammenhänge\n\n"
            "Die Team-Velocity steigt. [Quelle: Erfundener Report, 2026-03-01]\n\n"
            "# Empfehlungen\n\n"
            "Nächste Schritte sollten priorisiert werden."
        )

        result = svc.analyze(llm_output)

        assert result.valid_source_count == 2
        assert result.invalid_source_count == 1

        # Check confidence distribution
        high_stmts = [s for s in result.statements if s.confidence == Confidence.HIGH]
        low_stmts = [s for s in result.statements if s.confidence == Confidence.LOW]

        assert len(high_stmts) >= 2  # The two valid-sourced statements + headings
        assert len(low_stmts) >= 1  # "Nächste Schritte" has no source

    def test_empty_input(self) -> None:
        svc = GroundingService()
        result = svc.analyze("")
        assert result.valid_source_count == 0
        assert result.invalid_source_count == 0
