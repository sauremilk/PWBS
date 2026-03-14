"""Tests for Slack bot integration (TASK-141)."""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.integrations.slack.bot import (
    SlackCommandResult,
    SlackRateLimiter,
    _format_briefing_blocks,
    _format_search_blocks,
    dispatch_command,
    handle_briefing_command,
    handle_search_command,
    link_slack_user,
    rate_limiter,
    resolve_pwbs_user,
    verify_slack_signature,
)


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


class TestVerifySlackSignature:
    def test_valid_signature(self) -> None:
        secret = "test-signing-secret"
        ts = str(int(time.time()))
        body = b"token=abc&user_id=U123"
        sig_base = f"v0:{ts}:{body.decode()}"
        expected = "v0=" + hmac.new(
            secret.encode(), sig_base.encode(), hashlib.sha256
        ).hexdigest()
        assert verify_slack_signature(secret, ts, body, expected) is True

    def test_invalid_signature(self) -> None:
        assert verify_slack_signature("secret", str(int(time.time())), b"body", "v0=bad") is False

    def test_expired_timestamp(self) -> None:
        secret = "test"
        old_ts = str(int(time.time()) - 600)  # 10 min ago
        body = b"data"
        sig_base = f"v0:{old_ts}:{body.decode()}"
        sig = "v0=" + hmac.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
        assert verify_slack_signature(secret, old_ts, body, sig) is False

    def test_invalid_timestamp(self) -> None:
        assert verify_slack_signature("secret", "not-a-number", b"body", "v0=sig") is False


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class TestSlackRateLimiter:
    def test_allows_under_limit(self) -> None:
        limiter = SlackRateLimiter(max_requests=3, window_seconds=3600)
        assert limiter.is_allowed("U1") is True
        assert limiter.is_allowed("U1") is True
        assert limiter.is_allowed("U1") is True
        assert limiter.is_allowed("U1") is False  # 4th request denied

    def test_separate_users(self) -> None:
        limiter = SlackRateLimiter(max_requests=1, window_seconds=3600)
        assert limiter.is_allowed("U1") is True
        assert limiter.is_allowed("U2") is True  # different user
        assert limiter.is_allowed("U1") is False

    def test_remaining(self) -> None:
        limiter = SlackRateLimiter(max_requests=5, window_seconds=3600)
        assert limiter.remaining("U1") == 5
        limiter.is_allowed("U1")
        assert limiter.remaining("U1") == 4


# ---------------------------------------------------------------------------
# User resolution
# ---------------------------------------------------------------------------


