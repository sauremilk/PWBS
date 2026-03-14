"""Verify that conftest fixtures are available and correctly typed (TASK-108)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestMockUser:
    def test_has_required_attrs(self, mock_user: MagicMock) -> None:
        assert isinstance(mock_user.id, uuid.UUID)
        assert mock_user.email == "testuser@example.com"
        assert mock_user.display_name == "Test User"
        assert mock_user.deletion_scheduled_at is None

    def test_unique_per_test(
        self, mock_user: MagicMock, test_user_id: uuid.UUID
    ) -> None:
        assert mock_user.id == test_user_id


class TestMockDb:
    def test_has_session_methods(self, mock_db: AsyncMock) -> None:
        assert hasattr(mock_db, "commit")
        assert hasattr(mock_db, "flush")
        assert hasattr(mock_db, "rollback")
        assert hasattr(mock_db, "add")
        assert hasattr(mock_db, "delete")
        assert hasattr(mock_db, "execute")
        assert hasattr(mock_db, "refresh")


class TestMockRequest:
    def test_has_headers_and_client(self, mock_request: MagicMock) -> None:
        assert mock_request.headers == {}
        assert mock_request.client.host == "127.0.0.1"


class TestMockLlm:
    def test_anthropic_client(self, mock_anthropic_client: MagicMock) -> None:
        assert hasattr(mock_anthropic_client.messages, "create")

    def test_openai_client(self, mock_openai_client: MagicMock) -> None:
        assert hasattr(mock_openai_client.chat.completions, "create")


class TestMockWeaviate:
    def test_client_connected(self, mock_weaviate_client: MagicMock) -> None:
        assert mock_weaviate_client.is_connected() is True
        assert mock_weaviate_client.is_ready() is True

    def test_collection_exists(self, mock_weaviate_client: MagicMock) -> None:
        assert mock_weaviate_client.collections.exists("anything") is True


class TestMockNeo4j:
    def test_driver_has_session(self, mock_neo4j_driver: MagicMock) -> None:
        assert hasattr(mock_neo4j_driver, "session")

    def test_session_is_async(self, mock_neo4j_session: AsyncMock) -> None:
        assert hasattr(mock_neo4j_session, "run")


class TestMockRedis:
    def test_has_basic_ops(self, mock_redis_client: AsyncMock) -> None:
        assert hasattr(mock_redis_client, "ping")
        assert hasattr(mock_redis_client, "get")
        assert hasattr(mock_redis_client, "set")
        assert hasattr(mock_redis_client, "delete")


class TestFakeRedis:
    @pytest.mark.asyncio
    async def test_set_and_get(self, fake_redis: object) -> None:
        await fake_redis.set("key", "value")  # type: ignore[union-attr]
        result = await fake_redis.get("key")  # type: ignore[union-attr]
        assert result == "value"

    @pytest.mark.asyncio
    async def test_delete(self, fake_redis: object) -> None:
        await fake_redis.set("key", "value")  # type: ignore[union-attr]
        await fake_redis.delete("key")  # type: ignore[union-attr]
        result = await fake_redis.get("key")  # type: ignore[union-attr]
        assert result is None
