"""Billing API endpoints (TASK-137).

GET    /api/v1/billing/subscription    -- Current subscription status
POST   /api/v1/billing/checkout        -- Create Stripe Checkout session
POST   /api/v1/billing/portal          -- Create Stripe Customer Portal session
POST   /api/v1/billing/webhooks/stripe -- Stripe webhook handler (no auth)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.billing.service import (
    create_checkout_session,
    create_portal_session,
    get_or_create_free_subscription,
    get_plan_limits,
    get_user_plan,
    handle_webhook_event,
    verify_stripe_signature,
)
from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.schemas.enums import SubscriptionPlan, SubscriptionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    stripe_customer_id: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False
    cohort: str | None = None
    limits: dict[str, int | None] = Field(default_factory=dict)


class CheckoutRequest(BaseModel):
    success_url: str = Field(max_length=2000)
    cancel_url: str = Field(max_length=2000)
    cohort: str | None = Field(default=None, max_length=50)


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalRequest(BaseModel):
    return_url: str = Field(max_length=2000)


class PortalResponse(BaseModel):
    portal_url: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get current subscription status",
)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SubscriptionResponse:
    sub = await get_or_create_free_subscription(db, current_user.id)
    await db.commit()

    plan = sub.plan
    if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
        plan = SubscriptionPlan.FREE

    limits = get_plan_limits().get(plan, get_plan_limits()[SubscriptionPlan.FREE])

    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status,
        stripe_customer_id=sub.stripe_customer_id if not sub.stripe_customer_id.startswith("cus_free_") else None,
        current_period_start=sub.current_period_start.isoformat() if sub.current_period_start else None,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        cancel_at_period_end=sub.cancel_at_period_end,
        cohort=sub.cohort,
        limits=limits,
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create Stripe Checkout session for Pro upgrade",
)
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CheckoutResponse:
    try:
        result = await create_checkout_session(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            cohort=body.cohort,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return CheckoutResponse(
        checkout_url=result["checkout_url"],
        session_id=result["session_id"],
    )


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Create Stripe Customer Portal session",
)
async def create_portal(
    body: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PortalResponse:
    try:
        result = await create_portal_session(
            db=db,
            user_id=current_user.id,
            return_url=body.return_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return PortalResponse(portal_url=result["portal_url"])


@router.post(
    "/webhooks/stripe",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook handler",
    include_in_schema=False,
)
async def stripe_webhook(request: Request) -> Response:
    """Process Stripe webhook events.

    No authentication required - verified via Stripe signature.
    """
    settings = get_settings()
    webhook_secret = settings.stripe_webhook_secret.get_secret_value()

    if not webhook_secret:
        logger.error("Stripe webhook secret not configured")
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        logger.warning("Stripe webhook: missing signature header")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        event = verify_stripe_signature(payload, sig_header, webhook_secret)
    except ValueError as exc:
        logger.warning("Stripe webhook: invalid signature: %s", exc)
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # Process event with a fresh DB session
    from pwbs.db.postgres import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            result = await handle_webhook_event(db, event)
            await db.commit()
            logger.info("Stripe webhook processed: %s -> %s", event.get("type"), result)
        except Exception:
            await db.rollback()
            logger.exception("Stripe webhook processing failed for event: %s", event.get("id"))
            return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Feature-gating dependency for use in other routes
# ---------------------------------------------------------------------------


async def require_paid_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """FastAPI dependency that raises 403 if user is on the free plan."""
    plan = await get_user_plan(db, current_user.id)
    if plan != SubscriptionPlan.PRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_gated",
                "message": "This feature requires a Pro subscription",
                "upgrade_url": "/billing/checkout",
            },
        )
    return current_user