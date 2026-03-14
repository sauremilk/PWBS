"""Tests for ChunkingStrategyResolver (TASK-057)."""

from __future__ import annotations

import pytest

from pwbs.processing.chunking import ChunkingStrategy
from pwbs.processing.strategy_resolver import (
    ChunkingStrategyResolver,
    StrategyMapping,
)
from pwbs.schemas.enums import SourceType


# ------------------------------------------------------------------
# Default Mapping Tests
# ------------------------------------------------------------------


class TestDefaultMapping:
    """Tests for default source_type -> strategy mapping."""

    def test_obsidian_paragraph(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve(SourceType.OBSIDIAN) == ChunkingStrategy.PARAGRAPH

    def test_notion_paragraph(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve(SourceType.NOTION) == ChunkingStrategy.PARAGRAPH

    def test_zoom_semantic(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve(SourceType.ZOOM) == ChunkingStrategy.SEMANTIC

    def test_google_calendar_fixed(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve(SourceType.GOOGLE_CALENDAR) == ChunkingStrategy.FIXED


# ------------------------------------------------------------------
# Fallback
# ------------------------------------------------------------------


class TestFallback:
    """Tests for fallback behavior."""

    def test_unknown_source_type_string(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve("unknown_source") == ChunkingStrategy.SEMANTIC

    def test_custom_fallback(self) -> None:
        mapping = StrategyMapping(fallback=ChunkingStrategy.FIXED)
        resolver = ChunkingStrategyResolver(mapping)
        assert resolver.resolve("unknown_source") == ChunkingStrategy.FIXED


# ------------------------------------------------------------------
# String Source Types
# ------------------------------------------------------------------


class TestStringSourceTypes:
    """Tests for string-based source type resolution."""

    def test_string_obsidian(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve("obsidian") == ChunkingStrategy.PARAGRAPH

    def test_string_notion(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve("notion") == ChunkingStrategy.PARAGRAPH

    def test_string_zoom(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve("zoom") == ChunkingStrategy.SEMANTIC

    def test_string_google_calendar(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve("google_calendar") == ChunkingStrategy.FIXED

    def test_string_case_insensitive(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert resolver.resolve("OBSIDIAN") == ChunkingStrategy.PARAGRAPH


# ------------------------------------------------------------------
# Configurable Mapping
# ------------------------------------------------------------------


class TestConfigurableMapping:
    """Tests for custom mappings."""

    def test_override_source_type(self) -> None:
        custom = StrategyMapping(
            source_type_map={
                SourceType.OBSIDIAN: ChunkingStrategy.FIXED,
                SourceType.NOTION: ChunkingStrategy.SEMANTIC,
            }
        )
        resolver = ChunkingStrategyResolver(custom)
        assert resolver.resolve(SourceType.OBSIDIAN) == ChunkingStrategy.FIXED
        assert resolver.resolve(SourceType.NOTION) == ChunkingStrategy.SEMANTIC

    def test_content_type_mapping(self) -> None:
        custom = StrategyMapping(
            source_type_map={},
            content_type_map={
                "markdown": ChunkingStrategy.PARAGRAPH,
                "plain": ChunkingStrategy.FIXED,
            },
        )
        resolver = ChunkingStrategyResolver(custom)
        assert resolver.resolve("unknown", content_type="markdown") == ChunkingStrategy.PARAGRAPH
        assert resolver.resolve("unknown", content_type="plain") == ChunkingStrategy.FIXED

    def test_source_type_takes_priority_over_content_type(self) -> None:
        custom = StrategyMapping(
            source_type_map={SourceType.NOTION: ChunkingStrategy.PARAGRAPH},
            content_type_map={"markdown": ChunkingStrategy.FIXED},
        )
        resolver = ChunkingStrategyResolver(custom)
        # source_type match wins over content_type
        assert resolver.resolve(SourceType.NOTION, content_type="markdown") == ChunkingStrategy.PARAGRAPH

    def test_content_type_case_insensitive(self) -> None:
        custom = StrategyMapping(
            source_type_map={},
            content_type_map={"markdown": ChunkingStrategy.PARAGRAPH},
        )
        resolver = ChunkingStrategyResolver(custom)
        assert resolver.resolve("unknown", content_type="MARKDOWN") == ChunkingStrategy.PARAGRAPH


# ------------------------------------------------------------------
# Strategy Mapping Dataclass
# ------------------------------------------------------------------


class TestStrategyMapping:
    """Tests for StrategyMapping defaults."""

    def test_default_has_all_source_types(self) -> None:
        mapping = StrategyMapping()
        assert SourceType.OBSIDIAN in mapping.source_type_map
        assert SourceType.NOTION in mapping.source_type_map
        assert SourceType.ZOOM in mapping.source_type_map
        assert SourceType.GOOGLE_CALENDAR in mapping.source_type_map

    def test_default_content_type_empty(self) -> None:
        mapping = StrategyMapping()
        assert mapping.content_type_map == {}

    def test_default_fallback_semantic(self) -> None:
        mapping = StrategyMapping()
        assert mapping.fallback == ChunkingStrategy.SEMANTIC


# ------------------------------------------------------------------
# Resolver Property
# ------------------------------------------------------------------


class TestResolverProperty:
    """Tests for resolver property and edge cases."""

    def test_mapping_property(self) -> None:
        resolver = ChunkingStrategyResolver()
        assert isinstance(resolver.mapping, StrategyMapping)

    def test_none_content_type(self) -> None:
        resolver = ChunkingStrategyResolver()
        result = resolver.resolve(SourceType.ZOOM, content_type=None)
        assert result == ChunkingStrategy.SEMANTIC

    def test_empty_content_type(self) -> None:
        resolver = ChunkingStrategyResolver()
        result = resolver.resolve("unknown", content_type="")
        assert result == ChunkingStrategy.SEMANTIC
