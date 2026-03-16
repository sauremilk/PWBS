"""Tests for Marketplace Service - publish, install, configure plugins (TASK-151)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.core.exceptions import NotFoundError, ValidationError
from pwbs.marketplace.marketplace_service import (
    MAX_INSTALLED_PLUGINS_PER_USER,
    MarketplaceError,
    get_plugin_detail,
    install_plugin,
    list_installed_plugins,
    list_plugins,
    publish_plugin,
    review_plugin,
    toggle_plugin,
    uninstall_plugin,
    update_plugin_config,
)
from pwbs.marketplace.plugin_sdk import PluginStatus, PluginType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin_mock(**overrides: Any) -> MagicMock:
    """Create a mock Plugin ORM object."""
    plugin = MagicMock()
    plugin.id = overrides.get("id", uuid.uuid4())
    plugin.slug = overrides.get("slug", "test-plugin")
    plugin.version = overrides.get("version", "1.0.0")
    plugin.name = overrides.get("name", "Test Plugin")
    plugin.description = overrides.get("description", "A test plugin")
    plugin.plugin_type = overrides.get("plugin_type", PluginType.CONNECTOR.value)
    plugin.author_id = overrides.get("author_id", uuid.uuid4())
    plugin.status = overrides.get("status", PluginStatus.PENDING_REVIEW.value)
    plugin.is_verified = overrides.get("is_verified", False)
    plugin.install_count = overrides.get("install_count", 0)
    plugin.manifest = overrides.get("manifest", {})
    plugin.permissions = overrides.get("permissions", [])
    plugin.entry_point = overrides.get("entry_point", "mod:factory")
    plugin.published_at = overrides.get("published_at")
    plugin.icon_url = overrides.get("icon_url")
    plugin.repository_url = overrides.get("repository_url")
    return plugin


def _make_installation_mock(**overrides: Any) -> MagicMock:
    """Create a mock InstalledPlugin ORM object."""
    inst = MagicMock()
    inst.id = overrides.get("id", uuid.uuid4())
    inst.user_id = overrides.get("user_id", uuid.uuid4())
    inst.plugin_id = overrides.get("plugin_id", uuid.uuid4())
    inst.config = overrides.get("config", {})
    inst.is_enabled = overrides.get("is_enabled", True)
    inst.installed_at = overrides.get(
        "installed_at", datetime.datetime(2024, 6, 1, tzinfo=datetime.UTC),
    )
    return inst


def _make_mock_db(
    scalar_return: Any = None,
    scalars_list: list[Any] | None = None,
    get_return: Any = None,
) -> AsyncMock:
    """Create a mock AsyncSession with configurable returns."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()

    # scalar() - single value
    db.scalar = AsyncMock(return_value=scalar_return)

    # get() - ORM get by PK
    db.get = AsyncMock(return_value=get_return)

    # execute() - for UPDATE statements and select().scalars()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = scalars_list or []
    db.execute = AsyncMock(return_value=result_mock)

    return db


# ---------------------------------------------------------------------------
# publish_plugin
# ---------------------------------------------------------------------------


class TestPublishPlugin:
    @pytest.mark.asyncio
    async def test_publishes_valid_plugin(self) -> None:
        db = _make_mock_db(scalar_return=None)  # no duplicate
        author_id = uuid.uuid4()

        await publish_plugin(
            db,
            author_id=author_id,
            slug="my-plugin",
            version="1.0.0",
            name="My Plugin",
            description="A great plugin",
            plugin_type="connector",
            entry_point="mod:factory",
        )
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_invalid_plugin_type(self) -> None:
        db = _make_mock_db()
        with pytest.raises(ValidationError, match="Invalid plugin_type"):
            await publish_plugin(
                db,
                author_id=uuid.uuid4(),
                slug="x",
                version="1.0.0",
                name="X",
                description="",
                plugin_type="INVALID",
                entry_point="mod:factory",
            )

    @pytest.mark.asyncio
    async def test_rejects_duplicate_slug_version(self) -> None:
        existing = _make_plugin_mock()
        db = _make_mock_db(scalar_return=existing)
        with pytest.raises(MarketplaceError, match="already exists"):
            await publish_plugin(
                db,
                author_id=uuid.uuid4(),
                slug="test-plugin",
                version="1.0.0",
                name="Test",
                description="",
                plugin_type="connector",
                entry_point="mod:factory",
            )


