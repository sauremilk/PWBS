"""Gmail Pub/Sub webhook endpoint (TASK-123).

Receives push notifications from Google Pub/Sub when new emails arrive.
Decodes the Pub/Sub message, looks up the Gmail connection for the
affected email address, and dispatches an ingestion Celery task.

Security: Google Pub/Sub push endpoints are unauthenticated  the endpoint
validates the message structure and checks that a matching Gmail connection
exists. No user secrets are exposed in the notification payload.
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