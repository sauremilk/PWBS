"""Plugin CLI  scaffold, validate, and package PWBS plugins (TASK-156).

Usage::

    python -m pwbs.marketplace.cli scaffold my-plugin
    python -m pwbs.marketplace.cli validate ./my-plugin
    python -m pwbs.marketplace.cli package ./my-plugin
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from textwrap import dedent
from typing import Any

import click

from pwbs.marketplace.plugin_sdk import (
    MANIFEST_JSON_SCHEMA,
    PluginType,
    validate_manifest_file,
)

# ---------------------------------------------------------------------------
# Scaffold templates
# ---------------------------------------------------------------------------

_MANIFEST_TEMPLATE: dict[str, Any] = {
    "name": "",
    "slug": "",
    "version": "0.1.0",
    "plugin_type": "connector",
    "description": "A PWBS connector plugin",
    "author": "",
    "entry_point": "plugin:create_plugin",
    "permissions": ["read_documents"],
    "config_schema": {},
    "min_pwbs_version": "0.1.0",
}

_PLUGIN_PY_TEMPLATE = dedent('''\
    """PWBS Plugin: {name}."""

    from __future__ import annotations

    from typing import Any

    from pwbs.marketplace.plugin_sdk import (
        ConnectorPlugin,
        PluginContext,
        PluginManifest,
        PluginType,
    )


    class {class_name}(ConnectorPlugin):
        """Connector plugin that ingests data from {name}."""

        def get_manifest(self) -> PluginManifest:
            return PluginManifest(
                name="{name}",
                slug="{slug}",
                version="0.1.0",
                plugin_type=PluginType.CONNECTOR,
                permissions=["read_documents"],
            )

        async def fetch_data(
            self,
            context: PluginContext,
            *,
            cursor: str | None = None,
        ) -> tuple[list[dict[str, Any]], str | None]:
            # TODO: Replace with real API integration
            raise NotImplementedError("TASK-156: Implement fetch_data for {name}")


    def create_plugin() -> {class_name}:
        """Factory function referenced by entry_point in manifest.json."""
        return {class_name}()
''')

_TEST_TEMPLATE = dedent('''\
    """Tests for {name} plugin."""

    from __future__ import annotations

    import uuid

    import pytest

    from plugin import {class_name}, create_plugin
    from pwbs.marketplace.plugin_sdk import PluginContext, PluginType


    @pytest.fixture()
    def plugin() -> {class_name}:
        return create_plugin()


    @pytest.fixture()
    def context() -> PluginContext:
        return PluginContext(
            user_id=uuid.uuid4(),
            plugin_id=uuid.uuid4(),
            config={{}},
        )


    class TestManifest:
        def test_slug(self, plugin: {class_name}) -> None:
            assert plugin.get_manifest().slug == "{slug}"

        def test_type(self, plugin: {class_name}) -> None:
            assert plugin.get_manifest().plugin_type == PluginType.CONNECTOR


    class TestFetchData:
        @pytest.mark.asyncio
        async def test_not_implemented(
            self, plugin: {class_name}, context: PluginContext
        ) -> None:
            with pytest.raises(NotImplementedError):
                await plugin.fetch_data(context)
''')

_README_TEMPLATE = dedent("""\
    # {name}

    A PWBS connector plugin.

    ## Installation

    ```bash
    pwbs plugin install ./{slug}.pwbs.zip
    ```

    ## Development

    ```bash
    pip install -e .
    pytest tests/
    ```
""")


def _slug_to_class(slug: str) -> str:
    """Convert a slug like ``my-plugin`` to ``MyPlugin``."""
    return "".join(part.capitalize() for part in slug.replace("_", "-").split("-"))


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.group("plugin")
def cli() -> None:
    """PWBS Plugin development tools."""


@cli.command()
@click.argument("name")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False),
    default=".",
    help="Parent directory for the generated plugin skeleton.",
)
@click.option(
    "--plugin-type",
    "-t",
    type=click.Choice([t.value for t in PluginType]),
    default="connector",
    help="Type of plugin to scaffold.",
)
def scaffold(name: str, output_dir: str, plugin_type: str) -> None:
    """Generate a plugin skeleton with manifest, code, and tests."""
    slug = name.lower().replace(" ", "-")
    class_name = _slug_to_class(slug)
    target = Path(output_dir) / slug

    if target.exists():
        raise click.ClickException(f"Directory {target} already exists")

    target.mkdir(parents=True)
    (target / "tests").mkdir()

    # manifest.json
    manifest = dict(_MANIFEST_TEMPLATE)
    manifest["name"] = name
    manifest["slug"] = slug
    manifest["plugin_type"] = plugin_type
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # plugin.py
    (target / "plugin.py").write_text(
        _PLUGIN_PY_TEMPLATE.format(name=name, slug=slug, class_name=class_name),
        encoding="utf-8",
    )

    # tests/test_plugin.py
    (target / "tests" / "test_plugin.py").write_text(
        _TEST_TEMPLATE.format(name=name, slug=slug, class_name=class_name),
        encoding="utf-8",
    )

    # README.md
    (target / "README.md").write_text(
        _README_TEMPLATE.format(name=name, slug=slug),
        encoding="utf-8",
    )

    click.echo(f"Plugin skeleton created at {target}/")
    click.echo("  manifest.json  – edit metadata and permissions")
    click.echo(f"  plugin.py      – implement {class_name}.fetch_data()")
    click.echo("  tests/         – add your tests here")


@cli.command()
@click.argument("plugin_dir", type=click.Path(exists=True, file_okay=False))
def validate(plugin_dir: str) -> None:
    """Validate a plugin's manifest.json."""
    manifest_path = Path(plugin_dir) / "manifest.json"
    if not manifest_path.exists():
        raise click.ClickException(f"No manifest.json found in {plugin_dir}")

    try:
        model = validate_manifest_file(manifest_path)
    except Exception as exc:
        raise click.ClickException(f"Manifest validation failed:\n{exc}") from exc

    click.echo(f"Manifest valid: {model.name} v{model.version} ({model.plugin_type.value})")

    # Check plugin.py exists
    entry_module = model.entry_point.split(":")[0]
    plugin_py = Path(plugin_dir) / f"{entry_module}.py"
    if not plugin_py.exists():
        click.echo(f"  WARNING: entry_point module '{entry_module}.py' not found", err=True)
    else:
        click.echo(f"  Entry point: {model.entry_point} -> {plugin_py.name}")


@cli.command()
@click.argument("plugin_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False),
    default=".",
    help="Directory to write the .pwbs.zip package to.",
)
def package(plugin_dir: str, output_dir: str) -> None:
    """Package a plugin directory into a .pwbs.zip archive."""
    plugin_path = Path(plugin_dir)
    manifest_path = plugin_path / "manifest.json"

    if not manifest_path.exists():
        raise click.ClickException(f"No manifest.json found in {plugin_dir}")

    model = validate_manifest_file(manifest_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{model.slug}-{model.version}.pwbs.zip"
    archive_path = out_dir / archive_name

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(plugin_path.rglob("*")):
            if file_path.is_file() and "__pycache__" not in str(file_path):
                arcname = file_path.relative_to(plugin_path)
                zf.write(file_path, arcname)

    click.echo(f"Package created: {archive_path} ({archive_path.stat().st_size} bytes)")


@cli.command("schema")
def dump_schema() -> None:
    """Print the manifest.json JSON Schema to stdout."""
    click.echo(json.dumps(MANIFEST_JSON_SCHEMA, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cli()
