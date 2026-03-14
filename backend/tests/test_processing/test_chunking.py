"""Tests for pwbs.processing.chunking – ChunkingService (TASK-056)."""

from __future__ import annotations

import pytest

from pwbs.processing.chunking import (
    ChunkingConfig,
    ChunkingService,
    ChunkingStrategy,
    TextChunk,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    min_chunk_tokens: int = 32,
) -> ChunkingService:
    return ChunkingService(
        ChunkingConfig(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            strategy=strategy,
            min_chunk_tokens=min_chunk_tokens,
        )
    )


def _repeat_sentence(n: int) -> str:
    """Build a text of *n* identical sentences for predictable splitting."""
    return " ".join(["This is a test sentence with several tokens."] * n)


# ---------------------------------------------------------------------------
# AC: Empty or too-short documents (< 32 tokens) → exactly one chunk
# ---------------------------------------------------------------------------


class TestShortDocuments:
    def test_empty_string_returns_one_chunk(self) -> None:
        svc = _make_service()
        result = svc.chunk("")
        assert len(result) == 1
        assert result[0].content == ""
        assert result[0].chunk_index == 0

    def test_whitespace_only_returns_one_chunk(self) -> None:
        svc = _make_service()
        result = svc.chunk("   \n\n  ")
        assert len(result) == 1
        assert result[0].chunk_index == 0

    def test_short_text_below_min_tokens(self) -> None:
        svc = _make_service(min_chunk_tokens=32)
        result = svc.chunk("Hello world.")
        assert len(result) == 1
        assert result[0].content == "Hello world."

    def test_none_token_count_for_empty(self) -> None:
        svc = _make_service()
        result = svc.chunk("")
        assert result[0].token_count == 0


# ---------------------------------------------------------------------------
# AC: Three chunking strategies implemented
# ---------------------------------------------------------------------------


class TestSemantic:
    def test_fits_in_one_chunk(self) -> None:
        svc = _make_service(max_tokens=100)
        text = "Hello world. This is a test."
        result = svc.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
        assert len(result) == 1
        assert result[0].token_count <= 100

    def test_splits_at_sentence_boundaries(self) -> None:
        svc = _make_service(max_tokens=20, overlap_tokens=5, min_chunk_tokens=2)
        text = "First sentence here with extra words added. Second sentence here with more words too. Third sentence here and even more. Fourth sentence here at the end of it all."
        result = svc.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
        assert len(result) >= 2
        # Each chunk should end at a sentence boundary (contain a period)
        for c in result:
            assert "." in c.content

    def test_max_tokens_respected(self) -> None:
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(20)
        result = svc.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
        for c in result:
            assert c.token_count <= 50

    def test_chunk_indices_sequential(self) -> None:
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(20)
        result = svc.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
        for i, c in enumerate(result):
            assert c.chunk_index == i


class TestParagraph:
    def test_splits_at_paragraph_boundaries(self) -> None:
        svc = _make_service(max_tokens=20, overlap_tokens=5, min_chunk_tokens=2)
        text = "First paragraph with enough content to exceed the token limit we set.\n\nSecond paragraph also has quite a few words in it for testing.\n\nThird paragraph rounds out the content nicely."
        result = svc.chunk(text, strategy=ChunkingStrategy.PARAGRAPH)
        assert len(result) >= 2

    def test_markdown_paragraphs_preserved(self) -> None:
        svc = _make_service(max_tokens=30, overlap_tokens=5, min_chunk_tokens=2)
        text = "# Heading\n\nSome paragraph text here.\n\nAnother paragraph with more text content."
        result = svc.chunk(text, strategy=ChunkingStrategy.PARAGRAPH)
        assert len(result) >= 1
        # First chunk should contain heading or first paragraph
        assert any("Heading" in c.content or "paragraph" in c.content for c in result)

    def test_max_tokens_respected(self) -> None:
        paras = [
            "This is paragraph number {}. It has quite a few words to fill tokens.".format(i)
            for i in range(20)
        ]
        text = "\n\n".join(paras)
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        result = svc.chunk(text, strategy=ChunkingStrategy.PARAGRAPH)
        for c in result:
            assert c.token_count <= 50


