"""Embedding-based Semantic Coherence Chunker.

Determines chunk boundaries by measuring semantic coherence between
adjacent sentences using cosine similarity of their embeddings.  Unlike
the regex-based SEMANTIC strategy in ``chunking.py``, this approach
identifies *topic shifts* — coherence breakpoints where the subject
matter changes — rather than relying on punctuation heuristics.

Algorithm overview
------------------

1. **Sentence segmentation**: Split the document into sentences using a
   robust regex that handles abbreviations, decimal numbers, and
   inline code far better than a naive ``[.!?]`` split.

2. **Sentence embedding**: Compute a dense vector for each sentence.
   The caller provides an async embedding function, keeping the chunker
   decoupled from any specific provider (OpenAI, Sentence Transformers, …).

3. **Pairwise similarity**: Compute cosine similarity between every
   consecutive sentence pair, yielding a *coherence curve*.

4. **Breakpoint detection**: Identify local minima in the coherence
   curve that fall below a dynamic threshold.  The threshold adapts
   to the document's own statistics (mean − ``sensitivity`` × stddev).

5. **Token-bounded grouping**: Merge sentence groups into chunks that
   respect the configured ``max_tokens`` limit.  Groups that exceed
   the limit are recursively sub-split; undersized trailing groups
   are merged into their predecessor.

6. **Overlap injection**: Carry the last ``overlap_sentences`` sentences
   of the previous chunk into the next for cross-chunk context.

Complexity
----------
Let *n* = number of sentences.

- Embedding: O(n) API calls (batched).
- Similarity: O(n) dot products in ℝ^d.
- Breakpoint detection: O(n) scan.
- Grouping + token counting: O(n · t) where t = avg tokens per sentence.

Total is dominated by the embedding step.
"""

from __future__ import annotations

import logging
import math
import re
import statistics
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import tiktoken

logger = logging.getLogger(__name__)

__all__ = [
    "CoherenceBreakpoint",
    "CoherenceChunkerConfig",
    "SemanticCoherenceChunker",
]

# Type alias for the embedding function the caller must provide.
# Signature:  async (list[str]) -> list[list[float]]
EmbedFn = Callable[[list[str]], Coroutine[Any, Any, list[list[float]]]]


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CoherenceChunkerConfig:
    """Configuration for the semantic coherence chunker.

    Attributes
    ----------
    max_tokens:
        Hard upper bound on tokens per chunk.
    min_tokens:
        Trailing chunks below this threshold are merged into the
        preceding chunk (unless the chunk is the only one).
    overlap_sentences:
        Number of trailing sentences to carry into the next chunk
        for cross-boundary context.
    sensitivity:
        Controls how aggressively breakpoints are detected.
        threshold = mean(similarities) − sensitivity × stddev(similarities).
        Higher values → fewer, stronger breakpoints.
    min_sentences_per_group:
        Minimum consecutive sentences between two breakpoints.
        Prevents single-sentence fragments from forming their own chunks.
    embed_batch_size:
        Maximum number of sentences embedded in a single API call.
    """

    max_tokens: int = 512
    min_tokens: int = 48
    overlap_sentences: int = 2
    sensitivity: float = 1.0
    min_sentences_per_group: int = 2
    embed_batch_size: int = 64


@dataclass(frozen=True, slots=True)
class CoherenceBreakpoint:
    """A detected topic-shift breakpoint between two sentences.

    Attributes
    ----------
    position:
        Index of the sentence *after* the breakpoint (0-based).
        A breakpoint at position *i* means sentences [0..i-1] form
        one coherent group and sentences [i..] start a new topic.
    similarity:
        Cosine similarity between sentence[position-1] and sentence[position].
    threshold:
        The adaptive threshold at the time of detection.
    """

    position: int
    similarity: float
    threshold: float


# ------------------------------------------------------------------
# Sentence segmentation
# ------------------------------------------------------------------

# Abbreviations that should NOT trigger a sentence split.
_ABBREVIATIONS = frozenset({
    "dr", "mr", "mrs", "ms", "prof", "inc", "ltd", "jr", "sr",
    "vs", "etc", "ca", "bzw", "vgl", "nr", "abs", "art",
    "st", "ft", "approx", "dept", "est", "govt", "assn",
})

# Matches a potential sentence boundary: punctuation [.!?] followed by
# whitespace and an uppercase letter (or digit, or end-of-string).
_BOUNDARY_CANDIDATE_RE = re.compile(
    r'([.!?])'
    r'(["\')]?\s+)'
    r'(?=[A-ZÄÖÜ\d])',
    re.MULTILINE,
)


