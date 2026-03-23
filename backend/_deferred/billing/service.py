"""Billing service (TASK-137): Stripe checkout, webhooks, feature gating.

Handles:
- Stripe Checkout Session creation for new subscriptions
- Stripe Customer Portal sessions for self-management
- Webhook processing (idempotent) for payment/subscription events
- Feature-gating logic: Free vs Pro tier
- A/B cohort assignment for price testing
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.config import get_settings
from pwbs.models.subscription import Subscription
from pwbs.schemas.enums import SubscriptionPlan, SubscriptionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature limits per plan
# ---------------------------------------------------------------------------

def _get_plan_limits() -> dict[str, dict[str, int | None]]:
    """Return feature limits per plan. None = unlimited."""
    settings = get_settings()
    return {
        SubscriptionPlan.FREE: {
            "max_connectors": settings.stripe_free_connector_limit,
            "max_searches_per_day": settings.stripe_free_search_daily_limit,
            "project_briefings": 0,
        },
        SubscriptionPlan.PRO: {
            "max_connectors": None,
            "max_searches_per_day": None,
            "project_briefings": None,
        },
    }


PLAN_LIMITS = None  # lazy-initialized


def get_plan_limits() -> dict[str, dict[str, int | None]]:
    global PLAN_LIMITS
    if PLAN_LIMITS is None:
        PLAN_LIMITS = _get_plan_limits()
    return PLAN_LIMITS


# ---------------------------------------------------------------------------
# Subscription queries
# ---------------------------------------------------------------------------

async def get_user_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Subscription | None:
    """Get the subscription record for a user, or None if none exists."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_free_subscription(
    db: AsyncSession,
    user_id: uuid.UUID,
    stripe_customer_id: str = "",
) -> Subscription:
    """Return existing subscription or create a free-tier one."""
    sub = await get_user_subscription(db, user_id)
    if sub is not None:
        return sub

    sub = Subscription(
        user_id=user_id,
        stripe_customer_id=stripe_customer_id or f"cus_free_{user_id.hex[:16]}",
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
    )
    db.add(sub)
    await db.flush()
    return sub


async def get_user_plan(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Return the user's current plan name (defaults to 'free')."""
    sub = await get_user_subscription(db, user_id)
    if sub is None:
        return SubscriptionPlan.FREE
    if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        return SubscriptionPlan.FREE
    return sub.plan


# ---------------------------------------------------------------------------
# Feature gating
# ---------------------------------------------------------------------------

async def check_feature_access(
    db: AsyncSession,
    user_id: uuid.UUID,
    feature: str,
    current_usage: int = 0,
) -> bool:
    """Check whether a user has access to a feature given their plan.

    Parameters
    ----------
    feature:
        Key from PLAN_LIMITS, e.g. "max_connectors", "max_searches_per_day"
    current_usage:
        Current count (e.g. number of active connectors).

    Returns
    -------
    True if allowed, False if limit reached.
    """
    plan = await get_user_plan(db, user_id)
    limits = get_plan_limits()
    plan_limits = limits.get(plan, limits[SubscriptionPlan.FREE])
    limit = plan_limits.get(feature)

    if limit is None:
        return True  # unlimited
    return current_usage < limit


# ---------------------------------------------------------------------------
# Stripe Checkout
# ---------------------------------------------------------------------------

async def create_checkout_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_email: str,
    success_url: str,
    cancel_url: str,
    cohort: str | None = None,
) -> dict[str, str]:
    """Create a Stripe Checkout Session for upgrading to Pro.

    Returns dict with 'checkout_url' and 'session_id'.
    Raises ValueError if Stripe is not configured or user already has active Pro.
    """
    settings = get_settings()
    stripe_key = settings.stripe_secret_key.get_secret_value()
    if not stripe_key:
        raise ValueError("Stripe is not configured (STRIPE_SECRET_KEY missing)")

    price_id = settings.stripe_price_id_pro
    if not price_id:
        raise ValueError("Stripe Pro price ID not configured (STRIPE_PRICE_ID_PRO)")

    # Check existing subscription
    sub = await get_user_subscription(db, user_id)
    if sub and sub.plan == SubscriptionPlan.PRO and sub.status == SubscriptionStatus.ACTIVE:
        raise ValueError("User already has an active Pro subscription")

    import stripe
    stripe.api_key = stripe_key

    # Get or create Stripe customer
    customer_id: str | None = None
    if sub and sub.stripe_customer_id and not sub.stripe_customer_id.startswith("cus_free_"):
        customer_id = sub.stripe_customer_id

    if not customer_id:
        customer = stripe.Customer.create(
            email=user_email,
            metadata={"pwbs_user_id": str(user_id)},
        )
        customer_id = customer.id

        # Upsert subscription record with Stripe customer ID
        if sub is None:
            sub = Subscription(
                user_id=user_id,
                stripe_customer_id=customer_id,
                plan=SubscriptionPlan.FREE,
                status=SubscriptionStatus.ACTIVE,
                cohort=cohort,
            )
            db.add(sub)
        else:
            sub.stripe_customer_id = customer_id
            if cohort:
                sub.cohort = cohort
        await db.flush()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"pwbs_user_id": str(user_id), "cohort": cohort or ""},
    )

    return {"checkout_url": session.url, "session_id": session.id}


