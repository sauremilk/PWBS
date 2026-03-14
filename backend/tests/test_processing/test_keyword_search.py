"""Tests für PostgreSQL tsvector Keyword-Suche (TASK-073)."""

from __future__ import annotations

import uuid
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.search.keyword import (
    KeywordSearchConfig,
    KeywordSearchResult,
    KeywordSearchService,
)

_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_CHUNK_ID_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
_CHUNK_ID_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
_DOC_ID_1 = uuid.UUID("33333333-3333-3333-3333-333333333333")
_DOC_ID_2 = uuid.UUID("44444444-4444-4444-4444-444444444444")

# Named tuple to mimic SQLAlchemy Row
_Row = namedtuple(
    "_Row",
    ["chunk_id", "document_id", "content_preview", "title", "source_type", "score"],
)


def _mock_session(rows: list[_Row] | None = None) -> AsyncMock:
    """Create a mock async session that returns the given rows."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows or []
    session.execute = AsyncMock(return_value=result_mock)
    return session


def _sample_rows() -> list[_Row]:
    return [
        _Row(
            chunk_id=str(_CHUNK_ID_1),
            document_id=str(_DOC_ID_1),
            content_preview="Sprint Planning ergab drei Prioritäten.",
            title="Sprint Planning Notes",
            source_type="notion",
            score=0.85,
        ),
        _Row(
            chunk_id=str(_CHUNK_ID_2),
            document_id=str(_DOC_ID_2),
            content_preview="Die API-Architektur wurde überarbeitet.",
            title="API Architektur",
            source_type="obsidian",
            score=0.62,
        ),
    ]


# ------------------------------------------------------------------
# tsquery builder tests
# ------------------------------------------------------------------


class TestBuildTsquery:
    """Tests for _build_tsquery static method."""

    def test_single_term(self) -> None:
        result = KeywordSearchService._build_tsquery("Sprint")
        assert result == "Sprint"

    def test_multiple_terms_joined_with_and(self) -> None:
        result = KeywordSearchService._build_tsquery("Sprint Planning")
        assert result == "Sprint & Planning"

    def test_special_chars_stripped(self) -> None:
        result = KeywordSearchService._build_tsquery("SELECT * FROM; DROP TABLE")
        assert ";" not in result
        assert "*" not in result

    def test_german_umlauts_preserved(self) -> None:
        result = KeywordSearchService._build_tsquery("Überprüfung Ärzte Öffnungszeiten")
        assert "Überprüfung" in result
        assert "Ärzte" in result
        assert "Öffnungszeiten" in result

    def test_empty_query_returns_empty(self) -> None:
        assert KeywordSearchService._build_tsquery("") == ""
        assert KeywordSearchService._build_tsquery("   ") == ""

    def test_only_special_chars_returns_empty(self) -> None:
        assert KeywordSearchService._build_tsquery("!@#$%") == ""

    def test_hyphens_preserved(self) -> None:
        result = KeywordSearchService._build_tsquery("Pre-Meeting Vorbereitung")
        assert "Pre-Meeting" in result


# ------------------------------------------------------------------
# Language resolution tests
# ------------------------------------------------------------------


class TestResolveLanguage:
    """Tests for language code resolution."""

    def test_de_maps_to_german(self) -> None:
        assert KeywordSearchService._resolve_language("de") == "german"

    def test_en_maps_to_english(self) -> None:
        assert KeywordSearchService._resolve_language("en") == "english"

    def test_full_name_passthrough(self) -> None:
        assert KeywordSearchService._resolve_language("german") == "german"

    def test_unknown_language_passthrough(self) -> None:
        assert KeywordSearchService._resolve_language("french") == "french"


# ------------------------------------------------------------------
# Search execution tests
# ------------------------------------------------------------------


class TestKeywordSearch:
    """Tests for the keyword search service."""

    @pytest.mark.asyncio
    async def test_basic_search_returns_results(self) -> None:
        session = _mock_session(_sample_rows())
        svc = KeywordSearchService(session)

        results = await svc.search("Sprint Planning", _USER_ID)

        assert len(results) == 2
        assert results[0].chunk_id == _CHUNK_ID_1
        assert results[0].score == 0.85
        assert results[0].title == "Sprint Planning Notes"
        assert results[1].chunk_id == _CHUNK_ID_2

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self) -> None:
        session = _mock_session()
        svc = KeywordSearchService(session)

        results = await svc.search("", _USER_ID)
        assert results == []
        session.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty(self) -> None:
        session = _mock_session()
        svc = KeywordSearchService(session)

        results = await svc.search("   ", _USER_ID)
        assert results == []

    @pytest.mark.asyncio
    async def test_user_id_passed_in_query(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("test", _USER_ID)

        session.execute.assert_awaited_once()
        call_args = session.execute.call_args
        params = call_args[0][1]
        assert params["user_id"] == str(_USER_ID)

    @pytest.mark.asyncio
    async def test_language_passed_in_query(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("test", _USER_ID, language="en")

        params = session.execute.call_args[0][1]
        assert params["lang"] == "english"

    @pytest.mark.asyncio
    async def test_default_language_is_german(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("test", _USER_ID)

        params = session.execute.call_args[0][1]
        assert params["lang"] == "german"

    @pytest.mark.asyncio
    async def test_top_k_default(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("test", _USER_ID)

        params = session.execute.call_args[0][1]
        assert params["top_k"] == 10

    @pytest.mark.asyncio
    async def test_top_k_custom(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("test", _USER_ID, top_k=25)

        params = session.execute.call_args[0][1]
        assert params["top_k"] == 25

    @pytest.mark.asyncio
    async def test_top_k_capped_at_max(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session, config=KeywordSearchConfig(max_top_k=20))

        await svc.search("test", _USER_ID, top_k=100)

        params = session.execute.call_args[0][1]
        assert params["top_k"] == 20

    @pytest.mark.asyncio
    async def test_result_types(self) -> None:
        session = _mock_session(_sample_rows())
        svc = KeywordSearchService(session)

        results = await svc.search("Sprint", _USER_ID)

        for r in results:
            assert isinstance(r, KeywordSearchResult)
            assert isinstance(r.chunk_id, uuid.UUID)
            assert isinstance(r.document_id, uuid.UUID)
            assert isinstance(r.score, float)

    @pytest.mark.asyncio
    async def test_null_title_becomes_none(self) -> None:
        rows = [
            _Row(
                chunk_id=str(_CHUNK_ID_1),
                document_id=str(_DOC_ID_1),
                content_preview="Some content",
                title="",
                source_type="",
                score=0.5,
            ),
        ]
        session = _mock_session(rows)
        svc = KeywordSearchService(session)

        results = await svc.search("content", _USER_ID)
        assert results[0].title is None
        assert results[0].source_type is None

    @pytest.mark.asyncio
    async def test_sql_contains_user_id_filter(self) -> None:
        """Verify the SQL text includes user_id filtering."""
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("test", _USER_ID)

        sql_text = str(session.execute.call_args[0][0].text)
        assert "user_id" in sql_text
        assert "ts_rank_cd" in sql_text
        assert "to_tsvector" in sql_text
        assert "to_tsquery" in sql_text

    @pytest.mark.asyncio
    async def test_tsquery_built_from_query(self) -> None:
        session = _mock_session([])
        svc = KeywordSearchService(session)

        await svc.search("Sprint Planning Meeting", _USER_ID)

        params = session.execute.call_args[0][1]
        assert params["query"] == "Sprint & Planning & Meeting"
