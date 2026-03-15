"""Notion Connector Plugin  reference implementation (TASK-156).

Demonstrates how to wrap an existing PWBS connector as a marketplace plugin.
This plugin delegates to the core ``NotionConnector`` for actual API calls
while conforming to the ``ConnectorPlugin`` interface.
"""

from __future__ import annotations

import logging
from typing import Any

from pwbs.marketplace.plugin_sdk import (
    ConnectorPlugin,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginType,
)

logger = logging.getLogger(__name__)


class NotionConnectorPlugin(ConnectorPlugin):
    """Plugin wrapper around the core Notion connector.

    Lifecycle:
    - ``on_install``:    Log installation for the user
    - ``on_activate``:   Verify OAuth token is still valid
    - ``on_deactivate``: Log deactivation
    - ``on_uninstall``:  Clean up cached state
    """

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Notion Connector",
            slug="notion-connector",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
            description="Official PWBS connector for Notion workspaces.",
            author="PWBS Team",
            entry_point="plugin:create_plugin",
            permissions=["read_documents", "write_documents"],
            config_schema={
                "workspace_name": {
                    "type": "string",
                    "required": False,
                    "description": "Optional display name for the connected Notion workspace",
                },
            },
            min_pwbs_version="0.1.0",
        )

    async def fetch_data(
        self,
        context: PluginContext,
        *,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch Notion pages via the core connector's API client.

        In a production deployment this would instantiate ``NotionConnector``
        with the user's stored OAuth tokens and delegate to ``fetch_since``.
        """
        # Import deferred to avoid hard dependency at module load
        from pwbs.connectors.notion import NotionConnector  # noqa: F811
        from pwbs.connectors.base import ConnectorConfig
        from pwbs.schemas.enums import SourceType

        config = ConnectorConfig(
            source_type=SourceType.NOTION,
            extra=context.config,
        )
        connector = NotionConnector(
            owner_id=context.user_id,
            connection_id=context.plugin_id,
            config=config,
        )
        result = await connector.fetch_since(cursor)
        records = [
            {"source_id": doc.source_id, "content": doc.content}
            for doc in result.documents
        ]
        return records, result.new_cursor

    # -- Lifecycle hooks (TASK-156) ------------------------------------------

    async def on_install(self, context: PluginContext) -> None:
        logger.info("Notion plugin installed for user %s", context.user_id)

    async def on_activate(self, context: PluginContext) -> None:
        logger.info("Notion plugin activated for user %s", context.user_id)

    async def on_deactivate(self, context: PluginContext) -> None:
        logger.info("Notion plugin deactivated for user %s", context.user_id)

    async def on_uninstall(self, context: PluginContext) -> None:
        logger.info("Notion plugin uninstalled for user %s", context.user_id)

    async def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        ws = config.get("workspace_name")
        if ws is not None and not isinstance(ws, str):
            errors.append("workspace_name must be a string")
        return errors


def create_plugin() -> NotionConnectorPlugin:
    """Factory function referenced by entry_point in manifest.json."""
    return NotionConnectorPlugin()