class TestResolveUser:
    @pytest.mark.asyncio
    async def test_returns_user_id(self) -> None:
        uid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uid
        session = AsyncMock()
        session.execute.return_value = mock_result
        result = await resolve_pwbs_user(session, "U123", "T456")
        assert result == uid

    @pytest.mark.asyncio
    async def test_returns_none_when_not_linked(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = mock_result
        result = await resolve_pwbs_user(session, "U999", "T999")
        assert result is None


class TestLinkSlackUser:
    @pytest.mark.asyncio
    async def test_creates_new_mapping(self) -> None:
        uid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = mock_result
        mapping = await link_slack_user(session, "U123", "T456", uid)
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert mapping.slack_user_id == "U123"
        assert mapping.pwbs_user_id == uid

    @pytest.mark.asyncio
    async def test_updates_existing_mapping(self) -> None:
        old_uid = uuid.uuid4()
        new_uid = uuid.uuid4()
        existing = MagicMock()
        existing.pwbs_user_id = old_uid
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        session = AsyncMock()
        session.execute.return_value = mock_result
        mapping = await link_slack_user(session, "U123", "T456", new_uid)
        assert mapping.pwbs_user_id == new_uid
        session.add.assert_not_called()


# ---------------------------------------------------------------------------
# Format functions
# ---------------------------------------------------------------------------


class TestFormatSearchBlocks:
    def test_empty_results(self) -> None:
        blocks = _format_search_blocks([])
        assert len(blocks) == 2  # header + empty message
        assert "Keine Ergebnisse" in blocks[1]["text"]["text"]

    def test_with_results(self) -> None:
        results = [
            {"title": "Doc 1", "source_type": "notion", "score": 0.95, "content": "Content 1"},
            {"title": "Doc 2", "source_type": "slack", "score": 0.8, "content": "Content 2"},
        ]
        blocks = _format_search_blocks(results)
        # header + (divider + section) * 2
        assert len(blocks) == 5
        assert blocks[0]["type"] == "header"
        assert "Doc 1" in blocks[2]["text"]["text"]

    def test_max_three_results(self) -> None:
        results = [{"title": f"Doc {i}", "source_type": "x", "score": 0.5, "content": "c"} for i in range(5)]
        blocks = _format_search_blocks(results)
        # header + (divider + section) * 3
        assert len(blocks) == 7


class TestFormatBriefingBlocks:
    def test_no_briefing(self) -> None:
        blocks = _format_briefing_blocks(None)
        assert len(blocks) == 2  # header + no briefing msg
        assert "Kein aktuelles" in blocks[1]["text"]["text"]

    def test_with_briefing(self) -> None:
        briefing = MagicMock()
        briefing.title = "Morgenbriefing 25.07.2025"
        briefing.content = "Heute stehen 3 Meetings an."
        briefing.generated_at = datetime(2025, 7, 25, 6, 30, tzinfo=timezone.utc)
        blocks = _format_briefing_blocks(briefing)
        assert len(blocks) == 4  # header + title + content + context
        assert "Morgenbriefing" in blocks[1]["text"]["text"]
        assert "3 Meetings" in blocks[2]["text"]["text"]

    def test_truncates_long_content(self) -> None:
        briefing = MagicMock()
        briefing.title = "Long Briefing"
        briefing.content = "x" * 5000
        briefing.generated_at = datetime(2025, 7, 25, 6, 30, tzinfo=timezone.utc)
        blocks = _format_briefing_blocks(briefing)
        content_block = blocks[2]["text"]["text"]
        assert len(content_block) < 3100
        assert "gekuerzt" in content_block


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------


class TestDispatchCommand:
    @pytest.mark.asyncio
    async def test_rate_limited(self) -> None:
        limiter = SlackRateLimiter(max_requests=0, window_seconds=3600)
        with patch("pwbs.integrations.slack.bot.rate_limiter", limiter):
            session = AsyncMock()
            result = await dispatch_command("search test", "U123", "T456", session)
            assert "Rate-Limit" in result.text

    @pytest.mark.asyncio
    async def test_unlinked_user(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = mock_result
        limiter = SlackRateLimiter(max_requests=10, window_seconds=3600)
        with patch("pwbs.integrations.slack.bot.rate_limiter", limiter):
            result = await dispatch_command("search test", "UNLINKED", "T456", session)
            assert "nicht mit PWBS verknuepft" in result.text

    @pytest.mark.asyncio
    async def test_unknown_command(self) -> None:
        uid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uid
        session = AsyncMock()
        session.execute.return_value = mock_result
        limiter = SlackRateLimiter(max_requests=10, window_seconds=3600)
        with patch("pwbs.integrations.slack.bot.rate_limiter", limiter):
            result = await dispatch_command("foobar", "U123", "T456", session)
            assert "Unbekannter Befehl" in result.text

    @pytest.mark.asyncio
    async def test_search_dispatch(self) -> None:
        uid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uid
        session = AsyncMock()
        session.execute.return_value = mock_result
        expected = SlackCommandResult("ephemeral", "ok")
        limiter = SlackRateLimiter(max_requests=10, window_seconds=3600)
        with (
            patch("pwbs.integrations.slack.bot.rate_limiter", limiter),
            patch("pwbs.integrations.slack.bot.handle_search_command", new_callable=AsyncMock, return_value=expected) as mock_search,
        ):
            result = await dispatch_command("search DSGVO", "U123", "T456", session)
            mock_search.assert_awaited_once_with("DSGVO", uid, session)
            assert result == expected

    @pytest.mark.asyncio
    async def test_briefing_dispatch(self) -> None:
        uid = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uid
        session = AsyncMock()
        session.execute.return_value = mock_result
        expected = SlackCommandResult("ephemeral", "briefing ok")
        limiter = SlackRateLimiter(max_requests=10, window_seconds=3600)
        with (
            patch("pwbs.integrations.slack.bot.rate_limiter", limiter),
            patch("pwbs.integrations.slack.bot.handle_briefing_command", new_callable=AsyncMock, return_value=expected) as mock_brief,
        ):
            result = await dispatch_command("briefing", "U123", "T456", session)
            mock_brief.assert_awaited_once_with(uid, session)
            assert result == expected


# ---------------------------------------------------------------------------
# Handle search command
# ---------------------------------------------------------------------------


class TestHandleSearchCommand:
    @pytest.mark.asyncio
    async def test_empty_query(self) -> None:
        session = AsyncMock()
        result = await handle_search_command("  ", uuid.uuid4(), session)
        assert "Suchbegriff" in result.text

    @pytest.mark.asyncio
    async def test_search_error_returns_graceful_message(self) -> None:
        session = AsyncMock()
        with patch("pwbs.db.weaviate_client.get_weaviate_client", side_effect=Exception("no weaviate")):
            result = await handle_search_command("test query", uuid.uuid4(), session)
            assert "fehlgeschlagen" in result.text


# ---------------------------------------------------------------------------
# Handle briefing command
# ---------------------------------------------------------------------------


class TestHandleBriefingCommand:
    @pytest.mark.asyncio
    async def test_no_briefing_found(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = mock_result
        result = await handle_briefing_command(uuid.uuid4(), session)
        assert "Kein aktuelles" in str(result.blocks)

    @pytest.mark.asyncio
    async def test_briefing_found(self) -> None:
        briefing = MagicMock()
        briefing.title = "Test Briefing"
        briefing.content = "Inhalt"
        briefing.generated_at = datetime(2025, 7, 25, 6, 30, tzinfo=timezone.utc)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = briefing
        session = AsyncMock()
        session.execute.return_value = mock_result
        result = await handle_briefing_command(uuid.uuid4(), session)
        assert "Test Briefing" in str(result.blocks)
        assert result.response_type == "ephemeral"

    @pytest.mark.asyncio
    async def test_db_error_returns_graceful_message(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = Exception("db error")
        result = await handle_briefing_command(uuid.uuid4(), session)
        assert "konnte nicht geladen" in result.text

