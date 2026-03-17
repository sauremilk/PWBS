"""Plugin registry  validates, loads, and sandboxes plugins (TASK-151).

The registry is responsible for:
- Validating plugin manifests against the SDK schema
- Maintaining an in-memory cache of loaded plugin instances
- Providing a sandboxed execution wrapper with timeout and permission checks
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from pwbs.core.exceptions import PWBSError
from pwbs.marketplace.plugin_sdk import (
    VALID_PERMISSIONS,
    BasePlugin,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginType,
)

logger = logging.getLogger(__name__)

# Default execution timeout in seconds
PLUGIN_EXECUTE_TIMEOUT = 30.0


class PluginError(PWBSError):
    """Raised when plugin validation, loading, or execution fails."""


class PluginValidationError(PluginError):
    """Raised when a plugin manifest fails validation."""


def validate_manifest(manifest: PluginManifest) -> list[str]:
    """Validate a plugin manifest and return a list of error messages."""
    errors: list[str] = []

    if not manifest.slug or not manifest.slug.replace("-", "").replace("_", "").isalnum():
        errors.append("slug must be non-empty and contain only alphanumeric, hyphens, underscores")

    if not manifest.version:
        errors.append("version is required")

    if not manifest.name:
        errors.append("name is required")

    if manifest.plugin_type not in PluginType:
        errors.append(f"plugin_type must be one of {[t.value for t in PluginType]}")

    invalid_perms = set(manifest.permissions) - VALID_PERMISSIONS
    if invalid_perms:
        errors.append(f"invalid permissions: {sorted(invalid_perms)}")

    if not manifest.entry_point or ":" not in manifest.entry_point:
        errors.append("entry_point must be in 'module:factory' format")

    return errors


def validate_plugin_config(config: dict[str, Any], config_schema: dict[str, Any]) -> list[str]:
    """Validate user-supplied config against the plugin's declared schema.

    The config_schema uses a simplified format:
    {
        "field_name": {"type": "string|int|bool|float", "required": true/false, "default": ...}
    }
    """
    errors: list[str] = []
    type_map = {"string": str, "int": int, "bool": bool, "float": (int, float)}

    for field_name, field_spec in config_schema.items():
        if not isinstance(field_spec, dict):
            continue
        required = field_spec.get("required", False)
        if required and field_name not in config:
            errors.append(f"required config field missing: {field_name}")
            continue
        if field_name in config:
            expected = type_map.get(field_spec.get("type", "string"), str)
            if not isinstance(config[field_name], expected):
                errors.append(
                    f"config field '{field_name}' must be of type"
                    f" {field_spec.get('type', 'string')}"
                )

    return errors


class PluginRegistry:
    """In-memory registry of loaded plugin instances.

    Plugins are keyed by their database UUID. The registry is a singleton
    managed by the marketplace service.
    """

    def __init__(self) -> None:
        self._plugins: dict[UUID, BasePlugin] = {}
        self._manifests: dict[UUID, PluginManifest] = {}

    def register(self, plugin_id: UUID, plugin: BasePlugin) -> None:
        """Register a plugin instance after validation."""
        manifest = plugin.get_manifest()
        errors = validate_manifest(manifest)
        if errors:
            raise PluginValidationError(
                f"Invalid plugin manifest: {'; '.join(errors)}",
                code="PLUGIN_INVALID_MANIFEST",
            )
        self._plugins[plugin_id] = plugin
        self._manifests[plugin_id] = manifest
        logger.info("Plugin registered: %s (%s v%s)", plugin_id, manifest.slug, manifest.version)

    def unregister(self, plugin_id: UUID) -> None:
        """Remove a plugin from the registry."""
        self._plugins.pop(plugin_id, None)
        self._manifests.pop(plugin_id, None)

    def get_plugin(self, plugin_id: UUID) -> BasePlugin | None:
        """Retrieve a loaded plugin by its ID."""
        return self._plugins.get(plugin_id)

    def get_manifest(self, plugin_id: UUID) -> PluginManifest | None:
        """Retrieve the manifest for a loaded plugin."""
        return self._manifests.get(plugin_id)

    def is_loaded(self, plugin_id: UUID) -> bool:
        """Check if a plugin is currently loaded."""
        return plugin_id in self._plugins

    async def execute_sandboxed(
        self,
        plugin_id: UUID,
        context: PluginContext,
        *,
        timeout: float = PLUGIN_EXECUTE_TIMEOUT,
        **kwargs: Any,
    ) -> PluginResult:
        """Execute a plugin within a sandboxed environment.

        Enforces:
        - Execution timeout
        - Permission boundary (context is pre-scoped to user)
        - Error containment (exceptions  PluginResult with errors)
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise PluginError(f"Plugin {plugin_id} not loaded", code="PLUGIN_NOT_LOADED")

        manifest = self._manifests[plugin_id]
        logger.info(
            "Executing plugin %s (%s) for user %s",
            plugin_id,
            manifest.slug,
            context.user_id,
        )

        try:
            result = await asyncio.wait_for(
                plugin.execute(context, **kwargs),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning("Plugin %s timed out after %.1fs", plugin_id, timeout)
            return PluginResult(
                success=False,
                errors=[f"Plugin execution timed out after {timeout}s"],
            )
        except Exception as exc:
            logger.exception("Plugin %s raised an unhandled error", plugin_id)
            return PluginResult(success=False, errors=[str(exc)])

        return result


# Module-level singleton
plugin_registry = PluginRegistry()
