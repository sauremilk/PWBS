"""Webhook endpoints for Gmail Pub/Sub and Slack Events API.

Gmail (TASK-123):
Receives push notifications from Google Pub/Sub when new emails arrive.

Slack (TASK-125):
Receives Slack Events API callbacks (url_verification + message events).
Validates signatures via HMAC-SHA256 signing secret.
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select

from pwbs.db.postgres import get_session_factory
from pwbs.models.connection import Connection
from pwbs.schemas.enums import ConnectionStatus, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post(
    "/gmail/pubsub",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Google Pub/Sub push notification for Gmail",
    responses={
        204: {"description": "Notification accepted"},
        400: {"description": "Malformed payload"},
    },
)
async def gmail_pubsub_webhook(request: Request) -> Response:
    """Handle a Google Pub/Sub push notification for Gmail.

    Pub/Sub message ``data`` is a base64-encoded JSON object::

        {"emailAddress": "user@example.com", "historyId": 12345}

    The endpoint looks up the active Gmail connection for that email
    address and enqueues an ingestion task.
    """
    try:
        body = await request.json()
    except Exception:
        logger.warning("Gmail Pub/Sub webhook: invalid JSON body")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    message = body.get("message")
    if not isinstance(message, dict):
        logger.warning("Gmail Pub/Sub webhook: missing 'message' field")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    raw_data = message.get("data")
    if not raw_data or not isinstance(raw_data, str):
        logger.warning("Gmail Pub/Sub webhook: missing 'data' in message")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        decoded = json.loads(base64.b64decode(raw_data))
    except Exception:
        logger.warning("Gmail Pub/Sub webhook: failed to decode message data")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    email_address = decoded.get("emailAddress")
    history_id = decoded.get("historyId")

    if not email_address or not isinstance(email_address, str):
        logger.warning("Gmail Pub/Sub webhook: missing emailAddress")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    logger.info(
        "Gmail Pub/Sub notification: email=%s historyId=%s",
        email_address,
        history_id,
    )

    # Look up the active Gmail connection for this email address.
    # The email is stored in connection.config["gmail_email"].
    factory = get_session_factory()
    async with factory() as db:
        stmt = (
            select(Connection)
            .where(
                Connection.source_type == SourceType.GMAIL.value,
                Connection.status == ConnectionStatus.ACTIVE.value,
            )
        )
        result = await db.execute(stmt)
        connections = result.scalars().all()

        matched_connection: Connection | None = None
        for conn in connections:
            config = conn.config or {}
            if config.get("gmail_email", "").lower() == email_address.lower():
                matched_connection = conn
                break

        if matched_connection is None:
            logger.info(
                "Gmail Pub/Sub: no active connection for %s  ignoring",
                email_address,
            )
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # Dispatch ingestion task via Celery
        try:
            from pwbs.queue.tasks.ingestion import run_connector_sync

            run_connector_sync.delay(
                str(matched_connection.id),
                str(matched_connection.user_id),
            )
            logger.info(
                "Gmail Pub/Sub: dispatched ingestion for connection=%s user=%s",
                matched_connection.id,
                matched_connection.user_id,
            )
        except Exception:
            logger.exception(
                "Gmail Pub/Sub: failed to dispatch ingestion task for connection=%s",
                matched_connection.id,
            )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Slack Events API webhook (TASK-125)
# ---------------------------------------------------------------------------


@router.post(
    "/slack/events",
    summary="Slack Events API webhook",
    responses={
        200: {"description": "URL verification or event accepted"},
        400: {"description": "Malformed payload or invalid signature"},
        403: {"description": "Invalid signature"},
    },
)
async def slack_events_webhook(request: Request) -> Response:
    """Handle Slack Events API callbacks.

    Two types of requests:
    1. **URL verification**: Slack sends a ``challenge`` to verify our endpoint.
       We echo it back in the response.
    2. **Event callbacks**: message events trigger ingestion for the channel.

    Security: All requests are validated via HMAC-SHA256 signature using
    the ``slack_signing_secret`` from settings.
    """
    from pwbs.connectors.slack import validate_event_signature
    from pwbs.core.config import get_settings

    settings = get_settings()
    signing_secret = settings.slack_signing_secret

    # Read raw body for signature verification
    body = await request.body()

    # Validate signature (skip if no signing secret configured - dev mode)
    if signing_secret:
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not timestamp or not signature:
            logger.warning("Slack webhook: missing signature headers")
            return Response(status_code=status.HTTP_403_FORBIDDEN)

        if not validate_event_signature(
            signing_secret=signing_secret,
            timestamp=timestamp,
            body=body,
            signature=signature,
        ):
            logger.warning("Slack webhook: invalid signature")
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    # Parse JSON body
    try:
        payload = json.loads(body)
    except Exception:
        logger.warning("Slack webhook: invalid JSON body")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # URL verification challenge
    event_type = payload.get("type")
    if event_type == "url_verification":
        challenge = payload.get("challenge", "")
        return Response(
            content=json.dumps({"challenge": challenge}),
            media_type="application/json",
            status_code=status.HTTP_200_OK,
        )

    # Event callback
    if event_type != "event_callback":
        logger.info("Slack webhook: ignoring type=%s", event_type)
        return Response(status_code=status.HTTP_200_OK)

    event = payload.get("event", {})
    if not isinstance(event, dict):
        return Response(status_code=status.HTTP_200_OK)

    event_subtype = event.get("type")
    channel_id = event.get("channel")

    # Only process message events
    if event_subtype != "message" or not channel_id:
        return Response(status_code=status.HTTP_200_OK)

    # Skip bot messages and message subtypes (edits, deletes, etc.)
    if event.get("subtype") and event.get("subtype") != "thread_broadcast":
        return Response(status_code=status.HTTP_200_OK)

    team_id = payload.get("team_id", "")
    logger.info(
        "Slack event: message in channel=%s team=%s",
        channel_id,
        team_id,
    )

    # Look up active Slack connection that includes this channel
    factory = get_session_factory()
    async with factory() as db:
        stmt = select(Connection).where(
            Connection.source_type == SourceType.SLACK.value,
            Connection.status == ConnectionStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        connections = result.scalars().all()

        for conn in connections:
            config = conn.config or {}
            channels = config.get("channels", [])
            if not isinstance(channels, list):
                continue
            if channel_id in channels:
                try:
                    from pwbs.queue.tasks.ingestion import run_connector_sync

                    run_connector_sync.delay(
                        str(conn.id),
                        str(conn.user_id),
                    )
                    logger.info(
                        "Slack webhook: dispatched ingestion for connection=%s channel=%s",
                        conn.id,
                        channel_id,
                    )
                except Exception:
                    logger.exception(
                        "Slack webhook: failed to dispatch ingestion for connection=%s",
                        conn.id,
                    )
                break

    return Response(status_code=status.HTTP_200_OK)
