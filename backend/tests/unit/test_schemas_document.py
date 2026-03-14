"""Tests for pwbs.schemas.document – UnifiedDocument (TASK-032)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pwbs.schemas.document import UnifiedDocument
from pwbs.schemas.enums import ContentType, SourceType

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=timezone.utc)
_VALID_HASH = "a" * 64  # 64-char hex → valid SHA-256


def _make_doc(**overrides: object) -> dict:
    """Return a minimal valid UnifiedDocument payload as dict."""
    base: dict = {
        "id": uuid4(),
        "user_id": uuid4(),
        "source_type": SourceType.NOTION,
        "source_id": "page-123",
        "title": "Test Document",
        "content": "Hello world",
        "content_type": ContentType.PLAINTEXT,
        "created_at": _NOW,
        "updated_at": _NOW,
        "fetched_at": _NOW,
        "language": "de",
        "raw_hash": _VALID_HASH,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestUnifiedDocumentValid:
    """Verify that well-formed payloads are accepted."""

    def test_minimal_valid(self) -> None:
        doc = UnifiedDocument(**_make_doc())
        assert doc.source_type is SourceType.NOTION
        assert doc.content_type is ContentType.PLAINTEXT
        assert doc.metadata == {}
        assert doc.participants == []
        assert doc.expires_at is None

    def test_all_source_types(self) -> None:
        for st in SourceType:
            doc = UnifiedDocument(**_make_doc(source_type=st))
            assert doc.source_type is st

    def test_all_content_types(self) -> None:
        for ct in ContentType:
            doc = UnifiedDocument(**_make_doc(content_type=ct))
            assert doc.content_type is ct

    def test_with_metadata_and_participants(self) -> None:
        doc = UnifiedDocument(
            **_make_doc(
                metadata={"key": "value", "nested": {"a": 1}},
                participants=["alice@example.com", "Bob"],
            )
        )
        assert doc.metadata["key"] == "value"
        assert len(doc.participants) == 2

    def test_expires_at_set(self) -> None:
        doc = UnifiedDocument(**_make_doc(expires_at=_NOW))
        assert doc.expires_at == _NOW

    def test_str_strip_whitespace(self) -> None:
        doc = UnifiedDocument(**_make_doc(title="  trimmed  "))
        assert doc.title == "trimmed"

    def test_serialisation_roundtrip(self) -> None:
        doc = UnifiedDocument(**_make_doc())
        payload = doc.model_dump(mode="json")
        doc2 = UnifiedDocument.model_validate(payload)
        assert doc2 == doc


# ---------------------------------------------------------------------------
# Validation-error tests
# ---------------------------------------------------------------------------


class TestUnifiedDocumentInvalid:
    """Ensure bad payloads are rejected."""

    def test_missing_required_field(self) -> None:
        data = _make_doc()
        del data["content"]
        with pytest.raises(ValidationError):
            UnifiedDocument(**data)

    def test_invalid_source_type(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(source_type="unknown_source"))

    def test_invalid_content_type(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(content_type="pdf"))

    def test_language_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(language="deu"))

    def test_language_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(language="DE"))

    def test_raw_hash_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(raw_hash="abc"))

    def test_raw_hash_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(raw_hash="a" * 65))

    def test_empty_source_id(self) -> None:
        with pytest.raises(ValidationError):
            UnifiedDocument(**_make_doc(source_id=""))


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Verify enum values match specification."""

    def test_source_type_values(self) -> None:
        expected = {"google_calendar", "notion", "obsidian", "zoom", "gmail"}
        actual = {st.value for st in SourceType}
        assert actual == expected

    def test_content_type_values(self) -> None:
        expected = {"plaintext", "markdown", "html"}
        actual = {ct.value for ct in ContentType}
        assert actual == expected

    def test_source_type_is_str_enum(self) -> None:
        assert isinstance(SourceType.NOTION, str)
        assert SourceType.NOTION == "notion"

    def test_content_type_is_str_enum(self) -> None:
        assert isinstance(ContentType.HTML, str)
        assert ContentType.HTML == "html"
