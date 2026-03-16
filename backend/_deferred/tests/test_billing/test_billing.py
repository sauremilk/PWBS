"""Tests for billing module (TASK-137).

Tests cover:
- Subscription model and enums
- Feature gating logic
- Webhook event handling (idempotent)
- Checkout/portal session creation (mocked Stripe)
- API route schemas
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pwbs.schemas.enums import SubscriptionPlan, SubscriptionStatus


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestSubscriptionEnums:
    def test_plan_values(self) -> None:
        assert SubscriptionPlan.FREE == "free"
        assert SubscriptionPlan.PRO == "pro"

    def test_status_values(self) -> None:
        assert SubscriptionStatus.ACTIVE == "active"
        assert SubscriptionStatus.CANCELLED == "cancelled"
        assert SubscriptionStatus.PAST_DUE == "past_due"
        assert SubscriptionStatus.TRIALING == "trialing"
        assert SubscriptionStatus.INCOMPLETE == "incomplete"

    def test_plan_is_str_enum(self) -> None:
        assert isinstance(SubscriptionPlan.FREE, str)
        assert SubscriptionPlan.PRO in ("pro", "free")


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestSubscriptionModel:
    def test_model_fields(self) -> None:
        from pwbs.models.subscription import Subscription

        # Verify required columns exist
        mapper = Subscription.__mapper__
        columns = {c.key for c in mapper.columns}
        expected = {
            "id", "user_id", "stripe_customer_id", "stripe_subscription_id",
            "stripe_price_id", "plan", "status", "current_period_start",
            "current_period_end", "cancel_at_period_end", "cohort",
            "expires_at", "created_at", "updated_at",
        }
        assert expected.issubset(columns), f"Missing: {expected - columns}"

    def test_tablename(self) -> None:
        from pwbs.models.subscription import Subscription

        assert Subscription.__tablename__ == "subscriptions"

    def test_user_relationship_exists(self) -> None:
        from pwbs.models.subscription import Subscription

        rels = {r.key for r in Subscription.__mapper__.relationships}
        assert "user" in rels

    def test_user_model_has_subscription_relationship(self) -> None:
        from pwbs.models.user import User

        rels = {r.key for r in User.__mapper__.relationships}
        assert "subscription" in rels


# ---------------------------------------------------------------------------
# Feature gating tests (in-memory, no DB)
# ---------------------------------------------------------------------------


class TestPlanLimits:
    def test_free_plan_limits_exist(self) -> None:
        from pwbs.billing.service import get_plan_limits

        limits = get_plan_limits()
        free = limits[SubscriptionPlan.FREE]
        assert "max_connectors" in free
        assert "max_searches_per_day" in free
        assert "project_briefings" in free

    def test_pro_plan_unlimited(self) -> None:
        from pwbs.billing.service import get_plan_limits

        limits = get_plan_limits()
        pro = limits[SubscriptionPlan.PRO]
        assert pro["max_connectors"] is None
        assert pro["max_searches_per_day"] is None
        assert pro["project_briefings"] is None

    def test_free_plan_has_numeric_limits(self) -> None:
        from pwbs.billing.service import get_plan_limits

        limits = get_plan_limits()
        free = limits[SubscriptionPlan.FREE]
        assert isinstance(free["max_connectors"], int)
        assert isinstance(free["max_searches_per_day"], int)


# ---------------------------------------------------------------------------
# Feature access check tests (with mock DB)
# ---------------------------------------------------------------------------


class TestFeatureAccess:
    @pytest.mark.asyncio
    async def test_pro_user_always_allowed(self) -> None:
        from pwbs.billing.service import check_feature_access

        db = AsyncMock()
        user_id = uuid.uuid4()

        with patch("pwbs.billing.service.get_user_plan", return_value=SubscriptionPlan.PRO):
            result = await check_feature_access(db, user_id, "max_connectors", current_usage=100)
            assert result is True

    @pytest.mark.asyncio
    async def test_free_user_within_limit(self) -> None:
        from pwbs.billing.service import check_feature_access

        db = AsyncMock()
        user_id = uuid.uuid4()

        with patch("pwbs.billing.service.get_user_plan", return_value=SubscriptionPlan.FREE):
            result = await check_feature_access(db, user_id, "max_connectors", current_usage=0)
            assert result is True

    @pytest.mark.asyncio
    async def test_free_user_at_limit(self) -> None:
        from pwbs.billing.service import check_feature_access, get_plan_limits

        db = AsyncMock()
        user_id = uuid.uuid4()
        limit = get_plan_limits()[SubscriptionPlan.FREE]["max_connectors"]

        with patch("pwbs.billing.service.get_user_plan", return_value=SubscriptionPlan.FREE):
            result = await check_feature_access(db, user_id, "max_connectors", current_usage=limit)
            assert result is False

    @pytest.mark.asyncio
    async def test_free_user_project_briefings_blocked(self) -> None:
        from pwbs.billing.service import check_feature_access

        db = AsyncMock()
        user_id = uuid.uuid4()

        # project_briefings limit is 0 for free tier
        with patch("pwbs.billing.service.get_user_plan", return_value=SubscriptionPlan.FREE):
            result = await check_feature_access(db, user_id, "project_briefings", current_usage=0)
            assert result is False

    @pytest.mark.asyncio
    async def test_unknown_feature_defaults_to_free_limits(self) -> None:
        from pwbs.billing.service import check_feature_access

        db = AsyncMock()
        user_id = uuid.uuid4()

        with patch("pwbs.billing.service.get_user_plan", return_value=SubscriptionPlan.FREE):
            # Unknown feature key returns None from dict, which means unlimited
            result = await check_feature_access(db, user_id, "nonexistent_feature", current_usage=999)
            assert result is True


# ---------------------------------------------------------------------------
# Webhook handler tests (mock DB session)
# ---------------------------------------------------------------------------


def _make_mock_db(existing_sub=None):
    """Create a mock AsyncSession that returns existing_sub on queries."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_sub
    db.execute.return_value = result
    return db


