"""Tests for User API endpoints (TASK-092)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Shared fixtures ──────────────────────────────────────────────────────────

USER_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID = USER_ID) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.email = "alice@example.com"
    u.display_name = "Alice"
    return u


def _make_audit_log(
    *,
    log_id: int = 1,
    user_id: uuid.UUID = USER_ID,
    action: str = "POST",
    resource_type: str | None = "briefing",
    resource_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    log = MagicMock()
    log.id = log_id
    log.user_id = user_id
    log.action = action
    log.resource_type = resource_type
    log.resource_id = resource_id or uuid.uuid4()
    log.created_at = created_at or datetime(2024, 6, 1, tzinfo=timezone.utc)
    return log


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestSchemaValidation:
    """Validate Pydantic response schemas."""

    def test_user_settings_response(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsResponse

        resp = UserSettingsResponse(
            user_id=USER_ID,
            email="alice@example.com",
            display_name="Alice",
            timezone="UTC",
            language="de",
            briefing_auto_generate=True,
        )
        assert resp.timezone == "UTC"

    def test_user_settings_update(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate

        update = UserSettingsUpdate(timezone="Europe/Berlin", language="en")
        assert update.timezone == "Europe/Berlin"
        assert update.display_name is None

    def test_export_start_response(self) -> None:
        from pwbs.api.v1.routes.user import ExportStartResponse

        resp = ExportStartResponse(export_id=uuid.uuid4())
        assert resp.status == "processing"

    def test_account_deletion_request(self) -> None:
        from pwbs.api.v1.routes.user import AccountDeletionRequest

        req = AccountDeletionRequest(password="mypassword123", confirmation="DELETE")
        assert req.confirmation == "DELETE"

    def test_account_deletion_request_invalid_confirmation(self) -> None:
        from pwbs.api.v1.routes.user import AccountDeletionRequest

        with pytest.raises(Exception):
            AccountDeletionRequest(password="mypassword123", confirmation="WRONG")

    def test_audit_log_entry(self) -> None:
        from pwbs.api.v1.routes.user import AuditLogEntry

        entry = AuditLogEntry(
            id=1,
            action="POST",
            resource_type="briefing",
            created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        assert entry.action == "POST"

    def test_security_status_response(self) -> None:
        from pwbs.api.v1.routes.user import SecurityStatusResponse, StorageLayerStatus

        resp = SecurityStatusResponse(
            storage_layers=[
                StorageLayerStatus(layer="PostgreSQL", encrypted=True),
            ],
            data_location="Local",
            llm_usage="RAG only",
        )
        assert len(resp.storage_layers) == 1

    def test_storage_layer_status(self) -> None:
        from pwbs.api.v1.routes.user import StorageLayerStatus

        s = StorageLayerStatus(
            layer="Redis",
            encrypted=False,
            note="Session only",
        )
        assert s.encryption_type is None


# ── GET /settings ────────────────────────────────────────────────────────────


class TestGetSettings:
    """Test GET /api/v1/user/settings."""

    @pytest.mark.asyncio
    async def test_returns_defaults(self) -> None:
        from pwbs.api.v1.routes.user import get_settings_endpoint

        user = _make_user()
        db = AsyncMock()

        resp = await get_settings_endpoint(
            response=MagicMock(),
            user=user,
            db=db,
        )
        assert resp.user_id == USER_ID
        assert resp.timezone == "UTC"
        assert resp.language == "de"
        assert resp.briefing_auto_generate is True

    @pytest.mark.asyncio
    async def test_returns_user_email(self) -> None:
        from pwbs.api.v1.routes.user import get_settings_endpoint

        user = _make_user()
        db = AsyncMock()

        resp = await get_settings_endpoint(
            response=MagicMock(),
            user=user,
            db=db,
        )
        assert resp.email == "alice@example.com"


# ── PATCH /settings ──────────────────────────────────────────────────────────


class TestUpdateSettings:
    """Test PATCH /api/v1/user/settings."""

    @pytest.mark.asyncio
    async def test_update_display_name(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()

        update = UserSettingsUpdate(display_name="Bob")
        resp = await update_settings(
            update=update,
            response=MagicMock(),
            user=user,
            db=db,
        )
        assert user.display_name == "Bob"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_timezone(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()

        update = UserSettingsUpdate(timezone="Invalid/Zone")
        with pytest.raises(Exception) as exc_info:
            await update_settings(
                update=update,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_language(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()

        update = UserSettingsUpdate(language="klingon")
        with pytest.raises(Exception) as exc_info:
            await update_settings(
                update=update,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_display_name(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()

        update = UserSettingsUpdate(display_name="   ")
        with pytest.raises(Exception) as exc_info:
            await update_settings(
                update=update,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_timezone(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()

        update = UserSettingsUpdate(timezone="Europe/Berlin")
        resp = await update_settings(
            update=update,
            response=MagicMock(),
            user=user,
            db=db,
        )
        assert resp.timezone == "Europe/Berlin"

    @pytest.mark.asyncio
    async def test_no_changes(self) -> None:
        from pwbs.api.v1.routes.user import UserSettingsUpdate, update_settings

        user = _make_user()
        db = AsyncMock()

        update = UserSettingsUpdate()
        resp = await update_settings(
            update=update,
            response=MagicMock(),
            user=user,
            db=db,
        )
        # No commit since no display_name change
        db.commit.assert_not_awaited()
        assert resp.timezone == "UTC"


# ── POST /export (TASK-104 implemented) ───────────────────────────────────────


class TestStartExport:
    """Test POST /api/v1/user/export."""

    @pytest.mark.asyncio
    async def test_starts_export_successfully(self) -> None:
        from pwbs.api.v1.routes.user import start_export

        user = _make_user()
        db = AsyncMock()
        bg_tasks = MagicMock()
        export_mock = MagicMock()
        export_mock.id = uuid.uuid4()

        with (
            patch(
                "pwbs.api.v1.routes.user.export_service.check_running_export", return_value=None
            ) as check_mock,
            patch(
                "pwbs.api.v1.routes.user.export_service.create_export_job", return_value=export_mock
            ) as create_mock,
            patch("pwbs.api.v1.routes.user.get_settings") as settings_mock,
        ):
            settings_mock.return_value.database_url = "postgresql+asyncpg://test"
            settings_mock.return_value.export_dir = "/tmp/exports"
            resp = await start_export(
                background_tasks=bg_tasks,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert resp.status == "processing"
        assert resp.export_id == export_mock.id
        check_mock.assert_awaited_once_with(user.id, db)
        create_mock.assert_awaited_once_with(user.id, db)
        bg_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_429_when_export_already_running(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.user import start_export

        user = _make_user()
        db = AsyncMock()
        bg_tasks = MagicMock()
        running_export = MagicMock()
        running_export.id = uuid.uuid4()

        with patch(
            "pwbs.api.v1.routes.user.export_service.check_running_export",
            return_value=running_export,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await start_export(
                    background_tasks=bg_tasks,
                    response=MagicMock(),
                    user=user,
                    db=db,
                )
        assert exc_info.value.status_code == 429


# ── GET /export/{id} (TASK-104 implemented) ──────────────────────────────────


class TestGetExportStatus:
    """Test GET /api/v1/user/export/{export_id}."""

    @pytest.mark.asyncio
    async def test_returns_status_for_processing_export(self) -> None:
        from pwbs.api.v1.routes.user import get_export_status

        user = _make_user()
        db = AsyncMock()
        export_mock = MagicMock()
        export_mock.id = uuid.uuid4()
        export_mock.status = "processing"
        export_mock.file_path = None
        export_mock.created_at = datetime.now(tz=timezone.utc)

        with patch("pwbs.api.v1.routes.user.export_service.get_export", return_value=export_mock):
            resp = await get_export_status(
                export_id=export_mock.id,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert resp.status == "processing"
        assert resp.download_url is None

    @pytest.mark.asyncio
    async def test_returns_download_url_for_completed_export(self) -> None:
        from pwbs.api.v1.routes.user import get_export_status

        user = _make_user()
        db = AsyncMock()
        export_id = uuid.uuid4()
        export_mock = MagicMock()
        export_mock.id = export_id
        export_mock.status = "completed"
        export_mock.file_path = "/tmp/exports/test.zip"
        export_mock.created_at = datetime.now(tz=timezone.utc)

        with (
            patch("pwbs.api.v1.routes.user.export_service.get_export", return_value=export_mock),
            patch("pwbs.api.v1.routes.user.export_service.is_export_expired", return_value=False),
        ):
            resp = await get_export_status(
                export_id=export_id,
                response=MagicMock(),
                user=user,
                db=db,
            )
        assert resp.status == "completed"
        assert resp.download_url is not None
        assert str(export_id) in resp.download_url

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_export(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.user import get_export_status

        user = _make_user()
        db = AsyncMock()

        with patch("pwbs.api.v1.routes.user.export_service.get_export", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_export_status(
                    export_id=uuid.uuid4(),
                    response=MagicMock(),
                    user=user,
                    db=db,
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_for_expired_export(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.user import get_export_status

        user = _make_user()
        db = AsyncMock()
        export_mock = MagicMock()
        export_mock.id = uuid.uuid4()
        export_mock.status = "completed"
        export_mock.file_path = "/tmp/exports/test.zip"
        export_mock.created_at = datetime.now(tz=timezone.utc)

        with (
            patch("pwbs.api.v1.routes.user.export_service.get_export", return_value=export_mock),
            patch("pwbs.api.v1.routes.user.export_service.is_export_expired", return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_export_status(
                    export_id=export_mock.id,
                    response=MagicMock(),
                    user=user,
                    db=db,
                )
        assert exc_info.value.status_code == 410


# ── DELETE /account ──────────────────────────────────────────────────────────


class TestDeleteAccount:
    """Test DELETE /api/v1/user/account."""

    @pytest.mark.asyncio
    async def test_invalid_confirmation_raises_422(self) -> None:
        from pwbs.api.v1.routes.user import AccountDeletionRequest, delete_account

        user = _make_user()
        db = AsyncMock()

        body = AccountDeletionRequest(password="mypassword123", confirmation="DELETE")
        # Even with valid confirmation, raises NotImplementedError (TASK-105)
        with pytest.raises(NotImplementedError, match="TASK-105"):
            await delete_account(
                body=body,
                response=MagicMock(),
                user=user,
                db=db,
            )


# ── POST /account/cancel-deletion ───────────────────────────────────────────


class TestCancelDeletion:
    """Test POST /api/v1/user/account/cancel-deletion."""

    @pytest.mark.asyncio
    async def test_raises_not_implemented(self) -> None:
        from pwbs.api.v1.routes.user import cancel_deletion

        user = _make_user()
        db = AsyncMock()

        with pytest.raises(NotImplementedError, match="TASK-105"):
            await cancel_deletion(
                response=MagicMock(),
                user=user,
                db=db,
            )


# ── GET /audit-log ───────────────────────────────────────────────────────────


class TestGetAuditLog:
    """Test GET /api/v1/user/audit-log."""

    @pytest.mark.asyncio
    async def test_returns_entries(self) -> None:
        from pwbs.api.v1.routes.user import get_audit_log

        user = _make_user()
        db = AsyncMock()

        log1 = _make_audit_log(log_id=1, action="POST")
        log2 = _make_audit_log(log_id=2, action="DELETE")

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [log1, log2]
        db.execute.return_value = result_mock

        resp = await get_audit_log(
            response=MagicMock(),
            user=user,
            db=db,
            limit=100,
        )
        assert resp.total == 2
        assert resp.entries[0].action == "POST"

    @pytest.mark.asyncio
    async def test_empty_log(self) -> None:
        from pwbs.api.v1.routes.user import get_audit_log

        user = _make_user()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        resp = await get_audit_log(
            response=MagicMock(),
            user=user,
            db=db,
            limit=100,
        )
        assert resp.total == 0
        assert resp.entries == []

    @pytest.mark.asyncio
    async def test_limit_clamped(self) -> None:
        from pwbs.api.v1.routes.user import get_audit_log

        user = _make_user()
        db = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        # limit=500 should be clamped to 100
        resp = await get_audit_log(
            response=MagicMock(),
            user=user,
            db=db,
            limit=500,
        )
        assert resp.total == 0


# ── GET /security ────────────────────────────────────────────────────────────


class TestGetSecurityStatus:
    """Test GET /api/v1/user/security."""

    @pytest.mark.asyncio
    async def test_returns_storage_layers(self) -> None:
        from pwbs.api.v1.routes.user import get_security_status

        user = _make_user()

        resp = await get_security_status(
            response=MagicMock(),
            user=user,
        )
        assert len(resp.storage_layers) == 4
        layer_names = [l.layer for l in resp.storage_layers]
        assert "PostgreSQL" in layer_names
        assert "Weaviate" in layer_names
        assert "Neo4j" in layer_names
        assert "Redis" in layer_names

    @pytest.mark.asyncio
    async def test_redis_not_encrypted(self) -> None:
        from pwbs.api.v1.routes.user import get_security_status

        user = _make_user()

        resp = await get_security_status(
            response=MagicMock(),
            user=user,
        )
        redis_layer = [l for l in resp.storage_layers if l.layer == "Redis"][0]
        assert redis_layer.encrypted is False

    @pytest.mark.asyncio
    async def test_llm_usage_info(self) -> None:
        from pwbs.api.v1.routes.user import get_security_status

        user = _make_user()

        resp = await get_security_status(
            response=MagicMock(),
            user=user,
        )
        assert "RAG" in resp.llm_usage
        assert "training" in resp.llm_usage.lower()


# ── Router metadata ──────────────────────────────────────────────────────────


class TestRouterMetadata:
    """Verify router configuration."""

    def test_prefix(self) -> None:
        from pwbs.api.v1.routes.user import router

        assert router.prefix == "/api/v1/user"

    def test_tags(self) -> None:
        from pwbs.api.v1.routes.user import router

        assert "user" in router.tags

    def test_route_count(self) -> None:
        from pwbs.api.v1.routes.user import router

        paths = [r.path for r in router.routes]
        assert "/api/v1/user/settings" in paths
        assert "/api/v1/user/export" in paths
        assert "/api/v1/user/export/{export_id}" in paths
        assert "/api/v1/user/export/{export_id}/download" in paths
        assert "/api/v1/user/account" in paths
        assert "/api/v1/user/account/cancel-deletion" in paths
        assert "/api/v1/user/audit-log" in paths
        assert "/api/v1/user/security" in paths
