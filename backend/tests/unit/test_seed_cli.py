"""Unit tests for TASK-198: Seed-Data-Generator CLI."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.cli.seed import (
    DEMO_USER_ID,
    _content_hash,
    _doc_id,
    generate_documents,
    run_seed,
)


class TestDemoConstants:
    def test_demo_user_id_is_fixed_uuid(self) -> None:
        assert isinstance(DEMO_USER_ID, uuid.UUID)
        assert str(DEMO_USER_ID) == "00000000-0000-4000-a000-000000000001"

    def test_content_hash_deterministic(self) -> None:
        h1 = _content_hash("hello")
        h2 = _content_hash("hello")
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex


class TestBuildDocuments:
    def test_builds_exact_count(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 50)
        assert len(docs) == 50

    def test_all_four_connectors_present(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 50)
        sources = {d["source_type"] for d in docs}
        assert sources == {"google_calendar", "notion", "obsidian", "zoom"}

    def test_documents_have_required_fields(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 4)
        required = {
            "id",
            "user_id",
            "source_type",
            "source_id",
            "title",
            "content",
            "content_hash",
            "language",
            "processing_status",
            "created_at",
            "updated_at",
        }
        for doc in docs:
            assert required.issubset(doc.keys()), f"Missing: {required - doc.keys()}"

    def test_documents_have_stable_ids(self) -> None:
        """Idempotency: same input produces same UUIDs."""
        docs_a = generate_documents(DEMO_USER_ID, 10)
        docs_b = generate_documents(DEMO_USER_ID, 10)
        ids_a = [d["id"] for d in docs_a]
        ids_b = [d["id"] for d in docs_b]
        assert ids_a == ids_b

    def test_all_documents_belong_to_owner(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 20)
        for d in docs:
            assert d["user_id"] == DEMO_USER_ID

    def test_source_ids_are_prefixed_seed(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 8)
        for d in docs:
            assert d["source_id"].startswith("seed-")

    def test_small_count_works(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 1)
        assert len(docs) == 1

    def test_large_count_cycles_templates(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 100)
        assert len(docs) == 100
        # Higher cycle docs have modified titles
        titles = [d["title"] for d in docs]
        assert any("#" in t for t in titles), "Expected cycling marker in titles"

    def test_even_distribution_across_connectors(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 48)  # evenly divisible by 4
        counts = {}
        for d in docs:
            counts[d["source_type"]] = counts.get(d["source_type"], 0) + 1
        assert counts["google_calendar"] == 12
        assert counts["notion"] == 12
        assert counts["obsidian"] == 12
        assert counts["zoom"] == 12

    def test_language_is_german(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 4)
        for d in docs:
            assert d["language"] == "de"

    def test_doc_id_deterministic(self) -> None:
        assert _doc_id("notion", 5) == _doc_id("notion", 5)

    def test_doc_id_differs_by_source(self) -> None:
        assert _doc_id("notion", 0) != _doc_id("zoom", 0)


class TestRunSeedEntryPoint:
    @patch("pwbs.core.config.get_settings")
    def test_exits_on_missing_database_url(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.database_url = ""
        with pytest.raises(SystemExit):
            run_seed(clean=False)

    @patch("pwbs.core.config.get_settings")
    @patch("pwbs.cli.seed.asyncio")
    def test_clean_flag_calls_clean_async(
        self, mock_asyncio: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value.database_url = "postgresql+asyncpg://test/db"
        run_seed(clean=True)
        # Should call asyncio.run with _clean_async coroutine
        mock_asyncio.run.assert_called_once()

    @patch("pwbs.core.config.get_settings")
    @patch("pwbs.cli.seed.asyncio")
    def test_seed_calls_seed_async(self, mock_asyncio: MagicMock, mock_settings: MagicMock) -> None:
        mock_settings.return_value.database_url = "postgresql+asyncpg://test/db"
        run_seed(user_email="test@test.dev", document_count=10, clean=False)
        mock_asyncio.run.assert_called_once()


class TestCLIArgparse:
    def test_main_seed_subcommand(self) -> None:
        """Verify __main__.py parses seed args correctly."""
        import sys

        from pwbs.cli.__main__ import main

        with patch.object(sys, "argv", ["pwbs.cli", "seed", "--documents", "10", "--clean"]):
            with patch("pwbs.cli.seed.run_seed") as mock_run:
                main()
                mock_run.assert_called_once_with(
                    user_email="demo@pwbs.dev",
                    document_count=10,
                    clean=True,
                )
