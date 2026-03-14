"""Tests for BaseConnector ABC (TASK-041)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncError, SyncResult
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from pwbs.schemas.document import UnifiedDocument


# ---------------------------------------------------------------------------
# Concrete test connector
# ---------------------------------------------------------------------------


class StubConnector(BaseConnector):
    """Minimal concrete implementation for testing the ABC."""

    def __init__(
        self,
        *,
        owner_id: uuid.UUID,
        connection_id: uuid.UUID,
        config: ConnectorConfig,
        documents: list[UnifiedDocument] | None = None,
        healthy: bool = True,
    ) -> None:
        super().__init__(owner_id=owner_id, connection_id=connection_id, config=config)
        self._documents = documents or []
        self._healthy = healthy

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        return SyncResult(
            documents=self._documents,
            new_cursor="cursor-after",
            has_more=False,
        )

    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        raise NotImplementedError("Not used in stub")

    async def health_check(self) -> bool:
        return self._healthy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def connection_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def config() -> ConnectorConfig:
    return ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR)


@pytest.fixture()
def connector(
    owner_id: uuid.UUID,
    connection_id: uuid.UUID,
    config: ConnectorConfig,
) -> StubConnector:
    return StubConnector(
        owner_id=owner_id,
        connection_id=connection_id,
        config=config,
    )


# ---------------------------------------------------------------------------
# ConnectorConfig tests
# ---------------------------------------------------------------------------


class TestConnectorConfig:
    def test_defaults(self) -> None:
        cfg = ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR)
        assert cfg.max_batch_size == 100
        assert cfg.timeout_seconds == 30
        assert cfg.extra == {}

    def test_custom_values(self) -> None:
        cfg = ConnectorConfig(
            source_type=SourceType.NOTION,
            max_batch_size=50,
            timeout_seconds=60,
            extra={"workspace_id": "abc"},
        )
        assert cfg.max_batch_size == 50
        assert cfg.timeout_seconds == 60
        assert cfg.extra["workspace_id"] == "abc"

    def test_batch_size_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ConnectorConfig(source_type=SourceType.ZOOM, max_batch_size=0)
        with pytest.raises(ValidationError):
            ConnectorConfig(source_type=SourceType.ZOOM, max_batch_size=501)


# ---------------------------------------------------------------------------
# SyncResult tests
# ---------------------------------------------------------------------------


class TestSyncResult:
    def test_empty_result(self) -> None:
        result = SyncResult()
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.total_count == 0
        assert result.has_more is False
        assert result.new_cursor is None

    def test_with_errors(self) -> None:
        result = SyncResult(
            errors=[
                SyncError(source_id="evt1", error="parse failed"),
                SyncError(source_id="evt2", error="missing field"),
            ],
        )
        assert result.error_count == 2
        assert result.success_count == 0
        assert result.total_count == 2


# ---------------------------------------------------------------------------
# BaseConnector tests
# ---------------------------------------------------------------------------


class TestBaseConnector:
    async def test_run_delegates_to_fetch_since(
        self,
        connector: StubConnector,
    ) -> None:
        result = await connector.run(cursor=None)
        assert isinstance(result, SyncResult)
        assert result.new_cursor == "cursor-after"

    async def test_source_type_property(
        self,
        connector: StubConnector,
    ) -> None:
        assert connector.source_type == SourceType.GOOGLE_CALENDAR

    async def test_health_check(
        self,
        owner_id: uuid.UUID,
        connection_id: uuid.UUID,
        config: ConnectorConfig,
    ) -> None:
        healthy = StubConnector(
            owner_id=owner_id, connection_id=connection_id, config=config, healthy=True
        )
        assert await healthy.health_check() is True

        unhealthy = StubConnector(
            owner_id=owner_id, connection_id=connection_id, config=config, healthy=False
        )
        assert await unhealthy.health_check() is False

    def test_repr(self, connector: StubConnector) -> None:
        r = repr(connector)
        assert "StubConnector" in r
        assert "google_calendar" in r

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            BaseConnector(  # type: ignore[abstract]
                owner_id=uuid.uuid4(),
                connection_id=uuid.uuid4(),
                config=ConnectorConfig(source_type=SourceType.ZOOM),
            )