def segment_sentences(text: str) -> list[str]:
    """Split *text* into sentences with a robust boundary regex.

    Uses a two-pass approach to avoid false splits on abbreviations
    and decimal numbers:

    1. Find all candidate boundaries (punctuation + space + uppercase).
    2. Filter out false positives: digits before '.', known abbreviations.

    Returns
    -------
    list[str]
        Non-empty stripped sentences.
    """
    if not text or not text.strip():
        return []

    boundaries: list[int] = []
    for match in _BOUNDARY_CANDIDATE_RE.finditer(text):
        punct_pos = match.start(1)

        # Skip if this is a decimal point (digit.digit pattern like 3.14)
        if match.group(1) == "." and punct_pos > 0 and text[punct_pos - 1].isdigit():
            # Only skip if the next non-space char is also a digit
            rest = text[punct_pos + 1:].lstrip()
            if rest and rest[0].isdigit():
                continue

        # Skip if the word before the period is a known abbreviation
        if match.group(1) == ".":
            # Walk backwards to find the word before the period
            word_end = punct_pos
            word_start = word_end
            while word_start > 0 and text[word_start - 1].isalpha():
                word_start -= 1
            word = text[word_start:word_end].lower()
            if word in _ABBREVIATIONS:
                continue

            # Skip single-letter initials (e.g., "J." in "J. K. Rowling")
            if len(word) == 1 and word.isalpha():
                continue

        # Valid boundary — split after the whitespace
        boundaries.append(match.end(2))

    if not boundaries:
        stripped = text.strip()
        return [stripped] if stripped else []

    parts: list[str] = []
    last_end = 0
    for boundary in boundaries:
        segment = text[last_end:boundary].strip()
        if segment:
            parts.append(segment)
        last_end = boundary

    tail = text[last_end:].strip()
    if tail:
        parts.append(tail)

    return parts


# ------------------------------------------------------------------
# Linear algebra helpers (no numpy dependency)
# ------------------------------------------------------------------


def _dot(a: list[float], b: list[float]) -> float:
    """Dot product of two vectors."""
    return sum(x * y for x, y in zip(a, b, strict=True))