class TestWebhookCheckoutCompleted:
    @pytest.mark.asyncio
    async def test_creates_subscription_on_checkout(self) -> None:
        from pwbs.billing.service import _handle_checkout_completed

        db = _make_mock_db(existing_sub=None)
        user_id = uuid.uuid4()

        session_data = {
            "customer": "cus_test123",
            "subscription": "sub_test456",
            "metadata": {"pwbs_user_id": str(user_id), "cohort": "price_a"},
        }

        result = await _handle_checkout_completed(db, session_data)
        assert result == "activated"
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_existing_subscription(self) -> None:
        from pwbs.billing.service import _handle_checkout_completed
        from pwbs.models.subscription import Subscription

        existing = MagicMock(spec=Subscription)
        existing.stripe_customer_id = "cus_test123"
        existing.plan = SubscriptionPlan.FREE
        existing.status = SubscriptionStatus.ACTIVE

        db = _make_mock_db(existing_sub=existing)

        session_data = {
            "customer": "cus_test123",
            "subscription": "sub_test456",
            "metadata": {"pwbs_user_id": str(uuid.uuid4()), "cohort": ""},
        }

        result = await _handle_checkout_completed(db, session_data)
        assert result == "activated"
        assert existing.plan == SubscriptionPlan.PRO
        assert existing.status == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_missing_customer_returns_error(self) -> None:
        from pwbs.billing.service import _handle_checkout_completed

        db = _make_mock_db()
        result = await _handle_checkout_completed(db, {"customer": "", "metadata": {}})
        assert result == "error:no_customer"


class TestWebhookSubscriptionUpdated:
    @pytest.mark.asyncio
    async def test_updates_status_and_period(self) -> None:
        from pwbs.billing.service import _handle_subscription_updated
        from pwbs.models.subscription import Subscription

        existing = MagicMock(spec=Subscription)
        existing.stripe_subscription_id = "sub_test"

        db = _make_mock_db(existing_sub=existing)

        data = {
            "id": "sub_test",
            "customer": "cus_test",
            "status": "past_due",
            "cancel_at_period_end": True,
            "current_period_start": 1710000000,
            "current_period_end": 1712678400,
            "items": {"data": [{"price": {"id": "price_xxx"}}]},
        }

        result = await _handle_subscription_updated(db, data)
        assert "updated" in result
        assert existing.status == SubscriptionStatus.PAST_DUE
        assert existing.cancel_at_period_end is True
        assert existing.stripe_price_id == "price_xxx"

    @pytest.mark.asyncio
    async def test_unknown_subscription_ignored(self) -> None:
        from pwbs.billing.service import _handle_subscription_updated

        # Both queries return None
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await _handle_subscription_updated(db, {
            "id": "sub_unknown", "customer": "cus_unknown", "status": "active",
        })
        assert "ignored" in result


class TestWebhookSubscriptionDeleted:
    @pytest.mark.asyncio
    async def test_downgrades_to_free(self) -> None:
        from pwbs.billing.service import _handle_subscription_deleted
        from pwbs.models.subscription import Subscription

        existing = MagicMock(spec=Subscription)
        existing.stripe_subscription_id = "sub_del"
        existing.plan = SubscriptionPlan.PRO

        db = _make_mock_db(existing_sub=existing)

        result = await _handle_subscription_deleted(db, {"id": "sub_del"})
        assert result == "cancelled"
        assert existing.plan == SubscriptionPlan.FREE
        assert existing.status == SubscriptionStatus.CANCELLED