# ---------------------------------------------------------------------------
# review_plugin
# ---------------------------------------------------------------------------


class TestReviewPlugin:
    @pytest.mark.asyncio
    async def test_approve_pending_plugin(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.PENDING_REVIEW.value)
        db = _make_mock_db(get_return=plugin)

        await review_plugin(
            db,
            plugin_id=plugin.id,
            new_status=PluginStatus.APPROVED.value,
        )
        assert plugin.status == PluginStatus.APPROVED.value
        assert plugin.is_verified is True
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reject_pending_plugin(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.PENDING_REVIEW.value)
        db = _make_mock_db(get_return=plugin)

        await review_plugin(
            db,
            plugin_id=plugin.id,
            new_status=PluginStatus.REJECTED.value,
        )
        assert plugin.status == PluginStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.REJECTED.value)
        db = _make_mock_db(get_return=plugin)

        with pytest.raises(ValidationError, match="Cannot transition"):
            await review_plugin(
                db,
                plugin_id=plugin.id,
                new_status=PluginStatus.APPROVED.value,
            )

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        db = _make_mock_db(get_return=None)
        with pytest.raises(NotFoundError):
            await review_plugin(
                db,
                plugin_id=uuid.uuid4(),
                new_status=PluginStatus.APPROVED.value,
            )


# ---------------------------------------------------------------------------
# list_plugins
# ---------------------------------------------------------------------------


class TestListPlugins:
    @pytest.mark.asyncio
    async def test_returns_plugins_and_total(self) -> None:
        plugins = [_make_plugin_mock(), _make_plugin_mock()]
        db = _make_mock_db(scalar_return=2, scalars_list=plugins)
        result_plugins, total = await list_plugins(db)
        assert total == 2


# ---------------------------------------------------------------------------
# get_plugin_detail
# ---------------------------------------------------------------------------


