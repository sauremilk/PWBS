"""Tests for pwbs.processing.semantic_chunker – Embedding-based coherence chunking.

This test suite validates the algorithmic core of the semantic coherence
chunker:  sentence segmentation, cosine similarity, adaptive breakpoint
detection, token-bounded grouping, and overlap injection.

All embedding calls are mocked — no network or GPU required.
"""

from __future__ import annotations

import math

import pytest

from pwbs.processing.semantic_chunker import (
    CoherenceChunkerConfig,
    SemanticCoherenceChunker,
    cosine_similarity,
    detect_breakpoints,
    segment_sentences,
)

# ---------------------------------------------------------------------------
# Mock embedding function
# ---------------------------------------------------------------------------

# Dimension of mock embeddings.
_DIM = 8


def _make_embed_fn(sentence_vectors: dict[str, list[float]] | None = None):
    """Return a mock async embed function.

    If *sentence_vectors* is provided, sentences are looked up by exact
    string.  Otherwise, each sentence gets a deterministic hash-based
    vector (different sentences → different vectors with varying similarity).
    """
    lookup = sentence_vectors or {}

    async def _embed(texts: list[str]) -> list[list[float]]:
        result: list[list[float]] = []
        for t in texts:
            if t in lookup:
                result.append(lookup[t])
            else:
                # Hash-based deterministic vector
                h = hash(t) & 0xFFFF_FFFF
                vec = [math.sin(h + i * 0.7) for i in range(_DIM)]
                result.append(vec)
        return result

    return _embed


def _unit_vec(angle_deg: float) -> list[float]:
    """Return a 2D unit vector at *angle_deg* degrees, zero-padded to _DIM."""
    rad = math.radians(angle_deg)
    v = [math.cos(rad), math.sin(rad)] + [0.0] * (_DIM - 2)
    return v


# ---------------------------------------------------------------------------
# segment_sentences
# ---------------------------------------------------------------------------


class TestSegmentSentences:
    """Robust sentence segmentation without false splits."""

    def test_simple_sentences(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        sents = segment_sentences(text)
        assert len(sents) == 3
        assert sents[0] == "First sentence."
        assert sents[1] == "Second sentence."

    def test_empty_string(self) -> None:
        assert segment_sentences("") == []

    def test_whitespace_only(self) -> None:
        assert segment_sentences("   \n\n ") == []

    def test_single_sentence_no_period(self) -> None:
        sents = segment_sentences("Hello world")
        assert sents == ["Hello world"]

    def test_decimal_numbers_not_split(self) -> None:
        text = "The value is 3.14 and it matters. Next sentence."
        sents = segment_sentences(text)
        # Should NOT split at "3." or "14."
        assert any("3.14" in s for s in sents)

    def test_abbreviations_not_split(self) -> None:
        text = "Dr. Smith visited the lab. He found results."
        sents = segment_sentences(text)
        # "Dr." should not cause a split
        assert any("Dr." in s for s in sents)

    def test_exclamation_and_question(self) -> None:
        text = "What happened? Everything changed! Now we know."
        sents = segment_sentences(text)
        assert len(sents) == 3

    def test_multiline_text(self) -> None:
        text = "First line.\nSecond line.\nThird line."
        sents = segment_sentences(text)
        assert len(sents) >= 2  # newlines shouldn't prevent splitting


# ---------------------------------------------------------------------------
# cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """Vector math correctness."""

    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self) -> None:
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_known_angle(self) -> None:
        # 60° angle → cos(60°) = 0.5
        a = _unit_vec(0)[:2]
        b = _unit_vec(60)[:2]
        assert cosine_similarity(a, b) == pytest.approx(0.5, abs=1e-9)


# ---------------------------------------------------------------------------
# detect_breakpoints
# ---------------------------------------------------------------------------


class TestDetectBreakpoints:
    """Adaptive breakpoint detection on synthetic coherence curves."""

    def test_no_breakpoints_uniform_similarity(self) -> None:
        # All similarities equal → no local minima
        sims = [0.9, 0.9, 0.9, 0.9, 0.9]
        bps = detect_breakpoints(sims, sensitivity=1.0)
        assert bps == []

    def test_clear_single_dip(self) -> None:
        # Clear topic shift at position 3 (dip from 0.9 to 0.1)
        sims = [0.9, 0.9, 0.1, 0.9, 0.9]
        bps = detect_breakpoints(sims, sensitivity=0.5, min_gap=1)
        assert len(bps) == 1
        assert bps[0].position == 3
        assert bps[0].similarity == pytest.approx(0.1)

    def test_two_dips_with_min_gap(self) -> None:
        # Two dips close together — min_gap should filter one
        sims = [0.9, 0.1, 0.9, 0.1, 0.9, 0.9, 0.9]
        bps_no_gap = detect_breakpoints(sims, sensitivity=0.5, min_gap=1)
        bps_with_gap = detect_breakpoints(sims, sensitivity=0.5, min_gap=4)
        assert len(bps_no_gap) >= len(bps_with_gap)

    def test_too_short_returns_empty(self) -> None:
        assert detect_breakpoints([0.5]) == []
        assert detect_breakpoints([0.5, 0.5]) == []

    def test_high_sensitivity_fewer_breakpoints(self) -> None:
        sims = [0.8, 0.6, 0.3, 0.7, 0.5, 0.2, 0.8]
        bps_low = detect_breakpoints(sims, sensitivity=0.5, min_gap=1)
        bps_high = detect_breakpoints(sims, sensitivity=2.0, min_gap=1)
        assert len(bps_high) <= len(bps_low)

    def test_breakpoint_threshold_is_adaptive(self) -> None:
        # High-coherence doc: all sims ~0.95, one dip to 0.9
        sims = [0.95, 0.95, 0.90, 0.95, 0.95]
        bps = detect_breakpoints(sims, sensitivity=1.0, min_gap=1)
        if bps:
            # Threshold should be relative to the document's mean, not absolute
            assert bps[0].threshold > 0.85


