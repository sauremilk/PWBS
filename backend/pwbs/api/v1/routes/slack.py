"""Slack integration API endpoints (TASK-141).

POST /api/v1/integrations/slack/commands  -- Handle Slack slash commands
POST /api/v1/integrations/slack/link      -- Link Slack user to PWBS account
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.integrations.slack.bot import (
    SlackCommandResult,
    dispatch_command,
    link_slack_user,
    verify_slack_signature,
)
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/integrations/slack",
    tags=["slack"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SlackCommandResponse(BaseModel):
    response_type: str
    text: str
    blocks: list[dict] | None = None


class LinkRequest(BaseModel):
    slack_user_id: str
    slack_workspace_id: str


class LinkResponse(BaseModel):
    message: str
    slack_user_id: str
    slack_workspace_id: str


# ---------------------------------------------------------------------------
# POST /commands -- Slack slash command webhook
# ---------------------------------------------------------------------------


@router.post(
    "/commands",
    response_model=SlackCommandResponse,
    summary="Handle Slack slash commands",
)
async def handle_slack_command(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> SlackCommandResponse:
    """Receive and process a Slack slash command.

    Slack sends form-urlencoded POST with fields:
    token, team_id, team_domain, channel_id, channel_name,
    user_id, user_name, command, text, response_url, trigger_id.
    """
    settings = get_settings()
    signing_secret = settings.slack_signing_secret
    if not signing_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SLACK_NOT_CONFIGURED", "message": "Slack integration not configured"},
        )

    # Verify Slack request signature
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not verify_slack_signature(signing_secret, timestamp, body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SIGNATURE", "message": "Invalid Slack request signature"},
        )

    # Parse form data
    form = await request.form()
    slack_user_id = str(form.get("user_id", ""))
    slack_workspace_id = str(form.get("team_id", ""))
    command_text = str(form.get("text", ""))

    if not slack_user_id or not slack_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_FIELDS", "message": "Missing user_id or team_id"},
        )

    result: SlackCommandResult = await dispatch_command(
        command_text=command_text,
        slack_user_id=slack_user_id,
        slack_workspace_id=slack_workspace_id,
        session=session,
    )
    await session.commit()

    return SlackCommandResponse(
        response_type=result.response_type,
        text=result.text,
        blocks=result.blocks,
    )


# ---------------------------------------------------------------------------
# POST /link -- Link Slack user to PWBS account (requires JWT)
# ---------------------------------------------------------------------------


@router.post(
    "/link",
    response_model=LinkResponse,
    summary="Link Slack user to PWBS account",
)
async def link_slack_account(
    body: LinkRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> LinkResponse:
    """Link a Slack user ID to the authenticated PWBS user."""
    await link_slack_user(
        session=session,
        slack_user_id=body.slack_user_id,
        slack_workspace_id=body.slack_workspace_id,
        pwbs_user_id=user.id,
    )
    await session.commit()

    return LinkResponse(
        message="Slack-Account erfolgreich verknuepft",
        slack_user_id=body.slack_user_id,
        slack_workspace_id=body.slack_workspace_id,
    )

