"""Tests for TASK-156: Plugin SDK extensions (lifecycle hooks, manifest schema, CLI)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from pwbs.marketplace.cli import cli
from pwbs.marketplace.plugin_sdk import (
    MANIFEST_JSON_SCHEMA,
    ConnectorPlugin,
    PluginContext,
    PluginManifest,
    PluginManifestModel,
    PluginType,
    validate_manifest_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**overrides: Any) -> PluginContext:
    defaults: dict[str, Any] = {
        "user_id": uuid.uuid4(),
        "plugin_id": uuid.uuid4(),
        "config": {},
    }
    defaults.update(overrides)
    return PluginContext(**defaults)


class _LifecycleTracker(ConnectorPlugin):
    """Concrete plugin that records lifecycle calls."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Tracker",
            slug="tracker",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
        )

    async def fetch_data(
        self,
        context: PluginContext,
        *,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        return [], None

    async def on_install(self, context: PluginContext) -> None:
        self.calls.append("install")

    async def on_activate(self, context: PluginContext) -> None:
        self.calls.append("activate")

    async def on_deactivate(self, context: PluginContext) -> None:
        self.calls.append("deactivate")

    async def on_uninstall(self, context: PluginContext) -> None:
        self.calls.append("uninstall")


# ---------------------------------------------------------------------------
# Lifecycle hooks (AC-1)
# ---------------------------------------------------------------------------


class TestLifecycleHooks:
    @pytest.mark.asyncio
    async def test_full_lifecycle_order(self) -> None:
        plugin = _LifecycleTracker()
        ctx = _make_context()
        await plugin.on_install(ctx)
        await plugin.on_activate(ctx)
        await plugin.on_deactivate(ctx)
        await plugin.on_uninstall(ctx)
        assert plugin.calls == ["install", "activate", "deactivate", "uninstall"]

    @pytest.mark.asyncio
    async def test_default_activate_is_noop(self) -> None:
        """Base class activate/deactivate should not raise."""

        class Minimal(ConnectorPlugin):
            def get_manifest(self) -> PluginManifest:
                return PluginManifest(
                    name="M", slug="m", version="0.1.0",
                    plugin_type=PluginType.CONNECTOR,
                )

            async def fetch_data(
                self, context: PluginContext, *, cursor: str | None = None,
            ) -> tuple[list[dict[str, Any]], str | None]:
                return [], None

        p = Minimal()
        ctx = _make_context()
        await p.on_activate(ctx)  # should not raise
        await p.on_deactivate(ctx)  # should not raise


# ---------------------------------------------------------------------------
# Manifest JSON Schema (AC-2)
# ---------------------------------------------------------------------------


class TestManifestJsonSchema:
    def test_schema_has_required_fields(self) -> None:
        required = MANIFEST_JSON_SCHEMA["required"]
        for field in ["name", "version", "entry_point", "min_pwbs_version", "plugin_type"]:
            assert field in required

    def test_schema_has_plugin_type_enum(self) -> None:
        pt = MANIFEST_JSON_SCHEMA["properties"]["plugin_type"]
        assert "enum" in pt
        assert "connector" in pt["enum"]

    def test_schema_disallows_additional_properties(self) -> None:
        assert MANIFEST_JSON_SCHEMA.get("additionalProperties") is False


class TestPluginManifestModel:
    def test_valid_manifest(self) -> None:
        m = PluginManifestModel(
            name="Test",
            slug="test-plugin",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
            entry_point="plugin:create_plugin",
            min_pwbs_version="0.1.0",
        )
        assert m.slug == "test-plugin"

    def test_invalid_slug_rejected(self) -> None:
        with pytest.raises(ValidationError, match="slug"):
            PluginManifestModel(
                name="Bad",
                slug="",
                version="1.0.0",
                plugin_type=PluginType.CONNECTOR,
            )

    def test_invalid_entry_point_rejected(self) -> None:
        with pytest.raises(ValidationError, match="entry_point"):
            PluginManifestModel(
                name="Bad",
                slug="ok",
                version="1.0.0",
                plugin_type=PluginType.CONNECTOR,
                entry_point="no_colon_here",
            )

    def test_invalid_permissions_rejected(self) -> None:
        with pytest.raises(ValidationError, match="permissions"):
            PluginManifestModel(
                name="Bad",
                slug="ok",
                version="1.0.0",
                plugin_type=PluginType.CONNECTOR,
                permissions=["nonexistent_perm"],
            )

    def test_to_dataclass(self) -> None:
        m = PluginManifestModel(
            name="X",
            slug="x",
            version="2.0.0",
            plugin_type=PluginType.BRIEFING_TEMPLATE,
        )
        dc = m.to_dataclass()
        assert isinstance(dc, PluginManifest)
        assert dc.name == "X"
        assert dc.plugin_type == PluginType.BRIEFING_TEMPLATE


class TestValidateManifestFile:
    def test_valid_file(self, tmp_path: Path) -> None:
        manifest = {
            "name": "Test Plugin",
            "slug": "test-plugin",
            "version": "1.0.0",
            "plugin_type": "connector",
            "entry_point": "plugin:create_plugin",
            "min_pwbs_version": "0.1.0",
            "permissions": [],
            "config_schema": {},
        }
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(manifest), encoding="utf-8")
        result = validate_manifest_file(p)
        assert result.name == "Test Plugin"

    def test_invalid_file_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps({"name": "X"}), encoding="utf-8")
        with pytest.raises(ValidationError):
            validate_manifest_file(p)


