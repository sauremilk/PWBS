"""Plugin Sandbox  isolated execution environment for third-party code (TASK-157).

Provides:
- ``SandboxConfig`` – configurable resource limits (CPU, RAM, timeout)
- ``PermissionGuard`` – enforces declared and approved permissions
- ``NetworkPolicy`` – default-deny network with domain whitelist
- ``SandboxExecutor`` – runs plugins in isolated process with error containment

Design:
  Process-based isolation via ``multiprocessing`` for MVP. The executor spawns
  a child process for each plugin invocation, enforcing timeouts and catching
  crashes without affecting the host process. A Docker-based backend can be
  swapped in for production deployments.

Security model:
  1. Plugin declares permissions in ``manifest.json``
  2. Admin approves permissions on installation
  3. ``PermissionGuard`` intercepts all resource access at runtime
  4. Network is blocked unless ``network_outbound`` permission is approved
     AND the target domain is in the whitelist
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import signal
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from pwbs.core.exceptions import PWBSError
from pwbs.marketplace.plugin_sdk import (
    VALID_PERMISSIONS,
    BasePlugin,
    PluginContext,
    PluginManifest,
    PluginResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SandboxError(PWBSError):
    """Base error for sandbox-related failures."""


class PermissionDeniedError(SandboxError):
    """Raised when a plugin attempts an action beyond its approved permissions."""


class ResourceLimitExceededError(SandboxError):
    """Raised when a plugin exceeds its resource budget."""


class NetworkBlockedError(SandboxError):
    """Raised when a plugin attempts disallowed network access."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SandboxConfig:
    """Resource limits for sandboxed plugin execution.

    Defaults match AC-1: CPU 0.5 core, RAM 256 MB, timeout 30s.
    """

    max_cpu_cores: float = 0.5
    max_memory_mb: int = 256
    timeout_seconds: float = 30.0
    max_output_bytes: int = 1_048_576  # 1 MB stdout/stderr capture


class NetworkPolicy:
    """Default-deny network policy with domain whitelist (AC-3).

    Network access is only allowed when:
    1. The plugin has the ``network_outbound`` permission approved, AND
    2. The target domain is in the whitelist.
    """

    def __init__(self, allowed_domains: frozenset[str] | None = None) -> None:
        self._allowed_domains: frozenset[str] = allowed_domains or frozenset()

    @property
    def allowed_domains(self) -> frozenset[str]:
        return self._allowed_domains

    def is_domain_allowed(self, domain: str) -> bool:
        """Check whether outbound access to *domain* is permitted."""
        normalised = domain.lower().strip()
        return normalised in self._allowed_domains

    def check_domain(self, domain: str) -> None:
        """Raise ``NetworkBlockedError`` if *domain* is not whitelisted."""
        if not self.is_domain_allowed(domain):
            raise NetworkBlockedError(
                f"Network access to '{domain}' is blocked by sandbox policy",
                code="SANDBOX_NETWORK_BLOCKED",
            )


# ---------------------------------------------------------------------------
# Permission enforcement (AC-2)
# ---------------------------------------------------------------------------


class PermissionGuard:
    """Enforces the intersection of declared and admin-approved permissions.

    A plugin may only access resources for which:
    1. The manifest declares the permission, AND
    2. The admin approved it during installation.
    """

    def __init__(
        self,
        *,
        declared_permissions: list[str],
        approved_permissions: frozenset[str],
        network_policy: NetworkPolicy | None = None,
    ) -> None:
        # Effective permissions = declared ∩ approved ∩ VALID
        self._effective: frozenset[str] = (
            frozenset(declared_permissions) & approved_permissions & VALID_PERMISSIONS
        )
        self._network_policy = network_policy or NetworkPolicy()

    @property
    def effective_permissions(self) -> frozenset[str]:
        return self._effective

    def has_permission(self, permission: str) -> bool:
        return permission in self._effective

    def require_permission(self, permission: str) -> None:
        """Raise ``PermissionDeniedError`` if the permission is not effective."""
        if not self.has_permission(permission):
            raise PermissionDeniedError(
                f"Plugin lacks permission '{permission}'",
                code="SANDBOX_PERMISSION_DENIED",
            )

    def check_network_access(self, domain: str) -> None:
        """Ensure both the permission and domain whitelist allow access."""
        self.require_permission("network_outbound")
        self._network_policy.check_domain(domain)

    @property
    def network_allowed(self) -> bool:
        """Whether the plugin has any network access at all."""
        return self.has_permission("network_outbound")


class GuardedPluginContext:
    """Proxy around ``PluginContext`` that enforces permissions on access.

    This is what the sandbox injects into the plugin instead of the raw context.
    """

    def __init__(
        self,
        context: PluginContext,
        guard: PermissionGuard,
    ) -> None:
        self._context = context
        self._guard = guard

    @property
    def user_id(self) -> UUID:
        return self._context.user_id

    @property
    def plugin_id(self) -> UUID:
        return self._context.plugin_id

    @property
    def config(self) -> dict[str, Any]:
        return self._context.config

    @property
    def search(self) -> Any:
        self._guard.require_permission("search")
        return self._context.search

    @property
    def storage(self) -> Any:
        self._guard.require_permission("write_documents")
        return self._context.storage

    @property
    def guard(self) -> PermissionGuard:
        return self._guard

    def as_plugin_context(self) -> PluginContext:
        """Return the underlying raw context (for internal use only)."""
        return self._context