# ---------------------------------------------------------------------------
# Stripe Customer Portal
# ---------------------------------------------------------------------------

async def create_portal_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    return_url: str,
) -> dict[str, str]:
    """Create a Stripe Customer Portal session for self-service management.

    Returns dict with 'portal_url'.
    """
    settings = get_settings()
    stripe_key = settings.stripe_secret_key.get_secret_value()
    if not stripe_key:
        raise ValueError("Stripe is not configured")

    sub = await get_user_subscription(db, user_id)
    if not sub or sub.stripe_customer_id.startswith("cus_free_"):
        raise ValueError("No Stripe customer found for this user")

    import stripe
    stripe.api_key = stripe_key

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )

    return {"portal_url": session.url}


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def verify_stripe_signature(
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
) -> dict[str, Any]:
    """Verify Stripe webhook signature and return parsed event.

    Raises ValueError if signature is invalid.
    """
    import stripe
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        return dict(event)
    except stripe.error.SignatureVerificationError as exc:
        raise ValueError(f"Invalid Stripe webhook signature: {exc}") from exc


# ---------------------------------------------------------------------------
# Webhook event processing (idempotent)
# ---------------------------------------------------------------------------

async def handle_webhook_event(
    db: AsyncSession,
    event: dict[str, Any],
) -> str:
    """Process a Stripe webhook event idempotently.

    Returns a status string for logging.
    Supported events:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    logger.info("Processing Stripe event: type=%s id=%s", event_type, event.get("id"))

    if event_type == "checkout.session.completed":
        return await _handle_checkout_completed(db, data_obj)
    elif event_type == "customer.subscription.updated":
        return await _handle_subscription_updated(db, data_obj)
    elif event_type == "customer.subscription.deleted":
        return await _handle_subscription_deleted(db, data_obj)
    elif event_type == "invoice.payment_succeeded":
        return await _handle_payment_succeeded(db, data_obj)
    elif event_type == "invoice.payment_failed":
        return await _handle_payment_failed(db, data_obj)
    else:
        logger.debug("Ignoring unhandled Stripe event type: %s", event_type)
        return f"ignored:{event_type}"


async def _handle_checkout_completed(
    db: AsyncSession,
    session: dict[str, Any],
) -> str:
    """Handle checkout.session.completed: activate Pro subscription."""
    customer_id = session.get("customer", "")
    subscription_id = session.get("subscription", "")
    metadata = session.get("metadata", {})
    user_id_str = metadata.get("pwbs_user_id", "")
    cohort = metadata.get("cohort", "")

    if not customer_id:
        logger.warning("checkout.session.completed without customer ID")
        return "error:no_customer"

    # Find subscription by stripe_customer_id
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None and user_id_str:
        # Create new subscription record
        sub = Subscription(
            user_id=uuid.UUID(user_id_str),
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            cohort=cohort or None,
        )
        db.add(sub)
    elif sub is not None:
        # Upsert: update existing
        sub.stripe_subscription_id = subscription_id
        sub.plan = SubscriptionPlan.PRO
        sub.status = SubscriptionStatus.ACTIVE
        if cohort:
            sub.cohort = cohort
    else:
        logger.warning("checkout.session.completed: no user_id in metadata")
        return "error:no_user_id"

    await db.flush()
    logger.info("Subscription activated: customer=%s user=%s", customer_id, user_id_str)
    return "activated"


async def _handle_subscription_updated(
    db: AsyncSession,
    subscription_data: dict[str, Any],
) -> str:
    """Handle customer.subscription.updated: sync status and period."""
    stripe_sub_id = subscription_data.get("id", "")
    customer_id = subscription_data.get("customer", "")
    status_val = subscription_data.get("status", "")
    cancel_at_end = subscription_data.get("cancel_at_period_end", False)

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        # Try by customer ID
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == customer_id
            )
        )
        sub = result.scalar_one_or_none()

    if sub is None:
        logger.warning("subscription.updated for unknown subscription: %s", stripe_sub_id)
        return "ignored:unknown_subscription"

    # Map Stripe status to our enum
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "canceled": SubscriptionStatus.CANCELLED,
        "past_due": SubscriptionStatus.PAST_DUE,
        "trialing": SubscriptionStatus.TRIALING,
        "incomplete": SubscriptionStatus.INCOMPLETE,
    }
    sub.status = status_map.get(status_val, SubscriptionStatus.ACTIVE)
    sub.cancel_at_period_end = bool(cancel_at_end)

    # Update period
    period_start = subscription_data.get("current_period_start")
    period_end = subscription_data.get("current_period_end")
    if period_start:
        sub.current_period_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    # Update price ID from items
    items = subscription_data.get("items", {}).get("data", [])
    if items:
        first_item = items[0]
        price = first_item.get("price", {})
        sub.stripe_price_id = price.get("id")

    await db.flush()
    logger.info("Subscription updated: sub_id=%s status=%s", stripe_sub_id, sub.status)
    return f"updated:{sub.status}"


async def _handle_subscription_deleted(
    db: AsyncSession,
    subscription_data: dict[str, Any],
) -> str:
    """Handle customer.subscription.deleted: downgrade to free."""
    stripe_sub_id = subscription_data.get("id", "")

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_sub_id
        )
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        logger.warning("subscription.deleted for unknown: %s", stripe_sub_id)
        return "ignored:unknown"

    sub.plan = SubscriptionPlan.FREE
    sub.status = SubscriptionStatus.CANCELLED
    sub.stripe_subscription_id = None
    sub.stripe_price_id = None
    sub.current_period_start = None
    sub.current_period_end = None
    sub.cancel_at_period_end = False

    await db.flush()
    logger.info("Subscription cancelled, downgraded to free: sub_id=%s", stripe_sub_id)
    return "cancelled"


async def _handle_payment_succeeded(
    db: AsyncSession,
    invoice: dict[str, Any],
) -> str:
    """Handle invoice.payment_succeeded: confirm active status."""
    subscription_id = invoice.get("subscription", "")
    if not subscription_id:
        return "ignored:no_subscription"

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if sub and sub.status != SubscriptionStatus.ACTIVE:
        sub.status = SubscriptionStatus.ACTIVE
        await db.flush()
        logger.info("Payment succeeded, status set to active: sub=%s", subscription_id)

    return "payment_ok"


async def _handle_payment_failed(
    db: AsyncSession,
    invoice: dict[str, Any],
) -> str:
    """Handle invoice.payment_failed: set past_due status."""
    subscription_id = invoice.get("subscription", "")
    if not subscription_id:
        return "ignored:no_subscription"

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = SubscriptionStatus.PAST_DUE
        await db.flush()
        logger.info("Payment failed, status set to past_due: sub=%s", subscription_id)

    return "payment_failed"
