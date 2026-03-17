"""Performance regression benchmarks (TASK-170).

pytest-benchmark based tests measuring:
  - CRUD API response times (document/entity queries)
  - Data aggregation performance (data-report endpoint pattern)
  - Search query patterns (keyword/filter queries)

These tests require Docker (testcontainers) and are run in CI
via the perf-regression workflow.

Markers:
  - @pytest.mark.perf: Performance test marker (for selective runs)
  - Tests are skipped if testcontainers/Docker is unavailable
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [pytest.mark.perf]


# ---------------------------------------------------------------------------
# Document Query Benchmarks
# ---------------------------------------------------------------------------


class TestDocumentQueryPerformance:
    """Benchmark document query patterns against synthetic data."""

    @pytest.mark.asyncio
    async def test_list_documents_by_user(
        self,
        perf_session: Any,
        perf_synthetic_data: dict[str, Any],
        benchmark: Any,
    ) -> None:
        """Benchmark: List all documents for a user (paginated)."""
        from sqlalchemy import text

        user_id = perf_synthetic_data["user_id"]

        async def query() -> list[Any]:
            result = await perf_session.execute(
                text(
                    "SELECT id, source_type, title, processing_status "
                    "FROM documents WHERE user_id = :uid "
                    "ORDER BY created_at DESC LIMIT 50"
                ),
                {"uid": user_id},
            )
            return result.fetchall()

        # pytest-benchmark doesn't support async natively;
        # use sync wrapper via event loop
        import asyncio

        result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(query()))
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_count_documents_by_source(
        self,
        perf_session: Any,
        perf_synthetic_data: dict[str, Any],
        benchmark: Any,
    ) -> None:
        """Benchmark: Aggregate document counts per source_type."""
        from sqlalchemy import text

        user_id = perf_synthetic_data["user_id"]

        async def query() -> list[Any]:
            result = await perf_session.execute(
                text(
                    "SELECT source_type, COUNT(*) as cnt "
                    "FROM documents WHERE user_id = :uid "
                    "GROUP BY source_type"
                ),
                {"uid": user_id},
            )
            return result.fetchall()

        import asyncio

        result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(query()))
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Chunk Query Benchmarks
# ---------------------------------------------------------------------------


class TestChunkQueryPerformance:
    """Benchmark chunk retrieval patterns."""

    @pytest.mark.asyncio
    async def test_chunks_for_document(
        self,
        perf_session: Any,
        perf_synthetic_data: dict[str, Any],
        benchmark: Any,
    ) -> None:
        """Benchmark: Retrieve all chunks for a single document."""
        from sqlalchemy import text

        user_id = perf_synthetic_data["user_id"]

        # Get first document ID
        result = await perf_session.execute(
            text("SELECT id FROM documents WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        )
        doc_id = result.scalar()
        assert doc_id is not None

        async def query() -> list[Any]:
            result = await perf_session.execute(
                text(
                    "SELECT id, chunk_index, token_count, content_preview "
                    "FROM chunks WHERE document_id = :did AND user_id = :uid "
                    "ORDER BY chunk_index"
                ),
                {"did": doc_id, "uid": user_id},
            )
            return result.fetchall()

        import asyncio

        result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(query()))
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chunk_count_total(
        self,
        perf_session: Any,
        perf_synthetic_data: dict[str, Any],
        benchmark: Any,
    ) -> None:
        """Benchmark: Count total chunks for a user."""
        from sqlalchemy import text

        user_id = perf_synthetic_data["user_id"]

        async def query() -> int:
            result = await perf_session.execute(
                text("SELECT COUNT(*) FROM chunks WHERE user_id = :uid"),
                {"uid": user_id},
            )
            return result.scalar() or 0

        import asyncio

        count = benchmark(lambda: asyncio.get_event_loop().run_until_complete(query()))
        assert count == perf_synthetic_data["chunk_count"]


# ---------------------------------------------------------------------------
# Entity Query Benchmarks
# ---------------------------------------------------------------------------


class TestEntityQueryPerformance:
    """Benchmark entity retrieval and filtering."""

    @pytest.mark.asyncio
    async def test_entity_search_by_name(
        self,
        perf_session: Any,
        perf_synthetic_data: dict[str, Any],
        benchmark: Any,
    ) -> None:
        """Benchmark: Search entities by normalized name prefix."""
        from sqlalchemy import text

        user_id = perf_synthetic_data["user_id"]

        async def query() -> list[Any]:
            result = await perf_session.execute(
                text(
                    "SELECT id, entity_type, name "
                    "FROM entities WHERE user_id = :uid "
                    "AND normalized_name LIKE :pattern "
                    "ORDER BY name LIMIT 20"
                ),
                {"uid": user_id, "pattern": "entity-%"},
            )
            return result.fetchall()

        import asyncio

        result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(query()))
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Data Report Aggregation Benchmark (mirrors data-report endpoint)
# ---------------------------------------------------------------------------


class TestDataReportPerformance:
    """Benchmark the full data-report aggregation query pattern."""

    @pytest.mark.asyncio
    async def test_full_data_report_aggregation(
        self,
        perf_session: Any,
        perf_synthetic_data: dict[str, Any],
        benchmark: Any,
    ) -> None:
        """Benchmark: Full data-report query pattern (3 aggregation queries)."""
        from sqlalchemy import text

        user_id = perf_synthetic_data["user_id"]

        async def query() -> dict[str, Any]:
            # Query 1: Documents by source
            doc_result = await perf_session.execute(
                text(
                    "SELECT source_type, COUNT(*) as cnt, "
                    "MIN(created_at) as oldest, MAX(created_at) as newest "
                    "FROM documents WHERE user_id = :uid "
                    "GROUP BY source_type"
                ),
                {"uid": user_id},
            )
            sources = doc_result.fetchall()

            # Query 2: Connections
            conn_result = await perf_session.execute(
                text("SELECT source_type, status, watermark FROM connections WHERE user_id = :uid"),
                {"uid": user_id},
            )
            connections = conn_result.fetchall()

            # Query 3: LLM usage
            llm_result = await perf_session.execute(
                text(
                    "SELECT provider, model, "
                    "SUM(input_tokens) as total_in, "
                    "SUM(output_tokens) as total_out, "
                    "COUNT(*) as call_count "
                    "FROM llm_audit_log WHERE owner_id = :uid "
                    "GROUP BY provider, model"
                ),
                {"uid": user_id},
            )
            llm_usage = llm_result.fetchall()

            return {
                "sources": sources,
                "connections": connections,
                "llm_usage": llm_usage,
            }

        import asyncio

        result = benchmark(lambda: asyncio.get_event_loop().run_until_complete(query()))
        assert "sources" in result
