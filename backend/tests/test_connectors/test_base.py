"""Tests for BaseConnector ABC (TASK-041)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from pwbs.connectors.base import BaseConnector, ConnectorConfig, JsonValue, SyncError, SyncResult
from pwbs.core.exceptions import ConnectorError, RateLimitError
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

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
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


# ---------------------------------------------------------------------------
# Retry with exponential backoff tests
# ---------------------------------------------------------------------------


class RateLimitStubConnector(BaseConnector):
    """Connector that raises RateLimitError N times before succeeding."""

    RETRY_DELAYS: tuple[float, ...] = (0.01, 0.02, 0.03)  # fast for tests

    def __init__(
        self,
        *,
        owner_id: uuid.UUID,
        connection_id: uuid.UUID,
        config: ConnectorConfig,
        fail_count: int = 0,
    ) -> None:
        super().__init__(owner_id=owner_id, connection_id=connection_id, config=config)
        self._fail_count = fail_count
        self._attempts = 0

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        self._attempts += 1
        if self._attempts <= self._fail_count:
            raise RateLimitError(
                f"Rate limited (attempt {self._attempts})",
                status_code=429,
            )
        return SyncResult(new_cursor="ok", has_more=False)

    async def normalize(self, raw: dict[str, JsonValue]) -> UnifiedDocument:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True


class TestRetryWithBackoff:
    """Tests for BaseConnector._execute_with_retry / run() retry behaviour."""

    @pytest.fixture()
    def _ids(self) -> tuple[uuid.UUID, uuid.UUID]:
        return uuid.uuid4(), uuid.uuid4()

    @pytest.fixture()
    def _config(self) -> ConnectorConfig:
        return ConnectorConfig(source_type=SourceType.NOTION)

    async def test_succeeds_without_retry(
        self, _ids: tuple[uuid.UUID, uuid.UUID], _config: ConnectorConfig
    ) -> None:
        conn = RateLimitStubConnector(
            owner_id=_ids[0], connection_id=_ids[1], config=_config, fail_count=0
        )
        result = await conn.run(cursor=None)
        assert result.new_cursor == "ok"
        assert conn._attempts == 1

    async def test_succeeds_after_one_retry(
        self, _ids: tuple[uuid.UUID, uuid.UUID], _config: ConnectorConfig
    ) -> None:
        conn = RateLimitStubConnector(
            owner_id=_ids[0], connection_id=_ids[1], config=_config, fail_count=1
        )
        result = await conn.run(cursor=None)
        assert result.new_cursor == "ok"
        assert conn._attempts == 2

    async def test_succeeds_after_max_retries(
        self, _ids: tuple[uuid.UUID, uuid.UUID], _config: ConnectorConfig
    ) -> None:
        conn = RateLimitStubConnector(
            owner_id=_ids[0], connection_id=_ids[1], config=_config, fail_count=3
        )
        result = await conn.run(cursor=None)
        assert result.new_cursor == "ok"
        assert conn._attempts == 4  # 1 initial + 3 retries

    async def test_raises_after_retries_exhausted(
        self, _ids: tuple[uuid.UUID, uuid.UUID], _config: ConnectorConfig
    ) -> None:
        conn = RateLimitStubConnector(
            owner_id=_ids[0], connection_id=_ids[1], config=_config, fail_count=99
        )
        with pytest.raises(RateLimitError):
            await conn.run(cursor=None)
        assert conn._attempts == 4  # 1 initial + 3 retries, then give up

    async def test_non_rate_limit_error_not_retried(
        self, _ids: tuple[uuid.UUID, uuid.UUID], _config: ConnectorConfig
    ) -> None:
        """ConnectorError (non-rate-limit) should propagate immediately."""
        conn = RateLimitStubConnector(
            owner_id=_ids[0], connection_id=_ids[1], config=_config, fail_count=0
        )
        conn.fetch_since = AsyncMock(  # type: ignore[method-assign]
            side_effect=ConnectorError("auth failed", code="AUTH_ERROR")
        )
        with pytest.raises(ConnectorError, match="auth failed"):
            await conn.run(cursor=None)
        conn.fetch_since.assert_called_once()

    async def test_retry_delays_are_respected(
        self, _ids: tuple[uuid.UUID, uuid.UUID], _config: ConnectorConfig
    ) -> None:
        """Verify asyncio.sleep is called with the configured delays."""
        conn = RateLimitStubConnector(
            owner_id=_ids[0], connection_id=_ids[1], config=_config, fail_count=2
        )
        with patch("pwbs.connectors.base.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await conn.run(cursor=None)
        assert result.new_cursor == "ok"
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(0.01)
        mock_sleep.assert_any_call(0.02)

    async def test_rate_limit_error_attributes(self) -> None:
        err = RateLimitError("too many requests", status_code=429, retry_after=60.0)
        assert err.status_code == 429
        assert err.retry_after == 60.0
        assert err.code == "RATE_LIMITED"
        assert str(err) == "too many requests"
