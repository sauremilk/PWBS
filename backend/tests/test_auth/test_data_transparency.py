"""Tests for Data Transparency endpoints (TASK-172).

Covers: GET /data-report, GET /llm-usage, LlmAuditLog model, export integration.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Response as FastAPIResponse

from pwbs.models.llm_audit_log import LlmAuditLog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID = USER_ID) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    return u


def _make_llm_log(
    *,
    owner_id: uuid.UUID = USER_ID,
    provider: str = "anthropic",
    model: str = "claude-3-5-sonnet",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    purpose: str = "briefing",
) -> MagicMock:
    log = MagicMock()
    log.id = uuid.uuid4()
    log.owner_id = owner_id
    log.provider = provider
    log.model = model
    log.input_tokens = input_tokens
    log.output_tokens = output_tokens
    log.purpose = purpose
    log.created_at = datetime(2025, 3, 1, 10, 0, tzinfo=UTC)
    return log


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestLlmAuditLogModel:
    """Verify LlmAuditLog ORM model structure."""

    def test_tablename(self) -> None:
        assert LlmAuditLog.__tablename__ == "llm_audit_log"

    def test_has_required_columns(self) -> None:
        cols = {c.name for c in LlmAuditLog.__table__.columns}
        expected = {
            "id",
            "owner_id",
            "provider",
            "model",
            "input_tokens",
            "output_tokens",
            "purpose",
            "created_at",
        }
        assert expected <= cols

    def test_owner_id_indexed(self) -> None:
        col = LlmAuditLog.__table__.columns["owner_id"]
        assert col.index or any(
            idx.name == "ix_llm_audit_log_owner_id" for idx in LlmAuditLog.__table__.indexes
        )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestDataReportSchemas:
    """Validate response schemas for data-report endpoint."""

    def test_source_stats_schema(self) -> None:
        from pwbs.api.v1.routes.user import SourceStats

        s = SourceStats(
            source_type="google_calendar",
            document_count=42,
            oldest_document=datetime(2024, 1, 1, tzinfo=UTC),
            newest_document=datetime(2025, 3, 1, tzinfo=UTC),
        )
        assert s.document_count == 42
        assert s.source_type == "google_calendar"

    def test_source_stats_optional_dates(self) -> None:
        from pwbs.api.v1.routes.user import SourceStats

        s = SourceStats(source_type="notion", document_count=0)
        assert s.oldest_document is None
        assert s.newest_document is None

    def test_connection_info_schema(self) -> None:
        from pwbs.api.v1.routes.user import ConnectionInfo

        c = ConnectionInfo(
            source_type="slack",
            status="active",
            last_sync=datetime(2025, 3, 1, 12, 0, tzinfo=UTC),
        )
        assert c.status == "active"

    def test_llm_provider_usage_schema(self) -> None:
        from pwbs.api.v1.routes.user import LlmProviderUsage

        u = LlmProviderUsage(
            provider="anthropic",
            model="claude-3-5-sonnet",
            total_input_tokens=50000,
            total_output_tokens=25000,
            call_count=100,
        )
        assert u.call_count == 100

    def test_data_report_response_schema(self) -> None:
        from pwbs.api.v1.routes.user import DataReportResponse

        r = DataReportResponse(
            total_documents=10,
            sources=[],
            connections=[],
            llm_provider_usage=[],
        )
        assert r.total_documents == 10

    def test_llm_usage_entry_schema(self) -> None:
        from pwbs.api.v1.routes.user import LlmUsageEntry

        entry = LlmUsageEntry(
            id=uuid.uuid4(),
            provider="openai",
            model="gpt-4",
            input_tokens=500,
            output_tokens=200,
            purpose="search",
            created_at=datetime(2025, 3, 1, tzinfo=UTC),
        )
        assert entry.provider == "openai"

    def test_llm_usage_response_schema(self) -> None:
        from pwbs.api.v1.routes.user import LlmUsageResponse

        r = LlmUsageResponse(entries=[], total=0)
        assert r.total == 0


# ---------------------------------------------------------------------------
# data-report endpoint tests
# ---------------------------------------------------------------------------


class TestDataReportEndpoint:
    """Tests for GET /api/v1/user/data-report."""

    @pytest.mark.asyncio
    async def test_returns_empty_report(self) -> None:
        from pwbs.api.v1.routes.user import get_data_report

        db = AsyncMock()

        # Documents query: no rows
        doc_result = MagicMock()
        doc_result.all.return_value = []

        # Connections query: no rows
        conn_result = MagicMock()
        conn_scalars = MagicMock()
        conn_scalars.all.return_value = []
        conn_result.scalars.return_value = conn_scalars

        # LLM query: no rows
        llm_result = MagicMock()
        llm_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[doc_result, conn_result, llm_result])

        user = _make_user()
        resp = await get_data_report(response=FastAPIResponse(), user=user, db=db)

        assert resp.total_documents == 0
        assert resp.sources == []
        assert resp.connections == []
        assert resp.llm_provider_usage == []

    @pytest.mark.asyncio
    async def test_aggregates_documents_by_source(self) -> None:
        from pwbs.api.v1.routes.user import get_data_report

        db = AsyncMock()

        # Documents: 2 source types
        doc_row1 = MagicMock(
            source_type="google_calendar",
            doc_count=10,
            oldest=datetime(2024, 1, 1, tzinfo=UTC),
            newest=datetime(2025, 1, 1, tzinfo=UTC),
        )
        doc_row2 = MagicMock(
            source_type="notion",
            doc_count=5,
            oldest=datetime(2024, 6, 1, tzinfo=UTC),
            newest=datetime(2025, 3, 1, tzinfo=UTC),
        )
        doc_result = MagicMock()
        doc_result.all.return_value = [doc_row1, doc_row2]

        conn_result = MagicMock()
        conn_scalars = MagicMock()
        conn_scalars.all.return_value = []
        conn_result.scalars.return_value = conn_scalars

        llm_result = MagicMock()
        llm_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[doc_result, conn_result, llm_result])

        user = _make_user()
        resp = await get_data_report(response=FastAPIResponse(), user=user, db=db)

        assert resp.total_documents == 15
        assert len(resp.sources) == 2
        assert resp.sources[0].source_type == "google_calendar"
        assert resp.sources[0].document_count == 10
        assert resp.sources[1].source_type == "notion"

    @pytest.mark.asyncio
    async def test_includes_connections(self) -> None:
        from pwbs.api.v1.routes.user import get_data_report

        db = AsyncMock()

        doc_result = MagicMock()
        doc_result.all.return_value = []

        conn_obj = MagicMock()
        conn_obj.source_type = "slack"
        conn_obj.status = "active"
        conn_obj.watermark = datetime(2025, 3, 1, tzinfo=UTC)

        conn_result = MagicMock()
        conn_scalars = MagicMock()
        conn_scalars.all.return_value = [conn_obj]
        conn_result.scalars.return_value = conn_scalars

        llm_result = MagicMock()
        llm_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[doc_result, conn_result, llm_result])

        user = _make_user()
        resp = await get_data_report(response=FastAPIResponse(), user=user, db=db)

        assert len(resp.connections) == 1
        assert resp.connections[0].source_type == "slack"
        assert resp.connections[0].status == "active"

    @pytest.mark.asyncio
    async def test_includes_llm_usage(self) -> None:
        from pwbs.api.v1.routes.user import get_data_report

        db = AsyncMock()

        doc_result = MagicMock()
        doc_result.all.return_value = []

        conn_result = MagicMock()
        conn_scalars = MagicMock()
        conn_scalars.all.return_value = []
        conn_result.scalars.return_value = conn_scalars

        llm_row = MagicMock(
            provider="anthropic",
            model="claude-3-5-sonnet",
            total_in=50000,
            total_out=25000,
            call_count=100,
        )
        llm_result = MagicMock()
        llm_result.all.return_value = [llm_row]

        db.execute = AsyncMock(side_effect=[doc_result, conn_result, llm_result])

        user = _make_user()
        resp = await get_data_report(response=FastAPIResponse(), user=user, db=db)

        assert len(resp.llm_provider_usage) == 1
        assert resp.llm_provider_usage[0].provider == "anthropic"
        assert resp.llm_provider_usage[0].total_input_tokens == 50000
        assert resp.llm_provider_usage[0].call_count == 100


# ---------------------------------------------------------------------------
# llm-usage endpoint tests
# ---------------------------------------------------------------------------


class TestLlmUsageEndpoint:
    """Tests for GET /api/v1/user/llm-usage."""

    @pytest.mark.asyncio
    async def test_returns_empty_usage(self) -> None:
        from pwbs.api.v1.routes.user import get_llm_usage

        db = AsyncMock()

        # count query
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # rows query
        rows_result = MagicMock()
        rows_scalars = MagicMock()
        rows_scalars.all.return_value = []
        rows_result.scalars.return_value = rows_scalars

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        user = _make_user()
        resp = await get_llm_usage(response=FastAPIResponse(), user=user, db=db)

        assert resp.total == 0
        assert resp.entries == []

    @pytest.mark.asyncio
    async def test_returns_entries_with_pagination(self) -> None:
        from pwbs.api.v1.routes.user import get_llm_usage

        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 5

        log1 = _make_llm_log(provider="anthropic", model="claude-3-5-sonnet")
        log2 = _make_llm_log(provider="openai", model="gpt-4")

        rows_result = MagicMock()
        rows_scalars = MagicMock()
        rows_scalars.all.return_value = [log1, log2]
        rows_result.scalars.return_value = rows_scalars

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        user = _make_user()
        resp = await get_llm_usage(response=FastAPIResponse(), user=user, db=db, limit=2, offset=0)

        assert resp.total == 5
        assert len(resp.entries) == 2
        assert resp.entries[0].provider == "anthropic"
        assert resp.entries[1].provider == "openai"

    @pytest.mark.asyncio
    async def test_limit_clamped_to_max(self) -> None:
        from pwbs.api.v1.routes.user import _LLM_USAGE_MAX, get_llm_usage

        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        rows_result = MagicMock()
        rows_scalars = MagicMock()
        rows_scalars.all.return_value = []
        rows_result.scalars.return_value = rows_scalars

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        user = _make_user()
        # Request absurdly high limit
        resp = await get_llm_usage(response=FastAPIResponse(), user=user, db=db, limit=9999)

        assert resp.total == 0
        assert _LLM_USAGE_MAX == 200

    @pytest.mark.asyncio
    async def test_negative_offset_clamped_to_zero(self) -> None:
        from pwbs.api.v1.routes.user import get_llm_usage

        db = AsyncMock()

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        rows_result = MagicMock()
        rows_scalars = MagicMock()
        rows_scalars.all.return_value = []
        rows_result.scalars.return_value = rows_scalars

        db.execute = AsyncMock(side_effect=[count_result, rows_result])

        user = _make_user()
        resp = await get_llm_usage(response=FastAPIResponse(), user=user, db=db, offset=-10)

        assert resp.total == 0


# ---------------------------------------------------------------------------
# Export integration tests
# ---------------------------------------------------------------------------


class TestExportIntegration:
    """Verify llm_audit_log is included in DSGVO export ZIP."""

    def test_build_zip_includes_llm_usage(self) -> None:
        import json
        import zipfile
        from io import BytesIO

        from pwbs.dsgvo.export_service import _build_zip

        llm_data = [
            {
                "id": str(uuid.uuid4()),
                "provider": "anthropic",
                "model": "claude-3-5-sonnet",
                "input_tokens": 1000,
                "output_tokens": 500,
                "purpose": "briefing",
                "created_at": "2025-03-01T10:00:00+00:00",
            }
        ]

        zip_bytes = _build_zip(
            documents=[],
            chunks=[],
            entities=[],
            briefings=[],
            audit_entries=[],
            llm_usage=llm_data,
        )

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            assert "llm_usage.json" in zf.namelist()
            content = json.loads(zf.read("llm_usage.json"))
            assert len(content) == 1
            assert content[0]["provider"] == "anthropic"

    def test_build_zip_empty_llm_usage(self) -> None:
        import json
        import zipfile
        from io import BytesIO

        from pwbs.dsgvo.export_service import _build_zip

        zip_bytes = _build_zip(
            documents=[],
            chunks=[],
            entities=[],
            briefings=[],
            audit_entries=[],
            llm_usage=[],
        )

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            assert "llm_usage.json" in zf.namelist()
            content = json.loads(zf.read("llm_usage.json"))
            assert content == []