class TestGetPluginDetail:
    @pytest.mark.asyncio
    async def test_returns_plugin(self) -> None:
        plugin = _make_plugin_mock()
        db = _make_mock_db(get_return=plugin)
        result = await get_plugin_detail(db, plugin_id=plugin.id)
        assert result.id == plugin.id

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        db = _make_mock_db(get_return=None)
        with pytest.raises(NotFoundError):
            await get_plugin_detail(db, plugin_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# install_plugin
# ---------------------------------------------------------------------------


class TestInstallPlugin:
    @pytest.mark.asyncio
    async def test_installs_approved_plugin(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.APPROVED.value)
        db = _make_mock_db(get_return=plugin)
        # scalar calls: first = existing install (None), second = count (0)
        db.scalar = AsyncMock(side_effect=[None, 0])

        user_id = uuid.uuid4()
        await install_plugin(
            db, user_id=user_id, plugin_id=plugin.id,
        )
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_unapproved_plugin(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.PENDING_REVIEW.value)
        db = _make_mock_db(get_return=plugin)

        with pytest.raises(MarketplaceError, match="approved"):
            await install_plugin(
                db, user_id=uuid.uuid4(), plugin_id=plugin.id,
            )

    @pytest.mark.asyncio
    async def test_rejects_already_installed(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.APPROVED.value)
        existing_install = _make_installation_mock()
        db = _make_mock_db(get_return=plugin)
        db.scalar = AsyncMock(return_value=existing_install)

        with pytest.raises(MarketplaceError, match="already installed"):
            await install_plugin(
                db, user_id=uuid.uuid4(), plugin_id=plugin.id,
            )

    @pytest.mark.asyncio
    async def test_rejects_over_limit(self) -> None:
        plugin = _make_plugin_mock(status=PluginStatus.APPROVED.value)
        db = _make_mock_db(get_return=plugin)
        # scalar: no existing install, count at limit
        db.scalar = AsyncMock(
            side_effect=[None, MAX_INSTALLED_PLUGINS_PER_USER],
        )

        with pytest.raises(MarketplaceError, match="Maximum"):
            await install_plugin(
                db, user_id=uuid.uuid4(), plugin_id=plugin.id,
            )

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        db = _make_mock_db(get_return=None)
        with pytest.raises(NotFoundError):
            await install_plugin(
                db, user_id=uuid.uuid4(), plugin_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_validates_config_against_schema(self) -> None:
        plugin = _make_plugin_mock(
            status=PluginStatus.APPROVED.value,
            manifest={"config_schema": {"api_key": {"type": "string", "required": True}}},
        )
        db = _make_mock_db(get_return=plugin)
        db.scalar = AsyncMock(side_effect=[None, 0])

        with pytest.raises(ValidationError, match="Invalid plugin config"):
            await install_plugin(
                db, user_id=uuid.uuid4(), plugin_id=plugin.id,
                config={},  # missing required api_key
            )


# ---------------------------------------------------------------------------
# uninstall_plugin
# ---------------------------------------------------------------------------


class TestUninstallPlugin:
    @pytest.mark.asyncio
    async def test_uninstalls_existing(self) -> None:
        installation = _make_installation_mock()
        db = _make_mock_db(scalar_return=installation)

        await uninstall_plugin(
            db, user_id=installation.user_id, plugin_id=installation.plugin_id,
        )
        db.delete.assert_awaited_once()
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_installed_raises(self) -> None:
        db = _make_mock_db(scalar_return=None)
        with pytest.raises(NotFoundError, match="not installed"):
            await uninstall_plugin(
                db, user_id=uuid.uuid4(), plugin_id=uuid.uuid4(),
            )


# ---------------------------------------------------------------------------
# update_plugin_config
# ---------------------------------------------------------------------------


class TestUpdatePluginConfig:
    @pytest.mark.asyncio
    async def test_updates_config(self) -> None:
        installation = _make_installation_mock()
        plugin = _make_plugin_mock(manifest={})
        db = _make_mock_db(scalar_return=installation, get_return=plugin)

        await update_plugin_config(
            db,
            user_id=installation.user_id,
            plugin_id=installation.plugin_id,
            config={"new_key": "new_val"},
        )
        assert installation.config == {"new_key": "new_val"}
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_installed_raises(self) -> None:
        db = _make_mock_db(scalar_return=None)
        with pytest.raises(NotFoundError):
            await update_plugin_config(
                db,
                user_id=uuid.uuid4(),
                plugin_id=uuid.uuid4(),
                config={"k": "v"},
            )

    @pytest.mark.asyncio
    async def test_validates_config_against_schema(self) -> None:
        installation = _make_installation_mock()
        plugin = _make_plugin_mock(
            manifest={"config_schema": {"url": {"type": "string", "required": True}}},
        )
        db = _make_mock_db(scalar_return=installation, get_return=plugin)

        with pytest.raises(ValidationError, match="Invalid plugin config"):
            await update_plugin_config(
                db,
                user_id=installation.user_id,
                plugin_id=installation.plugin_id,
                config={},  # missing required url
            )


# ---------------------------------------------------------------------------
# toggle_plugin
# ---------------------------------------------------------------------------


class TestTogglePlugin:
    @pytest.mark.asyncio
    async def test_disable_plugin(self) -> None:
        installation = _make_installation_mock(is_enabled=True)
        db = _make_mock_db(scalar_return=installation)

        await toggle_plugin(
            db,
            user_id=installation.user_id,
            plugin_id=installation.plugin_id,
            enabled=False,
        )
        assert installation.is_enabled is False
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_enable_plugin(self) -> None:
        installation = _make_installation_mock(is_enabled=False)
        db = _make_mock_db(scalar_return=installation)

        await toggle_plugin(
            db,
            user_id=installation.user_id,
            plugin_id=installation.plugin_id,
            enabled=True,
        )
        assert installation.is_enabled is True

    @pytest.mark.asyncio
    async def test_not_installed_raises(self) -> None:
        db = _make_mock_db(scalar_return=None)
        with pytest.raises(NotFoundError):
            await toggle_plugin(
                db,
                user_id=uuid.uuid4(),
                plugin_id=uuid.uuid4(),
                enabled=False,
            )


# ---------------------------------------------------------------------------
# list_installed_plugins
# ---------------------------------------------------------------------------


class TestListInstalledPlugins:
    @pytest.mark.asyncio
    async def test_returns_user_installations(self) -> None:
        user_id = uuid.uuid4()
        installs = [
            _make_installation_mock(user_id=user_id),
            _make_installation_mock(user_id=user_id),
        ]
        db = _make_mock_db(scalars_list=installs)

        result = await list_installed_plugins(db, user_id=user_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_list_for_new_user(self) -> None:
        db = _make_mock_db(scalars_list=[])
        result = await list_installed_plugins(db, user_id=uuid.uuid4())
        assert result == []