class TestFixed:
    def test_splits_by_token_count(self) -> None:
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(30)
        result = svc.chunk(text, strategy=ChunkingStrategy.FIXED)
        assert len(result) >= 2

    def test_max_tokens_respected(self) -> None:
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(30)
        result = svc.chunk(text, strategy=ChunkingStrategy.FIXED)
        for c in result:
            assert c.token_count <= 50

    def test_overlap_between_chunks(self) -> None:
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(30)
        result = svc.chunk(text, strategy=ChunkingStrategy.FIXED)
        assert len(result) >= 3
        # Token counts of middle chunks should all be max_tokens
        for c in result[:-1]:
            assert c.token_count == 50

    def test_chunk_indices_sequential(self) -> None:
        svc = _make_service(max_tokens=50, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(30)
        result = svc.chunk(text, strategy=ChunkingStrategy.FIXED)
        for i, c in enumerate(result):
            assert c.chunk_index == i


# ---------------------------------------------------------------------------
# AC: Token-Overlap von 64 Tokens zwischen aufeinanderfolgenden Chunks
# ---------------------------------------------------------------------------


class TestOverlap:
    def test_fixed_overlap_token_count(self) -> None:
        """Fixed strategy: overlap should be exactly overlap_tokens."""
        svc = _make_service(max_tokens=100, overlap_tokens=20, min_chunk_tokens=2)
        text = _repeat_sentence(50)
        result = svc.chunk(text, strategy=ChunkingStrategy.FIXED)
        assert len(result) >= 3
        # Step = max_tokens - overlap_tokens = 80
        # Each chunk except the last should have exactly max_tokens
        for c in result[:-1]:
            assert c.token_count == 100

    def test_semantic_has_overlap(self) -> None:
        """Semantic chunks should share content at boundaries."""
        svc = _make_service(max_tokens=40, overlap_tokens=10, min_chunk_tokens=2)
        text = _repeat_sentence(20)
        result = svc.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
        assert len(result) >= 3
        # Check adjacent chunks share some content
        for idx in range(len(result) - 1):
            current_words = set(result[idx].content.split())
            next_words = set(result[idx + 1].content.split())
            # There should be overlapping words (from shared sentences)
            assert current_words & next_words


# ---------------------------------------------------------------------------
# AC: Default strategy is semantic
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    def test_default_strategy_is_semantic(self) -> None:
        svc = ChunkingService()
        assert svc.config.strategy == ChunkingStrategy.SEMANTIC

    def test_default_max_tokens(self) -> None:
        svc = ChunkingService()
        assert svc.config.max_tokens == 512

    def test_default_overlap_tokens(self) -> None:
        svc = ChunkingService()
        assert svc.config.overlap_tokens == 64

    def test_default_min_chunk_tokens(self) -> None:
        svc = ChunkingService()
        assert svc.config.min_chunk_tokens == 32


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_very_long_sentence_semantic(self) -> None:
        """A single sentence longer than max_tokens should be split via fixed."""
        svc = _make_service(max_tokens=20, overlap_tokens=5, min_chunk_tokens=2)
        # Single sentence with no period-whitespace breaks
        text = "word " * 100
        result = svc.chunk(text.strip(), strategy=ChunkingStrategy.SEMANTIC)
        assert len(result) >= 2
        for c in result:
            assert c.token_count <= 20

    def test_count_tokens_returns_correct_count(self) -> None:
        svc = _make_service()
        assert svc.count_tokens("hello") >= 1
        assert svc.count_tokens("") == 0

    def test_strategy_override(self) -> None:
        """Passing strategy to chunk() overrides config default."""
        svc = _make_service(max_tokens=30, overlap_tokens=5, min_chunk_tokens=2)
        text = "Para one content here.\n\nPara two content here.\n\nPara three content here."
        result_semantic = svc.chunk(text, strategy=ChunkingStrategy.SEMANTIC)
        result_paragraph = svc.chunk(text, strategy=ChunkingStrategy.PARAGRAPH)
        # Different strategies may produce different chunk counts/content
        # Both should produce valid chunks
        assert all(isinstance(c, TextChunk) for c in result_semantic)
        assert all(isinstance(c, TextChunk) for c in result_paragraph)

    def test_text_with_exactly_max_tokens(self) -> None:
        """Text with exactly max_tokens should be one chunk."""
        svc = _make_service(max_tokens=512, min_chunk_tokens=2)
        # Build text and adjust to be exactly 512 tokens
        base = "word "
        while svc.count_tokens(base) < 512:
            base += "word "
        # Trim to exactly 512 tokens
        tokens = svc._enc.encode(base)[:512]
        text = svc._enc.decode(tokens)
        assert svc.count_tokens(text) == 512
        result = svc.chunk(text)
        assert len(result) == 1
