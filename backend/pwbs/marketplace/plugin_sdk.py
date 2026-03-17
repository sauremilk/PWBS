"""Plugin SDK  base classes for community plugin development (TASK-151, TASK-156).

External developers subclass these bases to create PWBS plugins:

- ``ConnectorPlugin``  Ingest data from a new source
- ``BriefingTemplatePlugin``  Generate a new briefing type
- ``ProcessingPlugin``  Add a custom processing step

Each plugin declares its manifest (metadata, permissions, config schema)
and is executed in a sandboxed context with restricted I/O.

TASK-156 additions:
- Lifecycle hooks: ``on_activate`` / ``on_deactivate``
- ``MANIFEST_JSON_SCHEMA`` for JSON-Schema-based manifest validation
- ``PluginManifestModel`` Pydantic v2 model for strict manifest validation
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Enums & value objects
# ---------------------------------------------------------------------------


class PluginType(str, Enum):
    CONNECTOR = "connector"
    BRIEFING_TEMPLATE = "briefing_template"
    PROCESSING = "processing"


class PluginStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


VALID_PERMISSIONS = frozenset(
    {
        "read_documents",
        "write_documents",
        "read_entities",
        "read_briefings",
        "write_briefings",
        "search",
        "network_outbound",
    }
)


@dataclass(frozen=True)
class PluginManifest:
    """Metadata + requirements declared by a plugin."""

    name: str
    slug: str
    version: str
    plugin_type: PluginType
    description: str = ""
    author: str = ""
    entry_point: str = "plugin:create_plugin"
    permissions: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    min_pwbs_version: str = "0.1.0"


@dataclass
class PluginContext:
    """Runtime context injected into plugin execute() calls.

    Restricts what the plugin can access to only the owning user's data.
    """

    user_id: UUID
    plugin_id: UUID
    config: dict[str, Any]
    # Sandboxed service accessors (set by the registry at load time)
    search: Any = None
    storage: Any = None


@dataclass
class PluginResult:
    """Standardised return value from plugin execution."""

    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class BasePlugin(abc.ABC):
    """Root base class all PWBS plugins must inherit from."""

    @abc.abstractmethod
    def get_manifest(self) -> PluginManifest:
        """Return the plugin manifest describing capabilities."""

    @abc.abstractmethod
    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        """Run the plugin's main logic within a sandboxed context."""

    async def on_install(self, context: PluginContext) -> None:
        """Hook called once when a user installs the plugin."""

    async def on_activate(self, context: PluginContext) -> None:
        """Hook called when the plugin is activated (enabled) for a user."""

    async def on_deactivate(self, context: PluginContext) -> None:
        """Hook called when the plugin is deactivated (disabled) for a user."""

    async def on_uninstall(self, context: PluginContext) -> None:
        """Hook called when a user uninstalls the plugin."""

    async def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Return a list of validation error messages (empty = valid)."""
        return []


class ConnectorPlugin(BasePlugin):
    """Base class for connector plugins that ingest external data."""

    @abc.abstractmethod
    async def fetch_data(
        self, context: PluginContext, *, cursor: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch a batch of raw records and return (records, next_cursor).

        Must support cursor-based pagination for idempotent re-runs.
        """

    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        cursor = kwargs.get("cursor")
        try:
            records, next_cursor = await self.fetch_data(context, cursor=cursor)
            return PluginResult(
                success=True,
                data={"records": records, "next_cursor": next_cursor},
            )
        except Exception as exc:
            return PluginResult(success=False, errors=[str(exc)])


class BriefingTemplatePlugin(BasePlugin):
    """Base class for custom briefing generation plugins."""

    @abc.abstractmethod
    async def generate_briefing(
        self,
        context: PluginContext,
        *,
        search_results: list[dict[str, Any]],
        graph_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a briefing dict with keys: title, content, source_refs."""

    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        search_results = kwargs.get("search_results", [])
        graph_context = kwargs.get("graph_context")
        try:
            briefing = await self.generate_briefing(
                context, search_results=search_results, graph_context=graph_context,
            )
            return PluginResult(
                success=True,
                data=briefing,
                source_refs=briefing.get("source_refs", []),
            )
        except Exception as exc:
            return PluginResult(success=False, errors=[str(exc)])


class ProcessingPlugin(BasePlugin):
    """Base class for custom document processing step plugins."""

    @abc.abstractmethod
    async def process_documents(
        self,
        context: PluginContext,
        *,
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Process a list of document dicts and return enriched versions."""

    async def execute(self, context: PluginContext, **kwargs: Any) -> PluginResult:
        documents = kwargs.get("documents", [])
        try:
            processed = await self.process_documents(context, documents=documents)
            return PluginResult(success=True, data={"documents": processed})
        except Exception as exc:
            return PluginResult(success=False, errors=[str(exc)])


# ---------------------------------------------------------------------------
# JSON Schema for manifest.json (TASK-156)
# ---------------------------------------------------------------------------

MANIFEST_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PWBS Plugin Manifest",
    "type": "object",
    "required": ["name", "slug", "version", "plugin_type", "entry_point", "min_pwbs_version"],
    "properties": {
        "name": {"type": "string", "minLength": 1, "description": "Human-readable plugin name"},
        "slug": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9_-]*$",
            "description": "URL-safe unique identifier",
        },
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+",
            "description": "SemVer version string",
        },
        "plugin_type": {
            "type": "string",
            "enum": [t.value for t in PluginType],
        },
        "description": {"type": "string", "default": ""},
        "author": {"type": "string", "default": ""},
        "entry_point": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_.]+:[a-zA-Z0-9_]+$",
            "description": "module:factory format",
        },
        "permissions": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(VALID_PERMISSIONS)},
            "uniqueItems": True,
            "default": [],
        },
        "config_schema": {"type": "object", "default": {}},
        "min_pwbs_version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+",
            "default": "0.1.0",
        },
    },
    "additionalProperties": False,
}


class PluginManifestModel(BaseModel):
    """Pydantic v2 model for strict manifest.json validation (TASK-156).

    Use this instead of the dataclass ``PluginManifest`` when validating
    untrusted manifest files from third-party plugin packages.
    """

    name: str
    slug: str
    version: str
    plugin_type: PluginType
    description: str = ""
    author: str = ""
    entry_point: str = "plugin:create_plugin"
    permissions: list[str] = []
    config_schema: dict[str, Any] = {}
    min_pwbs_version: str = "0.1.0"

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, v: str) -> str:
        if not v or not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("slug must be non-empty alphanumeric (hyphens/underscores allowed)")
        return v

    @field_validator("entry_point")
    @classmethod
    def _validate_entry_point(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("entry_point must be in 'module:factory' format")
        return v

    @field_validator("permissions")
    @classmethod
    def _validate_permissions(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_PERMISSIONS
        if invalid:
            raise ValueError(f"invalid permissions: {sorted(invalid)}")
        return v

    def to_dataclass(self) -> PluginManifest:
        """Convert to the internal ``PluginManifest`` dataclass."""
        return PluginManifest(
            name=self.name,
            slug=self.slug,
            version=self.version,
            plugin_type=self.plugin_type,
            description=self.description,
            author=self.author,
            entry_point=self.entry_point,
            permissions=self.permissions,
            config_schema=self.config_schema,
            min_pwbs_version=self.min_pwbs_version,
        )


def validate_manifest_file(path: Path) -> PluginManifestModel:
    """Load and validate a ``manifest.json`` from disk.

    Raises ``pydantic.ValidationError`` on invalid manifests.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PluginManifestModel.model_validate(raw)