# ---------------------------------------------------------------------------
# CLI: scaffold (AC-3)
# ---------------------------------------------------------------------------


class TestCLIScaffold:
    def test_scaffold_creates_files(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["scaffold", "my-test-plugin", "-o", str(tmp_path)])
        assert result.exit_code == 0, result.output
        plugin_dir = tmp_path / "my-test-plugin"
        assert (plugin_dir / "manifest.json").exists()
        assert (plugin_dir / "plugin.py").exists()
        assert (plugin_dir / "tests" / "test_plugin.py").exists()
        assert (plugin_dir / "README.md").exists()

    def test_scaffold_manifest_is_valid(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["scaffold", "valid-plugin", "-o", str(tmp_path)])
        manifest = validate_manifest_file(tmp_path / "valid-plugin" / "manifest.json")
        assert manifest.slug == "valid-plugin"

    def test_scaffold_rejects_existing_dir(self, tmp_path: Path) -> None:
        (tmp_path / "existing").mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, ["scaffold", "existing", "-o", str(tmp_path)])
        assert result.exit_code != 0
        assert "already exists" in result.output


# ---------------------------------------------------------------------------
# CLI: validate
# ---------------------------------------------------------------------------


class TestCLIValidate:
    def test_validate_valid_plugin(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["scaffold", "vp", "-o", str(tmp_path)])
        result = runner.invoke(cli, ["validate", str(tmp_path / "vp")])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_missing_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", str(tmp_path / "empty")])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI: package
# ---------------------------------------------------------------------------


class TestCLIPackage:
    def test_package_creates_zip(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["scaffold", "pkg-test", "-o", str(tmp_path)])
        out_dir = tmp_path / "dist"
        result = runner.invoke(
            cli,
            ["package", str(tmp_path / "pkg-test"), "-o", str(out_dir)],
        )
        assert result.exit_code == 0, result.output
        zips = list(out_dir.glob("*.pwbs.zip"))
        assert len(zips) == 1
        assert "pkg-test" in zips[0].name


# ---------------------------------------------------------------------------
# CLI: schema
# ---------------------------------------------------------------------------


class TestCLISchema:
    def test_schema_outputs_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["schema"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["title"] == "PWBS Plugin Manifest"


# ---------------------------------------------------------------------------
# Reference plugin (AC-4)
# ---------------------------------------------------------------------------


class TestReferencePlugin:
    def test_notion_manifest_is_valid(self) -> None:
        manifest_path = (
            Path(__file__).resolve().parents[2]
            / "pwbs"
            / "marketplace"
            / "examples"
            / "notion_plugin"
            / "manifest.json"
        )
        if not manifest_path.exists():
            pytest.skip("Reference plugin not found")
        model = validate_manifest_file(manifest_path)
        assert model.slug == "notion-connector"
        assert model.plugin_type == PluginType.CONNECTOR

    def test_notion_plugin_instantiates(self) -> None:
        from pwbs.marketplace.examples.notion_plugin.plugin import create_plugin

        plugin = create_plugin()
        manifest = plugin.get_manifest()
        assert manifest.slug == "notion-connector"
        assert manifest.version == "1.0.0"