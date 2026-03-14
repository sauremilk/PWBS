"""Tests for DSGVO Export Service (TASK-104)."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.dsgvo.export_service import (
    _build_zip,
    _collect_audit_log,
    _collect_briefings,
    _collect_chunks,
    _collect_documents,
    _collect_entities,
    check_running_export,
    create_export_job,
    get_export,
    is_export_expired,
    run_export,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()


def _mock_scalars(rows: list) -> AsyncMock:
    """Build a mock db.execute(...) that returns scalars().all() -> rows."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db = AsyncMock()
    db.execute.return_value = result
    return db


def _mock_scalar_one_or_none(value) -> AsyncMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    db = AsyncMock()
    db.execute.return_value = result
    return db


# ---------------------------------------------------------------------------
# check_running_export
# ---------------------------------------------------------------------------


class TestCheckRunningExport:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_running(self) -> None:
        db = _mock_scalar_one_or_none(None)
        result = await check_running_export(USER_ID, db)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_export_when_running(self) -> None:
        running = MagicMock()
        running.status = "processing"
        db = _mock_scalar_one_or_none(running)
        result = await check_running_export(USER_ID, db)
        assert result is running


# ---------------------------------------------------------------------------
# create_export_job
# ---------------------------------------------------------------------------


class TestCreateExportJob:
    @pytest.mark.asyncio
    async def test_creates_and_returns_export(self) -> None:
        db = AsyncMock()
        export = await create_export_job(USER_ID, db)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_export
# ---------------------------------------------------------------------------


class TestGetExport:
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self) -> None:
        db = _mock_scalar_one_or_none(None)
        result = await get_export(uuid.uuid4(), USER_ID, db)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_export_for_owner(self) -> None:
        export = MagicMock()
        db = _mock_scalar_one_or_none(export)
        result = await get_export(uuid.uuid4(), USER_ID, db)
        assert result is export


# ---------------------------------------------------------------------------
# is_export_expired
# ---------------------------------------------------------------------------


class TestIsExportExpired:
    def test_not_expired_when_no_expires_at(self) -> None:
        export = MagicMock()
        export.expires_at = None
        assert is_export_expired(export) is False

    def test_not_expired_when_future(self) -> None:
        export = MagicMock()
        export.expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=12)
        assert is_export_expired(export) is False

    def test_expired_when_past(self) -> None:
        export = MagicMock()
        export.expires_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        assert is_export_expired(export) is True


# ---------------------------------------------------------------------------
# _build_zip
# ---------------------------------------------------------------------------


class TestBuildZip:
    def test_creates_valid_zip_with_all_sections(self) -> None:
        docs = [
            {
                "id": "d1",
                "source_type": "notion",
                "source_id": "s1",
                "title": "Test",
                "language": "de",
                "chunk_count": 1,
                "processing_status": "done",
                "created_at": None,
                "updated_at": None,
            }
        ]
        chunks = [
            {
                "id": "c1",
                "document_id": "d1",
                "chunk_index": 0,
                "token_count": 50,
                "content_preview": "Hello world",
            }
        ]
        entities = [
            {
                "id": "e1",
                "entity_type": "Person",
                "name": "Alice",
                "normalized_name": "alice",
                "first_seen": None,
                "last_seen": None,
            }
        ]
        briefings = [
            {
                "id": "b1",
                "briefing_type": "morning",
                "title": "Morning",
                "content": "Good morning",
                "generated_at": None,
            }
        ]
        audit = [
            {
                "id": 1,
                "action": "POST",
                "resource_type": "doc",
                "resource_id": None,
                "created_at": None,
            }
        ]

        zip_bytes = _build_zip(
            documents=docs,
            chunks=chunks,
            entities=entities,
            briefings=briefings,
            audit_entries=audit,
        )

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "documents.json" in names
            assert "entities.json" in names
            assert "audit_log.json" in names
            assert any(n.startswith("chunks/") for n in names)
            assert any(n.startswith("briefings/") for n in names)

            # Verify JSON validity
            parsed_docs = json.loads(zf.read("documents.json"))
            assert len(parsed_docs) == 1
            assert parsed_docs[0]["id"] == "d1"

    def test_empty_data_produces_valid_zip(self) -> None:
        zip_bytes = _build_zip(
            documents=[],
            chunks=[],
            entities=[],
            briefings=[],
            audit_entries=[],
        )
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "documents.json" in zf.namelist()
            parsed = json.loads(zf.read("documents.json"))
            assert parsed == []


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------


