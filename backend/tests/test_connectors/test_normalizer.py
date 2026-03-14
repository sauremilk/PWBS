"""Tests for UnifiedDocument normalizer (TASK-044)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from pwbs.connectors.normalizer import (
    compute_content_hash,
    compute_expiry,
    has_content_changed,
    normalize_document,
)
from pwbs.schemas.enums import ContentType, SourceType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    def test_deterministic(self) -> None:
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_sha256_length(self) -> None:
        h = compute_content_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_content_different_hash(self) -> None:
        assert compute_content_hash("foo") != compute_content_hash("bar")

    def test_empty_string(self) -> None:
        h = compute_content_hash("")
        assert len(h) == 64


# ---------------------------------------------------------------------------
# compute_expiry
# ---------------------------------------------------------------------------


class TestComputeExpiry:
    def test_default_google_calendar(self) -> None:
        now = datetime.now(tz=UTC)
        expiry = compute_expiry(SourceType.GOOGLE_CALENDAR, base_time=now)
        assert expiry == now + timedelta(days=365)

    def test_default_zoom(self) -> None:
        now = datetime.now(tz=UTC)
        expiry = compute_expiry(SourceType.ZOOM, base_time=now)
        assert expiry == now + timedelta(days=180)

    def test_custom_retention(self) -> None:
        now = datetime.now(tz=UTC)
        expiry = compute_expiry(SourceType.NOTION, base_time=now, retention_days=90)
        assert expiry == now + timedelta(days=90)

    def test_fallback_for_unknown_source(self) -> None:
        """Sources without explicit retention use the fallback (365 days)."""
        now = datetime.now(tz=UTC)
        expiry = compute_expiry(SourceType.OBSIDIAN, base_time=now)
        # OBSIDIAN has 730 days in the mapping
        assert expiry == now + timedelta(days=730)


# ---------------------------------------------------------------------------
# has_content_changed
# ---------------------------------------------------------------------------


class TestHasContentChanged:
    def test_same_content(self) -> None:
        h = compute_content_hash("same")
        assert has_content_changed(h, "same") is False

    def test_different_content(self) -> None:
        h = compute_content_hash("old")
        assert has_content_changed(h, "new") is True


# ---------------------------------------------------------------------------
# normalize_document
# ---------------------------------------------------------------------------


class TestNormalizeDocument:
    def test_minimal_valid(self, owner_id: uuid.UUID) -> None:
        doc = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.NOTION,
            source_id="page-123",
            title="Test Page",
            content="Hello World",
        )
        assert doc.user_id == owner_id
        assert doc.source_type == SourceType.NOTION
        assert doc.source_id == "page-123"
        assert doc.title == "Test Page"
        assert doc.content == "Hello World"
        assert doc.content_type == ContentType.PLAINTEXT
        assert doc.language == "de"
        assert doc.raw_hash == compute_content_hash("Hello World")
        assert doc.expires_at is not None
        assert doc.metadata == {}
        assert doc.participants == []

    def test_custom_fields(self, owner_id: uuid.UUID) -> None:
        now = datetime.now(tz=UTC)
        doc_id = uuid.uuid4()
        doc = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.ZOOM,
            source_id="meeting-456",
            title="Standup",
            content="Meeting transcript",
            content_type=ContentType.MARKDOWN,
            metadata={"duration": 30},
            participants=["alice@example.com"],
            language="en",
            created_at=now,
            updated_at=now,
            document_id=doc_id,
        )
        assert doc.id == doc_id
        assert doc.content_type == ContentType.MARKDOWN
        assert doc.metadata == {"duration": 30}
        assert doc.participants == ["alice@example.com"]
        assert doc.language == "en"
        assert doc.created_at == now
        assert doc.updated_at == now

    def test_expiry_auto_computed(self, owner_id: uuid.UUID) -> None:
        doc = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.ZOOM,
            source_id="m-1",
            title="t",
            content="c",
        )
        # Zoom default: 180 days
        assert doc.expires_at is not None
        expected_min = datetime.now(tz=UTC) + timedelta(days=179)
        assert doc.expires_at > expected_min

    def test_explicit_expiry_overrides_default(self, owner_id: uuid.UUID) -> None:
        custom_expiry = datetime(2027, 1, 1, tzinfo=UTC)
        doc = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.NOTION,
            source_id="p-1",
            title="t",
            content="c",
            expires_at=custom_expiry,
        )
        assert doc.expires_at == custom_expiry

    def test_content_hash_consistency(self, owner_id: uuid.UUID) -> None:
        """Two documents with the same content get the same hash."""
        doc1 = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.NOTION,
            source_id="a",
            title="t",
            content="identical content",
        )
        doc2 = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.NOTION,
            source_id="b",
            title="t2",
            content="identical content",
        )
        assert doc1.raw_hash == doc2.raw_hash

    def test_generates_uuid_if_none(self, owner_id: uuid.UUID) -> None:
        doc = normalize_document(
            owner_id=owner_id,
            source_type=SourceType.OBSIDIAN,
            source_id="note-1",
            title="Note",
            content="text",
        )
        assert doc.id is not None
        assert isinstance(doc.id, uuid.UUID)
