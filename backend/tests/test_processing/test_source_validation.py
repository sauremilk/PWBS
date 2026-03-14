"""Tests for BriefingSourceValidator (TASK-079)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.briefing.validation import (
    BriefingSourceValidator,
    SourceValidationResult,
    ValidatedReference,
    _SOURCE_REF_RE,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_doc(
    title: str,
    chunk_count: int = 2,
    created_at: datetime | None = None,
) -> dict:
    """Create a mock document row dict."""
    doc_id = uuid.uuid4()
    return {
        "doc_id": doc_id,
        "title": title,
        "created_at": created_at or datetime(2025, 1, 15, tzinfo=timezone.utc),
        "chunk_ids": [uuid.uuid4() for _ in range(chunk_count)],
    }


def _make_row(
    doc_id: uuid.UUID,
    title: str,
    created_at: datetime,
    chunk_ids: list[uuid.UUID] | None,
) -> Any:
    """Create a mock DB row with attribute access."""
    row = MagicMock()
    row.doc_id = doc_id
    row.title = title
    row.created_at = created_at
    row.chunk_ids = chunk_ids
    return row


def _mock_session(docs: list[dict]) -> AsyncMock:
    """Create a mock session returning given documents."""
    session = AsyncMock()
    rows = [
        _make_row(
            doc_id=d["doc_id"],
            title=d["title"],
            created_at=d["created_at"],
            chunk_ids=d["chunk_ids"],
        )
        for d in docs
    ]
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows
    session.execute = AsyncMock(return_value=result_mock)
    return session


# ------------------------------------------------------------------
# Regex Tests
# ------------------------------------------------------------------


class TestSourceRefRegex:
    """Tests for the [Quelle: Title, Date] regex."""

    def test_basic_match(self) -> None:
        text = "[Quelle: Meeting Notes, 2025-01-15]"
        matches = _SOURCE_REF_RE.findall(text)
        assert len(matches) == 1
        assert matches[0][0].strip() == "Meeting Notes"
        assert matches[0][1].strip() == "2025-01-15"

    def test_multiple_matches(self) -> None:
        text = (
            "Text [Quelle: Doc A, 15.01.2025] und "
            "[Quelle: Doc B, 16.01.2025] Ende."
        )
        matches = _SOURCE_REF_RE.findall(text)
        assert len(matches) == 2

    def test_no_match(self) -> None:
        text = "No references here."
        matches = _SOURCE_REF_RE.findall(text)
        assert len(matches) == 0

    def test_title_with_spaces(self) -> None:
        text = "[Quelle: Projekt Alpha Meeting Notes, 2025-01]"
        matches = _SOURCE_REF_RE.findall(text)
        assert len(matches) == 1
        assert matches[0][0].strip() == "Projekt Alpha Meeting Notes"


# ------------------------------------------------------------------
# Extract References
# ------------------------------------------------------------------


class TestExtractReferences:
    """Tests for the reference extraction logic."""

    def test_extract_empty(self) -> None:
        refs = BriefingSourceValidator._extract_references("No refs here.")
        assert refs == []

    def test_extract_single(self) -> None:
        text = "Some text [Quelle: My Document, 2025-01-15] more text."
        refs = BriefingSourceValidator._extract_references(text)
        assert len(refs) == 1
        assert refs[0]["title"] == "My Document"
        assert refs[0]["date"] == "2025-01-15"
        assert refs[0]["raw"] == "[Quelle: My Document, 2025-01-15]"

    def test_extract_multiple(self) -> None:
        text = (
            "[Quelle: A, 2025-01-01] text [Quelle: B, 2025-01-02] end"
        )
        refs = BriefingSourceValidator._extract_references(text)
        assert len(refs) == 2
        assert refs[0]["title"] == "A"
        assert refs[1]["title"] == "B"


# ------------------------------------------------------------------
# Fuzzy Matching
# ------------------------------------------------------------------


class TestFuzzyMatching:
    """Tests for the fuzzy matching logic."""

    def setup_method(self) -> None:
        self.session = AsyncMock()
        self.validator = BriefingSourceValidator(self.session)

    def test_exact_match(self) -> None:
        doc = _make_doc("Meeting Notes")
        ref = {"title": "Meeting Notes", "date": "2025-01-15", "raw": ""}
        result = self.validator._find_best_match(ref, [doc])
        assert result is not None
        assert result[0] == doc["doc_id"]
        assert result[2] == 1.0

    def test_case_insensitive(self) -> None:
        doc = _make_doc("Meeting Notes")
        ref = {"title": "meeting notes", "date": "2025-01-15", "raw": ""}
        result = self.validator._find_best_match(ref, [doc])
        assert result is not None
        assert result[2] == 1.0

    def test_substring_match(self) -> None:
        doc = _make_doc("Projekt Alpha - Quarterly Review Meeting Notes")
        ref = {"title": "Quarterly Review Meeting Notes", "date": "2025-01", "raw": ""}
        result = self.validator._find_best_match(ref, [doc])
        assert result is not None
        assert result[2] == 0.9

    def test_fuzzy_match(self) -> None:
        doc = _make_doc("Quarterly Review Meeting")
        ref = {"title": "Quarterly Review Meetng", "date": "2025-01", "raw": ""}
        result = self.validator._find_best_match(ref, [doc])
        assert result is not None
        assert result[2] >= 0.6

    def test_no_match_below_threshold(self) -> None:
        doc = _make_doc("Totally Different Document")
        ref = {"title": "XYZ Unrelated", "date": "2025-01", "raw": ""}
        result = self.validator._find_best_match(ref, [doc])
        assert result is None

    def test_empty_doc_title_skipped(self) -> None:
        doc = _make_doc("")
        ref = {"title": "Something", "date": "2025-01", "raw": ""}
        result = self.validator._find_best_match(ref, [doc])
        assert result is None

    def test_best_match_chosen(self) -> None:
        docs = [
            _make_doc("Sprint Planning Notes"),
            _make_doc("Sprint Planning"),
        ]
        ref = {"title": "Sprint Planning", "date": "2025-01", "raw": ""}
        result = self.validator._find_best_match(ref, docs)
        assert result is not None
        assert result[0] == docs[1]["doc_id"]
        assert result[2] == 1.0

    def test_custom_threshold(self) -> None:
        validator = BriefingSourceValidator(self.session, min_fuzzy_ratio=0.95)
        doc = _make_doc("Quarterly Review Meeting")
        ref = {"title": "Quartly Revew Meting", "date": "2025-01", "raw": ""}
        result = validator._find_best_match(ref, [doc])
        assert result is None  # Multiple typos don't meet 0.95 threshold


# ------------------------------------------------------------------
# Text Cleaning
# ------------------------------------------------------------------


class TestTextCleaning:
    """Tests for the text cleaning logic."""

    def setup_method(self) -> None:
        self.session = AsyncMock()

    def test_remove_invalid(self) -> None:
        validator = BriefingSourceValidator(self.session, remove_invalid=True)
        vref = ValidatedReference(
            title="Fake", date="2025", raw="[Quelle: Fake, 2025]", is_valid=False,
        )
        result = validator._clean_text(
            "Begin [Quelle: Fake, 2025] end.", [vref],
        )
        assert "[Quelle: Fake, 2025]" not in result
        assert "Begin" in result

    def test_mark_invalid(self) -> None:
        validator = BriefingSourceValidator(self.session, remove_invalid=False)
        vref = ValidatedReference(
            title="Fake", date="2025", raw="[Quelle: Fake, 2025]", is_valid=False,
        )
        result = validator._clean_text(
            "Begin [Quelle: Fake, 2025] end.", [vref],
        )
        assert "[WARNUNG: Quelle nicht verifiziert]" in result

    def test_valid_refs_preserved(self) -> None:
        validator = BriefingSourceValidator(self.session, remove_invalid=True)
        vref = ValidatedReference(
            title="Real", date="2025", raw="[Quelle: Real, 2025]",
            document_id=uuid.uuid4(), is_valid=True, match_score=1.0,
        )
        result = validator._clean_text(
            "Begin [Quelle: Real, 2025] end.", [vref],
        )
        assert "[Quelle: Real, 2025]" in result

    def test_double_spaces_cleaned(self) -> None:
        validator = BriefingSourceValidator(self.session, remove_invalid=True)
        vref = ValidatedReference(
            title="X", date="2025", raw="[Quelle: X, 2025]", is_valid=False,
        )
        result = validator._clean_text(
            "A  [Quelle: X, 2025]  B", [vref],
        )
        assert "  " not in result


# ------------------------------------------------------------------
# Full Validation Flow (Integration with mock DB)
# ------------------------------------------------------------------


class TestValidateFlow:
    """Tests for the full validate() method."""

    @pytest.mark.asyncio
    async def test_no_references(self) -> None:
        session = _mock_session([])
        validator = BriefingSourceValidator(session)
        result = await validator.validate("No refs here.", uuid.uuid4())
        assert result.total_refs == 0
        assert result.source_chunks == []
        assert result.validated_text == "No refs here."
        # DB should not be queried
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_valid(self) -> None:
        doc = _make_doc("Sprint Planning", chunk_count=3)
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        text = "Meeting morgen [Quelle: Sprint Planning, 2025-01-15] ist wichtig."
        user_id = uuid.uuid4()
        result = await validator.validate(text, user_id)

        assert result.total_refs == 1
        assert result.removed_count == 0
        assert len(result.source_chunks) == 3
        assert result.validated_refs[0].is_valid is True
        assert "[Quelle: Sprint Planning, 2025-01-15]" in result.validated_text

    @pytest.mark.asyncio
    async def test_all_invalid(self) -> None:
        session = _mock_session([])  # No docs
        validator = BriefingSourceValidator(session)

        text = "Claim [Quelle: Nonexistent, 2025-01-01] here."
        result = await validator.validate(text, uuid.uuid4())

        assert result.total_refs == 1
        assert result.removed_count == 1
        assert result.source_chunks == []
        assert "[Quelle: Nonexistent, 2025-01-01]" not in result.validated_text

    @pytest.mark.asyncio
    async def test_mixed_valid_invalid(self) -> None:
        doc = _make_doc("Real Doc", chunk_count=2)
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        text = (
            "A [Quelle: Real Doc, 2025-01-15] B "
            "[Quelle: Zzz Nonexistent, 2025-01-01] C."
        )
        result = await validator.validate(text, uuid.uuid4())

        assert result.total_refs == 2
        assert result.removed_count == 1
        assert len(result.source_chunks) == 2
        assert "[Quelle: Real Doc, 2025-01-15]" in result.validated_text
        assert "[Quelle: Zzz Nonexistent, 2025-01-01]" not in result.validated_text

    @pytest.mark.asyncio
    async def test_fuzzy_match_resolves(self) -> None:
        doc = _make_doc("Quarterly Review Meeting", chunk_count=1)
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        text = "Info [Quelle: Quarterly Review Meetng, 2025-01-15] end."
        result = await validator.validate(text, uuid.uuid4())

        assert result.total_refs == 1
        assert result.removed_count == 0
        assert result.validated_refs[0].is_valid is True
        assert result.validated_refs[0].match_score >= 0.6

    @pytest.mark.asyncio
    async def test_deduplicated_chunk_ids(self) -> None:
        doc = _make_doc("Same Doc", chunk_count=2)
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        text = (
            "[Quelle: Same Doc, 2025-01-15] und "
            "[Quelle: Same Doc, 2025-01-16]"
        )
        result = await validator.validate(text, uuid.uuid4())

        assert result.total_refs == 2
        # Chunk IDs should be deduplicated
        assert len(result.source_chunks) == 2  # doc has 2 chunks

    @pytest.mark.asyncio
    async def test_user_isolation(self) -> None:
        """Verify user_id is passed to the DB query."""
        doc = _make_doc("Some Doc")
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        user_id = uuid.uuid4()
        await validator.validate("[Quelle: Some Doc, 2025]", user_id)

        session.execute.assert_called_once()
        call_args = session.execute.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("parameters", {})
        assert params["user_id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_mark_mode(self) -> None:
        session = _mock_session([])
        validator = BriefingSourceValidator(session, remove_invalid=False)

        text = "Claim [Quelle: Missing, 2025] here."
        result = await validator.validate(text, uuid.uuid4())

        assert "[WARNUNG: Quelle nicht verifiziert]" in result.validated_text

    @pytest.mark.asyncio
    async def test_documents_with_no_chunks(self) -> None:
        """Documents with no chunks should match but return empty chunk list."""
        doc_id = uuid.uuid4()
        now = datetime(2025, 1, 15, tzinfo=timezone.utc)
        row = _make_row(doc_id, "Lonely Doc", now, None)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [row]
        session.execute = AsyncMock(return_value=result_mock)

        validator = BriefingSourceValidator(session)
        result = await validator.validate(
            "[Quelle: Lonely Doc, 2025]", uuid.uuid4(),
        )

        assert result.total_refs == 1
        assert result.validated_refs[0].is_valid is True
        assert result.source_chunks == []

    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        session = _mock_session([])
        validator = BriefingSourceValidator(session)
        result = await validator.validate("", uuid.uuid4())
        assert result.total_refs == 0
        assert result.validated_text == ""


# ------------------------------------------------------------------
# Edge Cases
# ------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_special_chars_in_title(self) -> None:
        doc = _make_doc("Q&A Session (2025)")
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        text = "[Quelle: Q&A Session (2025), 2025-01-15]"
        result = await validator.validate(text, uuid.uuid4())

        assert result.validated_refs[0].is_valid is True

    @pytest.mark.asyncio
    async def test_long_title(self) -> None:
        long_title = "A" * 200
        doc = _make_doc(long_title)
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        text = f"[Quelle: {long_title}, 2025-01-15]"
        result = await validator.validate(text, uuid.uuid4())

        assert result.validated_refs[0].is_valid is True

    @pytest.mark.asyncio
    async def test_multiple_docs_best_match(self) -> None:
        docs = [
            _make_doc("Sprint Retrospective Q1"),
            _make_doc("Sprint Planning Q1"),
            _make_doc("Sprint Review Q1"),
        ]
        session = _mock_session(docs)
        validator = BriefingSourceValidator(session)

        text = "[Quelle: Sprint Planning Q1, 2025]"
        result = await validator.validate(text, uuid.uuid4())

        assert result.validated_refs[0].is_valid is True
        assert result.validated_refs[0].document_id == docs[1]["doc_id"]

    @pytest.mark.asyncio
    async def test_source_entities_empty(self) -> None:
        """source_entities is always empty (future work)."""
        doc = _make_doc("Doc")
        session = _mock_session([doc])
        validator = BriefingSourceValidator(session)

        result = await validator.validate("[Quelle: Doc, 2025]", uuid.uuid4())
        assert result.source_entities == []