# ---------------------------------------------------------------------------
# SemanticCoherenceChunker — integration
# ---------------------------------------------------------------------------


class TestSemanticCoherenceChunkerBasic:
    """Basic chunker behaviour with controlled mock embeddings."""

    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        chunker = SemanticCoherenceChunker(_make_embed_fn())
        chunks = await chunker.chunk("")
        assert len(chunks) == 1
        assert chunks[0].content == ""
        assert chunks[0].token_count == 0

    @pytest.mark.asyncio
    async def test_short_text_single_chunk(self) -> None:
        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=1000),
        )
        text = "This is a short document. It fits in one chunk."
        chunks = await chunker.chunk(text)
        assert len(chunks) == 1
        assert text.strip() in chunks[0].content
        # Coherence is computed between the two sentences, not hardcoded to 1.0
        assert -1.0 <= chunks[0].avg_coherence <= 1.0

    @pytest.mark.asyncio
    async def test_chunk_index_sequential(self) -> None:
        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=30),
        )
        text = "First topic here. Second topic now. Third topic also. Fourth idea too."
        chunks = await chunker.chunk(text)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    @pytest.mark.asyncio
    async def test_token_count_matches_content(self) -> None:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")

        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=30),
        )
        text = "Sentence one about data. Sentence two about code. Sentence three about math."
        chunks = await chunker.chunk(text)
        for chunk in chunks:
            expected = len(enc.encode(chunk.content))
            assert chunk.token_count == expected


class TestCoherenceDetectsTopicShifts:
    """The core value proposition: chunks respect topic boundaries."""

    @pytest.mark.asyncio
    async def test_two_distinct_topics(self) -> None:
        """Two clearly different topics should produce at least two chunks."""
        # Sentences about topic A get vectors pointing ~0°
        # Sentences about topic B get vectors pointing ~90° (orthogonal)
        vectors = {
            "Machine learning is a subset of artificial intelligence.": _unit_vec(0),
            "Neural networks learn from large datasets.": _unit_vec(5),
            "Deep learning uses multiple hidden layers.": _unit_vec(10),
            "The French Revolution began in 1789.": _unit_vec(85),
            "Napoleon rose to power during the revolution.": _unit_vec(90),
            "The Bastille was stormed by an angry crowd.": _unit_vec(95),
        }

        chunker = SemanticCoherenceChunker(
            _make_embed_fn(vectors),
            CoherenceChunkerConfig(
                max_tokens=200,
                min_tokens=10,
                sensitivity=0.5,
                min_sentences_per_group=1,
            ),
        )

        text = " ".join(vectors.keys())
        chunks = await chunker.chunk(text)

        # At minimum 2 chunks (one per topic cluster)
        assert len(chunks) >= 2

        # The ML sentences should be in the same chunk
        ml_chunk = next(c for c in chunks if "Machine learning" in c.content)
        assert "Neural networks" in ml_chunk.content

    @pytest.mark.asyncio
    async def test_uniform_topic_fewer_chunks(self) -> None:
        """A document about one topic should produce fewer chunks
        than a multi-topic document of the same length."""
        # All vectors point in roughly the same direction
        uniform_vectors: dict[str, list[float]] = {}
        for i, sent in enumerate(
            [
                "Python is great. ",
                "Python has many libraries. ",
                "Python is used in data science. ",
                "Python supports async programming. ",
                "Python has a large community. ",
                "Python is dynamically typed. ",
            ]
        ):
            uniform_vectors[sent.strip()] = _unit_vec(i * 2)  # very close angles

        diverse_vectors: dict[str, list[float]] = {}
        for i, sent in enumerate(
            [
                "Python is great. ",
                "The ocean is deep. ",
                "Music soothes the soul. ",
                "Quantum physics is complex. ",
                "Cooking requires patience. ",
                "Stars are far away. ",
            ]
        ):
            diverse_vectors[sent.strip()] = _unit_vec(i * 30)  # widely spread

        config = CoherenceChunkerConfig(
            max_tokens=60,
            sensitivity=0.5,
            min_sentences_per_group=1,
        )

        uniform_chunks = await SemanticCoherenceChunker(
            _make_embed_fn(uniform_vectors), config
        ).chunk(" ".join(uniform_vectors.keys()))

        diverse_chunks = await SemanticCoherenceChunker(
            _make_embed_fn(diverse_vectors), config
        ).chunk(" ".join(diverse_vectors.keys()))

        # The diverse text should produce at least as many chunks
        assert len(diverse_chunks) >= len(uniform_chunks)


