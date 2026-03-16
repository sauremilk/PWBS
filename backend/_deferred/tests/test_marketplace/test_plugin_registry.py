"""Tests for Plugin Registry - validation, loading, sandboxed execution (TASK-151)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import pytest

from pwbs.marketplace.plugin_registry import (
    PluginError,
    PluginRegistry,
    PluginValidationError,
    validate_manifest,
    validate_plugin_config,
)
from pwbs.marketplace.plugin_sdk import (
    BasePlugin,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_manifest(**overrides: Any) -> PluginManifest:
    defaults: dict[str, Any] = {
        "name": "Test Plugin",
        "slug": "test-plugin",
        "version": "1.0.0",
        "plugin_type": PluginType.CONNECTOR,
        "entry_point": "module:factory",
        "permissions": ["read_documents"],
    }
    defaults.update(overrides)
    return PluginManifest(**defaults)


class _SimplePlugin(BasePlugin):
    def __init__(
        self,
        manifest: PluginManifest | None = None,
        result: PluginResult | None = None,
    ) -> None:
        self._manifest = manifest or _valid_manifest()
        self._result = result or PluginResult(success=True, data="ok")

    def get_manifest(self) -> PluginManifest:
        return self._manifest

    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        return self._result


class _SlowPlugin(BasePlugin):
    def get_manifest(self) -> PluginManifest:
        return _valid_manifest(slug="slow-plugin")

    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        await asyncio.sleep(60)
        return PluginResult(success=True)


class _ExplodingPlugin(BasePlugin):
    def get_manifest(self) -> PluginManifest:
        return _valid_manifest(slug="exploding-plugin")

    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        raise ValueError("kaboom")


def _make_context(**overrides: Any) -> PluginContext:
    defaults: dict[str, Any] = {
        "user_id": uuid.uuid4(),
        "plugin_id": uuid.uuid4(),
        "config": {},
    }
    defaults.update(overrides)
    return PluginContext(**defaults)


# ---------------------------------------------------------------------------
# validate_manifest
# ---------------------------------------------------------------------------


class TestValidateManifest:
    def test_valid_manifest_no_errors(self) -> None:
        errors = validate_manifest(_valid_manifest())
        assert errors == []

    def test_empty_slug(self) -> None:
        errors = validate_manifest(_valid_manifest(slug=""))
        assert any("slug" in e for e in errors)

    def test_invalid_slug_chars(self) -> None:
        errors = validate_manifest(_valid_manifest(slug="has spaces!"))
        assert any("slug" in e for e in errors)

    def test_empty_version(self) -> None:
        errors = validate_manifest(_valid_manifest(version=""))
        assert any("version" in e for e in errors)

    def test_empty_name(self) -> None:
        errors = validate_manifest(_valid_manifest(name=""))
        assert any("name" in e for e in errors)

    def test_invalid_permissions(self) -> None:
        errors = validate_manifest(_valid_manifest(permissions=["hack_system"]))
        assert any("permissions" in e for e in errors)

    def test_missing_colon_in_entry_point(self) -> None:
        errors = validate_manifest(_valid_manifest(entry_point="no_colon"))
        assert any("entry_point" in e for e in errors)

    def test_multiple_errors_combined(self) -> None:
        errors = validate_manifest(_valid_manifest(
            slug="", name="", version="", entry_point="bad",
        ))
        assert len(errors) >= 4


# ---------------------------------------------------------------------------
# validate_plugin_config
# ---------------------------------------------------------------------------


class TestValidatePluginConfig:
    def test_valid_config(self) -> None:
        schema = {"api_key": {"type": "string", "required": True}}
        errors = validate_plugin_config({"api_key": "abc"}, schema)
        assert errors == []

    def test_missing_required_field(self) -> None:
        schema = {"api_key": {"type": "string", "required": True}}
        errors = validate_plugin_config({}, schema)
        assert any("api_key" in e for e in errors)

    def test_wrong_type(self) -> None:
        schema = {"count": {"type": "int", "required": True}}
        errors = validate_plugin_config({"count": "not_int"}, schema)
        assert any("count" in e for e in errors)

    def test_optional_field_absent_ok(self) -> None:
        schema = {"opt": {"type": "string", "required": False}}
        errors = validate_plugin_config({}, schema)
        assert errors == []

    def test_bool_type(self) -> None:
        schema = {"flag": {"type": "bool", "required": True}}
        assert validate_plugin_config({"flag": True}, schema) == []
        assert len(validate_plugin_config({"flag": "yes"}, schema)) > 0

    def test_float_accepts_int(self) -> None:
        schema = {"rate": {"type": "float", "required": True}}
        assert validate_plugin_config({"rate": 3}, schema) == []
        assert validate_plugin_config({"rate": 3.14}, schema) == []


# ---------------------------------------------------------------------------
# PluginRegistry — registration
# ---------------------------------------------------------------------------


class TestPluginRegistryRegistration:
    def test_register_valid_plugin(self) -> None:
        reg = PluginRegistry()
        pid = uuid.uuid4()
        reg.register(pid, _SimplePlugin())
        assert reg.is_loaded(pid)
        assert reg.get_plugin(pid) is not None
        assert reg.get_manifest(pid) is not None

    def test_register_invalid_manifest_raises(self) -> None:
        reg = PluginRegistry()
        bad = _SimplePlugin(manifest=_valid_manifest(slug=""))
        with pytest.raises(PluginValidationError):
            reg.register(uuid.uuid4(), bad)

    def test_unregister(self) -> None:
        reg = PluginRegistry()
        pid = uuid.uuid4()
        reg.register(pid, _SimplePlugin())
        reg.unregister(pid)
        assert not reg.is_loaded(pid)
        assert reg.get_plugin(pid) is None

    def test_unregister_nonexistent_is_noop(self) -> None:
        reg = PluginRegistry()
        reg.unregister(uuid.uuid4())  # No error


# ---------------------------------------------------------------------------
# PluginRegistry — sandboxed execution
# ---------------------------------------------------------------------------


class TestPluginRegistryExecution:
    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        reg = PluginRegistry()
        pid = uuid.uuid4()
        reg.register(pid, _SimplePlugin())
        ctx = _make_context(plugin_id=pid)
        result = await reg.execute_sandboxed(pid, ctx)
        assert result.success is True
        assert result.data == "ok"

    @pytest.mark.asyncio
    async def test_execute_not_loaded_raises(self) -> None:
        reg = PluginRegistry()
        ctx = _make_context()
        with pytest.raises(PluginError, match="not loaded"):
            await reg.execute_sandboxed(uuid.uuid4(), ctx)

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        reg = PluginRegistry()
        pid = uuid.uuid4()
        reg.register(pid, _SlowPlugin())
        ctx = _make_context(plugin_id=pid)
        result = await reg.execute_sandboxed(pid, ctx, timeout=0.05)
        assert result.success is False
        assert any("timed out" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_unhandled_error_contained(self) -> None:
        reg = PluginRegistry()
        pid = uuid.uuid4()
        reg.register(pid, _ExplodingPlugin())
        ctx = _make_context(plugin_id=pid)
        result = await reg.execute_sandboxed(pid, ctx)
        assert result.success is False
        assert "kaboom" in result.errors[0]
