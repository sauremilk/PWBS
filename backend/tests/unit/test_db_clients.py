"""Tests for pwbs.db client singletons - postgres, redis, weaviate, neo4j."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Neo4j client
# ---------------------------------------------------------------------------


class TestNeo4jClient:
    def setup_method(self) -> None:
        import pwbs.db.neo4j_client as mod

        mod._driver = None
        mod._init_failed = False

    def test_returns_none_on_init_failure(self) -> None:
        with patch(
            "pwbs.db.neo4j_client.AsyncGraphDatabase.driver", side_effect=Exception("no neo4j")
        ):
            from pwbs.db.neo4j_client import get_neo4j_driver

            result = get_neo4j_driver()
            assert result is None

    def test_short_circuits_after_failure(self) -> None:
        import pwbs.db.neo4j_client as mod

        mod._init_failed = True
        from pwbs.db.neo4j_client import get_neo4j_driver

        assert get_neo4j_driver() is None

    def test_returns_driver_when_available(self) -> None:
        mock_driver = MagicMock()
        with patch("pwbs.db.neo4j_client.AsyncGraphDatabase.driver", return_value=mock_driver):
            import pwbs.db.neo4j_client as mod

            mod._driver = None
            mod._init_failed = False
            result = mod.get_neo4j_driver()
            assert result is mock_driver

    @pytest.mark.asyncio
    async def test_health_false_when_no_driver(self) -> None:
        import pwbs.db.neo4j_client as mod

        mod._driver = None
        mod._init_failed = True
        result = await mod.check_neo4j_health()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_true_when_connected(self) -> None:
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        import pwbs.db.neo4j_client as mod

        mod._driver = mock_driver
        result = await mod.check_neo4j_health()
        assert result is True

    @pytest.mark.asyncio
    async def test_close_resets_driver(self) -> None:
        mock_driver = AsyncMock()
        import pwbs.db.neo4j_client as mod

        mod._driver = mock_driver
        await mod.close_neo4j_driver()
        assert mod._driver is None
        mock_driver.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Redis client
# ---------------------------------------------------------------------------


class TestRedisClient:
    def setup_method(self) -> None:
        import pwbs.db.redis_client as mod

        mod._client = None

    def test_creates_client_on_first_call(self) -> None:
        mock_client = MagicMock()
        with patch("pwbs.db.redis_client.aioredis.from_url", return_value=mock_client):
            from pwbs.db.redis_client import get_redis_client

            result = get_redis_client()
            assert result is mock_client

    def test_returns_cached_client(self) -> None:
        import pwbs.db.redis_client as mod

        mock_client = MagicMock()
        mod._client = mock_client
        result = mod.get_redis_client()
        assert result is mock_client

    @pytest.mark.asyncio
    async def test_health_true_on_ping(self) -> None:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        import pwbs.db.redis_client as mod

        mod._client = mock_client
        assert await mod.check_redis_health() is True

    @pytest.mark.asyncio
    async def test_health_false_on_error(self) -> None:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=Exception("no redis"))
        import pwbs.db.redis_client as mod

        mod._client = mock_client
        assert await mod.check_redis_health() is False

    @pytest.mark.asyncio
    async def test_close_resets_client(self) -> None:
        mock_client = AsyncMock()
        import pwbs.db.redis_client as mod

        mod._client = mock_client
        await mod.close_redis_client()
        assert mod._client is None
        mock_client.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# Weaviate client
# ---------------------------------------------------------------------------


class TestWeaviateClient:
    def setup_method(self) -> None:
        import pwbs.db.weaviate_client as mod

        mod._client = None

    def test_creates_client_on_first_call(self) -> None:
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        with patch("pwbs.db.weaviate_client.weaviate.connect_to_local", return_value=mock_client):
            from pwbs.db.weaviate_client import get_weaviate_client

            result = get_weaviate_client()
            assert result is mock_client

    @pytest.mark.asyncio
    async def test_health_true_when_ready(self) -> None:
        mock_client = MagicMock()
        mock_client.is_ready.return_value = True
        mock_client.is_connected.return_value = True
        import pwbs.db.weaviate_client as mod

        mod._client = mock_client
        assert await mod.check_weaviate_health() is True

    @pytest.mark.asyncio
    async def test_health_false_on_error(self) -> None:
        import pwbs.db.weaviate_client as mod

        mod._client = None
        with patch(
            "pwbs.db.weaviate_client.weaviate.connect_to_local",
            side_effect=Exception("no weaviate"),
        ):
            assert await mod.check_weaviate_health() is False

    @pytest.mark.asyncio
    async def test_close_resets_client(self) -> None:
        mock_client = MagicMock()
        import pwbs.db.weaviate_client as mod

        mod._client = mock_client
        await mod.close_weaviate_client()
        assert mod._client is None
        mock_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------


class TestPostgresClient:
    def setup_method(self) -> None:
        import pwbs.db.postgres as mod

        mod._engine = None
        mod._session_factory = None

    def test_creates_engine_on_first_call(self) -> None:
        mock_engine = MagicMock()
        with patch("pwbs.db.postgres.create_async_engine", return_value=mock_engine):
            from pwbs.db.postgres import get_engine

            result = get_engine()
            assert result is mock_engine

    def test_returns_cached_engine(self) -> None:
        import pwbs.db.postgres as mod

        mock_engine = MagicMock()
        mod._engine = mock_engine
        result = mod.get_engine()
        assert result is mock_engine

    @pytest.mark.asyncio
    async def test_dispose_resets_engine(self) -> None:
        mock_engine = AsyncMock()
        import pwbs.db.postgres as mod

        mod._engine = mock_engine
        mod._session_factory = MagicMock()
        await mod.dispose_engine()
        assert mod._engine is None
        assert mod._session_factory is None
        mock_engine.dispose.assert_awaited_once()
