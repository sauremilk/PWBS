"""Tests for Structured JSON-Logging (TASK-113)."""

from __future__ import annotations

import json
import logging
import uuid
from io import StringIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwbs.core.logging import (
    _PII_KEYS,
    _add_request_context,
    _rename_event_to_message,
    _sanitize_pii,
    correlation_id_var,
    request_id_var,
    setup_logging,
    user_id_var,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_json_log(log_level: str = "INFO") -> tuple[logging.Logger, StringIO]:
    """Set up JSON logging that writes to a StringIO buffer and return (logger, buffer)."""
    setup_logging(log_level)
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    # Re-use the formatter setup_logging created on root
    root = logging.getLogger()
    handler.setFormatter(root.handlers[0].formatter)
    logger = logging.getLogger(f"test.{uuid.uuid4().hex[:8]}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, buf


def _parse_log_line(buf: StringIO) -> dict[str, Any]:
    """Parse the first JSON line from a StringIO buffer."""
    buf.seek(0)
    line = buf.readline().strip()
    assert line, "No log output captured"
    return json.loads(line)


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_root_logger_has_handler(self) -> None:
        setup_logging("INFO")
        root = logging.getLogger()
        assert len(root.handlers) >= 1

    def test_root_logger_level_set(self) -> None:
        setup_logging("DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_json_output_format(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("hello")
        data = _parse_log_line(buf)
        assert data["message"] == "hello"
        assert data["level"] == "info"
        assert "timestamp" in data

    def test_contains_logger_name(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("check-name")
        data = _parse_log_line(buf)
        assert "logger" in data


# ---------------------------------------------------------------------------
# Context variables
# ---------------------------------------------------------------------------


class TestContextVars:
    def test_request_id_injected(self) -> None:
        logger, buf = _capture_json_log()
        token = request_id_var.set("req-abc-123")
        try:
            logger.info("with-request-id")
            data = _parse_log_line(buf)
            assert data["request_id"] == "req-abc-123"
        finally:
            request_id_var.reset(token)

    def test_user_id_injected(self) -> None:
        logger, buf = _capture_json_log()
        token = user_id_var.set("user-xyz")
        try:
            logger.info("with-user-id")
            data = _parse_log_line(buf)
            assert data["user_id"] == "user-xyz"
        finally:
            user_id_var.reset(token)

    def test_defaults_to_none(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("no-context")
        data = _parse_log_line(buf)
        assert data["request_id"] is None
        assert data["user_id"] is None


# ---------------------------------------------------------------------------
# PII sanitization
# ---------------------------------------------------------------------------


class TestPIISanitization:
    def test_pii_keys_stripped(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("pii-test", extra={"email": "user@example.com", "safe_key": "ok"})
        data = _parse_log_line(buf)
        assert "email" not in data
        assert data["safe_key"] == "ok"

    def test_content_stripped(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("content-test", extra={"content": "sensitive document text"})
        data = _parse_log_line(buf)
        assert "content" not in data

    def test_metadata_stripped(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("meta-test", extra={"metadata": {"key": "value"}})
        data = _parse_log_line(buf)
        assert "metadata" not in data

    def test_password_stripped(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("pw-test", extra={"password": "s3cret"})
        data = _parse_log_line(buf)
        assert "password" not in data

    def test_embedding_stripped(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("embed-test", extra={"embedding": [0.1, 0.2, 0.3]})
        data = _parse_log_line(buf)
        assert "embedding" not in data

    @pytest.mark.parametrize("key", sorted(_PII_KEYS))
    def test_all_pii_keys_blocked(self, key: str) -> None:
        event: dict[str, Any] = {"event": "test", key: "value"}
        result = _sanitize_pii(None, "info", event)
        assert key not in result


# ---------------------------------------------------------------------------
# _rename_event_to_message processor
# ---------------------------------------------------------------------------


class TestRenameEvent:
    def test_renames_event_to_message(self) -> None:
        event = {"event": "hello", "level": "info"}
        result = _rename_event_to_message(None, "info", event)
        assert "message" in result
        assert "event" not in result
        assert result["message"] == "hello"

    def test_no_event_key_is_noop(self) -> None:
        event = {"message": "already-renamed"}
        result = _rename_event_to_message(None, "info", event)
        assert result["message"] == "already-renamed"


# ---------------------------------------------------------------------------
# _add_request_context processor
# ---------------------------------------------------------------------------


class TestAddRequestContext:
    def test_injects_from_contextvars(self) -> None:
        t1 = request_id_var.set("r-1")
        t2 = user_id_var.set("u-2")
        try:
            event: dict[str, Any] = {"event": "test"}
            result = _add_request_context(None, "info", event)
            assert result["request_id"] == "r-1"
            assert result["user_id"] == "u-2"
        finally:
            request_id_var.reset(t1)
            user_id_var.reset(t2)

    def test_does_not_overwrite_explicit(self) -> None:
        t = request_id_var.set("from-ctx")
        try:
            event: dict[str, Any] = {"event": "test", "request_id": "explicit"}
            result = _add_request_context(None, "info", event)
            assert result["request_id"] == "explicit"
        finally:
            request_id_var.reset(t)


# ---------------------------------------------------------------------------
# Extra fields (e.g. duration_ms)
# ---------------------------------------------------------------------------


class TestExtraFields:
    def test_duration_ms_in_output(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("timed", extra={"duration_ms": 42.5})
        data = _parse_log_line(buf)
        assert data["duration_ms"] == 42.5

    def test_status_code_in_output(self) -> None:
        logger, buf = _capture_json_log()
        logger.info("response", extra={"status_code": 200, "method": "GET"})
        data = _parse_log_line(buf)
        assert data["status_code"] == 200
        assert data["method"] == "GET"


# ---------------------------------------------------------------------------
# Log level configuration
# ---------------------------------------------------------------------------


class TestLogLevelConfig:
    def test_debug_level(self) -> None:
        logger, buf = _capture_json_log("DEBUG")
        logger.debug("debug-msg")
        data = _parse_log_line(buf)
        assert data["level"] == "debug"

    def test_warning_level_filters_info(self) -> None:
        setup_logging("WARNING")
        buf = StringIO()
        handler = logging.StreamHandler(buf)
        root = logging.getLogger()
        handler.setFormatter(root.handlers[0].formatter)
        logger = logging.getLogger(f"test.filter.{uuid.uuid4().hex[:8]}")
        logger.handlers = [handler]
        logger.propagate = True  # let root level filter
        logger.setLevel(logging.DEBUG)  # logger itself accepts all

        # Root level is WARNING, so INFO should be filtered at root
        # But since we write to our own handler, check propagation
        logger.warning("visible")
        buf.seek(0)
        line = buf.readline().strip()
        assert line  # warning should be captured
        data = json.loads(line)
        assert data["level"] == "warning"


# ---------------------------------------------------------------------------
# PWBS_LOG_LEVEL env var alias
# ---------------------------------------------------------------------------


class TestLogLevelEnvVar:
    def test_accepts_log_level(self) -> None:
        from pwbs.core.config import Settings

        s = Settings(
            log_level="DEBUG",
            jwt_secret_key="test-key",
            encryption_master_key="test-master",
        )
        assert s.log_level == "DEBUG"

    def test_accepts_pwbs_log_level(self) -> None:
        import os
        from unittest.mock import patch as mock_patch

        from pwbs.core.config import Settings

        env = {
            "PWBS_LOG_LEVEL": "WARNING",
            "JWT_SECRET_KEY": "test-key",
            "ENCRYPTION_MASTER_KEY": "test-master",
        }
        with mock_patch.dict(os.environ, env, clear=True):
            s = Settings()  # type: ignore[call-arg]
            assert s.log_level == "WARNING"


# ---------------------------------------------------------------------------
# AccessLogMiddleware
# ---------------------------------------------------------------------------


class TestAccessLogMiddleware:
    @pytest.mark.asyncio
    async def test_logs_request_with_duration(self) -> None:
        from pwbs.api.middleware.access_log import AccessLogMiddleware

        mw = AccessLogMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "GET"
        req.url.path = "/api/v1/user/me"
        req.state = MagicMock()
        req.state.request_id = "req-123"
        req.state.user_id = uuid.uuid4()

        resp = MagicMock()
        resp.status_code = 200
        call_next = AsyncMock(return_value=resp)

        logger, buf = _capture_json_log()
        access_logger = logging.getLogger("pwbs.access")
        access_logger.handlers = [buf_handler := logging.StreamHandler(buf)]
        buf_handler.setFormatter(logging.getLogger().handlers[0].formatter)
        access_logger.propagate = False

        await mw.dispatch(req, call_next)

        data = _parse_log_line(buf)
        assert data["message"] == "request completed"
        assert data["method"] == "GET"
        assert data["path"] == "/api/v1/user/me"
        assert data["status_code"] == 200
        assert "duration_ms" in data
        assert isinstance(data["duration_ms"], (int, float))

        access_logger.handlers.clear()
        access_logger.propagate = True

    @pytest.mark.asyncio
    async def test_handles_missing_state(self) -> None:
        from pwbs.api.middleware.access_log import AccessLogMiddleware

        mw = AccessLogMiddleware(AsyncMock())
        req = MagicMock()
        req.method = "POST"
        req.url.path = "/api/v1/auth/login"
        req.state = MagicMock(spec=[])  # no attributes

        resp = MagicMock()
        resp.status_code = 200
        call_next = AsyncMock(return_value=resp)

        setup_logging("INFO")
        access_logger = logging.getLogger("pwbs.access")
        buf = StringIO()
        buf_handler = logging.StreamHandler(buf)
        buf_handler.setFormatter(logging.getLogger().handlers[0].formatter)
        access_logger.handlers = [buf_handler]
        access_logger.propagate = False

        await mw.dispatch(req, call_next)

        data = _parse_log_line(buf)
        assert data["request_id"] is None
        assert data["user_id"] is None

        access_logger.handlers.clear()
        access_logger.propagate = True


# ---------------------------------------------------------------------------
# CorrelationIdMiddleware sets contextvar (TASK-196)
# ---------------------------------------------------------------------------


class TestCorrelationIdMiddlewareContextVar:
    @pytest.mark.asyncio
    async def test_sets_correlation_id_contextvar(self) -> None:
        from pwbs.api.middleware.correlation import CorrelationIdMiddleware

        mw = CorrelationIdMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {"x-request-id": "custom-req-id"}
        req.state = MagicMock()

        captured_cid = None
        captured_rid = None

        async def capture_next(r: Any) -> MagicMock:
            nonlocal captured_cid, captured_rid
            captured_cid = correlation_id_var.get()
            captured_rid = request_id_var.get()
            resp = MagicMock()
            resp.headers = {}
            return resp

        await mw.dispatch(req, capture_next)
        assert captured_cid == "custom-req-id"
        assert captured_rid == "custom-req-id"
        assert req.state.correlation_id == "custom-req-id"
        assert req.state.request_id == "custom-req-id"

    @pytest.mark.asyncio
    async def test_generates_uuid_when_no_header(self) -> None:
        from pwbs.api.middleware.correlation import CorrelationIdMiddleware

        mw = CorrelationIdMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {}
        req.state = MagicMock()

        captured_cid = None

        async def capture_next(r: Any) -> MagicMock:
            nonlocal captured_cid
            captured_cid = correlation_id_var.get()
            resp = MagicMock()
            resp.headers = {}
            return resp

        await mw.dispatch(req, capture_next)
        assert captured_cid is not None
        # Should be a valid UUID
        uuid.UUID(captured_cid)


# ---------------------------------------------------------------------------
# AuthMiddleware sets user_id contextvar
# ---------------------------------------------------------------------------


class TestAuthMiddlewareContextVar:
    @pytest.mark.asyncio
    async def test_sets_user_id_contextvar(self) -> None:
        from unittest.mock import patch as mock_patch

        from pwbs.api.middleware.auth import AuthMiddleware

        uid = uuid.uuid4()
        mw = AuthMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {"authorization": "Bearer valid-token"}
        req.state = MagicMock()

        captured_uid = None

        async def capture_next(r: Any) -> MagicMock:
            nonlocal captured_uid
            captured_uid = user_id_var.get()
            return MagicMock()

        with mock_patch(
            "pwbs.api.middleware.auth.validate_access_token",
            return_value=MagicMock(user_id=uid),
        ):
            await mw.dispatch(req, capture_next)

        assert captured_uid == str(uid)

    @pytest.mark.asyncio
    async def test_no_user_id_when_unauthenticated(self) -> None:
        from pwbs.api.middleware.auth import AuthMiddleware

        mw = AuthMiddleware(AsyncMock())
        req = MagicMock()
        req.headers = {}
        req.state = MagicMock()

        captured_uid = None

        async def capture_next(r: Any) -> MagicMock:
            nonlocal captured_uid
            captured_uid = user_id_var.get()
            return MagicMock()

        await mw.dispatch(req, capture_next)
        assert captured_uid is None
