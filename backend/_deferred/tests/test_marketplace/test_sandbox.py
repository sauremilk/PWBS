"""Tests for Plugin Sandbox (TASK-157)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from pwbs.marketplace.plugin_sdk import (
    BasePlugin,
    ConnectorPlugin,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginType,
)
from pwbs.marketplace.sandbox import (
    GuardedPluginContext,
    NetworkBlockedError,
    NetworkPolicy,
    PermissionDeniedError,
    PermissionGuard,
    SandboxConfig,
    SandboxExecutor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(**overrides: Any) -> PluginContext:
    defaults: dict[str, Any] = {
        "user_id": uuid.uuid4(),
        "plugin_id": uuid.uuid4(),
        "config": {},
    }
    defaults.update(overrides)
    return PluginContext(**defaults)


class _OkPlugin(ConnectorPlugin):
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="OK",
            slug="ok-plugin",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
            permissions=["read_documents"],
        )

    async def fetch_data(
        self, context: PluginContext, *, cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        return [{"id": "1"}], None


class _SlowPlugin(ConnectorPlugin):
    """Plugin that takes too long."""

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Slow",
            slug="slow-plugin",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
        )

    async def fetch_data(
        self, context: PluginContext, *, cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        import asyncio
        await asyncio.sleep(999)
        return [], None


class _CrashingPlugin(ConnectorPlugin):
    """Plugin that crashes the process."""

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Crasher",
            slug="crash-plugin",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
        )

    async def fetch_data(
        self, context: PluginContext, *, cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        raise RuntimeError("Intentional crash")


# ---------------------------------------------------------------------------
# SandboxConfig tests (AC-1)
# ---------------------------------------------------------------------------


class TestSandboxConfig:
    def test_defaults(self) -> None:
        cfg = SandboxConfig()
        assert cfg.max_cpu_cores == 0.5
        assert cfg.max_memory_mb == 256
        assert cfg.timeout_seconds == 30.0

    def test_custom_values(self) -> None:
        cfg = SandboxConfig(max_cpu_cores=1.0, max_memory_mb=512, timeout_seconds=10.0)
        assert cfg.max_cpu_cores == 1.0
        assert cfg.max_memory_mb == 512

    def test_immutable(self) -> None:
        cfg = SandboxConfig()
        with pytest.raises(AttributeError):
            cfg.max_memory_mb = 1024  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NetworkPolicy tests (AC-3)
# ---------------------------------------------------------------------------


class TestNetworkPolicy:
    def test_default_blocks_all(self) -> None:
        policy = NetworkPolicy()
        assert not policy.is_domain_allowed("example.com")

    def test_whitelisted_domain_allowed(self) -> None:
        policy = NetworkPolicy(allowed_domains=frozenset({"api.notion.com"}))
        assert policy.is_domain_allowed("api.notion.com")
        assert not policy.is_domain_allowed("evil.com")

    def test_check_domain_raises(self) -> None:
        policy = NetworkPolicy()
        with pytest.raises(NetworkBlockedError, match="blocked"):
            policy.check_domain("example.com")

    def test_case_insensitive(self) -> None:
        policy = NetworkPolicy(allowed_domains=frozenset({"api.notion.com"}))
        assert policy.is_domain_allowed("API.NOTION.COM")


# ---------------------------------------------------------------------------
# PermissionGuard tests (AC-2)
# ---------------------------------------------------------------------------


class TestPermissionGuard:
    def test_effective_is_intersection(self) -> None:
        guard = PermissionGuard(
            declared_permissions=["read_documents", "search", "network_outbound"],
            approved_permissions=frozenset({"read_documents", "search"}),
        )
        assert guard.effective_permissions == frozenset({"read_documents", "search"})

    def test_require_permission_passes(self) -> None:
        guard = PermissionGuard(
            declared_permissions=["read_documents"],
            approved_permissions=frozenset({"read_documents"}),
        )
        guard.require_permission("read_documents")  # should not raise

    def test_require_permission_denies(self) -> None:
        guard = PermissionGuard(
            declared_permissions=["read_documents"],
            approved_permissions=frozenset({"read_documents"}),
        )
        with pytest.raises(PermissionDeniedError):
            guard.require_permission("write_documents")

    def test_invalid_permission_not_effective(self) -> None:
        guard = PermissionGuard(
            declared_permissions=["fake_perm"],
            approved_permissions=frozenset({"fake_perm"}),
        )
        assert not guard.has_permission("fake_perm")

    def test_network_access_without_permission(self) -> None:
        guard = PermissionGuard(
            declared_permissions=["read_documents"],
            approved_permissions=frozenset({"read_documents"}),
        )
        with pytest.raises(PermissionDeniedError):
            guard.check_network_access("example.com")

    def test_network_access_allowed_domain(self) -> None:
        policy = NetworkPolicy(allowed_domains=frozenset({"api.example.com"}))
        guard = PermissionGuard(
            declared_permissions=["network_outbound"],
            approved_permissions=frozenset({"network_outbound"}),
            network_policy=policy,
        )
        guard.check_network_access("api.example.com")  # should not raise

    def test_network_access_blocked_domain(self) -> None:
        policy = NetworkPolicy(allowed_domains=frozenset({"api.example.com"}))
        guard = PermissionGuard(
            declared_permissions=["network_outbound"],
            approved_permissions=frozenset({"network_outbound"}),
            network_policy=policy,
        )
        with pytest.raises(NetworkBlockedError):
            guard.check_network_access("evil.com")


# ---------------------------------------------------------------------------
# GuardedPluginContext tests
# ---------------------------------------------------------------------------


class TestGuardedPluginContext:
    def test_basic_properties(self) -> None:
        ctx = _ctx()
        guard = PermissionGuard(
            declared_permissions=["read_documents"],
            approved_permissions=frozenset({"read_documents"}),
        )
        guarded = GuardedPluginContext(ctx, guard)
        assert guarded.user_id == ctx.user_id
        assert guarded.plugin_id == ctx.plugin_id
        assert guarded.config == ctx.config

    def test_search_requires_permission(self) -> None:
        ctx = _ctx()
        guard = PermissionGuard(
            declared_permissions=["read_documents"],
            approved_permissions=frozenset({"read_documents"}),
        )
        guarded = GuardedPluginContext(ctx, guard)
        with pytest.raises(PermissionDeniedError):
            _ = guarded.search

    def test_search_with_permission(self) -> None:
        ctx = _ctx(search="mock_search_fn")
        guard = PermissionGuard(
            declared_permissions=["search"],
            approved_permissions=frozenset({"search"}),
        )
        guarded = GuardedPluginContext(ctx, guard)
        assert guarded.search == "mock_search_fn"

    def test_storage_requires_write_permission(self) -> None:
        ctx = _ctx()
        guard = PermissionGuard(
            declared_permissions=["read_documents"],
            approved_permissions=frozenset({"read_documents"}),
        )
        guarded = GuardedPluginContext(ctx, guard)
        with pytest.raises(PermissionDeniedError):
            _ = guarded.storage


# ---------------------------------------------------------------------------
# SandboxExecutor tests (AC-1, AC-4)
# ---------------------------------------------------------------------------


class TestSandboxExecutor:
    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        executor = SandboxExecutor(config=SandboxConfig(timeout_seconds=10.0))
        plugin = _OkPlugin()
        ctx = _ctx()
        result = await executor.execute(
            plugin, ctx,
            approved_permissions=frozenset({"read_documents"}),
        )
        assert result.success is True
        assert result.data["records"] == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_timeout_kills_plugin(self) -> None:
        """AC-1: Timeout enforcement."""
        executor = SandboxExecutor(config=SandboxConfig(timeout_seconds=1.0))
        plugin = _SlowPlugin()
        ctx = _ctx()
        result = await executor.execute(
            plugin, ctx,
            approved_permissions=frozenset(),
        )
        assert result.success is False
        assert any("timed out" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_crash_contained(self) -> None:
        """AC-4: Plugin crash doesn't affect host process."""
        executor = SandboxExecutor(config=SandboxConfig(timeout_seconds=10.0))
        plugin = _CrashingPlugin()
        ctx = _ctx()
        result = await executor.execute(
            plugin, ctx,
            approved_permissions=frozenset(),
        )
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_create_guard(self) -> None:
        executor = SandboxExecutor()
        plugin = _OkPlugin()
        manifest = plugin.get_manifest()
        guard = executor.create_guard(
            manifest,
            approved_permissions=frozenset({"read_documents"}),
        )
        assert guard.has_permission("read_documents")
        assert not guard.has_permission("write_documents")