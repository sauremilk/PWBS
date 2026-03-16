"""Tests for pwbs.briefing.validation - source reference validation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.validation import (
    BriefingSourceValidator,
    SourceValidationResult,
    ValidatedReference,
)

# ---------------------------------------------------------------------------
# _extract_references (static method)
# ---------------------------------------------------------------------------


class TestExtractReferences:
    def test_single_reference(self) -> None:
        text = "Hier ist der Absatz. [Quelle: Meeting Notes, 2024-01-15]"
        refs = BriefingSourceValidator._extract_references(text)
        assert len(refs) == 1
        assert refs[0]["title"] == "Meeting Notes"
        assert refs[0]["date"] == "2024-01-15"

    def test_multiple_references(self) -> None:
        text = "Info A [Quelle: Doc A, 2024-01-01] und Info B [Quelle: Doc B, 2024-02-01]."
        refs = BriefingSourceValidator._extract_references(text)
        assert len(refs) == 2

    def test_no_references(self) -> None:
        refs = BriefingSourceValidator._extract_references("No sources here.")
        assert refs == []

    def test_whitespace_handling(self) -> None:
        text = "[Quelle:  Spaced Title ,  2024-03-01 ]"
        refs = BriefingSourceValidator._extract_references(text)
        assert len(refs) == 1
        assert refs[0]["title"] == "Spaced Title"
        assert refs[0]["date"] == "2024-03-01"


# ---------------------------------------------------------------------------
# _find_best_match
# ---------------------------------------------------------------------------


class TestFindBestMatch:
    def _make_validator(self, min_fuzzy_ratio: float = 0.6) -> BriefingSourceValidator:
        return BriefingSourceValidator(
            session=AsyncMock(),
            min_fuzzy_ratio=min_fuzzy_ratio,
        )

    def test_exact_match(self) -> None:
        validator = self._make_validator()
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        docs = [{"doc_id": doc_id, "title": "Sprint Review", "chunk_ids": [chunk_id]}]
        ref = {"title": "Sprint Review", "date": "2024-01-01", "raw": "..."}
        result = validator._find_best_match(ref, docs)
        assert result is not None
        assert result[0] == doc_id
        assert result[2] == 1.0

    def test_substring_match(self) -> None:
        validator = self._make_validator()
        doc_id = uuid.uuid4()
        docs = [{"doc_id": doc_id, "title": "Sprint Review Q1 2024", "chunk_ids": []}]
        ref = {"title": "Sprint Review", "date": "2024-01-01", "raw": "..."}
        result = validator._find_best_match(ref, docs)
        assert result is not None
        assert result[2] == 0.9

    def test_fuzzy_match_above_threshold(self) -> None:
        validator = self._make_validator(min_fuzzy_ratio=0.5)
        doc_id = uuid.uuid4()
        docs = [{"doc_id": doc_id, "title": "Sprint Review Notes", "chunk_ids": []}]
        ref = {"title": "Sprint Reviw Notes", "date": "2024-01-01", "raw": "..."}
        result = validator._find_best_match(ref, docs)
        assert result is not None
        assert result[0] == doc_id

    def test_no_match_below_threshold(self) -> None:
        validator = self._make_validator(min_fuzzy_ratio=0.99)
        doc_id = uuid.uuid4()
        docs = [{"doc_id": doc_id, "title": "Completely Different", "chunk_ids": []}]
        ref = {"title": "Sprint Review", "date": "2024-01-01", "raw": "..."}
        result = validator._find_best_match(ref, docs)
        assert result is None

    def test_empty_document_title_skipped(self) -> None:
        validator = self._make_validator()
        docs = [{"doc_id": uuid.uuid4(), "title": "", "chunk_ids": []}]
        ref = {"title": "Sprint Review", "date": "2024-01-01", "raw": "..."}
        result = validator._find_best_match(ref, docs)
        assert result is None


# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------


class TestCleanText:
    def test_removes_invalid_references(self) -> None:
        validator = BriefingSourceValidator(session=AsyncMock(), remove_invalid=True)
        text = "Good text. [Quelle: Bad Source, 2024-01-01] More text."
        invalid = ValidatedReference(
            title="Bad Source",
            date="2024-01-01",
            raw="[Quelle: Bad Source, 2024-01-01]",
            is_valid=False,
        )
        result = validator._clean_text(text, [invalid])
        assert "[Quelle:" not in result
        assert "Good text." in result
        assert "More text." in result

    def test_marks_invalid_when_not_removing(self) -> None:
        validator = BriefingSourceValidator(session=AsyncMock(), remove_invalid=False)
        text = "Text [Quelle: Unbekannt, 2024-01-01] end."
        invalid = ValidatedReference(
            title="Unbekannt",
            date="2024-01-01",
            raw="[Quelle: Unbekannt, 2024-01-01]",
            is_valid=False,
        )
        result = validator._clean_text(text, [invalid])
        assert "[WARNUNG: Quelle nicht verifiziert]" in result

    def test_valid_references_untouched(self) -> None:
        validator = BriefingSourceValidator(session=AsyncMock(), remove_invalid=True)
        text = "Text [Quelle: Valid, 2024-01-01] end."
        valid = ValidatedReference(
            title="Valid",
            date="2024-01-01",
            raw="[Quelle: Valid, 2024-01-01]",
            is_valid=True,
            match_score=1.0,
        )
        result = validator._clean_text(text, [valid])
        assert "[Quelle: Valid, 2024-01-01]" in result


# ---------------------------------------------------------------------------
# validate (integration-style with mocked DB)
# ---------------------------------------------------------------------------


class TestValidate:
    @pytest.mark.asyncio
    async def test_no_references_returns_empty(self) -> None:
        validator = BriefingSourceValidator(session=AsyncMock())
        result = await validator.validate("No sources here.", uuid.uuid4())
        assert isinstance(result, SourceValidationResult)
        assert result.total_refs == 0
        assert result.removed_count == 0
        assert result.source_chunks == []

    @pytest.mark.asyncio
    async def test_valid_reference_resolved(self) -> None:
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()

        # Mock DB result
        mock_row = MagicMock()
        mock_row.doc_id = str(doc_id)
        mock_row.title = "Sprint Review"
        mock_row.created_at = "2024-01-15"
        mock_row.chunk_ids = [str(chunk_id)]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        validator = BriefingSourceValidator(session=session)
        text = "Info [Quelle: Sprint Review, 2024-01-15] here."
        result = await validator.validate(text, uuid.uuid4())

        assert result.total_refs == 1
        assert result.removed_count == 0
        assert len(result.source_chunks) == 1
        assert result.source_chunks[0] == chunk_id

    @pytest.mark.asyncio
    async def test_invalid_reference_removed(self) -> None:
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        session = AsyncMock()
        session.execute = AsyncMock(return_value=mock_result)

        validator = BriefingSourceValidator(session=session, remove_invalid=True)
        text = "Info [Quelle: Unknown, 2024-01-01] here."
        result = await validator.validate(text, uuid.uuid4())

        assert result.total_refs == 1
        assert result.removed_count == 1
        assert "[Quelle:" not in result.validated_text
