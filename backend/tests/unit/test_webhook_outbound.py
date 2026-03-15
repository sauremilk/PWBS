"""Tests for Outbound Webhook service and API (TASK-189).

All external HTTP calls and DB sessions are mocked.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pwbs.services.webhook_outbound import (
    SUPPORTED_EVENTS,
    DeliveryResult,
    deliver_webhook,
    sign_payload,
)

# ---------------------------------------------------------------------------
# sign_payload
# ---------------------------------------------------------------------------


class TestSignPayload:
    def test_produces_sha256_prefix(self) -> None:
        sig = sign_payload(b'{"test": true}', "secret123")
        assert sig.startswith("sha256=")

    def test_deterministic(self) -> None:
        body = b'{"a": 1}'
        assert sign_payload(body, "s") == sign_payload(body, "s")

    def test_different_secrets(self) -> None:
        body = b"hello"
        assert sign_payload(body, "s1") != sign_payload(body, "s2")

    def test_matches_manual_hmac(self) -> None:
        body = b'{"event": "test"}'
        secret = "my_secret"
        expected = (
            "sha256="
            + hmac.new(
                secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
        )
        assert sign_payload(body, secret) == expected


# ---------------------------------------------------------------------------
# SUPPORTED_EVENTS
# ---------------------------------------------------------------------------


class TestSupportedEvents:
    def test_contains_required_events(self) -> None:
        assert "briefing.generated" in SUPPORTED_EVENTS
        assert "document.ingested" in SUPPORTED_EVENTS
        assert "connector.error" in SUPPORTED_EVENTS

    def test_is_frozenset(self) -> None:
        assert isinstance(SUPPORTED_EVENTS, frozenset)


# ---------------------------------------------------------------------------
# deliver_webhook
# ---------------------------------------------------------------------------


class TestDeliverWebhook:
    @pytest.mark.asyncio
    async def test_success_first_attempt(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post.return_value = mock_response

        with patch("pwbs.services.webhook_outbound.httpx.AsyncClient", return_value=mock_client):
            results = await deliver_webhook(
                url="https://example.com/hook",
                secret="test_secret",
                event_type="briefing.generated",
                payload={"test": True},
                max_attempts=3,
            )

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].status_code == 200
        assert results[0].attempt == 1

    @pytest.mark.asyncio
    async def test_failure_returns_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post.return_value = mock_response

        with patch("pwbs.services.webhook_outbound.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                results = await deliver_webhook(
                    url="https://example.com/hook",
                    secret="s",
                    event_type="test",
                    payload={},
                    max_attempts=2,
                )

        assert len(results) == 2
        assert all(not r.success for r in results)
        assert results[0].attempt == 1
        assert results[1].attempt == 2

    @pytest.mark.asyncio
    async def test_network_error_caught(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post.side_effect = ConnectionError("Connection refused")

        with patch("pwbs.services.webhook_outbound.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                results = await deliver_webhook(
                    url="https://example.com/hook",
                    secret="s",
                    event_type="test",
                    payload={},
                    max_attempts=1,
                )

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].status_code is None
        assert "Connection refused" in (results[0].error_message or "")

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        fail_resp.text = "Unavailable"

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.text = "OK"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post.side_effect = [fail_resp, ok_resp]

        with patch("pwbs.services.webhook_outbound.httpx.AsyncClient", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                results = await deliver_webhook(
                    url="https://example.com/hook",
                    secret="s",
                    event_type="test",
                    payload={},
                    max_attempts=3,
                )

        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True
        assert results[1].attempt == 2

    @pytest.mark.asyncio
    async def test_signature_header_sent(self) -> None:
        payload = {"event": "briefing.generated"}
        secret = "my_secret"
        body = json.dumps(payload, default=str).encode()
        expected_sig = sign_payload(body, secret)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post.return_value = mock_response

        with patch("pwbs.services.webhook_outbound.httpx.AsyncClient", return_value=mock_client):
            await deliver_webhook(
                url="https://example.com/hook",
                secret=secret,
                event_type="briefing.generated",
                payload=payload,
                max_attempts=1,
            )

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert headers["X-PWBS-Signature"] == expected_sig
        assert headers["X-PWBS-Event"] == "briefing.generated"

    @pytest.mark.asyncio
    async def test_duration_ms_positive(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post.return_value = mock_response

        with patch("pwbs.services.webhook_outbound.httpx.AsyncClient", return_value=mock_client):
            results = await deliver_webhook(
                url="https://example.com/hook",
                secret="s",
                event_type="test",
                payload={},
                max_attempts=1,
            )

        assert results[0].duration_ms >= 0


# ---------------------------------------------------------------------------
# Webhook model import check
# ---------------------------------------------------------------------------


class TestWebhookModel:
    def test_model_importable(self) -> None:
        from pwbs.models.webhook import Webhook, WebhookDelivery

        assert Webhook.__tablename__ == "webhooks"
        assert WebhookDelivery.__tablename__ == "webhook_deliveries"

    def test_registered_in_init(self) -> None:
        from pwbs.models import Webhook, WebhookDelivery

        assert Webhook is not None
        assert WebhookDelivery is not None
