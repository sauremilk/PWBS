"""Tests for Feature Flag system (TASK-174)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from pwbs.api.v1.routes.feature_flags import (
    FeatureFlagCheckResponse,
    FeatureFlagListResponse,
    FeatureFlagRequest,
    FeatureFlagResponse,
    _require_admin,
    check_feature_flag,
    list_feature_flags,
    upsert_feature_flag,
)
from pwbs.feature_flags.service import FeatureFlagService, _parse_env_overrides
from pwbs.models.feature_flag import FeatureFlag
from pwbs.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID | None = None, is_admin: bool = False) -> User:
    u = MagicMock(spec=User)
    u.id = user_id or USER_ID
    u.email = "test@example.com"
    u.display_name = "Test User"
    u.is_admin = is_admin
    return u


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def _mock_response() -> MagicMock:
    return MagicMock()


def _make_flag(
    flag_name: str = "test_flag",
    enabled_globally: bool = False,
    enabled_for_users: list[uuid.UUID] | None = None,
) -> FeatureFlag:
    f = MagicMock(spec=FeatureFlag)
    f.flag_name = flag_name
    f.enabled_globally = enabled_globally
    f.enabled_for_users = enabled_for_users or []
    return f


# ---------------------------------------------------------------------------
# Tests: _parse_env_overrides
# ---------------------------------------------------------------------------


class TestParseEnvOverrides:
    def test_empty_string(self) -> None:
        assert _parse_env_overrides("") == {}

    def test_single_flag(self) -> None:
        assert _parse_env_overrides("my_flag:true") == {"my_flag": True}

    def test_multiple_flags(self) -> None:
        result = _parse_env_overrides("flag_a:true,flag_b:false,flag_c:true")
        assert result == {"flag_a": True, "flag_b": False, "flag_c": True}

    def test_whitespace_handling(self) -> None:
        result = _parse_env_overrides(" flag_a : true , flag_b : false ")
        assert result == {"flag_a": True, "flag_b": False}

    def test_invalid_entries_skipped(self) -> None:
        result = _parse_env_overrides("valid:true,invalid,also_invalid:maybe")
        assert result == {"valid": True}


# ---------------------------------------------------------------------------
# Tests: _require_admin
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    def test_admin_passes(self) -> None:
        user = _make_user(is_admin=True)
        _require_admin(user)  # should not raise

    def test_non_admin_raises_403(self) -> None:
        user = _make_user(is_admin=False)
        with pytest.raises(HTTPException) as exc_info:
            _require_admin(user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Tests: FeatureFlagService.is_enabled
# ---------------------------------------------------------------------------


class TestFeatureFlagServiceIsEnabled:
    @pytest.mark.asyncio
    async def test_env_override_true(self) -> None:
        db = _mock_db()
        svc = FeatureFlagService(db)

        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={"beta_feature": True},
        ):
            result = await svc.is_enabled("beta_feature", USER_ID)
            assert result is True
            # No DB call needed
            db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_env_override_false(self) -> None:
        db = _mock_db()
        svc = FeatureFlagService(db)

        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={"beta_feature": False},
        ):
            result = await svc.is_enabled("beta_feature", USER_ID)
            assert result is False

    @pytest.mark.asyncio
    async def test_globally_enabled(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_flag(enabled_globally=True)
        db.execute.return_value = mock_result

        svc = FeatureFlagService(db)
        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={},
        ):
            result = await svc.is_enabled("test_flag", USER_ID)
            assert result is True

    @pytest.mark.asyncio
    async def test_user_in_whitelist(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_flag(
            enabled_globally=False, enabled_for_users=[USER_ID]
        )
        db.execute.return_value = mock_result

        svc = FeatureFlagService(db)
        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={},
        ):
            result = await svc.is_enabled("test_flag", USER_ID)
            assert result is True

    @pytest.mark.asyncio
    async def test_user_not_in_whitelist(self) -> None:
        other_id = uuid.uuid4()
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_flag(
            enabled_globally=False, enabled_for_users=[other_id]
        )
        db.execute.return_value = mock_result

        svc = FeatureFlagService(db)
        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={},
        ):
            result = await svc.is_enabled("test_flag", USER_ID)
            assert result is False

    @pytest.mark.asyncio
    async def test_flag_not_found(self) -> None:
        db = _mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        svc = FeatureFlagService(db)
        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={},
        ):
            result = await svc.is_enabled("nonexistent", USER_ID)
            assert result is False


# ---------------------------------------------------------------------------
# Tests: Admin API endpoints
# ---------------------------------------------------------------------------


class TestUpsertFeatureFlag:
    @pytest.mark.asyncio
    async def test_admin_can_create_flag(self) -> None:
        db = _mock_db()
        admin = _make_user(user_id=ADMIN_ID, is_admin=True)
        body = FeatureFlagRequest(flag_name="new_feature", enabled_globally=True)

        flag_mock = _make_flag(flag_name="new_feature", enabled_globally=True)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = flag_mock
        db.execute.return_value = mock_result

        result = await upsert_feature_flag(
            body=body,
            response=_mock_response(),
            user=admin,
            db=db,
        )

        assert isinstance(result, FeatureFlagResponse)
        assert result.flag_name == "new_feature"
        assert result.enabled_globally is True

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self) -> None:
        db = _mock_db()
        user = _make_user(is_admin=False)
        body = FeatureFlagRequest(flag_name="new_feature", enabled_globally=True)

        with pytest.raises(HTTPException) as exc_info:
            await upsert_feature_flag(
                body=body,
                response=_mock_response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


class TestListFeatureFlags:
    @pytest.mark.asyncio
    async def test_admin_can_list_flags(self) -> None:
        db = _mock_db()
        admin = _make_user(user_id=ADMIN_ID, is_admin=True)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_flag("flag_a", True),
            _make_flag("flag_b", False),
        ]
        db.execute.return_value = mock_result

        result = await list_feature_flags(
            response=_mock_response(),
            user=admin,
            db=db,
        )

        assert isinstance(result, FeatureFlagListResponse)
        assert len(result.flags) == 2

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self) -> None:
        db = _mock_db()
        user = _make_user(is_admin=False)

        with pytest.raises(HTTPException) as exc_info:
            await list_feature_flags(
                response=_mock_response(),
                user=user,
                db=db,
            )
        assert exc_info.value.status_code == 403


class TestCheckFeatureFlag:
    @pytest.mark.asyncio
    async def test_check_enabled_flag(self) -> None:
        db = _mock_db()
        user = _make_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_flag(enabled_globally=True)
        db.execute.return_value = mock_result

        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={},
        ):
            result = await check_feature_flag(
                flag_name="test_flag",
                response=_mock_response(),
                user=user,
                db=db,
            )

        assert isinstance(result, FeatureFlagCheckResponse)
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_check_disabled_flag(self) -> None:
        db = _mock_db()
        user = _make_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with patch(
            "pwbs.feature_flags.service._get_env_overrides",
            return_value={},
        ):
            result = await check_feature_flag(
                flag_name="missing_flag",
                response=_mock_response(),
                user=user,
                db=db,
            )

        assert result.enabled is False


# ---------------------------------------------------------------------------
# Tests: FeatureFlag model
# ---------------------------------------------------------------------------


class TestFeatureFlagModel:
    def test_table_name(self) -> None:
        assert FeatureFlag.__tablename__ == "feature_flags"

    def test_columns_present(self) -> None:
        cols = {c.name for c in FeatureFlag.__table__.columns}
        assert {"id", "flag_name", "enabled_globally", "enabled_for_users", "created_at"} <= cols

    def test_flag_name_unique(self) -> None:
        flag_name_col = FeatureFlag.__table__.c.flag_name
        assert flag_name_col.unique is True


# ---------------------------------------------------------------------------
# Tests: FeatureFlagRequest schema validation
# ---------------------------------------------------------------------------


class TestFeatureFlagRequestSchema:
    def test_valid_flag_name(self) -> None:
        req = FeatureFlagRequest(flag_name="beta.new-feature_v2")
        assert req.flag_name == "beta.new-feature_v2"

    def test_invalid_flag_name_uppercase(self) -> None:
        with pytest.raises(Exception):
            FeatureFlagRequest(flag_name="UPPERCASE")

    def test_empty_flag_name(self) -> None:
        with pytest.raises(Exception):
            FeatureFlagRequest(flag_name="")
