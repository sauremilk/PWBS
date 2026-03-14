"""Chunking-Strategie-Auswahl nach Dokumenttyp (TASK-057).

Automatic strategy selection based on `source_type` of the document.
Mapping is configurable via `StrategyMapping`.

Default mapping (D1 Section 3.2):
- OBSIDIAN  -> paragraph
- NOTION    -> paragraph
- ZOOM      -> semantic
- GOOGLE_CALENDAR -> fixed

Fallback: semantic (if no specific mapping exists).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pwbs.processing.chunking import ChunkingStrategy
from pwbs.schemas.enums import SourceType

__all__ = [
    "ChunkingStrategyResolver",
    "StrategyMapping",
]

# Default mapping per D1 Section 3.2
_DEFAULT_MAPPING: dict[SourceType, ChunkingStrategy] = {
    SourceType.OBSIDIAN: ChunkingStrategy.PARAGRAPH,
    SourceType.NOTION: ChunkingStrategy.PARAGRAPH,
    SourceType.ZOOM: ChunkingStrategy.SEMANTIC,
    SourceType.GOOGLE_CALENDAR: ChunkingStrategy.FIXED,
}


@dataclass(frozen=True, slots=True)
class StrategyMapping:
    """Configurable mapping from source type to chunking strategy.

    Parameters
    ----------
    source_type_map:
        Mapping from `SourceType` to `ChunkingStrategy`.
        Overrides defaults for specified source types.
    content_type_map:
        Mapping from content type string (e.g. `"markdown"`, `"plain"`)
        to `ChunkingStrategy`. Checked after source_type_map.
    fallback:
        Default strategy when no mapping matches.
    """

    source_type_map: dict[SourceType, ChunkingStrategy] = field(
        default_factory=lambda: dict(_DEFAULT_MAPPING)
    )
    content_type_map: dict[str, ChunkingStrategy] = field(
        default_factory=dict
    )
    fallback: ChunkingStrategy = ChunkingStrategy.SEMANTIC


class ChunkingStrategyResolver:
    """Resolves the chunking strategy for a document.

    Uses a two-level lookup:
    1. `source_type` -> strategy (most specific)
    2. `content_type` -> strategy (content-based fallback)
    3. Global fallback (`semantic`)

    Parameters
    ----------
    mapping:
        Strategy mapping configuration. Uses defaults if None.
    """

    def __init__(self, mapping: StrategyMapping | None = None) -> None:
        self._mapping = mapping or StrategyMapping()

    @property
    def mapping(self) -> StrategyMapping:
        """Current strategy mapping."""
        return self._mapping

    def resolve(
        self,
        source_type: SourceType | str,
        content_type: str | None = None,
    ) -> ChunkingStrategy:
        """Determine the chunking strategy for a document.

        Parameters
        ----------
        source_type:
            The document's source type (e.g. `SourceType.NOTION`).
        content_type:
            Optional content type hint (e.g. `"markdown"`).

        Returns
        -------
        ChunkingStrategy
            The resolved strategy.
        """
        # Normalize source_type to enum
        st = self._normalize_source_type(source_type)

        # Level 1: source_type mapping
        if st is not None and st in self._mapping.source_type_map:
            return self._mapping.source_type_map[st]

        # Level 2: content_type mapping
        if content_type and content_type.lower() in self._mapping.content_type_map:
            return self._mapping.content_type_map[content_type.lower()]

        # Level 3: fallback
        return self._mapping.fallback

    @staticmethod
    def _normalize_source_type(source_type: SourceType | str) -> SourceType | None:
        """Convert string to SourceType enum, returning None on failure."""
        if isinstance(source_type, SourceType):
            return source_type
        try:
            return SourceType(source_type.lower())
        except (ValueError, AttributeError):
            return None
