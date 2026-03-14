"""Tests for the Audit Log Service (TASK-106)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.audit.audit_service import (
    _PII_KEYS,
    AuditAction,
    get_client_ip,
    log_event,
    sanitize_metadata,
)

# ---------------------------------------------------------------------------
# AuditAction enum
# ---------------------------------------------------------------------------


class TestAuditAction:
    """Verify all 10 defined audit actions exist."""

    def test_all_actions_present(self) -> None:
        expected = {
            "user.registered",
            "user.login",
            "user.login_failed",
            "connection.created",
            "connection.deleted",
            "data.ingested",
            "briefing.generated",
            "search.executed",
            "data.exported",
            "user.deleted",
        }
        values = {a.value for a in AuditAction}
        assert values == expected

    def test_action_count(self) -> None:
        assert len(AuditAction) == 10

    def test_str_enum_value(self) -> None:
        assert AuditAction.USER_LOGIN == "user.login"


# ---------------------------------------------------------------------------
# sanitize_metadata
# ---------------------------------------------------------------------------


class TestSanitizeMetadata:
    """Metadata must not contain PII."""

    def test_none_returns_empty(self) -> None:
        assert sanitize_metadata(None) == {}

    def test_empty_dict(self) -> None:
        assert sanitize_metadata({}) == {}

    def test_safe_keys_preserved(self) -> None:
        meta = {"result_count": 5, "status_code": 200, "source_type": "notion"}
        assert sanitize_metadata(meta) == meta

    def test_pii_keys_stripped(self) -> None:
        meta = {
            "email": "test@example.com",
            "password": "secret",
            "result_count": 5,
        }
        assert sanitize_metadata(meta) == {"result_count": 5}

    def test_case_insensitive_stripping(self) -> None:
        meta = {"Email": "test@example.com", "ok": 1}
        assert sanitize_metadata(meta) == {"ok": 1}

    def test_all_pii_keys_blocked(self) -> None:
        meta = {k: "value" for k in _PII_KEYS}
        meta["safe_key"] = "allowed"
        result = sanitize_metadata(meta)
        assert result == {"safe_key": "allowed"}


# ---------------------------------------------------------------------------
# get_client_ip
# ---------------------------------------------------------------------------


class TestGetClientIp:
    """IP extraction from request."""

    def test_from_client_host(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.1"
        assert get_client_ip(request) == "192.168.1.1"

    def test_from_x_forwarded_for(self) -> None:
        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 172.16.0.1"}
        assert get_client_ip(request) == "10.0.0.1"

    def test_x_forwarded_for_single(self) -> None:
        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1"}
        assert get_client_ip(request) == "10.0.0.1"

    def test_no_client(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert get_client_ip(request) is None


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


class TestLogEvent:
    """Core append-only audit logging function."""

    @pytest.mark.asyncio
    async def test_creates_audit_entry(self) -> None:
        db = AsyncMock()
        user_id = uuid.uuid4()

        await log_event(
            db,
            action=AuditAction.USER_LOGIN,
            user_id=user_id,
            resource_type="user",
            resource_id=user_id,
            ip_address="127.0.0.1",
        )

        db.add.assert_called_once()
        entry = db.add.call_args[0][0]
        assert entry.action == "user.login"
        assert entry.user_id == user_id
        assert entry.resource_type == "user"
        assert entry.resource_id == user_id
        assert entry.ip_address == "127.0.0.1"
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_strips_pii_from_metadata(self) -> None:
        db = AsyncMock()
        await log_event(
            db,
            action=AuditAction.SEARCH_EXECUTED,
            metadata={"result_count": 3, "email": "leak@example.com"},
        )

        entry = db.add.call_args[0][0]
        assert entry.metadata_ == {"result_count": 3}

    @pytest.mark.asyncio
    async def test_login_failed_without_user_id(self) -> None:
        db = AsyncMock()
        await log_event(
            db,
            action=AuditAction.USER_LOGIN_FAILED,
            ip_address="10.0.0.1",
            metadata={"reason": "invalid_credentials"},
        )

        entry = db.add.call_args[0][0]
        assert entry.action == "user.login_failed"
        assert entry.user_id is None
        assert entry.ip_address == "10.0.0.1"
        assert entry.metadata_ == {"reason": "invalid_credentials"}

    @pytest.mark.asyncio
    async def test_default_empty_metadata(self) -> None:
        db = AsyncMock()
        await log_event(db, action=AuditAction.DATA_EXPORTED)

        entry = db.add.call_args[0][0]
        assert entry.metadata_ == {}

    @pytest.mark.asyncio
    async def test_logs_error_on_db_failure(self) -> None:
        db = AsyncMock()
        db.flush.side_effect = RuntimeError("DB down")

        with patch("pwbs.audit.audit_service.logger") as mock_logger:
            await log_event(db, action=AuditAction.USER_LOGIN)
            mock_logger.exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_never_raises(self) -> None:
        db = AsyncMock()
        db.flush.side_effect = RuntimeError("DB down")

        # Must not raise
        await log_event(db, action=AuditAction.USER_LOGIN)

    @pytest.mark.asyncio
    async def test_all_action_types_accepted(self) -> None:
        """Every AuditAction can be logged without error."""
        for action in AuditAction:
            db = AsyncMock()
            await log_event(db, action=action)
            db.add.assert_called_once()


# ---------------------------------------------------------------------------
# Auth route integration (unit-level)
# ---------------------------------------------------------------------------


class TestAuthAuditIntegration:
    """Verify audit events are triggered in auth routes."""

    @pytest.mark.asyncio
    async def test_register_logs_user_registered(self) -> None:
        from pwbs.api.v1.routes.auth import register
        from pwbs.services.auth import TokenPair
        from pwbs.services.user import RegisterRequest

        uid = uuid.uuid4()
        pair = TokenPair(
            access_token="access",
            refresh_token="refresh",
            expires_in=900,
        )

        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.1"

        with (
            patch(
                "pwbs.api.v1.routes.auth.register_user",
                new_callable=AsyncMock,
                return_value=pair,
            ),
            patch(
                "pwbs.api.v1.routes.auth.validate_access_token",
                return_value=MagicMock(user_id=uid),
            ),
            patch(
                "pwbs.api.v1.routes.auth.log_event",
                new_callable=AsyncMock,
            ) as mock_audit,
        ):
            body = RegisterRequest(
                email="test@example.com",
                password="SecurePass123",
                display_name="Test",
            )
            result = await register(body=body, request=mock_request, db=mock_db)

        assert result.user_id == uid
        mock_audit.assert_awaited_once()
        call_kwargs = mock_audit.call_args
        assert call_kwargs[1]["action"] == AuditAction.USER_REGISTERED
        assert call_kwargs[1]["user_id"] == uid
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_login_logs_user_login(self) -> None:
        from pwbs.api.v1.routes.auth import LoginRequest, login
        from pwbs.services.auth import TokenPair

        uid = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = uid
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed"

        pair = TokenPair(
            access_token="access",
            refresh_token="refresh",
            expires_in=900,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"

        with (
            patch("pwbs.api.v1.routes.auth.verify_password", return_value=True),
            patch(
                "pwbs.api.v1.routes.auth.create_token_pair",
                new_callable=AsyncMock,
                return_value=pair,
            ),
            patch(
                "pwbs.api.v1.routes.auth.log_event",
                new_callable=AsyncMock,
            ) as mock_audit,
        ):
            body = LoginRequest(email="test@example.com", password="password")
            result = await login(body=body, request=mock_request, db=mock_db)

        assert result.access_token == "access"
        mock_audit.assert_awaited_once()
        assert mock_audit.call_args[1]["action"] == AuditAction.USER_LOGIN
        assert mock_audit.call_args[1]["user_id"] == uid
        assert mock_audit.call_args[1]["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_login_failed_logs_security_event(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.auth import LoginRequest, login

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.99"

        with (
            patch("pwbs.api.v1.routes.auth.verify_password", return_value=False),
            patch(
                "pwbs.api.v1.routes.auth.log_event",
                new_callable=AsyncMock,
            ) as mock_audit,
        ):
            with pytest.raises(HTTPException) as exc_info:
                body = LoginRequest(email="hacker@example.com", password="wrong")
                await login(body=body, request=mock_request, db=mock_db)

        assert exc_info.value.status_code == 401
        mock_audit.assert_awaited_once()
        assert mock_audit.call_args[1]["action"] == AuditAction.USER_LOGIN_FAILED
        assert mock_audit.call_args[1]["ip_address"] == "10.0.0.99"
        # user_id should NOT be set for failed logins (no user leak)
        assert "user_id" not in mock_audit.call_args[1]
        # Commit before raising to ensure audit persists
        mock_db.commit.assert_awaited()
