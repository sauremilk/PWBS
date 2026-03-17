"""Tests for Connector Consent Management API (TASK-173)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from pwbs.api.v1.routes.connectors import (
    _CONSENT_INFO,
    ConsentGrantRequest,
    ConsentStatusResponse,
    get_consent,
    grant_consent,
    revoke_consent,
)
from pwbs.audit.audit_service import AuditAction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    return user


def _make_consent(
    owner_id: uuid.UUID,
    connector_type: str = "google_calendar",
    consent_version: int = 1,
    revoked_at: datetime | None = None,
) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.owner_id = owner_id
    c.connector_type = connector_type
    c.consent_version = consent_version
    c.consented_at = datetime(2025, 1, 15, 10, 0, tzinfo=UTC)
    c.revoked_at = revoked_at
    return c


def _mock_request() -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    return req


# ---------------------------------------------------------------------------
# _CONSENT_INFO registry
# ---------------------------------------------------------------------------


class TestConsentInfo:
    """Verify consent info is defined for all source types."""

    def test_has_google_calendar(self) -> None:
        assert "google_calendar" in _CONSENT_INFO
        info = _CONSENT_INFO["google_calendar"]
        assert len(info["data_types"]) > 0
        assert info["processing_purpose"]
        assert len(info["llm_providers"]) > 0

    def test_has_notion(self) -> None:
        assert "notion" in _CONSENT_INFO

    def test_has_obsidian(self) -> None:
        assert "obsidian" in _CONSENT_INFO

    def test_has_zoom(self) -> None:
        assert "zoom" in _CONSENT_INFO

    def test_all_entries_have_required_keys(self) -> None:
        for ct, info in _CONSENT_INFO.items():
            assert "data_types" in info, f"{ct} missing data_types"
            assert "processing_purpose" in info, f"{ct} missing processing_purpose"
            assert "llm_providers" in info, f"{ct} missing llm_providers"


# ---------------------------------------------------------------------------
# GET /connectors/{type}/consent
# ---------------------------------------------------------------------------


class TestGetConsent:
    """GET consent status endpoint."""

    @pytest.mark.asyncio
    async def test_returns_not_consented_when_no_record(self) -> None:
        user = _make_user()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        resp = await get_consent(type="google_calendar", current_user=user, db=db)
        assert resp.consented is False
        assert resp.connector_type == "google_calendar"
        assert resp.consent_version is None
        assert len(resp.data_types) > 0

    @pytest.mark.asyncio
    async def test_returns_consented_when_active(self) -> None:
        user = _make_user()
        consent = _make_consent(owner_id=user.id)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = consent
        db.execute.return_value = result_mock

        resp = await get_consent(type="google_calendar", current_user=user, db=db)
        assert resp.consented is True
        assert resp.consent_version == 1
        assert resp.consented_at is not None


# ---------------------------------------------------------------------------
# POST /connectors/{type}/consent
# ---------------------------------------------------------------------------


class TestGrantConsent:
    """POST consent grant endpoint."""

    @pytest.mark.asyncio
    @patch("pwbs.api.v1.routes.connectors.log_event", new_callable=AsyncMock)
    async def test_grant_creates_consent(self, mock_log: AsyncMock) -> None:
        user = _make_user()
        db = AsyncMock()

        # No existing consent
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        body = ConsentGrantRequest(consent_version=1)
        req = _mock_request()

        resp = await grant_consent(
            type="google_calendar",
            body=body,
            request=req,
            current_user=user,
            db=db,
        )
        assert resp.consented is True
        assert resp.connector_type == "google_calendar"
        db.add.assert_called_once()
        assert db.commit.await_count >= 1

    @pytest.mark.asyncio
    async def test_grant_409_when_already_exists(self) -> None:
        user = _make_user()
        consent = _make_consent(owner_id=user.id)
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = consent
        db.execute.return_value = result_mock

        body = ConsentGrantRequest(consent_version=1)
        req = _mock_request()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await grant_consent(
                type="google_calendar",
                body=body,
                request=req,
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# DELETE /connectors/{type}/consent
# ---------------------------------------------------------------------------


class TestRevokeConsent:
    """DELETE consent revoke endpoint."""

    @pytest.mark.asyncio
    @patch("pwbs.api.v1.routes.connectors.log_event", new_callable=AsyncMock)
    async def test_revoke_marks_consent_and_deletes_data(self, mock_log: AsyncMock) -> None:
        user = _make_user()
        consent = _make_consent(owner_id=user.id)
        db = AsyncMock()

        # First call: find consent; second: doc count; third: delete docs; fourth: find connection
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = consent
            elif call_count == 2:
                result.scalar.return_value = 5
            elif call_count == 3:
                pass  # delete result
            elif call_count == 4:
                result.scalar_one_or_none.return_value = None  # no connection
            return result

        db.execute = AsyncMock(side_effect=side_effect)

        req = _mock_request()
        resp = await revoke_consent(type="google_calendar", request=req, current_user=user, db=db)
        assert resp.deleted_doc_count == 5
        assert consent.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_404_when_no_active_consent(self) -> None:
        user = _make_user()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        req = _mock_request()

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await revoke_consent(type="google_calendar", request=req, current_user=user, db=db)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# ConsentStatusResponse schema
# ---------------------------------------------------------------------------


class TestConsentStatusSchema:
    """Schema validation."""

    def test_minimal_not_consented(self) -> None:
        resp = ConsentStatusResponse(
            connector_type="notion",
            consented=False,
        )
        assert resp.consent_version is None
        assert resp.data_types == []

    def test_full_consented(self) -> None:
        resp = ConsentStatusResponse(
            connector_type="notion",
            consented=True,
            consent_version=2,
            consented_at=datetime(2025, 1, 1, tzinfo=UTC),
            data_types=["pages"],
            processing_purpose="test",
            llm_providers=["Claude"],
        )
        assert resp.consented is True
        assert resp.consent_version == 2


# ---------------------------------------------------------------------------
# AuditAction additions
# ---------------------------------------------------------------------------


class TestConsentAuditActions:
    """Verify consent audit actions exist."""

    def test_consent_granted_action(self) -> None:
        assert AuditAction.CONSENT_GRANTED.value == "consent.granted"

    def test_consent_revoked_action(self) -> None:
        assert AuditAction.CONSENT_REVOKED.value == "consent.revoked"
