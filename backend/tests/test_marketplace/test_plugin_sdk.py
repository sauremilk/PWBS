"""Tests for the Plugin SDK base classes (TASK-151)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from pwbs.marketplace.plugin_sdk import (
    VALID_PERMISSIONS,
    BriefingTemplatePlugin,
    ConnectorPlugin,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginStatus,
    PluginType,
    ProcessingPlugin,
)


# ---------------------------------------------------------------------------
# Helpers — concrete implementations of abstract plugins
# ---------------------------------------------------------------------------


class DummyConnector(ConnectorPlugin):
    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self._records = records or [{"id": "1", "text": "hello"}]

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Dummy Connector",
            slug="dummy-connector",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
            permissions=["read_documents"],
        )

    async def fetch_data(
        self, context: PluginContext, *, cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        return self._records, None


class FailingConnector(ConnectorPlugin):
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Failing", slug="failing", version="0.1.0",
            plugin_type=PluginType.CONNECTOR,
        )

    async def fetch_data(
        self, context: PluginContext, *, cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        raise RuntimeError("connection refused")


class DummyBriefing(BriefingTemplatePlugin):
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Dummy Briefing",
            slug="dummy-briefing",
            version="1.0.0",
            plugin_type=PluginType.BRIEFING_TEMPLATE,
        )

    async def generate_briefing(
        self, context: PluginContext, *,
        search_results: list[dict[str, Any]],
        graph_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "title": "Test Briefing",
            "content": "Summary of results",
            "source_refs": ["ref-1"],
        }


class DummyProcessing(ProcessingPlugin):
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Dummy Processing",
            slug="dummy-processing",
            version="1.0.0",
            plugin_type=PluginType.PROCESSING,
        )

    async def process_documents(
        self, context: PluginContext, *, documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [{"enriched": True, **doc} for doc in documents]


def _make_context(**overrides: Any) -> PluginContext:
    defaults: dict[str, Any] = {
        "user_id": uuid.uuid4(),
        "plugin_id": uuid.uuid4(),
        "config": {},
    }
    defaults.update(overrides)
    return PluginContext(**defaults)


# ---------------------------------------------------------------------------
# PluginManifest
# ---------------------------------------------------------------------------


class TestPluginManifest:
    def test_defaults(self) -> None:
        m = PluginManifest(
            name="X", slug="x", version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
        )
        assert m.permissions == []
        assert m.config_schema == {}
        assert m.min_pwbs_version == "0.1.0"

    def test_stores_values(self) -> None:
        m = PluginManifest(
            name="Y", slug="y", version="2.0.0",
            plugin_type=PluginType.BRIEFING_TEMPLATE,
            description="desc", author="me",
            permissions=["search"],
        )
        assert m.name == "Y"
        assert m.plugin_type == PluginType.BRIEFING_TEMPLATE
        assert m.permissions == ["search"]


# ---------------------------------------------------------------------------
# PluginContext
# ---------------------------------------------------------------------------


class TestPluginContext:
    def test_holds_user_scope(self) -> None:
        uid = uuid.uuid4()
        ctx = PluginContext(user_id=uid, plugin_id=uuid.uuid4(), config={"key": "val"})
        assert ctx.user_id == uid
        assert ctx.config == {"key": "val"}


# ---------------------------------------------------------------------------
# PluginResult
# ---------------------------------------------------------------------------


class TestPluginResult:
    def test_success(self) -> None:
        r = PluginResult(success=True, data={"x": 1})
        assert r.success is True
        assert r.errors == []

    def test_failure(self) -> None:
        r = PluginResult(success=False, errors=["boom"])
        assert r.success is False
        assert r.errors == ["boom"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_plugin_type_values(self) -> None:
        assert PluginType.CONNECTOR.value == "connector"
        assert PluginType.BRIEFING_TEMPLATE.value == "briefing_template"
        assert PluginType.PROCESSING.value == "processing"

    def test_plugin_status_values(self) -> None:
        assert PluginStatus.PENDING_REVIEW.value == "pending_review"
        assert PluginStatus.APPROVED.value == "approved"

    def test_valid_permissions_is_frozen(self) -> None:
        assert isinstance(VALID_PERMISSIONS, frozenset)
        assert "read_documents" in VALID_PERMISSIONS


# ---------------------------------------------------------------------------
# ConnectorPlugin
# ---------------------------------------------------------------------------


class TestConnectorPlugin:
    @pytest.mark.asyncio
    async def test_execute_returns_records(self) -> None:
        plugin = DummyConnector()
        ctx = _make_context()
        result = await plugin.execute(ctx)
        assert result.success is True
        assert result.data["records"] == [{"id": "1", "text": "hello"}]
        assert result.data["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_execute_catches_error(self) -> None:
        plugin = FailingConnector()
        ctx = _make_context()
        result = await plugin.execute(ctx)
        assert result.success is False
        assert "connection refused" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_passes_cursor(self) -> None:
        plugin = DummyConnector()
        ctx = _make_context()
        result = await plugin.execute(ctx, cursor="abc")
        assert result.success is True


# ---------------------------------------------------------------------------
# BriefingTemplatePlugin
# ---------------------------------------------------------------------------


class TestBriefingTemplatePlugin:
    @pytest.mark.asyncio
    async def test_execute_returns_briefing(self) -> None:
        plugin = DummyBriefing()
        ctx = _make_context()
        result = await plugin.execute(ctx, search_results=[{"doc": 1}])
        assert result.success is True
        assert result.data["title"] == "Test Briefing"
        assert result.source_refs == ["ref-1"]


# ---------------------------------------------------------------------------
# ProcessingPlugin
# ---------------------------------------------------------------------------


class TestProcessingPlugin:
    @pytest.mark.asyncio
    async def test_execute_enriches_documents(self) -> None:
        plugin = DummyProcessing()
        ctx = _make_context()
        result = await plugin.execute(ctx, documents=[{"id": "d1"}])
        assert result.success is True
        assert result.data["documents"][0]["enriched"] is True

    @pytest.mark.asyncio
    async def test_execute_empty_list(self) -> None:
        plugin = DummyProcessing()
        ctx = _make_context()
        result = await plugin.execute(ctx, documents=[])
        assert result.success is True
        assert result.data["documents"] == []


# ---------------------------------------------------------------------------
# Base hooks
# ---------------------------------------------------------------------------


class TestBasePluginHooks:
    @pytest.mark.asyncio
    async def test_default_on_install_is_noop(self) -> None:
        plugin = DummyConnector()
        ctx = _make_context()
        # Should not raise
        await plugin.on_install(ctx)

    @pytest.mark.asyncio
    async def test_default_on_uninstall_is_noop(self) -> None:
        plugin = DummyConnector()
        ctx = _make_context()
        await plugin.on_uninstall(ctx)

    @pytest.mark.asyncio
    async def test_default_validate_config_is_empty(self) -> None:
        plugin = DummyConnector()
        errors = await plugin.validate_config({"any": "thing"})
        assert errors == []