def _norm(v: list[float]) -> float:
    """L2 norm of a vector."""
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors.

    Returns 0.0 if either vector has zero norm (degenerate input).
    """
    norm_a = _norm(a)
    norm_b = _norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(a, b) / (norm_a * norm_b)


# ------------------------------------------------------------------
# Breakpoint detection
# ------------------------------------------------------------------


def detect_breakpoints(
    similarities: list[float],
    *,
    sensitivity: float = 1.0,
    min_gap: int = 2,
) -> list[CoherenceBreakpoint]:
    """Find topic-shift breakpoints in a coherence curve.

    A breakpoint is a *local minimum* in the pairwise similarity
    sequence whose value falls below an adaptive threshold.

    The threshold adapts to the document's own statistics::

        threshold = mean(similarities) - sensitivity * stdev(similarities)

    This makes the algorithm robust to documents with uniformly high or
    low coherence — the breakpoints are relative to the document's own
    baseline, not an absolute cutoff.

    Parameters
    ----------
    similarities:
        Pairwise cosine similarities: ``similarities[i]`` is the
        similarity between sentence *i* and sentence *i+1*.
        Length = (num_sentences - 1).
    sensitivity:
        Number of standard deviations below the mean to set the
        threshold.  Higher → fewer breakpoints.
    min_gap:
        Minimum distance (in sentence indices) between consecutive
        breakpoints.  Prevents over-fragmentation.

    Returns
    -------
    list[CoherenceBreakpoint]
        Breakpoints sorted by position (ascending).
    """
    n = len(similarities)
    if n < 3:
        return []

    mean_sim = statistics.mean(similarities)
    stdev_sim = statistics.stdev(similarities) if n >= 2 else 0.0

    # Adaptive threshold — documents with low variance won't produce
    # spurious breakpoints because stdev is small.
    threshold = mean_sim - sensitivity * stdev_sim

    breakpoints: list[CoherenceBreakpoint] = []
    last_bp_pos = -min_gap  # sentinel so the first BP is always eligible

    for i in range(1, n - 1):
        # Local minimum: lower than both neighbours
        is_local_min = (
            similarities[i] < similarities[i - 1]
            and similarities[i] < similarities[i + 1]
        )

        # Below adaptive threshold
        below_threshold = similarities[i] < threshold

        # Sufficient distance from the last breakpoint
        far_enough = (i + 1) - last_bp_pos >= min_gap

        if is_local_min and below_threshold and far_enough:
            # Breakpoint *position* is i+1 (the sentence after the dip).
            bp = CoherenceBreakpoint(
                position=i + 1,
                similarity=similarities[i],
                threshold=threshold,
            )
            breakpoints.append(bp)
            last_bp_pos = i + 1

    return breakpoints


# ------------------------------------------------------------------
# Main chunker class
# ------------------------------------------------------------------


class SemanticCoherenceChunker:
    """Token-bounded chunker driven by embedding-based coherence.

    Unlike regex-based chunkers that split at punctuation boundaries,
    this chunker identifies **topic shifts** by measuring how similar
    consecutive sentences are in embedding space.  Chunk boundaries
    are placed at points of low coherence, so each chunk covers a
    single coherent topic segment.

    Parameters
    ----------
    embed_fn:
        Async function ``(texts: list[str]) -> list[list[float]]``.
        The chunker is decoupled from the embedding provider.
    config:
        Chunker configuration.
    """

    def __init__(
        self,
        embed_fn: EmbedFn,
        config: CoherenceChunkerConfig | None = None,
    ) -> None:
        self._embed = embed_fn
        self._config = config or CoherenceChunkerConfig()
        self._enc = tiktoken.get_encoding("cl100k_base")

    @property
    def config(self) -> CoherenceChunkerConfig:
        return self._config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chunk(self, text: str) -> list[CoherenceChunk]:
        """Split *text* into semantically coherent, token-bounded chunks.

        Steps
        -----
        1. Segment text into sentences.
        2. Embed all sentences (batched).
        3. Compute pairwise cosine similarities.
        4. Detect coherence breakpoints.
        5. Group sentences between breakpoints.
        6. Enforce token limits (split oversized groups, merge tiny ones).
        7. Inject overlap sentences.

        Returns
        -------
        list[CoherenceChunk]
            Chunks with content, token count, and coherence metadata.
        """
        sentences = segment_sentences(text)

        if not sentences:
            return [CoherenceChunk(content="", chunk_index=0, token_count=0, avg_coherence=0.0)]

        if len(sentences) == 1:
            total_tokens = self._count_tokens(text)
            if total_tokens <= self._config.max_tokens:
                return [
                    CoherenceChunk(
                        content=text.strip(),
                        chunk_index=0,
                        token_count=total_tokens,
                        avg_coherence=1.0,
                    )
                ]
            return self._split_long_sentence(sentences[0])

        # Embed all sentences in batches
        embeddings = await self._embed_batched(sentences)

        # Pairwise cosine similarities
        similarities = [
            cosine_similarity(embeddings[i], embeddings[i + 1])
            for i in range(len(embeddings) - 1)
        ]

        # Detect breakpoints
        breakpoints = detect_breakpoints(
            similarities,
            sensitivity=self._config.sensitivity,
            min_gap=self._config.min_sentences_per_group,
        )

        # Group sentences between breakpoints
        groups = self._group_by_breakpoints(sentences, similarities, breakpoints)

        # Enforce token limits
        bounded_groups = self._enforce_token_limits(groups)

        # Build final chunks with overlap
        return self._build_chunks_with_overlap(bounded_groups, sentences)

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    async def _embed_batched(self, sentences: list[str]) -> list[list[float]]:
        """Embed sentences in batches of ``embed_batch_size``."""
        all_embeddings: list[list[float]] = []

        for start in range(0, len(sentences), self._config.embed_batch_size):
            batch = sentences[start : start + self._config.embed_batch_size]
            batch_embeddings = await self._embed(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    # ------------------------------------------------------------------
    # Grouping
    # ------------------------------------------------------------------

    def _group_by_breakpoints(
        self,
        sentences: list[str],
        similarities: list[float],
        breakpoints: list[CoherenceBreakpoint],
    ) -> list[_SentenceGroup]:
        """Partition sentences into groups delimited by breakpoints."""
        groups: list[_SentenceGroup] = []
        bp_positions = [bp.position for bp in breakpoints]

        group_start = 0
        for bp_pos in bp_positions:
            group_sents = sentences[group_start:bp_pos]
            group_sims = similarities[group_start : bp_pos - 1] if bp_pos - 1 > group_start else []
            groups.append(_SentenceGroup(
                sentences=group_sents,
                start_index=group_start,
                avg_coherence=statistics.mean(group_sims) if group_sims else 1.0,
            ))
            group_start = bp_pos

        # Trailing group
        trailing = sentences[group_start:]
        if trailing:
            end = len(sentences) - 1
            trailing_sims = (
                similarities[group_start:end]
                if end > group_start
                else []
            )
            groups.append(_SentenceGroup(
                sentences=trailing,
                start_index=group_start,
                avg_coherence=statistics.mean(trailing_sims) if trailing_sims else 1.0,
            ))

        return groups

    # ------------------------------------------------------------------
    # Token limit enforcement
    # ------------------------------------------------------------------

    def _enforce_token_limits(
        self,
        groups: list[_SentenceGroup],
    ) -> list[_SentenceGroup]:
        """Split oversized groups and merge undersized trailing ones.

        Oversized groups are split at the midpoint recursively until
        every group fits within ``max_tokens``.

        Undersized trailing groups (below ``min_tokens``) are merged
        into their predecessor.
        """
        # Phase 1: Split oversized groups
        split_groups: list[_SentenceGroup] = []
        for group in groups:
            split_groups.extend(self._split_if_oversized(group))

        if not split_groups:
            return split_groups

        # Phase 2: Merge undersized trailing groups
        merged: list[_SentenceGroup] = [split_groups[0]]
        for group in split_groups[1:]:
            group_tokens = self._count_tokens(" ".join(group.sentences))
            prev_tokens = self._count_tokens(" ".join(merged[-1].sentences))

            can_merge = (
                group_tokens < self._config.min_tokens
                and prev_tokens + group_tokens <= self._config.max_tokens
            )
            if can_merge:
                # Merge into predecessor
                merged[-1] = _SentenceGroup(
                    sentences=merged[-1].sentences + group.sentences,
                    start_index=merged[-1].start_index,
                    avg_coherence=(merged[-1].avg_coherence + group.avg_coherence) / 2,
                )
            else:
                merged.append(group)

        return merged

    def _split_if_oversized(self, group: _SentenceGroup) -> list[_SentenceGroup]:
        """Recursively split a group until it fits within max_tokens."""
        text = " ".join(group.sentences)
        if self._count_tokens(text) <= self._config.max_tokens:
            return [group]

        if len(group.sentences) <= 1:
            # Single sentence exceeds max_tokens — accept it as-is
            # (the fixed chunking fallback in the pipeline will handle it)
            return [group]

        # Split at the midpoint
        mid = len(group.sentences) // 2
        left = _SentenceGroup(
            sentences=group.sentences[:mid],
            start_index=group.start_index,
            avg_coherence=group.avg_coherence,
        )
        right = _SentenceGroup(
            sentences=group.sentences[mid:],
            start_index=group.start_index + mid,
            avg_coherence=group.avg_coherence,
        )

        return self._split_if_oversized(left) + self._split_if_oversized(right)

    # ------------------------------------------------------------------
    # Chunk building with overlap
    # ------------------------------------------------------------------

    def _build_chunks_with_overlap(
        self,
        groups: list[_SentenceGroup],
        all_sentences: list[str],
    ) -> list[CoherenceChunk]:
        """Build final chunks, injecting overlap sentences from the previous group."""
        if not groups:
            return []

        chunks: list[CoherenceChunk] = []
        overlap_count = self._config.overlap_sentences

        for idx, group in enumerate(groups):
            sentences = list(group.sentences)

            # Inject overlap from the previous group (if not the first chunk)
            if idx > 0 and overlap_count > 0:
                prev_sents = groups[idx - 1].sentences
                overlap_sents = prev_sents[-overlap_count:]
                sentences = list(overlap_sents) + sentences

            text = " ".join(sentences)
            chunks.append(CoherenceChunk(
                content=text,
                chunk_index=idx,
                token_count=self._count_tokens(text),
                avg_coherence=group.avg_coherence,
            ))

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def _split_long_sentence(self, sentence: str) -> list[CoherenceChunk]:
        """Handle a single sentence that exceeds max_tokens via fixed split."""
        tokens = self._enc.encode(sentence)
        total = len(tokens)

        if total <= self._config.max_tokens:
            return [
                CoherenceChunk(
                    content=sentence,
                    chunk_index=0,
                    token_count=total,
                    avg_coherence=1.0,
                )
            ]

        step = max(1, self._config.max_tokens - (self._config.overlap_sentences * 20))
        chunks: list[CoherenceChunk] = []
        pos = 0

        while pos < total:
            end = min(pos + self._config.max_tokens, total)
            window = tokens[pos:end]
            chunks.append(CoherenceChunk(
                content=self._enc.decode(window),
                chunk_index=len(chunks),
                token_count=len(window),
                avg_coherence=1.0,
            ))
            if end >= total:
                break
            pos += step

        return chunks


# ------------------------------------------------------------------
# Internal dataclasses
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CoherenceChunk:
    """A chunk produced by the semantic coherence chunker.

    Extends the basic ``TextChunk`` concept with a coherence metric
    that indicates how semantically unified the chunk's content is.

    Attributes
    ----------
    content:
        The chunk text.
    chunk_index:
        0-based index in the chunk sequence.
    token_count:
        Number of tokens (cl100k_base encoding).
    avg_coherence:
        Average pairwise cosine similarity between consecutive
        sentences within this chunk.  1.0 = perfectly coherent
        (single sentence or uniform topic).
    """

    content: str
    chunk_index: int
    token_count: int
    avg_coherence: float


@dataclass(slots=True)
class _SentenceGroup:
    """Internal grouping of consecutive sentences between breakpoints."""

    sentences: list[str]
    start_index: int
    avg_coherence: float

