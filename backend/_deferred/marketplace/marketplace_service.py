"""Marketplace service  browse, install, configure plugins (TASK-151).

Business logic for the plugin marketplace. Handles:
- Publishing new plugins (with review workflow)
- Browsing and searching the marketplace catalogue
- Installing / uninstalling plugins for a user
- Updating plugin configuration
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.exceptions import NotFoundError, PWBSError, ValidationError
from pwbs.marketplace.plugin_registry import (
    PluginError,
    validate_plugin_config,
)
from pwbs.marketplace.plugin_sdk import PluginStatus, PluginType
from pwbs.models.plugin import InstalledPlugin, Plugin

logger = logging.getLogger(__name__)

MAX_INSTALLED_PLUGINS_PER_USER = 50


class MarketplaceError(PWBSError):
    """Raised when a marketplace operation fails."""


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------


async def publish_plugin(
    db: AsyncSession,
    *,
    author_id: UUID,
    slug: str,
    version: str,
    name: str,
    description: str,
    plugin_type: str,
    entry_point: str,
    manifest: dict[str, Any] | None = None,
    permissions: list[str] | None = None,
    icon_url: str | None = None,
    repository_url: str | None = None,
) -> Plugin:
    """Submit a new plugin for review."""
    if plugin_type not in {t.value for t in PluginType}:
        raise ValidationError(
            f"Invalid plugin_type: {plugin_type}",
            code="INVALID_PLUGIN_TYPE",
        )

    # Check for duplicate slug+version
    existing = await db.scalar(
        select(Plugin).where(Plugin.slug == slug, Plugin.version == version)
    )
    if existing is not None:
        raise MarketplaceError(
            f"Plugin {slug} v{version} already exists",
            code="PLUGIN_ALREADY_EXISTS",
        )

    plugin = Plugin(
        slug=slug,
        version=version,
        name=name,
        description=description,
        plugin_type=plugin_type,
        author_id=author_id,
        entry_point=entry_point,
        manifest=manifest or {},
        permissions=permissions or [],
        status=PluginStatus.PENDING_REVIEW.value,
        icon_url=icon_url,
        repository_url=repository_url,
    )
    db.add(plugin)
    await db.flush()
    logger.info("Plugin %s (%s v%s) submitted for review", plugin.id, slug, version)
    return plugin


# ---------------------------------------------------------------------------
# Review (admin)
# ---------------------------------------------------------------------------


async def review_plugin(
    db: AsyncSession,
    *,
    plugin_id: UUID,
    new_status: str,
    reviewer_notes: str | None = None,
) -> Plugin:
    """Approve or reject a plugin (admin only)."""
    plugin = await db.get(Plugin, plugin_id)
    if plugin is None:
        raise NotFoundError(f"Plugin {plugin_id} not found", code="PLUGIN_NOT_FOUND")

    valid_transitions = {
        PluginStatus.PENDING_REVIEW.value: {PluginStatus.APPROVED.value, PluginStatus.REJECTED.value},
        PluginStatus.APPROVED.value: {PluginStatus.SUSPENDED.value},
        PluginStatus.REJECTED.value: {PluginStatus.PENDING_REVIEW.value},
        PluginStatus.SUSPENDED.value: {PluginStatus.APPROVED.value},
    }
    allowed = valid_transitions.get(plugin.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition from {plugin.status} to {new_status}",
            code="INVALID_STATUS_TRANSITION",
        )

    plugin.status = new_status
    if new_status == PluginStatus.APPROVED.value and plugin.published_at is None:
        plugin.published_at = datetime.now(timezone.utc)
    if new_status == PluginStatus.APPROVED.value:
        plugin.is_verified = True

    await db.flush()
    logger.info("Plugin %s status changed to %s", plugin_id, new_status)
    return plugin


# ---------------------------------------------------------------------------
# Browse / Search
# ---------------------------------------------------------------------------


async def list_plugins(
    db: AsyncSession,
    *,
    plugin_type: str | None = None,
    search_query: str | None = None,
    status_filter: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Plugin], int]:
    """List marketplace plugins with optional filters."""
    query = select(Plugin)
    count_query = select(func.count()).select_from(Plugin)

    # Default: only show approved plugins to non-admins
    if status_filter:
        query = query.where(Plugin.status == status_filter)
        count_query = count_query.where(Plugin.status == status_filter)
    else:
        query = query.where(Plugin.status == PluginStatus.APPROVED.value)
        count_query = count_query.where(Plugin.status == PluginStatus.APPROVED.value)

    if plugin_type:
        query = query.where(Plugin.plugin_type == plugin_type)
        count_query = count_query.where(Plugin.plugin_type == plugin_type)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.where(
            Plugin.name.ilike(pattern) | Plugin.description.ilike(pattern)
        )
        count_query = count_query.where(
            Plugin.name.ilike(pattern) | Plugin.description.ilike(pattern)
        )

    total = await db.scalar(count_query) or 0
    query = query.order_by(Plugin.install_count.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    plugins = list(result.scalars().all())

    return plugins, total


async def get_plugin_detail(db: AsyncSession, *, plugin_id: UUID) -> Plugin:
    """Get detailed information about a single plugin."""
    plugin = await db.get(Plugin, plugin_id)
    if plugin is None:
        raise NotFoundError(f"Plugin {plugin_id} not found", code="PLUGIN_NOT_FOUND")
    return plugin


# ---------------------------------------------------------------------------
# Install / Uninstall
# ---------------------------------------------------------------------------


async def install_plugin(
    db: AsyncSession,
    *,
    user_id: UUID,
    plugin_id: UUID,
    config: dict[str, Any] | None = None,
) -> InstalledPlugin:
    """Install a plugin for a user."""
    plugin = await db.get(Plugin, plugin_id)
    if plugin is None:
        raise NotFoundError(f"Plugin {plugin_id} not found", code="PLUGIN_NOT_FOUND")
    if plugin.status != PluginStatus.APPROVED.value:
        raise MarketplaceError(
            "Only approved plugins can be installed",
            code="PLUGIN_NOT_APPROVED",
        )

    # Check if already installed
    existing = await db.scalar(
        select(InstalledPlugin).where(
            InstalledPlugin.user_id == user_id,
            InstalledPlugin.plugin_id == plugin_id,
        )
    )
    if existing is not None:
        raise MarketplaceError("Plugin already installed", code="PLUGIN_ALREADY_INSTALLED")

    # Check install limit
    count = await db.scalar(
        select(func.count()).select_from(InstalledPlugin).where(
            InstalledPlugin.user_id == user_id
        )
    ) or 0
    if count >= MAX_INSTALLED_PLUGINS_PER_USER:
        raise MarketplaceError(
            f"Maximum {MAX_INSTALLED_PLUGINS_PER_USER} plugins per user",
            code="PLUGIN_LIMIT_REACHED",
        )

    # Validate config if schema is provided
    user_config = config or {}
    config_schema = plugin.manifest.get("config_schema", {})
    if config_schema:
        errors = validate_plugin_config(user_config, config_schema)
        if errors:
            raise ValidationError(
                f"Invalid plugin config: {'; '.join(errors)}",
                code="INVALID_PLUGIN_CONFIG",
            )

    installation = InstalledPlugin(
        user_id=user_id,
        plugin_id=plugin_id,
        config=user_config,
    )
    db.add(installation)

    # Increment install count
    await db.execute(
        update(Plugin)
        .where(Plugin.id == plugin_id)
        .values(install_count=Plugin.install_count + 1)
    )

    await db.flush()
    logger.info("User %s installed plugin %s", user_id, plugin_id)
    return installation


async def uninstall_plugin(
    db: AsyncSession,
    *,
    user_id: UUID,
    plugin_id: UUID,
) -> None:
    """Uninstall a plugin for a user."""
    installation = await db.scalar(
        select(InstalledPlugin).where(
            InstalledPlugin.user_id == user_id,
            InstalledPlugin.plugin_id == plugin_id,
        )
    )
    if installation is None:
        raise NotFoundError("Plugin not installed", code="PLUGIN_NOT_INSTALLED")

    await db.delete(installation)

    # Decrement install count (floor at 0)
    await db.execute(
        update(Plugin)
        .where(Plugin.id == plugin_id, Plugin.install_count > 0)
        .values(install_count=Plugin.install_count - 1)
    )

    await db.flush()
    logger.info("User %s uninstalled plugin %s", user_id, plugin_id)


# ---------------------------------------------------------------------------
# Configure
# ---------------------------------------------------------------------------


async def update_plugin_config(
    db: AsyncSession,
    *,
    user_id: UUID,
    plugin_id: UUID,
    config: dict[str, Any],
) -> InstalledPlugin:
    """Update configuration for an installed plugin."""
    installation = await db.scalar(
        select(InstalledPlugin).where(
            InstalledPlugin.user_id == user_id,
            InstalledPlugin.plugin_id == plugin_id,
        )
    )
    if installation is None:
        raise NotFoundError("Plugin not installed", code="PLUGIN_NOT_INSTALLED")

    # Validate against plugin's config schema
    plugin = await db.get(Plugin, plugin_id)
    if plugin is not None:
        config_schema = plugin.manifest.get("config_schema", {})
        if config_schema:
            errors = validate_plugin_config(config, config_schema)
            if errors:
                raise ValidationError(
                    f"Invalid plugin config: {'; '.join(errors)}",
                    code="INVALID_PLUGIN_CONFIG",
                )

    installation.config = config
    await db.flush()
    logger.info("User %s updated config for plugin %s", user_id, plugin_id)
    return installation


async def toggle_plugin(
    db: AsyncSession,
    *,
    user_id: UUID,
    plugin_id: UUID,
    enabled: bool,
) -> InstalledPlugin:
    """Enable or disable an installed plugin."""
    installation = await db.scalar(
        select(InstalledPlugin).where(
            InstalledPlugin.user_id == user_id,
            InstalledPlugin.plugin_id == plugin_id,
        )
    )
    if installation is None:
        raise NotFoundError("Plugin not installed", code="PLUGIN_NOT_INSTALLED")

    installation.is_enabled = enabled
    await db.flush()
    logger.info("User %s %s plugin %s", user_id, "enabled" if enabled else "disabled", plugin_id)
    return installation


async def list_installed_plugins(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> list[InstalledPlugin]:
    """List all plugins installed by a user."""
    result = await db.execute(
        select(InstalledPlugin)
        .where(InstalledPlugin.user_id == user_id)
        .order_by(InstalledPlugin.installed_at.desc())
    )
    return list(result.scalars().all())