class TestCollectors:
    @pytest.mark.asyncio
    async def test_collect_documents(self) -> None:
        doc = MagicMock()
        doc.id = uuid.uuid4()
        doc.source_type = "notion"
        doc.source_id = "s1"
        doc.title = "Test"
        doc.language = "de"
        doc.chunk_count = 0
        doc.processing_status = "done"
        doc.created_at = datetime.now(tz=timezone.utc)
        doc.updated_at = datetime.now(tz=timezone.utc)

        db = _mock_scalars([doc])
        result = await _collect_documents(USER_ID, db)
        assert len(result) == 1
        assert result[0]["source_type"] == "notion"

    @pytest.mark.asyncio
    async def test_collect_chunks(self) -> None:
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.document_id = uuid.uuid4()
        chunk.chunk_index = 0
        chunk.token_count = 64
        chunk.content_preview = "Test chunk"

        db = _mock_scalars([chunk])
        result = await _collect_chunks(USER_ID, db)
        assert len(result) == 1
        assert result[0]["content_preview"] == "Test chunk"

    @pytest.mark.asyncio
    async def test_collect_entities(self) -> None:
        entity = MagicMock()
        entity.id = uuid.uuid4()
        entity.entity_type = "Person"
        entity.name = "Alice"
        entity.normalized_name = "alice"
        entity.first_seen = None
        entity.last_seen = None

        db = _mock_scalars([entity])
        result = await _collect_entities(USER_ID, db)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_collect_briefings(self) -> None:
        briefing = MagicMock()
        briefing.id = uuid.uuid4()
        briefing.briefing_type = "morning"
        briefing.title = "Morning"
        briefing.content = "Good morning"
        briefing.generated_at = datetime.now(tz=timezone.utc)

        db = _mock_scalars([briefing])
        result = await _collect_briefings(USER_ID, db)
        assert len(result) == 1
        assert result[0]["briefing_type"] == "morning"

    @pytest.mark.asyncio
    async def test_collect_audit_log_no_pii(self) -> None:
        entry = MagicMock()
        entry.id = 1
        entry.action = "POST"
        entry.resource_type = "document"
        entry.resource_id = uuid.uuid4()
        entry.created_at = datetime.now(tz=timezone.utc)

        db = _mock_scalars([entry])
        result = await _collect_audit_log(USER_ID, db)
        assert len(result) == 1
        # Ensure no PII fields
        assert "email" not in result[0]
        assert "ip_address" not in result[0]
        assert "metadata" not in result[0]


# ---------------------------------------------------------------------------
# run_export (background task)
# ---------------------------------------------------------------------------


def _mock_session_factory(mock_session: AsyncMock) -> MagicMock:
    """Build a mock async_sessionmaker that yields *mock_session*."""
    ctx = AsyncMock()
    ctx.__aenter__.return_value = mock_session
    ctx.__aexit__.return_value = None
    factory = MagicMock(return_value=ctx)
    return factory


class TestRunExport:
    @pytest.mark.asyncio
    async def test_successful_export_writes_zip(self, tmp_path: Any) -> None:
        export_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_session = AsyncMock()
        # Collectors return empty lists for simplicity
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        # For the final SELECT to get the export record
        export_record = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one.return_value = export_record

        mock_session.execute.side_effect = [
            mock_result,  # documents
            mock_result,  # chunks
            mock_result,  # entities
            mock_result,  # briefings
            mock_result,  # audit
            scalar_result,  # SELECT export record
        ]

        factory = _mock_session_factory(mock_session)
        mock_engine = AsyncMock()

        with (
            patch("pwbs.dsgvo.export_service.create_async_engine", return_value=mock_engine),
            patch("pwbs.dsgvo.export_service.async_sessionmaker", return_value=factory),
        ):
            await run_export(export_id, user_id, "postgresql+asyncpg://test", str(tmp_path))

        assert export_record.status == "completed"
        assert export_record.file_path is not None
        assert export_record.completed_at is not None
        assert export_record.expires_at is not None
        mock_session.commit.assert_awaited()
        mock_engine.dispose.assert_awaited()

    @pytest.mark.asyncio
    async def test_failed_export_sets_status_failed(self, tmp_path: Any) -> None:
        export_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # First session raises, second session for error handling
        fail_session = AsyncMock()
        fail_session.execute.side_effect = RuntimeError("DB broke")

        error_session = AsyncMock()
        error_record = MagicMock()
        error_result = MagicMock()
        error_result.scalar_one_or_none.return_value = error_record

        error_session.execute.return_value = error_result

        call_count = 0
        call_contexts = []
        for s in [fail_session, error_session]:
            ctx = AsyncMock()
            ctx.__aenter__.return_value = s
            ctx.__aexit__.return_value = None
            call_contexts.append(ctx)

        factory = MagicMock(side_effect=call_contexts)
        mock_engine = AsyncMock()

        with (
            patch("pwbs.dsgvo.export_service.create_async_engine", return_value=mock_engine),
            patch("pwbs.dsgvo.export_service.async_sessionmaker", return_value=factory),
        ):
            await run_export(export_id, user_id, "postgresql+asyncpg://test", str(tmp_path))

        assert error_record.status == "failed"
        assert error_record.error_message == "Internal export error"
        mock_engine.dispose.assert_awaited()
