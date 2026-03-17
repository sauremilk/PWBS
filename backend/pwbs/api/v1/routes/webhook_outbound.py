"""Outbound Webhook API endpoints (TASK-189).

POST   /api/v1/webhook-subscriptions          -- Register a new webhook
GET    /api/v1/webhook-subscriptions          -- List own webhooks
GET    /api/v1/webhook-subscriptions/{id}     -- Get webhook details
DELETE /api/v1/webhook-subscriptions/{id}     -- Delete a webhook
PATCH  /api/v1/webhook-subscriptions/{id}     -- Update webhook (url, events, active)
GET    /api/v1/webhook-subscriptions/{id}/deliveries -- Recent deliveries
POST   /api/v1/webhook-subscriptions/{id}/test       -- Send test event
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.models.webhook import Webhook, WebhookDelivery
from pwbs.services.webhook_outbound import (
    SUPPORTED_EVENTS,
    deliver_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/webhook-subscriptions",
    tags=["webhook-subscriptions"],
)

_MAX_WEBHOOKS_PER_USER = 10


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WebhookCreate(BaseModel):
    url: str = Field(..., description="Target URL for webhook delivery")
    events: list[str] = Field(..., min_length=1, description="Event types to subscribe to")
    description: str | None = Field(None, max_length=256)


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = Field(None, min_length=1)
    description: str | None = None
    is_active: bool | None = None


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    events: list[str]
    description: str | None
    is_active: bool
    secret: str
    created_at: datetime
    updated_at: datetime


class WebhookListOut(BaseModel):
    webhooks: list[WebhookOut]
    total: int


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    payload: dict
    status_code: int | None
    response_body: str | None
    success: bool
    attempt: int
    error_message: str | None
    duration_ms: int | None
    created_at: datetime


class DeliveryListOut(BaseModel):
    deliveries: list[DeliveryOut]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_events(events: list[str]) -> None:
    invalid = set(events) - SUPPORTED_EVENTS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_EVENTS",
                "message": f"Unsupported event types: {', '.join(sorted(invalid))}",
                "supported": sorted(SUPPORTED_EVENTS),
            },
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=WebhookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new outbound webhook",
    description=(
        "Registriert einen neuen Outbound-Webhook mit URL, Event-Typen"
        " und HMAC-SHA256-Secret. Max. 10 Webhooks pro Nutzer."
    ),
)
async def create_webhook(
    body: WebhookCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WebhookOut:
    _validate_events(body.events)

    # Enforce per-user limit
    count_stmt = (
        select(func.count())
        .select_from(Webhook)
        .where(
            Webhook.user_id == user.id,
        )
    )
    total = (await db.execute(count_stmt)).scalar_one()
    if total >= _MAX_WEBHOOKS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WEBHOOK_LIMIT",
                "message": f"Maximum {_MAX_WEBHOOKS_PER_USER} webhooks per user",
            },
        )

    webhook = Webhook(
        user_id=user.id,
        url=body.url,
        secret=secrets.token_urlsafe(32),
        events=body.events,
        description=body.description,
        is_active=True,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    response.headers["X-Request-Id"] = response.headers.get("X-Request-Id", "")
    return WebhookOut.model_validate(webhook)


@router.get(
    "",
    response_model=WebhookListOut,
    summary="List own webhook subscriptions",
    description="Returns all webhook subscriptions of the authenticated user.",
)
async def list_webhooks(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WebhookListOut:
    stmt = select(Webhook).where(Webhook.user_id == user.id).order_by(Webhook.created_at.desc())
    result = await db.execute(stmt)
    hooks = list(result.scalars().all())
    return WebhookListOut(
        webhooks=[WebhookOut.model_validate(h) for h in hooks],
        total=len(hooks),
    )


@router.get(
    "/{webhook_id}",
    response_model=WebhookOut,
    summary="Get webhook details",
    description="Returns webhook details (URL, events, status, creation date).",
)
async def get_webhook(
    webhook_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WebhookOut:
    stmt = select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND"})
    return WebhookOut.model_validate(webhook)


@router.patch(
    "/{webhook_id}",
    response_model=WebhookOut,
    summary="Update webhook",
    description="Updates URL, events, description, or activation status of a webhook.",
)
async def update_webhook(
    webhook_id: uuid.UUID,
    body: WebhookUpdate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WebhookOut:
    stmt = select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND"})

    if body.events is not None:
        _validate_events(body.events)
        webhook.events = body.events
    if body.url is not None:
        webhook.url = body.url
    if body.description is not None:
        webhook.description = body.description
    if body.is_active is not None:
        webhook.is_active = body.is_active

    await db.flush()
    await db.refresh(webhook)
    return WebhookOut.model_validate(webhook)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
    description="Permanently deletes a webhook and all associated delivery records.",
)
async def delete_webhook(
    webhook_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    stmt = select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND"})
    await db.delete(webhook)


@router.get(
    "/{webhook_id}/deliveries",
    response_model=DeliveryListOut,
    summary="List recent delivery attempts",
    description=(
        "Returns recent delivery attempts for a webhook including HTTP status and payload."
    ),
)
async def list_deliveries(
    webhook_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 20,
) -> DeliveryListOut:
    # Ownership check
    wh_stmt = select(Webhook.id).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    wh = (await db.execute(wh_stmt)).scalar_one_or_none()
    if wh is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND"})

    count_stmt = (
        select(func.count())
        .select_from(WebhookDelivery)
        .where(
            WebhookDelivery.webhook_id == webhook_id,
        )
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    deliveries = list(result.scalars().all())

    return DeliveryListOut(
        deliveries=[DeliveryOut.model_validate(d) for d in deliveries],
        total=total,
    )


@router.post(
    "/{webhook_id}/test",
    response_model=DeliveryOut,
    summary="Send a test event to the webhook",
    description="Sends a test event to the webhook URL and returns the delivery result.",
)
async def test_webhook(
    webhook_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DeliveryOut:
    stmt = select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    result = await db.execute(stmt)
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND"})

    test_payload = {
        "event": "test.ping",
        "timestamp": datetime.now(UTC).isoformat(),
        "webhook_id": str(webhook.id),
    }

    results = await deliver_webhook(
        url=webhook.url,
        secret=webhook.secret,
        event_type="test.ping",
        payload=test_payload,
        max_attempts=1,
    )

    delivery_result = results[0]
    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type="test.ping",
        payload=test_payload,
        status_code=delivery_result.status_code,
        response_body=delivery_result.response_body,
        success=delivery_result.success,
        attempt=delivery_result.attempt,
        error_message=delivery_result.error_message,
        duration_ms=delivery_result.duration_ms,
    )
    db.add(delivery)
    await db.flush()
    await db.refresh(delivery)

    return DeliveryOut.model_validate(delivery)
