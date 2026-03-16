"""Tests for collaborative briefings – TASK-163.

Covers:
  - Pydantic schemas (validation, serialization)
  - Service layer (share, list_shares, mark_read, add_comment, list_comments)
  - API router registration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

OWNER_ID = uuid.uuid4()
RECIPIENT_A = uuid.uuid4()
RECIPIENT_B = uuid.uuid4()
BRIEFING_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


def _make_briefing(
    briefing_id: uuid.UUID = BRIEFING_ID,
    user_id: uuid.UUID = OWNER_ID,
) -> MagicMock:
    b = MagicMock()
    b.id = briefing_id
    b.user_id = user_id
    return b


def _make_share(
    briefing_id: uuid.UUID = BRIEFING_ID,
    shared_by: uuid.UUID = OWNER_ID,
    recipient_id: uuid.UUID = RECIPIENT_A,
    read_at: datetime | None = None,
) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.briefing_id = briefing_id
    s.shared_by = shared_by
    s.recipient_id = recipient_id
    s.shared_at = NOW
    s.read_at = read_at
    return s


def _make_comment(
    briefing_id: uuid.UUID = BRIEFING_ID,
    author_id: uuid.UUID = OWNER_ID,
    section_ref: str = "summary",
    content: str = "LGTM",
) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.briefing_id = briefing_id
    c.author_id = author_id
    c.section_ref = section_ref
    c.content = content
    c.created_at = NOW
    c.updated_at = NOW
    return c


# ═══════════════════════════════════════════════════════════════════════════════
# Schema Tests
# ═══════════════════════════════════════════════════════════════════════════════

from pwbs.briefing.collaboration.schemas import (
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    ReadReceiptResponse,
    ShareBriefingRequest,
    ShareListResponse,
    ShareResponse,
)


class TestShareBriefingRequest:
    def test_valid_request(self) -> None:
        req = ShareBriefingRequest(recipient_ids=[RECIPIENT_A])
        assert len(req.recipient_ids) == 1

    def test_multiple_recipients(self) -> None:
        req = ShareBriefingRequest(recipient_ids=[RECIPIENT_A, RECIPIENT_B])
        assert len(req.recipient_ids) == 2

    def test_empty_recipients_rejected(self) -> None:
        with pytest.raises(Exception):
            ShareBriefingRequest(recipient_ids=[])

    def test_too_many_recipients_rejected(self) -> None:
        ids = [uuid.uuid4() for _ in range(51)]
        with pytest.raises(Exception):
            ShareBriefingRequest(recipient_ids=ids)


class TestShareResponse:
    def test_roundtrip(self) -> None:
        share = ShareResponse(
            id=uuid.uuid4(),
            briefing_id=BRIEFING_ID,
            shared_by=OWNER_ID,
            recipient_id=RECIPIENT_A,
            shared_at=NOW,
            read_at=None,
        )
        data = share.model_dump()
        assert data["read_at"] is None
        assert data["briefing_id"] == BRIEFING_ID


class TestShareListResponse:
    def test_with_items(self) -> None:
        item = ShareResponse(
            id=uuid.uuid4(),
            briefing_id=BRIEFING_ID,
            shared_by=OWNER_ID,
            recipient_id=RECIPIENT_A,
            shared_at=NOW,
        )
        resp = ShareListResponse(shares=[item], total=1)
        assert resp.total == 1

    def test_empty(self) -> None:
        resp = ShareListResponse(shares=[], total=0)
        assert resp.shares == []


class TestReadReceiptResponse:
    def test_fields(self) -> None:
        rr = ReadReceiptResponse(
            briefing_id=BRIEFING_ID,
            recipient_id=RECIPIENT_A,
            read_at=NOW,
        )
        assert rr.read_at == NOW


class TestCreateCommentRequest:
    def test_valid(self) -> None:
        req = CreateCommentRequest(section_ref="summary", content="Nice briefing")
        assert req.section_ref == "summary"

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(Exception):
            CreateCommentRequest(section_ref="summary", content="")

    def test_default_section_ref(self) -> None:
        req = CreateCommentRequest(content="Good stuff")
        assert req.section_ref == ""

    def test_content_max_length(self) -> None:
        with pytest.raises(Exception):
            CreateCommentRequest(content="x" * 5001)


class TestCommentResponse:
    def test_roundtrip(self) -> None:
        cr = CommentResponse(
            id=uuid.uuid4(),
            briefing_id=BRIEFING_ID,
            author_id=OWNER_ID,
            section_ref="open-items",
            content="We should revisit this",
            created_at=NOW,
            updated_at=NOW,
        )
        data = cr.model_dump()
        assert data["section_ref"] == "open-items"


class TestCommentListResponse:
    def test_paginated(self) -> None:
        item = CommentResponse(
            id=uuid.uuid4(),
            briefing_id=BRIEFING_ID,
            author_id=OWNER_ID,
            section_ref="",
            content="test",
            created_at=NOW,
            updated_at=NOW,
        )
        resp = CommentListResponse(comments=[item], total=5)
        assert resp.total == 5
        assert len(resp.comments) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Service Tests
# ═══════════════════════════════════════════════════════════════════════════════

from pwbs.briefing.collaboration import service


class TestGetBriefingOr404:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        db = AsyncMock()
        briefing = _make_briefing()
        db.get.return_value = briefing
        result = await service._get_briefing_or_404(db, BRIEFING_ID)
        assert result is briefing

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        db = AsyncMock()
        db.get.return_value = None
        with pytest.raises(ValueError, match="BRIEFING_NOT_FOUND"):
            await service._get_briefing_or_404(db, BRIEFING_ID)


class TestAssertAccess:
    @pytest.mark.asyncio
    async def test_owner_has_access(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()
        result = await service._assert_access(db, BRIEFING_ID, OWNER_ID)
        assert result.user_id == OWNER_ID

    @pytest.mark.asyncio
    async def test_recipient_has_access(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.uuid4()
        db.execute.return_value = mock_result

        result = await service._assert_access(db, BRIEFING_ID, RECIPIENT_A)
        assert result is not None

    @pytest.mark.asyncio
    async def test_no_access_raises(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="ACCESS_DENIED"):
            await service._assert_access(db, BRIEFING_ID, RECIPIENT_A)


class TestShareBriefing:
    @pytest.mark.asyncio
    async def test_not_owner_raises(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        with pytest.raises(ValueError, match="NOT_OWNER"):
            await service.share_briefing(db, BRIEFING_ID, RECIPIENT_A, [RECIPIENT_B])

    @pytest.mark.asyncio
    async def test_self_share_filtered(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        result = await service.share_briefing(db, BRIEFING_ID, OWNER_ID, [OWNER_ID])
        assert result == []
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        share = _make_share()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [share]
        db.execute.return_value = mock_result

        result = await service.share_briefing(db, BRIEFING_ID, OWNER_ID, [RECIPIENT_A])
        assert len(result) == 1
        assert result[0].recipient_id == RECIPIENT_A

    @pytest.mark.asyncio
    async def test_briefing_not_found(self) -> None:
        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(ValueError, match="BRIEFING_NOT_FOUND"):
            await service.share_briefing(db, BRIEFING_ID, OWNER_ID, [RECIPIENT_A])


class TestListShares:
    @pytest.mark.asyncio
    async def test_returns_shares(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        share = _make_share()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [share]
        db.execute.return_value = mock_result

        result = await service.list_shares(db, BRIEFING_ID, OWNER_ID)
        assert len(result) == 1


class TestMarkRead:
    @pytest.mark.asyncio
    async def test_marks_unread(self) -> None:
        db = AsyncMock()
        share = _make_share(read_at=None)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = share
        db.execute.return_value = mock_result

        result = await service.mark_read(db, BRIEFING_ID, RECIPIENT_A)
        assert result.read_at is not None

    @pytest.mark.asyncio
    async def test_already_read_no_update(self) -> None:
        db = AsyncMock()
        original_time = NOW
        share = _make_share(read_at=original_time)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = share
        db.execute.return_value = mock_result

        result = await service.mark_read(db, BRIEFING_ID, RECIPIENT_A)
        assert result.read_at == original_time

    @pytest.mark.asyncio
    async def test_no_share_raises(self) -> None:
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="SHARE_NOT_FOUND"):
            await service.mark_read(db, BRIEFING_ID, RECIPIENT_A)


class TestAddComment:
    @pytest.mark.asyncio
    async def test_owner_can_comment(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        result = await service.add_comment(db, BRIEFING_ID, OWNER_ID, "summary", "Great briefing")
        db.add.assert_called_once()
        assert db.flush.called
        assert db.refresh.called

    @pytest.mark.asyncio
    async def test_non_authorized_raises(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="ACCESS_DENIED"):
            await service.add_comment(db, BRIEFING_ID, RECIPIENT_A, "summary", "test")


class TestListComments:
    @pytest.mark.asyncio
    async def test_returns_comments_and_total(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        comment = _make_comment()
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 3
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = [comment]

        db.execute.side_effect = [mock_count, mock_data]

        comments, total = await service.list_comments(db, BRIEFING_ID, OWNER_ID, offset=0, limit=10)
        assert total == 3
        assert len(comments) == 1

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        db = AsyncMock()
        db.get.return_value = _make_briefing()

        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []

        db.execute.side_effect = [mock_count, mock_data]

        comments, total = await service.list_comments(db, BRIEFING_ID, OWNER_ID)
        assert total == 0
        assert comments == []


# ═══════════════════════════════════════════════════════════════════════════════
# Router Registration Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRouterRegistration:
    def test_briefing_collab_router_has_routes(self) -> None:
        from pwbs.api.v1.routes.briefing_collab import router

        paths = [r.path for r in router.routes]  # type: ignore[union-attr]
        assert "/api/v1/briefings/{briefing_id}/share" in paths
        assert "/api/v1/briefings/{briefing_id}/shares" in paths
        assert "/api/v1/briefings/{briefing_id}/read" in paths
        assert "/api/v1/briefings/{briefing_id}/comments" in paths

    def test_router_prefix(self) -> None:
        from pwbs.api.v1.routes.briefing_collab import router

        assert router.prefix == "/api/v1/briefings"

    def test_router_tags(self) -> None:
        from pwbs.api.v1.routes.briefing_collab import router

        assert "briefing-collaboration" in router.tags


class TestMapValueError:
    def test_known_codes(self) -> None:
        from pwbs.api.v1.routes.briefing_collab import _map_value_error

        exc = _map_value_error(ValueError("BRIEFING_NOT_FOUND"))
        assert exc.status_code == 404

        exc = _map_value_error(ValueError("NOT_OWNER"))
        assert exc.status_code == 403

        exc = _map_value_error(ValueError("ACCESS_DENIED"))
        assert exc.status_code == 403

        exc = _map_value_error(ValueError("SHARE_NOT_FOUND"))
        assert exc.status_code == 404

    def test_unknown_code(self) -> None:
        from pwbs.api.v1.routes.briefing_collab import _map_value_error

        exc = _map_value_error(ValueError("UNKNOWN"))
        assert exc.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# ORM Model Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestBriefingShareModel:
    def test_tablename(self) -> None:
        from pwbs.briefing.collaboration.models import BriefingShare

        assert BriefingShare.__tablename__ == "briefing_shares"

    def test_has_required_columns(self) -> None:
        from pwbs.briefing.collaboration.models import BriefingShare

        columns = {c.name for c in BriefingShare.__table__.columns}
        assert "id" in columns
        assert "briefing_id" in columns
        assert "shared_by" in columns
        assert "recipient_id" in columns
        assert "shared_at" in columns
        assert "read_at" in columns


class TestBriefingCommentModel:
    def test_tablename(self) -> None:
        from pwbs.briefing.collaboration.models import BriefingComment

        assert BriefingComment.__tablename__ == "briefing_comments"

    def test_has_required_columns(self) -> None:
        from pwbs.briefing.collaboration.models import BriefingComment

        columns = {c.name for c in BriefingComment.__table__.columns}
        assert "id" in columns
        assert "briefing_id" in columns
        assert "author_id" in columns
        assert "section_ref" in columns
        assert "content" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_indexes_exist(self) -> None:
        from pwbs.briefing.collaboration.models import BriefingComment

        index_names = {idx.name for idx in BriefingComment.__table__.indexes}
        assert "idx_comments_briefing" in index_names
        assert "idx_comments_author" in index_names
        assert "idx_comments_briefing_section" in index_names
