"""BaseConnector ABC - abstract interface for all PWBS data-source connectors (TASK-041).

Every connector must implement:
- ``fetch_since`` - cursor-based incremental data retrieval
- ``normalize`` - raw API response to UnifiedDocument conversion
- ``health_check`` - verify the connection to the external data source

Design decisions:
- Cursor/watermark is opaque ``str | None`` - each connector defines its own format
  (ISO timestamp, page token, sync token, etc.).
- ``SyncResult`` bundles fetched documents with the new cursor for atomic persistence.
- Partial success is acceptable: individual document failures are captured in
  ``SyncResult.errors`` and do not abort the entire batch.
- Max batch size: 100 documents per fetch (configurable via ``ConnectorConfig``).
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from pwbs.schemas.enums import SourceType  # noqa: TC001 - needed at runtime by Pydantic

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.schemas.document import UnifiedDocument

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConnectorConfig(BaseModel):
    """Per-connector configuration stored alongside the Connection record."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source_type: SourceType
    max_batch_size: int = Field(default=100, ge=1, le=500)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Sync result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SyncError:
    """A single document-level error that did not abort the batch."""

    source_id: str
    error: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class SyncResult:
    """Result of a ``BaseConnector.fetch_since`` invocation.

    Attributes:
        documents: Successfully normalised documents ready for processing.
        new_cursor: Opaque cursor to persist for the next incremental fetch.
            ``None`` signals "no more data / initial state".
        errors: Per-document errors that did not abort the batch.
        has_more: ``True`` when additional pages remain (connector should be
            called again with ``new_cursor``).
    """

    documents: list[UnifiedDocument] = field(default_factory=list)
    new_cursor: str | None = None
    errors: list[SyncError] = field(default_factory=list)
    has_more: bool = False

    @property
    def success_count(self) -> int:
        return len(self.documents)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def total_count(self) -> int:
        return self.success_count + self.error_count


# ---------------------------------------------------------------------------
# Abstract base connector
# ---------------------------------------------------------------------------


class BaseConnector(abc.ABC):
    """Abstract base class for all PWBS data-source connectors.

    Subclasses must implement ``fetch_since``, ``normalize`` and
    ``health_check``.  The ``run`` entry-point orchestrates a full sync cycle
    with cursor management, partial-failure handling and logging.

    Parameters:
        owner_id: UUID of the user who owns this connection.
        connection_id: UUID of the ``Connection`` record in PostgreSQL.
        config: Connector-specific configuration.
    """

    def __init__(
        self,
        *,
        owner_id: UUID,
        connection_id: UUID,
        config: ConnectorConfig,
    ) -> None:
        self.owner_id = owner_id
        self.connection_id = connection_id
        self.config = config
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ---- abstract methods --------------------------------------------------

    @abc.abstractmethod
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch data from the external source starting after *cursor*.

        Must be idempotent: re-invoking with the same cursor yields the same
        documents (or a superset if new data appeared).

        Returns a ``SyncResult`` with normalised ``UnifiedDocument`` objects
        and the new cursor value.  Individual document failures should be
        captured in ``SyncResult.errors`` rather than raising.
        """

    @abc.abstractmethod
    async def normalize(self, raw: dict[str, Any]) -> UnifiedDocument:
        """Convert a single raw API response into a ``UnifiedDocument``.

        Must be a pure function (no side-effects, no network calls).
        Raises ``ConnectorError`` if the raw data cannot be normalised.
        """

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` if the external data source is reachable and
        the stored credentials are still valid.
        """

    # ---- orchestration -----------------------------------------------------

    async def run(self, cursor: str | None = None) -> SyncResult:
        """Execute a full sync cycle: fetch → normalise, respecting batch limits.

        This is the primary entry-point called by ``IngestionAgent`` or the
        API sync endpoint.  It delegates to ``fetch_since`` and handles
        logging and error counting.

        Returns the aggregated ``SyncResult`` for the entire run.
        """
        self._logger.info(
            "Starting sync: connection_id=%s cursor=%s",
            self.connection_id,
            cursor[:32] + "…" if cursor and len(cursor) > 32 else cursor,
        )

        result = await self.fetch_since(cursor)

        self._logger.info(
            "Sync complete: connection_id=%s fetched=%d errors=%d has_more=%s new_cursor=%s",
            self.connection_id,
            result.success_count,
            result.error_count,
            result.has_more,
            result.new_cursor[:32] + "…"
            if result.new_cursor and len(result.new_cursor) > 32
            else result.new_cursor,
        )

        if result.errors:
            for err in result.errors:
                self._logger.warning(
                    "Document error: connection_id=%s source_id=%s error=%s",
                    self.connection_id,
                    err.source_id,
                    err.error,
                )

        return result

    # ---- helpers -----------------------------------------------------------

    @property
    def source_type(self) -> SourceType:
        """Convenience accessor for the connector's source type."""
        return self.config.source_type

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"owner_id={self.owner_id} "
            f"connection_id={self.connection_id} "
            f"source_type={self.source_type.value}>"
        )
