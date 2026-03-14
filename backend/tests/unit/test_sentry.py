"""Tests for pwbs.core.sentry -- Sentry integration (TASK-115)."""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pwbs.core.sentry import (
    _pseudonymise_user_id,
    _scrub_dict,
    before_send,
    init_sentry,
)


# ---------------------------------------------------------------------------
# _pseudonymise_user_id
# ---------------------------------------------------------------------------


class TestPseudonymiseUserID:
    def test_returns_hex_prefix(self) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = _pseudonymise_user_id(uid)
        expected = hashlib.sha256(uid.encode()).hexdigest()[:16]
        assert result == expected
        assert len(result) == 16

    def test_deterministic(self) -> None:
        uid = "test-user-id"
        assert _pseudonymise_user_id(uid) == _pseudonymise_user_id(uid)

    def test_different_users_differ(self) -> None:
        assert _pseudonymise_user_id("user-a") != _pseudonymise_user_id("user-b")


# ---------------------------------------------------------------------------
# _scrub_dict
# ---------------------------------------------------------------------------


class TestScrubDict:
    def test_removes_pii_keys(self) -> None:
        data = {"email": "user@example.com", "status": "ok"}
        result = _scrub_dict(data)
        assert result["email"] == "[Filtered]"
        assert result["status"] == "ok"

    def test_recursive_scrub(self) -> None:
        data = {"nested": {"password": "secret123", "level": 1}}
        result = _scrub_dict(data)
        assert result["nested"]["password"] == "[Filtered]"
        assert result["nested"]["level"] == 1

    def test_scrubs_list_of_dicts(self) -> None:
        data = {"items": [{"content": "sensitive", "id": 1}, {"name": "Jane"}]}
        result = _scrub_dict(data)
        assert result["items"][0]["content"] == "[Filtered]"
        assert result["items"][0]["id"] == 1
        assert result["items"][1]["name"] == "[Filtered]"

    def test_case_insensitive_keys(self) -> None:
        data = {"Email": "user@x.com", "PASSWORD": "s"}
        result = _scrub_dict(data)
        assert result["Email"] == "[Filtered]"
        assert result["PASSWORD"] == "[Filtered]"

    def test_empty_dict(self) -> None:
        assert _scrub_dict({}) == {}

    @pytest.mark.parametrize(
        "key",
        [
            "email", "password", "password_hash", "display_name", "name",
            "content", "body", "text", "token", "access_token",
            "refresh_token", "secret", "api_key", "phone", "address",
            "embedding", "embeddings", "metadata",
        ],
    )
    def test_all_pii_keys_scrubbed(self, key: str) -> None:
        data = {key: "sensitive-value"}
        result = _scrub_dict(data)
        assert result[key] == "[Filtered]"


# ---------------------------------------------------------------------------
# before_send
# ---------------------------------------------------------------------------


class TestBeforeSend:
    def test_scrubs_request_data(self) -> None:
        event: dict[str, Any] = {
            "request": {
                "data": {"email": "user@x.com", "action": "login"},
                "headers": {"Authorization": "Bearer xxx"},
            }
        }
        result = before_send(event, {})
        assert result is not None
        assert result["request"]["data"]["email"] == "[Filtered]"
        assert result["request"]["data"]["action"] == "login"
        assert result["request"]["headers"]["Authorization"] == "[Filtered]"

    def test_scrubs_cookie_header(self) -> None:
        event: dict[str, Any] = {
            "request": {"headers": {"Cookie": "session=abc123"}},
        }
        result = before_send(event, {})
        assert result is not None
        assert result["request"]["headers"]["Cookie"] == "[Filtered]"

    def test_scrubs_exception_vars(self) -> None:
        event: dict[str, Any] = {
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {"vars": {"password": "s3cret", "count": 5}}
                            ]
                        }
                    }
                ]
            }
        }
        result = before_send(event, {})
        assert result is not None
        frame_vars = result["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"]
        assert frame_vars["password"] == "[Filtered]"
        assert frame_vars["count"] == 5

    def test_scrubs_breadcrumbs(self) -> None:
        event: dict[str, Any] = {
            "breadcrumbs": {
                "values": [{"data": {"content": "sensitive stuff", "level": "info"}}]
            }
        }
        result = before_send(event, {})
        assert result is not None
        assert result["breadcrumbs"]["values"][0]["data"]["content"] == "[Filtered]"

    def test_attaches_request_id(self) -> None:
        from pwbs.core.logging import request_id_var

        token = request_id_var.set("req-abc-123")
        try:
            event: dict[str, Any] = {}
            result = before_send(event, {})
            assert result is not None
            assert result["tags"]["request_id"] == "req-abc-123"
        finally:
            request_id_var.reset(token)

    def test_attaches_pseudonymised_user_id(self) -> None:
        from pwbs.core.logging import user_id_var

        token = user_id_var.set("user-uuid-123")
        try:
            event: dict[str, Any] = {}
            result = before_send(event, {})
            assert result is not None
            expected = _pseudonymise_user_id("user-uuid-123")
            assert result["user"]["id"] == expected
        finally:
            user_id_var.reset(token)

    def test_no_context_vars_no_tags(self) -> None:
        from pwbs.core.logging import request_id_var, user_id_var

        # Ensure context vars are unset
        tok1 = request_id_var.set(None)
        tok2 = user_id_var.set(None)
        try:
            event: dict[str, Any] = {}
            result = before_send(event, {})
            assert result is not None
            assert "tags" not in result
            assert "user" not in result
        finally:
            request_id_var.reset(tok1)
            user_id_var.reset(tok2)

    def test_handles_empty_event(self) -> None:
        result = before_send({}, {})
        assert result == {} or isinstance(result, dict)

    def test_does_not_scrub_non_pii_request_data(self) -> None:
        event: dict[str, Any] = {
            "request": {"data": {"page": 1, "limit": 50}},
        }
        result = before_send(event, {})
        assert result is not None
        assert result["request"]["data"]["page"] == 1
        assert result["request"]["data"]["limit"] == 50


