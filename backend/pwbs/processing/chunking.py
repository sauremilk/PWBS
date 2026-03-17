"""Chunking Service for the PWBS Processing Pipeline (TASK-056).

Three strategies for splitting documents into token-bounded chunks:

- ``semantic``: splits at sentence boundaries (default)
- ``paragraph``: splits at Markdown paragraph boundaries (``\\n\\n``)
- ``fixed``: splits by raw token count

Token counting uses tiktoken ``cl100k_base`` encoding for consistency
with OpenAI embedding models.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import tiktoken

__all__ = [
    "ChunkingConfig",
    "ChunkingService",
    "ChunkingStrategy",
    "TextChunk",
]


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Configuration for the chunking service (D1 §3.2 defaults)."""

    max_tokens: int = 512
    overlap_tokens: int = 64
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    min_chunk_tokens: int = 32


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A single chunk produced by the chunking service."""

    content: str
    chunk_index: int
    token_count: int


class ChunkingService:
    """Splits document text into token-bounded chunks with configurable overlap.

    Supports three strategies:

    - **semantic** (default): Splits at sentence boundaries (``.``, ``!``, ``?``
      followed by whitespace).  Keeps semantically coherent sections together.
    - **paragraph**: Splits at Markdown paragraph boundaries (double newline).
      Best for structured documents (Notion, Obsidian).
    - **fixed**: Splits by raw token count.  Fallback for unstructured long text.

    Consecutive chunks overlap by ``overlap_tokens`` tokens so that context
    is preserved across chunk boundaries.
    """

    _SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
    _PARAGRAPH_RE = re.compile(r"\n\s*\n")

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()
        self._enc = tiktoken.get_encoding("cl100k_base")

    @property
    def config(self) -> ChunkingConfig:
        return self._config

    def count_tokens(self, text: str) -> int:
        """Count tokens in *text* using the ``cl100k_base`` encoding."""
        return len(self._enc.encode(text))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(
        self,
        text: str,
        strategy: ChunkingStrategy | None = None,
    ) -> list[TextChunk]:
        """Split *text* into chunks.

        Args:
            text: The document text to chunk.
            strategy: Override the configured default strategy for this call.

        Returns:
            List of :class:`TextChunk` objects.  Empty or short documents
            (< ``min_chunk_tokens``) always produce exactly **one** chunk.
        """
        effective = strategy or self._config.strategy

        # AC: empty or too-short documents (< 32 tokens) → exactly one chunk
        token_count = self.count_tokens(text)
        if token_count < self._config.min_chunk_tokens:
            return [TextChunk(content=text, chunk_index=0, token_count=token_count)]

        # Fits in a single chunk – no splitting needed
        if token_count <= self._config.max_tokens:
            return [TextChunk(content=text, chunk_index=0, token_count=token_count)]

        match effective:
            case ChunkingStrategy.SEMANTIC:
                segments = self._split_sentences(text)
                joiner = " "
            case ChunkingStrategy.PARAGRAPH:
                segments = self._split_paragraphs(text)
                joiner = "\n\n"
            case ChunkingStrategy.FIXED:
                return self._chunk_fixed(text)

        return self._chunk_by_segments(segments, joiner)

    # ------------------------------------------------------------------
    # Segmentation helpers
    # ------------------------------------------------------------------

    def _split_sentences(self, text: str) -> list[str]:
        """Split *text* into sentences at ``[.!?]`` followed by whitespace."""
        parts = self._SENTENCE_RE.split(text)
        return [p for p in parts if p.strip()]

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split *text* at Markdown paragraph boundaries (double newline)."""
        parts = self._PARAGRAPH_RE.split(text)
        return [p for p in parts if p.strip()]

    # ------------------------------------------------------------------
    # Segment-based chunking (semantic + paragraph)
    # ------------------------------------------------------------------

    def _chunk_by_segments(
        self,
        segments: list[str],
        joiner: str,
    ) -> list[TextChunk]:
        """Build token-bounded chunks from natural-language *segments*.

        Greedily accumulates segments until ``max_tokens`` would be exceeded,
        then starts a new chunk with ``overlap_tokens`` worth of trailing
        segments carried over for context continuity.
        """
        if not segments:
            return [TextChunk(content="", chunk_index=0, token_count=0)]

        seg_tokens = [self.count_tokens(s) for s in segments]
        chunks: list[TextChunk] = []
        i = 0

        while i < len(segments):
            # Greedily accumulate segments starting from i
            current: list[str] = [segments[i]]
            j = i + 1

            while j < len(segments):
                candidate = joiner.join(current + [segments[j]])
                candidate_tok = self.count_tokens(candidate)
                if candidate_tok > self._config.max_tokens:
                    break
                current.append(segments[j])
                j += 1

            # Single segment exceeds max_tokens → fall back to fixed splitting
            if len(current) == 1 and seg_tokens[i] > self._config.max_tokens:
                for sc in self._chunk_fixed(segments[i]):
                    chunks.append(
                        TextChunk(
                            content=sc.content,
                            chunk_index=len(chunks),
                            token_count=sc.token_count,
                        )
                    )
                i += 1
                continue

            chunk_text = joiner.join(current)
            chunks.append(
                TextChunk(
                    content=chunk_text,
                    chunk_index=len(chunks),
                    token_count=self.count_tokens(chunk_text),
                )
            )

            consumed_end = j  # exclusive index of last consumed segment + 1
            if consumed_end >= len(segments):
                break

            # Compute overlap: walk backward from consumed_end to find the
            # segment index where the overlap region starts.
            i = self._overlap_start(seg_tokens, i, consumed_end)

        return chunks

    def _overlap_start(
        self,
        seg_tokens: list[int],
        chunk_start: int,
        chunk_end: int,
    ) -> int:
        """Return the segment index where the overlap region starts.

        Walks backward from *chunk_end* and includes trailing segments whose
        cumulative token count stays within ``overlap_tokens``.  Always
        advances past *chunk_start* to prevent infinite loops.
        """
        budget = self._config.overlap_tokens
        accumulated = 0
        idx = chunk_end - 1

        while idx > chunk_start and accumulated + seg_tokens[idx] <= budget:
            accumulated += seg_tokens[idx]
            idx -= 1

        result = idx + 1

        # Must advance past chunk_start to prevent infinite loops
        if result <= chunk_start:
            result = chunk_end

        return result

    # ------------------------------------------------------------------
    # Fixed (token-window) chunking
    # ------------------------------------------------------------------

    def _chunk_fixed(self, text: str) -> list[TextChunk]:
        """Split *text* by raw token count with sliding-window overlap."""
        all_tokens = self._enc.encode(text)
        total = len(all_tokens)

        if total <= self._config.max_tokens:
            return [TextChunk(content=text, chunk_index=0, token_count=total)]

        step = max(1, self._config.max_tokens - self._config.overlap_tokens)
        chunks: list[TextChunk] = []
        pos = 0

        while pos < total:
            end = min(pos + self._config.max_tokens, total)
            window = all_tokens[pos:end]
            chunks.append(
                TextChunk(
                    content=self._enc.decode(window),
                    chunk_index=len(chunks),
                    token_count=len(window),
                )
            )
            if end >= total:
                break
            pos += step

        return chunks
