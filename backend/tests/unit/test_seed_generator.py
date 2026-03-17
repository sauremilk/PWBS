"""Tests for the Seed-Data-Generator CLI (TASK-198).

Verifies:
- Document generation produces correct count across 4 connectors
- Deterministic UUIDs for idempotency
- CLI argument parsing
- --clean flag behavior
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from pwbs.cli.seed import (
    DEMO_USER_ID,
    _doc_id,
    generate_documents,
)


class TestDocumentGeneration:
    """Verify the document generation logic."""

    def test_generates_requested_count(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 50)
        assert len(docs) == 50

    def test_generates_fewer_if_requested(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 10)
        assert len(docs) == 10

    def test_generates_single_document(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 1)
        assert len(docs) == 1

    def test_covers_all_four_connectors(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 50)
        source_types = {d["source_type"] for d in docs}
        assert "google_calendar" in source_types
        assert "notion" in source_types
        assert "zoom" in source_types
        assert "obsidian" in source_types

    def test_all_documents_have_required_fields(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 20)
        required_fields = {
            "id",
            "user_id",
            "source_type",
            "source_id",
            "title",
            "content",
            "content_hash",
            "language",
            "created_at",
            "updated_at",
            "processing_status",
        }
        for doc in docs:
            missing = required_fields - set(doc.keys())
            assert not missing, f"Document {doc['title']} missing fields: {missing}"

    def test_all_documents_belong_to_user(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 20)
        for doc in docs:
            assert doc["user_id"] == DEMO_USER_ID

    def test_source_ids_are_unique(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 50)
        source_ids = [d["source_id"] for d in docs]
        assert len(source_ids) == len(set(source_ids))

    def test_content_hashes_are_sha256(self) -> None:
        docs = generate_documents(DEMO_USER_ID, 10)
        for doc in docs:
            assert len(doc["content_hash"]) == 64
            # Must be valid hex
            int(doc["content_hash"], 16)


class TestIdempotency:
    """Verify deterministic UUID generation for idempotent seeding."""

    def test_doc_id_is_deterministic(self) -> None:
        id1 = _doc_id("notion", 5)
        id2 = _doc_id("notion", 5)
        assert id1 == id2

    def test_doc_id_differs_by_source(self) -> None:
        id_notion = _doc_id("notion", 0)
        id_zoom = _doc_id("zoom", 0)
        assert id_notion != id_zoom

    def test_doc_id_differs_by_index(self) -> None:
        id1 = _doc_id("notion", 0)
        id2 = _doc_id("notion", 1)
        assert id1 != id2

    def test_generate_documents_same_ids_on_repeat(self) -> None:
        docs1 = generate_documents(DEMO_USER_ID, 20)
        docs2 = generate_documents(DEMO_USER_ID, 20)
        ids1 = [d["id"] for d in docs1]
        ids2 = [d["id"] for d in docs2]
        assert ids1 == ids2

    def test_demo_user_id_is_fixed_uuid(self) -> None:
        assert isinstance(DEMO_USER_ID, uuid.UUID)
        # Must be the same across imports
        assert str(DEMO_USER_ID) == "00000000-0000-4000-a000-000000000001"


class TestCLIArgumentParsing:
    """Verify the CLI entry point parses arguments correctly."""

    def test_seed_command_defaults(self) -> None:
        from pwbs.cli.__main__ import main

        with patch("pwbs.cli.seed.run_seed") as mock_seed:
            with patch("sys.argv", ["pwbs.cli", "seed"]):
                main()
            mock_seed.assert_called_once_with(
                user_email="demo@pwbs.dev",
                document_count=50,
                clean=False,
            )

    def test_seed_command_custom_args(self) -> None:
        from pwbs.cli.__main__ import main

        with patch("pwbs.cli.seed.run_seed") as mock_seed:
            with patch(
                "sys.argv", ["pwbs.cli", "seed", "--user", "test@example.com", "--documents", "25"]
            ):
                main()
            mock_seed.assert_called_once_with(
                user_email="test@example.com",
                document_count=25,
                clean=False,
            )

    def test_seed_command_clean_flag(self) -> None:
        from pwbs.cli.__main__ import main

        with patch("pwbs.cli.seed.run_seed") as mock_seed:
            with patch("sys.argv", ["pwbs.cli", "seed", "--clean"]):
                main()
            mock_seed.assert_called_once_with(
                user_email="demo@pwbs.dev",
                document_count=50,
                clean=True,
            )

    def test_no_command_exits_with_error(self) -> None:
        from pwbs.cli.__main__ import main

        with patch("sys.argv", ["pwbs.cli"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
