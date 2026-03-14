"""Tests for ConnectorRegistry (TASK-042)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import pytest

from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncResult
from pwbs.connectors.registry import (
    clear_registry,
    create_connector,
    get_connector_class,
    health_check_all,
    list_registered_types,
    register_connector,
)
from pwbs.core.exceptions import ConnectorError, NotFoundError
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from pwbs.schemas.document import UnifiedDocument


# ---------------------------------------------------------------------------
# Stub connector
# ---------------------------------------------------------------------------


class FakeCalendarConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        return SyncResult()

    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True


class FakeNotionConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        return SyncResult()

    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Ensure each test starts with an empty registry."""
    clear_registry()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterConnector:
    def test_register_and_lookup(self) -> None:
        register_connector(SourceType.GOOGLE_CALENDAR, FakeCalendarConnector)
        cls = get_connector_class(SourceType.GOOGLE_CALENDAR)
        assert cls is FakeCalendarConnector

    def test_double_registration_raises(self) -> None:
        register_connector(SourceType.GOOGLE_CALENDAR, FakeCalendarConnector)
        with pytest.raises(ConnectorError, match="already registered"):
            register_connector(SourceType.GOOGLE_CALENDAR, FakeNotionConnector)

    def test_lookup_unregistered_raises(self) -> None:
        with pytest.raises(NotFoundError, match="No connector registered"):
            get_connector_class(SourceType.ZOOM)


class TestCreateConnector:
    def test_create_returns_instance(self) -> None:
        register_connector(SourceType.NOTION, FakeNotionConnector)
        owner_id = uuid.uuid4()
        connection_id = uuid.uuid4()
        config = ConnectorConfig(source_type=SourceType.NOTION)

        connector = create_connector(
            SourceType.NOTION,
            owner_id=owner_id,
            connection_id=connection_id,
            config=config,
        )
        assert isinstance(connector, FakeNotionConnector)
        assert connector.owner_id == owner_id
        assert connector.connection_id == connection_id


class TestListRegisteredTypes:
    def test_empty_registry(self) -> None:
        assert list_registered_types() == []

    def test_multiple_registrations(self) -> None:
        register_connector(SourceType.GOOGLE_CALENDAR, FakeCalendarConnector)
        register_connector(SourceType.NOTION, FakeNotionConnector)
        types = list_registered_types()
        assert SourceType.GOOGLE_CALENDAR in types
        assert SourceType.NOTION in types
        assert len(types) == 2


class TestClearRegistry:
    def test_clear_removes_all(self) -> None:
        register_connector(SourceType.GOOGLE_CALENDAR, FakeCalendarConnector)
        assert len(list_registered_types()) == 1
        clear_registry()
        assert len(list_registered_types()) == 0


# ---------------------------------------------------------------------------
# health_check_all
# ---------------------------------------------------------------------------


class FakeHealthyConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        return SyncResult()

    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True


class FakeUnhealthyConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        return SyncResult()

    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return False


class FakeExplodingConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        return SyncResult()

    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise ConnectionError("Service unreachable")


class TestHealthCheckAll:
    @pytest.mark.asyncio
    async def test_all_healthy(self) -> None:
        register_connector(SourceType.GOOGLE_CALENDAR, FakeHealthyConnector)
        register_connector(SourceType.NOTION, FakeHealthyConnector)
        owner_id = uuid.uuid4()
        connection_id = uuid.uuid4()
        config = ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR)

        results = await health_check_all(
            owner_id=owner_id,
            connection_id=connection_id,
            config=config,
        )
        assert results[SourceType.GOOGLE_CALENDAR] is True
        assert results[SourceType.NOTION] is True

    @pytest.mark.asyncio
    async def test_unhealthy_connector(self) -> None:
        register_connector(SourceType.GOOGLE_CALENDAR, FakeUnhealthyConnector)
        owner_id = uuid.uuid4()
        connection_id = uuid.uuid4()
        config = ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR)

        results = await health_check_all(
            owner_id=owner_id,
            connection_id=connection_id,
            config=config,
        )
        assert results[SourceType.GOOGLE_CALENDAR] is False

    @pytest.mark.asyncio
    async def test_exception_maps_to_false(self) -> None:
        register_connector(SourceType.ZOOM, FakeExplodingConnector)
        owner_id = uuid.uuid4()
        connection_id = uuid.uuid4()
        config = ConnectorConfig(source_type=SourceType.ZOOM)

        results = await health_check_all(
            owner_id=owner_id,
            connection_id=connection_id,
            config=config,
        )
        assert results[SourceType.ZOOM] is False

    @pytest.mark.asyncio
    async def test_empty_registry(self) -> None:
        results = await health_check_all(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(source_type=SourceType.GOOGLE_CALENDAR),
        )
        assert results == {}