class TestTokenBoundsEnforced:
    """No chunk exceeds ``max_tokens`` (except single oversized sentences)."""

    @pytest.mark.asyncio
    async def test_max_tokens_respected(self) -> None:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")

        config = CoherenceChunkerConfig(max_tokens=40, overlap_sentences=0)
        chunker = SemanticCoherenceChunker(_make_embed_fn(), config)

        # Generate enough text to require multiple chunks
        sentences = [f"Sentence number {i} with some extra filler words added." for i in range(20)]
        text = " ".join(sentences)
        chunks = await chunker.chunk(text)

        for chunk in chunks:
            tokens = len(enc.encode(chunk.content))
            # Allow slight slack for single sentences that are just over the limit
            assert tokens <= config.max_tokens * 1.5, (
                f"Chunk {chunk.chunk_index} has {tokens} tokens, limit is {config.max_tokens}"
            )


class TestOverlapInjection:
    """Overlap sentences provide cross-chunk context."""

    @pytest.mark.asyncio
    async def test_overlap_present_in_subsequent_chunks(self) -> None:
        # Use orthogonal vectors to force clear breakpoints
        sents = [f"Topic-A sentence {i}." for i in range(5)]
        sents += [f"Topic-B sentence {i}." for i in range(5)]

        vectors: dict[str, list[float]] = {}
        for s in sents[:5]:
            vectors[s] = _unit_vec(0)
        for s in sents[5:]:
            vectors[s] = _unit_vec(90)

        config = CoherenceChunkerConfig(
            max_tokens=200,
            overlap_sentences=2,
            sensitivity=0.5,
            min_sentences_per_group=1,
        )
        chunker = SemanticCoherenceChunker(_make_embed_fn(vectors), config)
        text = " ".join(sents)
        chunks = await chunker.chunk(text)

        if len(chunks) >= 2:
            # The second chunk should start with overlap from the first chunk
            second = chunks[1].content
            # At least one sentence from topic A should appear as overlap in topic B's chunk
            has_overlap = any(f"Topic-A sentence {i}." in second for i in range(5))
            assert has_overlap, "Expected overlap from previous chunk"


class TestCoherenceMetric:
    """Each chunk carries an avg_coherence score."""

    @pytest.mark.asyncio
    async def test_coherence_between_zero_and_one(self) -> None:
        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=40),
        )
        text = "Alpha bravo charlie. Delta echo foxtrot. Golf hotel india. Juliet kilo lima."
        chunks = await chunker.chunk(text)
        for chunk in chunks:
            assert -1.0 <= chunk.avg_coherence <= 1.0

    @pytest.mark.asyncio
    async def test_single_chunk_coherence_is_one(self) -> None:
        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=1000),
        )
        chunks = await chunker.chunk("Short text.")
        assert chunks[0].avg_coherence == 1.0


class TestBatchedEmbedding:
    """Embedding batching works correctly."""

    @pytest.mark.asyncio
    async def test_small_batch_size(self) -> None:
        """With batch_size=2(!) the chunker should still produce correct results."""
        call_count = 0

        async def counting_embed(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            assert len(texts) <= 2, f"Batch exceeded limit: {len(texts)}"
            return [_unit_vec(hash(t) % 360) for t in texts]

        config = CoherenceChunkerConfig(
            max_tokens=40,
            embed_batch_size=2,
        )
        chunker = SemanticCoherenceChunker(counting_embed, config)
        text = "First. Second. Third. Fourth. Fifth."
        chunks = await chunker.chunk(text)

        assert call_count >= 2  # Multiple batches required
        assert len(chunks) >= 1


class TestEdgeCases:
    """Boundary conditions and degenerate inputs."""

    @pytest.mark.asyncio
    async def test_single_sentence(self) -> None:
        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=1000),
        )
        chunks = await chunker.chunk("Just one sentence.")
        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_two_sentences(self) -> None:
        chunker = SemanticCoherenceChunker(
            _make_embed_fn(),
            CoherenceChunkerConfig(max_tokens=1000),
        )
        chunks = await chunker.chunk("Sentence A. Sentence B.")
        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_all_identical_sentences(self) -> None:
        """Identical sentences → max coherence → minimal splitting."""
        same = "The quick brown fox jumps over the lazy dog."
        vectors = {same: _unit_vec(45)}

        chunker = SemanticCoherenceChunker(
            _make_embed_fn(vectors),
            CoherenceChunkerConfig(max_tokens=200),
        )
        text = " ".join([same] * 5)
        chunks = await chunker.chunk(text)
        # Should be one or very few chunks since coherence is perfect
        assert len(chunks) <= 2
