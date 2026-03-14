"""Obsidian Vault connector with filesystem watcher (TASK-051).

Implements ``BaseConnector`` for local Obsidian vaults.  Unlike the OAuth-based
connectors, Obsidian uses direct filesystem access:

- The user configures a local vault path (stored in ``config.extra["vault_path"]``).
- ``fetch_since(None)`` performs a **full scan** of all ``.md`` files.
- ``fetch_since(cursor)`` performs an **incremental scan** (files modified after
  the cursor timestamp).
- ``ObsidianWatcher`` uses the ``watchdog`` library to monitor the vault for
  real-time create/modify/delete events on ``.md`` files.
- ``.obsidian/``, ``.git/``, ``.trash/`` and similar configuration directories
  are excluded from scanning and watching.

References:
- Architecture: D1 §3.1 (Connector table: File-System-Watcher via watchdog)
- PRD: D4 US-1.4 / F-006

TASK-052 will add:
- ``normalize()`` implementation (Markdown-Parser with Frontmatter + Link extraction)
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncError, SyncResult
from pwbs.core.exceptions import ConnectorError
from pwbs.schemas.enums import SourceType

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.schemas.document import UnifiedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".obsidian",
        ".git",
        ".trash",
        "__pycache__",
        "node_modules",
        ".DS_Store",
    }
)

_MD_SUFFIX = ".md"


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------


def _is_excluded(path: Path, vault_root: Path) -> bool:
    """Return ``True`` if *path* is inside an excluded directory."""
    try:
        relative = path.relative_to(vault_root)
    except ValueError:
        return True
    return any(part in _EXCLUDE_DIRS for part in relative.parts)


def validate_vault_path(vault_path: str) -> tuple[bool, str]:
    """Validate that *vault_path* is a valid Obsidian vault directory.

    Returns ``(True, "")`` on success or ``(False, error_message)`` on failure.
    """
    p = Path(vault_path)
    if not p.exists():
        return False, f"Pfad existiert nicht: {vault_path}"
    if not p.is_dir():
        return False, f"Pfad ist kein Verzeichnis: {vault_path}"

    # Check for at least one .md file (non-excluded)
    for md_file in p.rglob(f"*{_MD_SUFFIX}"):
        if not _is_excluded(md_file, p):
            return True, ""

    return False, f"Kein gültiger Obsidian-Vault: keine .md-Dateien gefunden in {vault_path}"


def scan_vault_files(vault_path: Path) -> list[Path]:
    """Recursively list all ``.md`` files in the vault, excluding config dirs."""
    results: list[Path] = []
    for md_file in sorted(vault_path.rglob(f"*{_MD_SUFFIX}")):
        if not _is_excluded(md_file, vault_path):
            results.append(md_file)
    return results


def _file_to_raw(file_path: Path, vault_root: Path) -> dict[str, object]:
    """Read a ``.md`` file and build the raw dict for ``normalize()``.

    The raw dict contains:
    - ``relative_path``: path relative to vault root (used as ``source_id``)
    - ``absolute_path``: full filesystem path
    - ``content``: raw file content (UTF-8)
    - ``modified_at``: file mtime as ISO string
    - ``created_at``: file ctime as ISO string (best effort)
    - ``size_bytes``: file size
    - ``filename``: file name without extension
    """
    relative = file_path.relative_to(vault_root)
    stat = file_path.stat()

    content = file_path.read_text(encoding="utf-8")

    return {
        "relative_path": str(relative).replace(os.sep, "/"),
        "absolute_path": str(file_path),
        "content": content,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
        "filename": file_path.stem,
    }


# ---------------------------------------------------------------------------
# Filesystem event model
# ---------------------------------------------------------------------------


@dataclass
class FileEvent:
    """Represents a filesystem event on a vault file."""

    path: str  # relative to vault root, forward-slash separated
    event_type: str  # "created", "modified", "deleted"
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------


class ObsidianFileHandler(FileSystemEventHandler):
    """Watchdog handler that queues events for ``.md`` files.

    Filters out events in excluded directories and non-Markdown files.
    """

    def __init__(self, vault_root: Path) -> None:
        super().__init__()
        self._vault_root = vault_root
        self._lock = threading.Lock()
        self._events: list[FileEvent] = []

    # -- event callbacks ---------------------------------------------------

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._handle(event, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        # Treat a move as delete (old path) + create (new path)
        if hasattr(event, "src_path"):
            self._handle_path(str(event.src_path), "deleted")
        if hasattr(event, "dest_path"):
            self._handle_path(str(event.dest_path), "created")

    # -- internal ----------------------------------------------------------

    def _handle(self, event: FileSystemEvent, event_type: str) -> None:
        if event.is_directory:
            return
        self._handle_path(str(event.src_path), event_type)

    def _handle_path(self, path_str: str, event_type: str) -> None:
        path = Path(path_str)
        if path.suffix.lower() != _MD_SUFFIX:
            return
        if _is_excluded(path, self._vault_root):
            return

        try:
            relative = str(path.relative_to(self._vault_root)).replace(os.sep, "/")
        except ValueError:
            return

        fe = FileEvent(path=relative, event_type=event_type)
        with self._lock:
            self._events.append(fe)

        logger.debug("Obsidian FS event: %s %s", event_type, relative)

    def drain_events(self) -> list[FileEvent]:
        """Return and clear all pending events (thread-safe)."""
        with self._lock:
            events = list(self._events)
            self._events.clear()
        return events


# ---------------------------------------------------------------------------
# Watcher (manages Observer lifecycle)
# ---------------------------------------------------------------------------


class ObsidianWatcher:
    """Background filesystem watcher for an Obsidian vault.

    Usage::

        watcher = ObsidianWatcher(vault_path)
        watcher.start()
        ...
        events = watcher.get_pending_events()
        ...
        watcher.stop()
    """

    def __init__(self, vault_path: Path) -> None:
        self._vault_path = vault_path
        self._handler = ObsidianFileHandler(vault_path)
        self._observer: Observer | None = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def start(self) -> None:
        """Start watching the vault directory (non-blocking, daemon thread)."""
        if self.is_running:
            logger.warning("Watcher already running for %s", self._vault_path)
            return

        self._observer = Observer()
        self._observer.schedule(self._handler, str(self._vault_path), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        logger.info("Obsidian watcher started: %s", self._vault_path)

    def stop(self) -> None:
        """Stop the watcher and wait for the thread to finish."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
            logger.info("Obsidian watcher stopped: %s", self._vault_path)

    def get_pending_events(self) -> list[FileEvent]:
        """Return and clear all pending filesystem events."""
        return self._handler.drain_events()


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class ObsidianConnector(BaseConnector):
    """Obsidian vault connector with filesystem monitoring.

    Configuration (via ``config.extra``):
    - ``vault_path`` (str, required): Absolute path to the Obsidian vault.

    The connector supports two sync strategies:

    1. **Polling** via ``fetch_since(cursor)``:
       - ``cursor=None`` → full scan of all ``.md`` files.
       - ``cursor=<ISO timestamp>`` → incremental scan (files with
         ``mtime > cursor``).

    2. **Real-time** via ``start_watcher()`` / ``stop_watcher()``:
       Uses ``watchdog`` to detect create/modify/delete events.
       Accumulated events are available via ``get_watcher_events()``.
    """

    source_type = SourceType.OBSIDIAN  # type: ignore[assignment]

    def __init__(
        self,
        *,
        owner_id: UUID,
        connection_id: UUID,
        config: ConnectorConfig,
    ) -> None:
        super().__init__(owner_id=owner_id, connection_id=connection_id, config=config)
        self._watcher: ObsidianWatcher | None = None
        self._deleted_paths: set[str] = set()

    # ------------------------------------------------------------------
    # Vault path
    # ------------------------------------------------------------------

    def _get_vault_path(self) -> Path:
        """Extract and validate the vault path from config."""
        vault_path_str = self.config.extra.get("vault_path")
        if not vault_path_str or not isinstance(vault_path_str, str):
            raise ConnectorError(
                "Missing vault_path in connector config",
                code="OBSIDIAN_MISSING_VAULT_PATH",
            )
        return Path(vault_path_str)

    # ------------------------------------------------------------------
    # Watcher lifecycle
    # ------------------------------------------------------------------

    def start_watcher(self) -> None:
        """Start background filesystem monitoring."""
        vault_path = self._get_vault_path()
        valid, error = validate_vault_path(str(vault_path))
        if not valid:
            raise ConnectorError(error, code="OBSIDIAN_INVALID_VAULT")

        if self._watcher is not None and self._watcher.is_running:
            return

        self._watcher = ObsidianWatcher(vault_path)
        self._watcher.start()

    def stop_watcher(self) -> None:
        """Stop background filesystem monitoring."""
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    def get_watcher_events(self) -> list[FileEvent]:
        """Return and clear pending watcher events."""
        if self._watcher is None:
            return []
        return self._watcher.get_pending_events()

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Scan the Obsidian vault for files changed since *cursor*.

        - ``cursor=None`` → **full scan**: all ``.md`` files.
        - ``cursor=<ISO timestamp>`` → **incremental scan**: only files
          whose ``mtime`` is after the cursor timestamp.

        Deleted files (tracked by the watcher) are reported with empty
        content and ``metadata["deleted"] = True``.

        Returns a ``SyncResult`` with raw file dicts (normalised by
        TASK-052), errors, and the new cursor.
        """
        vault_path = self._get_vault_path()
        valid, error = validate_vault_path(str(vault_path))
        if not valid:
            raise ConnectorError(error, code="OBSIDIAN_INVALID_VAULT")

        # Parse cursor as ISO timestamp
        watermark: datetime | None = None
        if cursor:
            try:
                watermark = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
            except ValueError:
                logger.warning("Invalid cursor %r — falling back to full scan", cursor)

        # Scan vault
        all_files = scan_vault_files(vault_path)

        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []
        latest_mtime: datetime | None = None

        for file_path in all_files:
            try:
                stat = file_path.stat()
                file_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

                # Skip files not modified since watermark (incremental sync)
                if watermark and file_mtime <= watermark:
                    continue

                raw = _file_to_raw(file_path, vault_path)
                doc = self.normalize(raw)
                documents.append(doc)

                if latest_mtime is None or file_mtime > latest_mtime:
                    latest_mtime = file_mtime

            except NotImplementedError:
                # TASK-052 not yet done
                relative = str(file_path.relative_to(vault_path)).replace(os.sep, "/")
                errors.append(
                    SyncError(
                        source_id=relative,
                        error="Normalizer not yet implemented (TASK-052)",
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                relative = str(file_path.relative_to(vault_path)).replace(os.sep, "/")
                errors.append(
                    SyncError(
                        source_id=relative,
                        error=str(exc),
                    ),
                )

        # Process deleted files from watcher
        for deleted_path in self._deleted_paths:
            try:
                raw_deleted: dict[str, object] = {
                    "relative_path": deleted_path,
                    "absolute_path": str(vault_path / deleted_path),
                    "content": "",
                    "modified_at": datetime.now(tz=timezone.utc).isoformat(),
                    "created_at": "",
                    "size_bytes": 0,
                    "filename": Path(deleted_path).stem,
                    "deleted": True,
                }
                doc = self.normalize(raw_deleted)
                documents.append(doc)
            except NotImplementedError:
                errors.append(
                    SyncError(
                        source_id=deleted_path,
                        error="Normalizer not yet implemented (TASK-052)",
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    SyncError(source_id=deleted_path, error=str(exc)),
                )
        self._deleted_paths.clear()

        # Build new cursor
        new_cursor: str | None = None
        if latest_mtime:
            new_cursor = latest_mtime.isoformat()
        elif cursor:
            new_cursor = cursor  # keep old cursor if no new files

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=False,  # filesystem scan is always complete
        )

    def normalize(self, raw: dict[str, object]) -> UnifiedDocument:
        """Normalize a raw Obsidian file dict into a UnifiedDocument.

        Will be implemented in TASK-052 (Obsidian Markdown-Parser).
        """
        raise NotImplementedError("TASK-052: Obsidian normalize not yet implemented")

    async def health_check(self) -> bool:
        """Verify the vault path is valid and accessible."""
        try:
            vault_path = self._get_vault_path()
            valid, _ = validate_vault_path(str(vault_path))
            return valid
        except ConnectorError:
            return False

    # ------------------------------------------------------------------
    # Watcher event processing
    # ------------------------------------------------------------------

    def process_watcher_events(self) -> None:
        """Consume pending watcher events and track deletions.

        Creates/modifies are handled by the next ``fetch_since()`` call
        (mtime-based). Deletions are tracked in ``_deleted_paths`` for
        inclusion in the next sync result.
        """
        events = self.get_watcher_events()
        for event in events:
            if event.event_type == "deleted":
                self._deleted_paths.add(event.path)
            else:
                # Creates/modifies are picked up by mtime scan in fetch_since
                self._deleted_paths.discard(event.path)
