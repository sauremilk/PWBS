"""Tests for account deletion service (TASK-105)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.dsgvo.deletion_service import (
    GRACE_PERIOD_DAYS,
    _cascade_delete_user,
    _cleanup_export_files,
    _cleanup_neo4j,
    _cleanup_redis,
    _cleanup_weaviate,
    cancel_deletion,
    cleanup_expired_accounts,
    schedule_deletion,
)

USER_ID = uuid.uuid4()


def _make_user(
    user_id: uuid.UUID = USER_ID,
    deletion_scheduled_at: datetime | None = None,
) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.email = "alice@example.com"
    u.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$fake"
    u.deletion_scheduled_at = deletion_scheduled_at
    return u


# ---------------------------------------------------------------------------
# schedule_deletion
# ---------------------------------------------------------------------------


class TestScheduleDeletion:
    @pytest.mark.asyncio
    async def test_schedules_with_correct_password(self) -> None:
        user = _make_user()
        db = AsyncMock()

        with patch(
            "pwbs.dsgvo.deletion_service.verify_password",
            return_value=True,
        ):
            result = await schedule_deletion(db, user, "correct-password")

        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        # Should be ~30 days from now
        now = datetime.now(tz=timezone.utc)
        delta = result - now
        assert GRACE_PERIOD_DAYS - 1 <= delta.days <= GRACE_PERIOD_DAYS
        assert user.deletion_scheduled_at == result
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wrong_password_raises_value_error(self) -> None:
        user = _make_user()
        db = AsyncMock()

        with patch(
            "pwbs.dsgvo.deletion_service.verify_password",
            return_value=False,
        ):
            with pytest.raises(ValueError, match="Invalid password"):
                await schedule_deletion(db, user, "wrong-password")

        db.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_already_scheduled_raises_value_error(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=15)
        user = _make_user(deletion_scheduled_at=future)
        db = AsyncMock()

        with patch(
            "pwbs.dsgvo.deletion_service.verify_password",
            return_value=True,
        ):
            with pytest.raises(ValueError, match="already scheduled"):
                await schedule_deletion(db, user, "correct-password")


# ---------------------------------------------------------------------------
# cancel_deletion
# ---------------------------------------------------------------------------


class TestCancelDeletion:
    @pytest.mark.asyncio
    async def test_cancels_pending_deletion(self) -> None:
        future = datetime.now(tz=timezone.utc) + timedelta(days=15)
        user = _make_user(deletion_scheduled_at=future)
        db = AsyncMock()

        await cancel_deletion(db, user)

        assert user.deletion_scheduled_at is None
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_deletion_raises_value_error(self) -> None:
        user = _make_user(deletion_scheduled_at=None)
        db = AsyncMock()

        with pytest.raises(ValueError, match="No deletion scheduled"):
            await cancel_deletion(db, user)

        db.flush.assert_not_awaited()


# ---------------------------------------------------------------------------
# cleanup_expired_accounts
# ---------------------------------------------------------------------------


class TestCleanupExpiredAccounts:
    @pytest.mark.asyncio
    async def test_deletes_expired_accounts(self) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        user1 = _make_user(user_id=uuid.uuid4(), deletion_scheduled_at=past)

        db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [user1]
        mock_result.scalars.return_value = mock_scalars
        db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "pwbs.dsgvo.deletion_service._cascade_delete_user",
            new_callable=AsyncMock,
        ) as mock_cascade:
            deleted = await cleanup_expired_accounts(db)

        assert deleted == 1
        mock_cascade.assert_awaited_once_with(db, user1)

    @pytest.mark.asyncio
    async def test_no_expired_accounts(self) -> None:
        db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db.execute = AsyncMock(return_value=mock_result)

        deleted = await cleanup_expired_accounts(db)
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_continues_on_individual_failure(self) -> None:
        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        user1 = _make_user(user_id=uuid.uuid4(), deletion_scheduled_at=past)
        user2 = _make_user(user_id=uuid.uuid4(), deletion_scheduled_at=past)

        db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [user1, user2]
        mock_result.scalars.return_value = mock_scalars
        db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "pwbs.dsgvo.deletion_service._cascade_delete_user",
            new_callable=AsyncMock,
            side_effect=[Exception("DB error"), None],
        ):
            deleted = await cleanup_expired_accounts(db)

        # Only user2 succeeded
        assert deleted == 1


# ---------------------------------------------------------------------------
# _cleanup_weaviate
# ---------------------------------------------------------------------------


class TestCleanupWeaviate:
    @pytest.mark.asyncio
    async def test_calls_delete_user_data(self) -> None:
        mock_store = MagicMock()
        mock_client = MagicMock()

        with (
            patch(
                "pwbs.db.weaviate_client.get_weaviate_client",
                return_value=mock_client,
            ),
            patch(
                "pwbs.storage.weaviate.WeaviateChunkStore",
                return_value=mock_store,
            ),
        ):
            await _cleanup_weaviate(USER_ID)

        mock_store.delete_user_data.assert_called_once_with(USER_ID)

    @pytest.mark.asyncio
    async def test_handles_failure_gracefully(self) -> None:
        with patch(
            "pwbs.db.weaviate_client.get_weaviate_client",
            side_effect=Exception("Connection refused"),
        ):
            # Should not raise
            await _cleanup_weaviate(USER_ID)


# ---------------------------------------------------------------------------
# _cleanup_neo4j
# ---------------------------------------------------------------------------


class TestCleanupNeo4j:
    @pytest.mark.asyncio
    async def test_runs_detach_delete(self) -> None:
        mock_session = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_ctx

        with patch(
            "pwbs.db.neo4j_client.get_neo4j_driver",
            return_value=mock_driver,
        ):
            await _cleanup_neo4j(USER_ID)

        mock_session.run.assert_awaited_once()
        call_args = mock_session.run.call_args
        assert "DETACH DELETE" in call_args[0][0]
        assert call_args[1]["user_id"] == str(USER_ID)

    @pytest.mark.asyncio
    async def test_handles_failure_gracefully(self) -> None:
        with patch(
            "pwbs.db.neo4j_client.get_neo4j_driver",
            side_effect=Exception("Connection refused"),
        ):
            await _cleanup_neo4j(USER_ID)


# ---------------------------------------------------------------------------
# _cleanup_redis
# ---------------------------------------------------------------------------


class TestCleanupRedis:
    @pytest.mark.asyncio
    async def test_scans_and_deletes_keys(self) -> None:
        mock_client = AsyncMock()

        # scan_iter returns async iterator
        async def mock_scan_iter(match: str = "") -> list[str]:
            if "session" in match:
                yield f"session:{USER_ID}:abc"
            elif "refresh" in match:
                yield f"refresh:{USER_ID}:xyz"

        mock_client.scan_iter = mock_scan_iter

        with patch(
            "pwbs.db.redis_client.get_redis_client",
            return_value=mock_client,
        ):
            await _cleanup_redis(USER_ID)

        assert mock_client.delete.await_count == 2

    @pytest.mark.asyncio
    async def test_handles_failure_gracefully(self) -> None:
        with patch(
            "pwbs.db.redis_client.get_redis_client",
            side_effect=Exception("Connection refused"),
        ):
            await _cleanup_redis(USER_ID)


# ---------------------------------------------------------------------------
# _cleanup_export_files
# ---------------------------------------------------------------------------


class TestCleanupExportFiles:
    @pytest.mark.asyncio
    async def test_deletes_existing_files(self, tmp_path: Path) -> None:
        export_file = tmp_path / "export.zip"
        export_file.write_bytes(b"fake zip")

        mock_export = MagicMock()
        mock_export.file_path = str(export_file)

        db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_export]
        mock_result.scalars.return_value = mock_scalars
        db.execute = AsyncMock(return_value=mock_result)

        await _cleanup_export_files(USER_ID, db)

        assert not export_file.exists()

    @pytest.mark.asyncio
    async def test_skips_missing_files(self) -> None:
        mock_export = MagicMock()
        mock_export.file_path = "/nonexistent/path.zip"

        db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_export]
        mock_result.scalars.return_value = mock_scalars
        db.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await _cleanup_export_files(USER_ID, db)

    @pytest.mark.asyncio
    async def test_skips_null_file_path(self) -> None:
        mock_export = MagicMock()
        mock_export.file_path = None

        db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_export]
        mock_result.scalars.return_value = mock_scalars
        db.execute = AsyncMock(return_value=mock_result)

        await _cleanup_export_files(USER_ID, db)


# ---------------------------------------------------------------------------
# _cascade_delete_user (full cascade)
# ---------------------------------------------------------------------------


class TestCascadeDeleteUser:
    @pytest.mark.asyncio
    async def test_calls_all_cleanup_phases(self) -> None:
        user = _make_user()
        db = AsyncMock()

        with (
            patch(
                "pwbs.dsgvo.deletion_service._cleanup_weaviate",
                new_callable=AsyncMock,
            ) as mock_weaviate,
            patch(
                "pwbs.dsgvo.deletion_service._cleanup_neo4j",
                new_callable=AsyncMock,
            ) as mock_neo4j,
            patch(
                "pwbs.dsgvo.deletion_service._cleanup_redis",
                new_callable=AsyncMock,
            ) as mock_redis,
            patch(
                "pwbs.dsgvo.deletion_service._cleanup_export_files",
                new_callable=AsyncMock,
            ) as mock_exports,
        ):
            await _cascade_delete_user(db, user)

        mock_weaviate.assert_awaited_once_with(user.id)
        mock_neo4j.assert_awaited_once_with(user.id)
        mock_redis.assert_awaited_once_with(user.id)
        mock_exports.assert_awaited_once_with(user.id, db)
        # PostgreSQL delete
        db.execute.assert_awaited_once()
        db.flush.assert_awaited_once()
