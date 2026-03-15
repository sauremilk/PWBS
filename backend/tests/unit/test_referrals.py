"""Unit tests for referral endpoints (TASK-180)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_user(
    user_id: uuid.UUID | None = None,
    email: str = "user@test.com",
    display_name: str = "Test User",
) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.display_name = display_name
    return user


def _make_referral(
    referrer_id: uuid.UUID,
    referee_id: uuid.UUID | None = None,
    status: str = "pending",
    code: str | None = None,
    referee: MagicMock | None = None,
) -> MagicMock:
    ref = MagicMock()
    ref.id = uuid.uuid4()
    ref.referrer_id = referrer_id
    ref.referee_id = referee_id
    ref.code = code or str(uuid.uuid4())
    ref.status = status
    ref.converted_at = datetime.now(UTC) if status == "converted" else None
    ref.created_at = datetime.now(UTC)
    ref.referee = referee
    ref.referrer = _make_user(user_id=referrer_id)
    return ref


class TestListReferrals:
    @pytest.mark.asyncio
    async def test_returns_referral_code_and_list(self) -> None:
        from pwbs.api.v1.routes.referrals import list_referrals

        user = _make_user()
        db = AsyncMock()

        existing_code = str(uuid.uuid4())
        pending_ref = _make_referral(referrer_id=user.id, code=existing_code)

        # First call: get_or_create_referral_code (returns existing pending)
        # Second call: list all referrals
        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none.return_value = pending_ref

        mock_result_2 = MagicMock()
        mock_result_2.scalars.return_value.all.return_value = [pending_ref]

        db.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        result = await list_referrals(current_user=user, db=db)

        assert result.my_code == existing_code
        assert len(result.referrals) == 1
        assert result.total_converted == 0

    @pytest.mark.asyncio
    async def test_creates_new_code_when_none_exists(self) -> None:
        from pwbs.api.v1.routes.referrals import list_referrals

        user = _make_user()
        db = AsyncMock()

        # First call: no existing pending referral
        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none.return_value = None

        # Second call: list (empty)
        mock_result_2 = MagicMock()
        mock_result_2.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        result = await list_referrals(current_user=user, db=db)

        assert result.my_code  # UUID string
        assert len(result.referrals) == 0
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_counts_converted_referrals(self) -> None:
        from pwbs.api.v1.routes.referrals import list_referrals

        user = _make_user()
        db = AsyncMock()

        ref1 = _make_referral(referrer_id=user.id, status="converted")
        ref2 = _make_referral(referrer_id=user.id, status="converted")
        ref3 = _make_referral(referrer_id=user.id, status="pending")

        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none.return_value = ref3

        mock_result_2 = MagicMock()
        mock_result_2.scalars.return_value.all.return_value = [ref1, ref2, ref3]

        db.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        result = await list_referrals(current_user=user, db=db)

        assert result.total_converted == 2


class TestConvertReferral:
    @pytest.mark.asyncio
    async def test_converts_valid_code(self) -> None:
        from pwbs.api.v1.routes.referrals import ConvertReferralRequest, convert_referral

        referrer = _make_user(display_name="Alice")
        referee = _make_user()
        code = str(uuid.uuid4())
        referral = _make_referral(referrer_id=referrer.id, code=code)
        referral.referrer = referrer

        db = AsyncMock()
        # First call: find referral by code
        mock_result_1 = MagicMock()
        mock_result_1.scalar_one_or_none.return_value = referral
        # Second call: check existing referral for referee
        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        body = ConvertReferralRequest(code=code)
        result = await convert_referral(body=body, current_user=referee, db=db)

        assert result.message == "referral_linked"
        assert result.referrer_display_name == "Alice"
        assert referral.referee_id == referee.id
        assert referral.status == "converted"
        db.add.assert_called_once()  # new pending code for referrer
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_invalid_code(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.referrals import ConvertReferralRequest, convert_referral

        user = _make_user()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        body = ConvertReferralRequest(code="nonexistent")
        with pytest.raises(HTTPException) as exc_info:
            await convert_referral(body=body, current_user=user, db=db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_self_referral(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.referrals import ConvertReferralRequest, convert_referral

        user = _make_user()
        referral = _make_referral(referrer_id=user.id)

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = referral
        db.execute = AsyncMock(return_value=mock_result)

        body = ConvertReferralRequest(code=referral.code)
        with pytest.raises(HTTPException) as exc_info:
            await convert_referral(body=body, current_user=user, db=db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_idempotent_same_user(self) -> None:
        from pwbs.api.v1.routes.referrals import ConvertReferralRequest, convert_referral

        referrer = _make_user(display_name="Bob")
        referee = _make_user()

        referral = _make_referral(
            referrer_id=referrer.id,
            referee_id=referee.id,
            status="converted",
        )
        referral.referrer = referrer

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = referral
        db.execute = AsyncMock(return_value=mock_result)

        body = ConvertReferralRequest(code=referral.code)
        result = await convert_referral(body=body, current_user=referee, db=db)

        assert result.referrer_display_name == "Bob"
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rejects_already_used_code(self) -> None:
        from fastapi import HTTPException

        from pwbs.api.v1.routes.referrals import ConvertReferralRequest, convert_referral

        other_user = _make_user()
        new_user = _make_user()
        referral = _make_referral(
            referrer_id=uuid.uuid4(),
            referee_id=other_user.id,
            status="converted",
        )

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = referral
        db.execute = AsyncMock(return_value=mock_result)

        body = ConvertReferralRequest(code=referral.code)
        with pytest.raises(HTTPException) as exc_info:
            await convert_referral(body=body, current_user=new_user, db=db)
        assert exc_info.value.status_code == 409