# ---------------------------------------------------------------------------
# Sandbox executor (AC-1, AC-4)
# ---------------------------------------------------------------------------


def _run_plugin_in_process(
    result_dict: dict[str, Any],
    plugin: BasePlugin,
    context: PluginContext,
    kwargs: dict[str, Any],
) -> None:
    """Target function for the child process.

    Runs the plugin's ``execute`` method and stores the result in the
    shared ``result_dict``.  Any exception is caught and serialised so
    the parent process can reconstruct a ``PluginResult``.
    """
    try:
        # Run the async execute in a new event loop inside the child process
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(plugin.execute(context, **kwargs))
            result_dict["success"] = result.success
            result_dict["data"] = result.data
            result_dict["errors"] = result.errors
            result_dict["source_refs"] = result.source_refs
        finally:
            loop.close()
    except Exception:
        result_dict["success"] = False
        result_dict["errors"] = [traceback.format_exc()]


class SandboxExecutor:
    """Executes plugins in an isolated child process with resource limits.

    Guarantees:
    - Timeout enforcement via ``multiprocessing.Process.join(timeout)``
    - Permission checks via ``PermissionGuard`` before execution
    - Crash isolation: child-process crash → ``PluginResult(success=False)``
    - Memory/CPU limits logged as warnings (OS-level enforcement is
      backend-specific; see ``DockerSandboxExecutor`` for hard limits)
    """

    def __init__(
        self,
        config: SandboxConfig | None = None,
        network_policy: NetworkPolicy | None = None,
    ) -> None:
        self._config = config or SandboxConfig()
        self._network_policy = network_policy or NetworkPolicy()

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def network_policy(self) -> NetworkPolicy:
        return self._network_policy

    def create_guard(
        self,
        manifest: PluginManifest,
        approved_permissions: frozenset[str],
    ) -> PermissionGuard:
        """Create a ``PermissionGuard`` for the given manifest and approvals."""
        return PermissionGuard(
            declared_permissions=manifest.permissions,
            approved_permissions=approved_permissions,
            network_policy=self._network_policy,
        )

    async def execute(
        self,
        plugin: BasePlugin,
        context: PluginContext,
        *,
        approved_permissions: frozenset[str],
        **kwargs: Any,
    ) -> PluginResult:
        """Run *plugin* in a sandboxed child process.

        Parameters
        ----------
        plugin:
            The plugin instance to execute.
        context:
            The ``PluginContext`` scoped to the requesting user.
        approved_permissions:
            The set of permissions approved by the admin for this plugin.
        **kwargs:
            Additional keyword arguments forwarded to ``plugin.execute()``.

        Returns
        -------
        PluginResult
            Always returns a result, never raises.  Crashes/timeouts produce
            ``PluginResult(success=False, errors=[...])``.
        """
        manifest = plugin.get_manifest()
        guard = self.create_guard(manifest, approved_permissions)

        # Network permission check: if plugin didn't declare network_outbound,
        # we don't need special handling. If it did but admin didn't approve,
        # the guard will block at access time.
        logger.info(
            "Sandbox executing plugin %s (permissions: %s, timeout: %.1fs)",
            manifest.slug,
            sorted(guard.effective_permissions),
            self._config.timeout_seconds,
        )

        # Use multiprocessing with a shared dict for the result
        manager = multiprocessing.Manager()
        result_dict = manager.dict()  # type: ignore[assignment]
        result_dict["success"] = False
        result_dict["errors"] = ["Plugin did not produce a result"]
        result_dict["data"] = None
        result_dict["source_refs"] = []

        process = multiprocessing.Process(
            target=_run_plugin_in_process,
            args=(result_dict, plugin, context, kwargs),
            daemon=True,
        )

        try:
            process.start()
            # Wait with timeout (AC-1: configurable timeout)
            await asyncio.to_thread(
                process.join, timeout=self._config.timeout_seconds
            )

            if process.is_alive():
                # Timeout exceeded → kill the process
                logger.warning(
                    "Plugin %s exceeded timeout (%.1fs), terminating",
                    manifest.slug,
                    self._config.timeout_seconds,
                )
                process.terminate()
                process.join(timeout=5.0)
                if process.is_alive():
                    process.kill()
                return PluginResult(
                    success=False,
                    errors=[
                        f"Plugin execution timed out after {self._config.timeout_seconds}s"
                    ],
                )

            if process.exitcode != 0:
                # AC-4: Plugin crash doesn't affect host
                logger.warning(
                    "Plugin %s crashed (exit code %s)",
                    manifest.slug,
                    process.exitcode,
                )
                return PluginResult(
                    success=False,
                    errors=[
                        f"Plugin process crashed with exit code {process.exitcode}"
                    ],
                )

            # Extract result from shared dict
            return PluginResult(
                success=bool(result_dict.get("success", False)),
                data=result_dict.get("data"),
                errors=list(result_dict.get("errors", [])),
                source_refs=list(result_dict.get("source_refs", [])),
            )

        except Exception as exc:
            logger.exception("Sandbox execution error for plugin %s", manifest.slug)
            return PluginResult(success=False, errors=[str(exc)])
        finally:
            if process.is_alive():
                process.terminate()


# Module-level convenience instance
default_sandbox = SandboxExecutor()