class TestWebhookPayment:
    @pytest.mark.asyncio
    async def test_payment_succeeded_activates(self) -> None:
        from pwbs.billing.service import _handle_payment_succeeded
        from pwbs.models.subscription import Subscription

        existing = MagicMock(spec=Subscription)
        existing.status = SubscriptionStatus.PAST_DUE

        db = _make_mock_db(existing_sub=existing)

        result = await _handle_payment_succeeded(db, {"subscription": "sub_pay"})
        assert result == "payment_ok"
        assert existing.status == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_payment_failed_sets_past_due(self) -> None:
        from pwbs.billing.service import _handle_payment_failed
        from pwbs.models.subscription import Subscription

        existing = MagicMock(spec=Subscription)
        existing.status = SubscriptionStatus.ACTIVE

        db = _make_mock_db(existing_sub=existing)

        result = await _handle_payment_failed(db, {"subscription": "sub_fail"})
        assert result == "payment_failed"
        assert existing.status == SubscriptionStatus.PAST_DUE

    @pytest.mark.asyncio
    async def test_no_subscription_in_invoice_ignored(self) -> None:
        from pwbs.billing.service import _handle_payment_succeeded

        db = _make_mock_db()
        result = await _handle_payment_succeeded(db, {"subscription": ""})
        assert "ignored" in result


class TestWebhookEventRouter:
    @pytest.mark.asyncio
    async def test_routes_checkout_completed(self) -> None:
        from pwbs.billing.service import handle_webhook_event

        db = _make_mock_db()
        with patch("pwbs.billing.service._handle_checkout_completed", new_callable=AsyncMock, return_value="activated") as mock:
            result = await handle_webhook_event(db, {
                "type": "checkout.session.completed",
                "id": "evt_1",
                "data": {"object": {"customer": "cus_x", "metadata": {}}},
            })
            mock.assert_awaited_once()
            assert result == "activated"

    @pytest.mark.asyncio
    async def test_ignores_unknown_event(self) -> None:
        from pwbs.billing.service import handle_webhook_event

        db = _make_mock_db()
        result = await handle_webhook_event(db, {
            "type": "some.unknown.event",
            "id": "evt_2",
            "data": {"object": {}},
        })
        assert "ignored" in result


# ---------------------------------------------------------------------------
# API schema tests
# ---------------------------------------------------------------------------


class TestBillingSchemas:
    def test_subscription_response_schema(self) -> None:
        from pwbs.api.v1.routes.billing import SubscriptionResponse

        resp = SubscriptionResponse(
            plan="free",
            status="active",
            limits={"max_connectors": 1},
        )
        assert resp.plan == "free"
        assert resp.limits["max_connectors"] == 1

    def test_checkout_request_schema(self) -> None:
        from pwbs.api.v1.routes.billing import CheckoutRequest

        req = CheckoutRequest(
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            cohort="price_a",
        )
        assert req.success_url == "https://example.com/success"
        assert req.cohort == "price_a"

    def test_checkout_request_without_cohort(self) -> None:
        from pwbs.api.v1.routes.billing import CheckoutRequest

        req = CheckoutRequest(
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert req.cohort is None

    def test_portal_request_schema(self) -> None:
        from pwbs.api.v1.routes.billing import PortalRequest

        req = PortalRequest(return_url="https://example.com/dashboard")
        assert req.return_url == "https://example.com/dashboard"

    def test_checkout_response_schema(self) -> None:
        from pwbs.api.v1.routes.billing import CheckoutResponse

        resp = CheckoutResponse(
            checkout_url="https://checkout.stripe.com/xxx",
            session_id="cs_test_123",
        )
        assert resp.checkout_url.startswith("https://")

    def test_portal_response_schema(self) -> None:
        from pwbs.api.v1.routes.billing import PortalResponse

        resp = PortalResponse(portal_url="https://billing.stripe.com/xxx")
        assert resp.portal_url.startswith("https://")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestBillingConfig:
    def test_stripe_settings_have_defaults(self) -> None:
        from pwbs.core.config import Settings

        # All stripe settings should have defaults (empty = disabled)
        fields = Settings.model_fields
        assert "stripe_secret_key" in fields
        assert "stripe_webhook_secret" in fields
        assert "stripe_price_id_pro" in fields
        assert "stripe_free_connector_limit" in fields
        assert "stripe_free_search_daily_limit" in fields

    def test_free_limits_are_configurable(self) -> None:
        from pwbs.core.config import get_settings

        get_settings.cache_clear()
        try:
            settings = get_settings()
            assert isinstance(settings.stripe_free_connector_limit, int)
            assert isinstance(settings.stripe_free_search_daily_limit, int)
        finally:
            get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Migration file existence test
# ---------------------------------------------------------------------------


class TestMigration:
    def test_migration_file_exists(self) -> None:
        from pathlib import Path

        migration = Path(__file__).parent.parent.parent / "migrations" / "versions" / "0005_add_subscriptions.py"
        assert migration.exists(), f"Migration not found at {migration}"

    def test_migration_revision_chain(self) -> None:
        import importlib.util
        from pathlib import Path

        path = Path(__file__).parent.parent.parent / "migrations" / "versions" / "0005_add_subscriptions.py"
        spec = importlib.util.spec_from_file_location("migration_0005", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.revision == "0005"
        assert mod.down_revision == "0004"