# ---------------------------------------------------------------------------
# init_sentry
# ---------------------------------------------------------------------------


class TestInitSentry:
    def test_no_dsn_skips_init(self) -> None:
        with patch("pwbs.core.sentry.logger") as mock_logger:
            init_sentry(dsn="", environment="development")
            mock_logger.info.assert_called_once()
            assert "disabled" in mock_logger.info.call_args[0][0].lower()

    def test_import_error_logs_warning(self) -> None:
        with (
            patch.dict("sys.modules", {"sentry_sdk": None}),
            patch("pwbs.core.sentry.logger") as mock_logger,
        ):
            import importlib
            import sys

            # Force import to fail by removing the module
            saved = sys.modules.pop("sentry_sdk", None)
            saved_fastapi = sys.modules.pop("sentry_sdk.integrations.fastapi", None)
            saved_starlette = sys.modules.pop("sentry_sdk.integrations.starlette", None)
            try:
                # Monkey-patch builtins to make import fail
                import builtins
                original_import = builtins.__import__

                def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
                    if name.startswith("sentry_sdk"):
                        raise ImportError("No module named 'sentry_sdk'")
                    return original_import(name, *args, **kwargs)

                builtins.__import__ = mock_import
                init_sentry(dsn="https://key@sentry.io/123", environment="test")
                mock_logger.warning.assert_called_once()
            finally:
                builtins.__import__ = original_import
                if saved is not None:
                    sys.modules["sentry_sdk"] = saved
                if saved_fastapi is not None:
                    sys.modules["sentry_sdk.integrations.fastapi"] = saved_fastapi
                if saved_starlette is not None:
                    sys.modules["sentry_sdk.integrations.starlette"] = saved_starlette

    def test_valid_dsn_calls_sentry_init(self) -> None:
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {
            "sentry_sdk": mock_sdk,
            "sentry_sdk.integrations": MagicMock(),
            "sentry_sdk.integrations.fastapi": MagicMock(),
            "sentry_sdk.integrations.starlette": MagicMock(),
        }):
            # Need to reimport to pick up mocked module
            import importlib

            from pwbs.core import sentry as sentry_mod

            # Directly call with mock
            import sentry_sdk
            with patch.object(sentry_sdk, "init") as mock_init:
                init_sentry(
                    dsn="https://key@sentry.io/123",
                    environment="production",
                    traces_sample_rate=0.5,
                )
                mock_init.assert_called_once()
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["dsn"] == "https://key@sentry.io/123"
                assert call_kwargs["environment"] == "production"
                assert call_kwargs["traces_sample_rate"] == 0.5
                assert call_kwargs["send_default_pii"] is False
                assert call_kwargs["before_send"] is before_send

    def test_sentry_dsn_config_field(self) -> None:
        """Verify Settings accepts sentry_dsn and sentry_traces_sample_rate."""
        from pwbs.core.config import Settings

        s = Settings(
            jwt_secret_key="test",
            encryption_master_key="test",
            sentry_dsn="https://key@sentry.io/1",
            sentry_traces_sample_rate=0.25,
        )
        assert s.sentry_dsn == "https://key@sentry.io/1"
        assert s.sentry_traces_sample_rate == 0.25

    def test_sentry_dsn_defaults_empty(self) -> None:
        """Verify sentry_dsn defaults to empty string (disabled)."""
        from pwbs.core.config import Settings

        s = Settings(
            jwt_secret_key="test",
            encryption_master_key="test",
        )
        assert s.sentry_dsn == ""
        assert s.sentry_traces_sample_rate == 1.0
