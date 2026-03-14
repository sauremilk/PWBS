"""Tests for Obsidian Vault connector — File-System-Watcher (TASK-051)."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pytest

from pwbs.connectors.base import ConnectorConfig
from pwbs.connectors.obsidian import (
    FileEvent,
    ObsidianConnector,
    ObsidianFileHandler,
    ObsidianWatcher,
    _EXCLUDE_DIRS,
    _file_to_raw,
    _is_excluded,
    scan_vault_files,
    validate_vault_path,
)
from pwbs.core.exceptions import ConnectorError
from pwbs.schemas.enums import SourceType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_connector(vault_path: str = "/tmp/test-vault") -> ObsidianConnector:
    return ObsidianConnector(
        owner_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        config=ConnectorConfig(
            source_type=SourceType.OBSIDIAN,
            extra={"vault_path": vault_path},
        ),
    )


def _create_vault(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    """Create a temporary vault structure with .md files."""
    vault = tmp_path / "test-vault"
    vault.mkdir()
    if files is None:
        files = {
            "note1.md": "# Note 1\nHello world",
            "note2.md": "# Note 2\nAnother note",
            "subfolder/deep.md": "# Deep note",
        }
    for rel_path, content in files.items():
        p = vault / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return vault


# ---------------------------------------------------------------------------
# validate_vault_path
# ---------------------------------------------------------------------------


class TestValidateVaultPath:
    def test_valid_vault(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        valid, error = validate_vault_path(str(vault))
        assert valid is True
        assert error == ""

    def test_nonexistent_path(self) -> None:
        valid, error = validate_vault_path("/nonexistent/path/xyz")
        assert valid is False
        assert "existiert nicht" in error

    def test_file_not_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")
        valid, error = validate_vault_path(str(f))
        assert valid is False
        assert "kein Verzeichnis" in error

    def test_empty_directory(self, tmp_path: Path) -> None:
        vault = tmp_path / "empty-vault"
        vault.mkdir()
        valid, error = validate_vault_path(str(vault))
        assert valid is False
        assert "keine .md-Dateien" in error

    def test_only_excluded_md_files(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        obsidian_dir = vault / ".obsidian"
        obsidian_dir.mkdir()
        (obsidian_dir / "config.md").write_text("config")
        valid, error = validate_vault_path(str(vault))
        assert valid is False
        assert "keine .md-Dateien" in error


# ---------------------------------------------------------------------------
# _is_excluded
# ---------------------------------------------------------------------------


class TestIsExcluded:
    def test_obsidian_dir_excluded(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        path = vault / ".obsidian" / "config.md"
        assert _is_excluded(path, vault) is True

    def test_git_dir_excluded(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        path = vault / ".git" / "README.md"
        assert _is_excluded(path, vault) is True

    def test_trash_dir_excluded(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        path = vault / ".trash" / "deleted.md"
        assert _is_excluded(path, vault) is True

    def test_normal_file_not_excluded(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        path = vault / "notes" / "hello.md"
        assert _is_excluded(path, vault) is False

    def test_root_file_not_excluded(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        path = vault / "README.md"
        assert _is_excluded(path, vault) is False

    def test_outside_vault_excluded(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        path = tmp_path / "other" / "file.md"
        assert _is_excluded(path, vault) is True

    def test_all_exclude_dirs_defined(self) -> None:
        assert ".obsidian" in _EXCLUDE_DIRS
        assert ".git" in _EXCLUDE_DIRS
        assert ".trash" in _EXCLUDE_DIRS


# ---------------------------------------------------------------------------
# scan_vault_files
# ---------------------------------------------------------------------------


class TestScanVaultFiles:
    def test_finds_all_md_files(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        files = scan_vault_files(vault)
        names = {f.name for f in files}
        assert names == {"note1.md", "note2.md", "deep.md"}

    def test_excludes_obsidian_dir(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        obsidian = vault / ".obsidian"
        obsidian.mkdir()
        (obsidian / "config.md").write_text("config")
        files = scan_vault_files(vault)
        names = {f.name for f in files}
        assert "config.md" not in names

    def test_excludes_git_dir(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        git_dir = vault / ".git"
        git_dir.mkdir()
        (git_dir / "readme.md").write_text("git")
        files = scan_vault_files(vault)
        for f in files:
            assert ".git" not in f.parts

    def test_empty_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "empty"
        vault.mkdir()
        files = scan_vault_files(vault)
        assert files == []

    def test_sorted_output(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path, {
            "z_note.md": "z",
            "a_note.md": "a",
            "m_note.md": "m",
        })
        files = scan_vault_files(vault)
        names = [f.name for f in files]
        assert names == sorted(names)

    def test_skips_non_md_files(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path, {"note.md": "md", "image.png": "png"})
        files = scan_vault_files(vault)
        assert len(files) == 1
        assert files[0].name == "note.md"


# ---------------------------------------------------------------------------
# _file_to_raw
# ---------------------------------------------------------------------------


class TestFileToRaw:
    def test_basic_file(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path, {"hello.md": "# Hello\nWorld"})
        file_path = vault / "hello.md"
        raw = _file_to_raw(file_path, vault)
        assert raw["relative_path"] == "hello.md"
        assert raw["content"] == "# Hello\nWorld"
        assert raw["filename"] == "hello"
        assert isinstance(raw["size_bytes"], int)
        assert raw["size_bytes"] > 0

    def test_nested_file_uses_forward_slashes(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path, {"sub/folder/note.md": "content"})
        file_path = vault / "sub" / "folder" / "note.md"
        raw = _file_to_raw(file_path, vault)
        assert raw["relative_path"] == "sub/folder/note.md"
        assert "/" in raw["relative_path"]
        assert "\\" not in raw["relative_path"]

    def test_timestamps_are_iso_strings(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path, {"dated.md": "content"})
        file_path = vault / "dated.md"
        raw = _file_to_raw(file_path, vault)
        assert isinstance(raw["modified_at"], str)
        assert isinstance(raw["created_at"], str)
        assert "T" in str(raw["modified_at"])  # ISO format


# ---------------------------------------------------------------------------
# FileEvent
# ---------------------------------------------------------------------------


class TestFileEvent:
    def test_defaults(self) -> None:
        fe = FileEvent(path="notes/test.md", event_type="created")
        assert fe.path == "notes/test.md"
        assert fe.event_type == "created"
        assert fe.timestamp is not None

    def test_all_event_types(self) -> None:
        for et in ("created", "modified", "deleted"):
            fe = FileEvent(path="test.md", event_type=et)
            assert fe.event_type == et


# ---------------------------------------------------------------------------
# ObsidianFileHandler
# ---------------------------------------------------------------------------


class TestObsidianFileHandler:
    def test_handles_md_creation(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "note.md")

        handler.on_created(FakeEvent())  # type: ignore[arg-type]
        events = handler.drain_events()
        assert len(events) == 1
        assert events[0].event_type == "created"
        assert events[0].path == "note.md"

    def test_ignores_non_md_files(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "image.png")

        handler.on_created(FakeEvent())  # type: ignore[arg-type]
        assert handler.drain_events() == []

    def test_ignores_directories(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = True
            src_path = str(tmp_path / "subdir")

        handler.on_created(FakeEvent())  # type: ignore[arg-type]
        assert handler.drain_events() == []

    def test_ignores_excluded_dirs(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / ".obsidian" / "config.md")

        handler.on_created(FakeEvent())  # type: ignore[arg-type]
        assert handler.drain_events() == []

    def test_handles_modification(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "note.md")

        handler.on_modified(FakeEvent())  # type: ignore[arg-type]
        events = handler.drain_events()
        assert len(events) == 1
        assert events[0].event_type == "modified"

    def test_handles_deletion(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "note.md")

        handler.on_deleted(FakeEvent())  # type: ignore[arg-type]
        events = handler.drain_events()
        assert len(events) == 1
        assert events[0].event_type == "deleted"

    def test_handles_move(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "old.md")
            dest_path = str(tmp_path / "new.md")

        handler.on_moved(FakeEvent())  # type: ignore[arg-type]
        events = handler.drain_events()
        assert len(events) == 2
        types = {e.event_type for e in events}
        assert types == {"created", "deleted"}

    def test_drain_clears_events(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "note.md")

        handler.on_created(FakeEvent())  # type: ignore[arg-type]
        assert len(handler.drain_events()) == 1
        assert len(handler.drain_events()) == 0

    def test_nested_file_relative_path(self, tmp_path: Path) -> None:
        handler = ObsidianFileHandler(tmp_path)

        class FakeEvent:
            is_directory = False
            src_path = str(tmp_path / "sub" / "folder" / "note.md")

        handler.on_created(FakeEvent())  # type: ignore[arg-type]
        events = handler.drain_events()
        assert events[0].path == "sub/folder/note.md"


# ---------------------------------------------------------------------------
# ObsidianWatcher
# ---------------------------------------------------------------------------


class TestObsidianWatcher:
    def test_start_and_stop(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        watcher = ObsidianWatcher(vault)
        assert watcher.is_running is False

        watcher.start()
        assert watcher.is_running is True

        watcher.stop()
        assert watcher.is_running is False

    def test_double_start_is_safe(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        watcher = ObsidianWatcher(vault)
        watcher.start()
        watcher.start()  # should not raise
        assert watcher.is_running is True
        watcher.stop()

    def test_stop_when_not_running(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        watcher = ObsidianWatcher(vault)
        watcher.stop()  # should not raise

    def test_detects_file_creation(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        watcher = ObsidianWatcher(vault)
        watcher.start()

        try:
            # Create a new file
            new_file = vault / "new_note.md"
            new_file.write_text("# New Note", encoding="utf-8")

            # Give watchdog time to detect
            time.sleep(0.5)

            events = watcher.get_pending_events()
            # Events might include created + modified
            md_events = [e for e in events if "new_note" in e.path]
            assert len(md_events) >= 1
        finally:
            watcher.stop()

    def test_get_events_when_no_watcher(self) -> None:
        connector = _make_connector()
        events = connector.get_watcher_events()
        assert events == []


# ---------------------------------------------------------------------------
# ObsidianConnector basics
# ---------------------------------------------------------------------------


class TestObsidianConnectorBasics:
    def test_source_type(self) -> None:
        connector = _make_connector()
        assert connector.source_type == SourceType.OBSIDIAN

    def test_get_vault_path(self) -> None:
        connector = _make_connector(vault_path="/home/user/vault")
        path = connector._get_vault_path()
        assert path == Path("/home/user/vault")

    def test_get_vault_path_missing(self) -> None:
        connector = ObsidianConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.OBSIDIAN,
                extra={},
            ),
        )
        with pytest.raises(ConnectorError, match="Missing vault_path"):
            connector._get_vault_path()

    def test_deleted_paths_initialized_empty(self) -> None:
        connector = _make_connector()
        assert connector._deleted_paths == set()


# ---------------------------------------------------------------------------
# fetch_since
# ---------------------------------------------------------------------------


class TestFetchSince:
    @pytest.mark.asyncio
    async def test_full_scan_returns_errors_until_normalizer(self, tmp_path: Path) -> None:
        """Until TASK-052, files appear as errors."""
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))

        result = await connector.fetch_since(None)
        # 3 files in vault → 3 errors (normalizer not implemented)
        assert result.error_count == 3
        assert result.success_count == 0
        assert all("TASK-052" in e.error for e in result.errors)

    @pytest.mark.asyncio
    async def test_full_scan_source_ids(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))

        result = await connector.fetch_since(None)
        source_ids = {e.source_id for e in result.errors}
        assert "note1.md" in source_ids
        assert "note2.md" in source_ids
        assert "subfolder/deep.md" in source_ids

    @pytest.mark.asyncio
    async def test_incremental_scan_skips_old_files(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))

        # Use a cursor far in the future → no files should match
        result = await connector.fetch_since("2099-01-01T00:00:00+00:00")
        assert result.error_count == 0
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_incremental_scan_finds_new_files(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))

        # Use a cursor in the past → all files should match
        result = await connector.fetch_since("2020-01-01T00:00:00+00:00")
        assert result.error_count == 3

    @pytest.mark.asyncio
    async def test_invalid_vault_path_raises(self) -> None:
        connector = _make_connector(vault_path="/nonexistent/vault")
        with pytest.raises(ConnectorError, match="existiert nicht"):
            await connector.fetch_since(None)

    @pytest.mark.asyncio
    async def test_has_more_always_false(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        result = await connector.fetch_since(None)
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_cursor_updated_to_latest_mtime(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        result = await connector.fetch_since(None)
        # Even with errors, cursor should be None (no docs)
        # because normalize raises NotImplementedError before mtime tracking
        # Once TASK-052 is done, this will return a timestamp cursor
        assert result.new_cursor is None

    @pytest.mark.asyncio
    async def test_invalid_cursor_falls_back_to_full_scan(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        # Invalid cursor → treated as None (full scan)
        result = await connector.fetch_since("not-a-date")
        assert result.error_count == 3

    @pytest.mark.asyncio
    async def test_deleted_paths_included_in_sync(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))

        # Track a deleted file
        connector._deleted_paths.add("old_note.md")

        result = await connector.fetch_since("2099-01-01T00:00:00+00:00")
        # Future cursor → no regular files, but 1 deleted file
        error_ids = {e.source_id for e in result.errors}
        assert "old_note.md" in error_ids

    @pytest.mark.asyncio
    async def test_deleted_paths_cleared_after_sync(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        connector._deleted_paths.add("gone.md")

        await connector.fetch_since("2099-01-01T00:00:00+00:00")
        assert connector._deleted_paths == set()


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_valid_vault(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        assert await connector.health_check() is True

    @pytest.mark.asyncio
    async def test_nonexistent_vault(self) -> None:
        connector = _make_connector(vault_path="/nonexistent/vault")
        assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_missing_config(self) -> None:
        connector = ObsidianConnector(
            owner_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            config=ConnectorConfig(
                source_type=SourceType.OBSIDIAN,
                extra={},
            ),
        )
        assert await connector.health_check() is False


# ---------------------------------------------------------------------------
# normalize (stub — TASK-052)
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_raises_not_implemented(self) -> None:
        connector = _make_connector()
        with pytest.raises(NotImplementedError, match="TASK-052"):
            connector.normalize({"relative_path": "test.md"})


# ---------------------------------------------------------------------------
# Watcher lifecycle on connector
# ---------------------------------------------------------------------------


class TestConnectorWatcher:
    def test_start_watcher(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        connector.start_watcher()
        assert connector._watcher is not None
        assert connector._watcher.is_running is True
        connector.stop_watcher()

    def test_stop_watcher(self, tmp_path: Path) -> None:
        vault = _create_vault(tmp_path)
        connector = _make_connector(vault_path=str(vault))
        connector.start_watcher()
        connector.stop_watcher()
        assert connector._watcher is None

    def test_start_watcher_invalid_path(self) -> None:
        connector = _make_connector(vault_path="/nonexistent")
        with pytest.raises(ConnectorError):
            connector.start_watcher()


# ---------------------------------------------------------------------------
# process_watcher_events
# ---------------------------------------------------------------------------


class TestProcessWatcherEvents:
    def test_tracks_deletions(self) -> None:
        connector = _make_connector()
        # Manually inject watcher with events
        connector._watcher = ObsidianWatcher(Path("/tmp"))
        connector._watcher._handler._events = [
            FileEvent(path="deleted.md", event_type="deleted"),
        ]

        connector.process_watcher_events()
        assert "deleted.md" in connector._deleted_paths

    def test_create_discards_deletion(self) -> None:
        connector = _make_connector()
        connector._deleted_paths.add("recreated.md")

        connector._watcher = ObsidianWatcher(Path("/tmp"))
        connector._watcher._handler._events = [
            FileEvent(path="recreated.md", event_type="created"),
        ]

        connector.process_watcher_events()
        assert "recreated.md" not in connector._deleted_paths

    def test_no_watcher_returns_empty(self) -> None:
        connector = _make_connector()
        connector.process_watcher_events()  # should not raise
        assert connector._deleted_paths == set()
