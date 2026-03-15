"""Connectors API endpoints (TASK-087, TASK-173).

GET    /api/v1/connectors/              -- List available connector types
GET    /api/v1/connectors/status        -- Status of all connected sources
GET    /api/v1/connectors/{type}/auth-url  -- Generate OAuth2 auth URL
POST   /api/v1/connectors/{type}/callback  -- OAuth2 callback
POST   /api/v1/connectors/{type}/config    -- Configure connector (e.g. Obsidian vault)
DELETE /api/v1/connectors/{type}           -- Disconnect + cascade delete
POST   /api/v1/connectors/{type}/sync      -- Trigger manual sync
GET    /api/v1/connectors/{type}/consent   -- Get consent status
POST   /api/v1/connectors/{type}/consent   -- Grant consent
DELETE /api/v1/connectors/{type}/consent   -- Revoke consent + cascade delete
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.audit.audit_service import AuditAction, get_client_ip, log_event
from pwbs.connectors.oauth import OAuthTokens, encrypt_tokens
from pwbs.connectors.registry import list_registered_types
from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.models.connection import Connection
from pwbs.models.connector_consent import ConnectorConsent
from pwbs.models.document import Document
from pwbs.models.sync_run import SyncRun
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import ConnectionStatus, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/connectors",
    tags=["connectors"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ---------------------------------------------------------------------------
# Connector metadata (static registry of known types)
# ---------------------------------------------------------------------------

_CONNECTOR_META: dict[str, dict[str, str]] = {
    SourceType.GOOGLE_CALENDAR.value: {
        "name": "Google Calendar",
        "description": "Events und Termine aus Google Calendar",
        "auth_method": "oauth2",
    },
    SourceType.NOTION.value: {
        "name": "Notion",
        "description": "Seiten und Datenbanken aus Notion",
        "auth_method": "oauth2",
    },
    SourceType.OBSIDIAN.value: {
        "name": "Obsidian",
        "description": "Markdown-Dateien aus einem Obsidian-Vault",
        "auth_method": "local_path",
    },
    SourceType.ZOOM.value: {
        "name": "Zoom",
        "description": "Meeting-Transkripte und Aufzeichnungen aus Zoom",
        "auth_method": "oauth2",
    },
    SourceType.GMAIL.value: {
        "name": "Gmail",
        "description": "E-Mails und Threads aus Gmail",
        "auth_method": "oauth2",
    },
    SourceType.GOOGLE_DOCS.value: {
        "name": "Google Docs",
        "description": "Dokumente aus Google Docs",
        "auth_method": "oauth2",
    },
    SourceType.SLACK.value: {
        "name": "Slack",
        "description": "Nachrichten und Threads aus Slack-Channels",
        "auth_method": "oauth2",
    },
    SourceType.OUTLOOK_MAIL.value: {
        "name": "Outlook Mail",
        "description": "E-Mails und Threads aus Microsoft Outlook",
        "auth_method": "oauth2",
    },
}

# OAuth2 authorization URLs per provider
_AUTH_URLS: dict[SourceType, str] = {
    SourceType.GOOGLE_CALENDAR: "https://accounts.google.com/o/oauth2/v2/auth",
    SourceType.GMAIL: "https://accounts.google.com/o/oauth2/v2/auth",
    SourceType.GOOGLE_DOCS: "https://accounts.google.com/o/oauth2/v2/auth",
    SourceType.NOTION: "https://api.notion.com/v1/oauth/authorize",
    SourceType.ZOOM: "https://zoom.us/oauth/authorize",
    SourceType.SLACK: "https://slack.com/oauth/v2/authorize",
    SourceType.OUTLOOK_MAIL: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
}

_SCOPES: dict[SourceType, str] = {
    SourceType.GOOGLE_CALENDAR: "https://www.googleapis.com/auth/calendar.readonly",
    SourceType.GMAIL: "https://www.googleapis.com/auth/gmail.readonly",
    SourceType.GOOGLE_DOCS: "https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/documents.readonly",
    SourceType.NOTION: "",
    SourceType.ZOOM: "recording:read",
    SourceType.SLACK: "channels:history,channels:read,users:read",
    SourceType.OUTLOOK_MAIL: "https://graph.microsoft.com/Mail.Read offline_access",
}


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ConnectorTypeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: str
    name: str
    description: str
    auth_method: str
    status: str | None = None


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorTypeResponse]


class ConnectionStatusItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: str
    status: str
    doc_count: int
    last_sync: datetime | None = None
    error: str | None = None


class ConnectionStatusResponse(BaseModel):
    connections: list[ConnectionStatusItem]


class AuthUrlResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    auth_url: str
    state: str


class CallbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    code: str
    state: str


class CallbackResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    connection_id: uuid.UUID
    status: str
    initial_sync_started: bool


class ConfigRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    vault_path: str = Field(min_length=1, max_length=1024)


class ConfigResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    connection_id: uuid.UUID
    status: str
    file_count: int


class DisconnectResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    message: str
    deleted_doc_count: int


class SyncResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    sync_id: uuid.UUID
    status: str = "started"


class ConsentGrantRequest(BaseModel):
    """Body for granting consent to a connector."""

    model_config = ConfigDict(str_strip_whitespace=True)
    consent_version: int = 1


class ConsentStatusResponse(BaseModel):
    """Current consent status for a connector type."""

    model_config = ConfigDict(frozen=True)
    connector_type: str
    consented: bool
    consent_version: int | None = None
    consented_at: datetime | None = None
    data_types: list[str] = []
    processing_purpose: str = ""
    llm_providers: list[str] = []


class ConsentRevokeResponse(BaseModel):
    """Response after revoking consent."""

    model_config = ConfigDict(frozen=True)
    message: str
    deleted_doc_count: int


# ---------------------------------------------------------------------------
# Consent metadata: what each connector ingests and how data is processed
# ---------------------------------------------------------------------------

_CONSENT_INFO: dict[str, dict[str, list[str] | str]] = {
    SourceType.GOOGLE_CALENDAR.value: {
        "data_types": ["Kalendereinträge", "Teilnehmerlisten", "Besprechungsnotizen"],
        "processing_purpose": "Automatische Erstellung von Meeting-Briefings und Terminübersichten",
        "llm_providers": ["Claude API (Anthropic)", "GPT-4 (OpenAI, Fallback)"],
    },
    SourceType.NOTION.value: {
        "data_types": ["Notion-Seiten", "Datenbanken", "Kommentare"],
        "processing_purpose": "Semantische Suche und Wissensvernetzung über Notion-Inhalte",
        "llm_providers": ["Claude API (Anthropic)", "GPT-4 (OpenAI, Fallback)"],
    },
    SourceType.OBSIDIAN.value: {
        "data_types": ["Markdown-Dateien", "Vault-Struktur", "Tags und Links"],
        "processing_purpose": "Integration lokaler Notizen in die Wissenssuche und Briefings",
        "llm_providers": ["Claude API (Anthropic)", "GPT-4 (OpenAI, Fallback)"],
    },
    SourceType.ZOOM.value: {
        "data_types": ["Meeting-Transkripte", "Aufnahme-Metadaten", "Teilnehmerlisten"],
        "processing_purpose": "Automatische Zusammenfassung und Entscheidungsextraktion aus Meetings",
        "llm_providers": ["Claude API (Anthropic)", "GPT-4 (OpenAI, Fallback)"],
    },
}


def _resolve_source_type(type_str: str) -> SourceType:
    """Parse a URL path segment into a SourceType enum.

    Accepts both the enum value (``google_calendar``) and a
    hyphenated variant (``google-calendar``).
    """
    normalised = type_str.lower().replace("-", "_")
    try:
        return SourceType(normalised)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "UNKNOWN_CONNECTOR_TYPE",
                "message": f"Connector type '{type_str}' is not supported",
            },
        )


# ---------------------------------------------------------------------------
# GET /connectors/
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=ConnectorListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available connector types",
)
async def list_connectors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConnectorListResponse:
    # Which types does this user already have connected?
    stmt = select(Connection.source_type).where(Connection.user_id == current_user.id)
    result = await db.execute(stmt)
    connected_types = {row[0] for row in result.all()}

    items: list[ConnectorTypeResponse] = []
    for st in SourceType:
        meta = _CONNECTOR_META.get(st.value, {})
        user_status = "connected" if st.value in connected_types else "available"
        items.append(
            ConnectorTypeResponse(
                type=st.value,
                name=meta.get("name", st.value),
                description=meta.get("description", ""),
                auth_method=meta.get("auth_method", "unknown"),
                status=user_status,
            )
        )

    return ConnectorListResponse(connectors=items)


# ---------------------------------------------------------------------------
# GET /connectors/status
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=ConnectionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Status of all connected sources",
)
async def connection_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConnectionStatusResponse:
    # Fetch all connections for this user with doc counts
    conn_stmt = select(Connection).where(Connection.user_id == current_user.id)
    conn_result = await db.execute(conn_stmt)
    connections = conn_result.scalars().all()

    items: list[ConnectionStatusItem] = []
    for conn in connections:
        # Count documents per connection source_type
        doc_count_stmt = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.user_id == current_user.id,
                Document.source_type == conn.source_type,
            )
        )
        doc_count_result = await db.execute(doc_count_stmt)
        doc_count = doc_count_result.scalar() or 0

        items.append(
            ConnectionStatusItem(
                type=conn.source_type,
                status=conn.status,
                doc_count=doc_count,
                last_sync=conn.watermark,
                error=conn.config.get("last_error") if isinstance(conn.config, dict) else None,
            )
        )

    return ConnectionStatusResponse(connections=items)


# ---------------------------------------------------------------------------
# GET /connectors/{type}/auth-url
# ---------------------------------------------------------------------------


@router.get(
    "/{type}/auth-url",
    response_model=AuthUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate OAuth2 authorization URL",
)
async def get_auth_url(
    type: str,
    current_user: User = Depends(get_current_user),
) -> AuthUrlResponse:
    source_type = _resolve_source_type(type)

    if source_type not in _AUTH_URLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_OAUTH_SUPPORT",
                "message": f"Connector '{source_type.value}' does not use OAuth2",
            },
        )

    settings = get_settings()

    # Build redirect URI from settings
    redirect_uri_map: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: settings.google_oauth_redirect_uri,
        SourceType.GMAIL: settings.gmail_oauth_redirect_uri,
        SourceType.NOTION: settings.notion_oauth_redirect_uri,
        SourceType.ZOOM: getattr(settings, "zoom_oauth_redirect_uri", ""),
        SourceType.SLACK: settings.slack_oauth_redirect_uri,
        SourceType.OUTLOOK_MAIL: settings.ms_oauth_redirect_uri,
    }
    redirect_uri = redirect_uri_map.get(source_type, "")

    # Get client_id
    client_id_map: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: settings.google_client_id,
        SourceType.GMAIL: settings.google_client_id,
        SourceType.NOTION: settings.notion_client_id,
        SourceType.ZOOM: settings.zoom_client_id,
        SourceType.SLACK: settings.slack_client_id,
        SourceType.OUTLOOK_MAIL: settings.ms_client_id,
    }
    client_id = client_id_map.get(source_type, "")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_CLIENT_ID",
                "message": f"OAuth2 client_id not configured for {source_type.value}",
            },
        )

    state = secrets.token_urlsafe(32)
    scope = _SCOPES.get(source_type, "")

    base_url = _AUTH_URLS[source_type]
    params = (
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
        f"&access_type=offline"
    )

    return AuthUrlResponse(auth_url=base_url + params, state=state)


# ---------------------------------------------------------------------------
# POST /connectors/{type}/callback
# ---------------------------------------------------------------------------


@router.post(
    "/{type}/callback",
    response_model=CallbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process OAuth2 callback",
)
async def oauth_callback(
    type: str,
    body: CallbackRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CallbackResponse:
    source_type = _resolve_source_type(type)

    if source_type not in _AUTH_URLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_OAUTH_SUPPORT",
                "message": f"Connector '{source_type.value}' does not use OAuth2",
            },
        )

    # Check for existing connection (UNIQUE constraint)
    existing_stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.source_type == source_type.value,
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONNECTION_EXISTS",
                "message": f"Connection for {source_type.value} already exists",
            },
        )

    # Exchange auth code for tokens via provider endpoint
    settings = get_settings()
    tokens = await _exchange_code_for_tokens(source_type, body.code, settings)

    # Encrypt and persist
    encrypted = encrypt_tokens(tokens, owner_id=current_user.id)

    connection = Connection(
        id=uuid.uuid4(),
        user_id=current_user.id,
        source_type=source_type.value,
        status=ConnectionStatus.ACTIVE.value,
        credentials_enc=encrypted,
        config={},
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    await log_event(
        db,
        action=AuditAction.CONNECTION_CREATED,
        user_id=current_user.id,
        resource_type="connection",
        resource_id=connection.id,
        ip_address=get_client_ip(request),
        metadata={"source_type": source_type.value},
    )
    await db.commit()

    logger.info(
        "OAuth callback processed: user_id=%s source_type=%s connection_id=%s",
        current_user.id,
        source_type.value,
        connection.id,
    )

    return CallbackResponse(
        connection_id=connection.id,
        status=ConnectionStatus.ACTIVE.value,
        initial_sync_started=False,
    )


async def _exchange_code_for_tokens(
    source_type: SourceType,
    code: str,
    settings: Any,
) -> OAuthTokens:
    """Exchange an OAuth2 authorization code for tokens.

    Makes an HTTP POST to the provider's token endpoint.
    """
    import time

    import httpx
    from pydantic import SecretStr

    token_endpoints: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: "https://oauth2.googleapis.com/token",
        SourceType.GMAIL: "https://oauth2.googleapis.com/token",
        SourceType.NOTION: "https://api.notion.com/v1/oauth/token",
        SourceType.ZOOM: "https://zoom.us/oauth/token",
        SourceType.SLACK: "https://slack.com/api/oauth.v2.access",
        SourceType.OUTLOOK_MAIL: "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    }

    endpoint = token_endpoints.get(source_type)
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_TOKEN_ENDPOINT",
                "message": f"No token endpoint for {source_type.value}",
            },
        )

    redirect_uri_map: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: settings.google_oauth_redirect_uri,
        SourceType.GMAIL: settings.gmail_oauth_redirect_uri,
        SourceType.NOTION: settings.notion_oauth_redirect_uri,
        SourceType.ZOOM: getattr(settings, "zoom_oauth_redirect_uri", ""),
        SourceType.SLACK: settings.slack_oauth_redirect_uri,
        SourceType.OUTLOOK_MAIL: settings.ms_oauth_redirect_uri,
    }

    client_id_map: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: settings.google_client_id,
        SourceType.GMAIL: settings.google_client_id,
        SourceType.NOTION: settings.notion_client_id,
        SourceType.ZOOM: settings.zoom_client_id,
        SourceType.SLACK: settings.slack_client_id,
        SourceType.OUTLOOK_MAIL: settings.ms_client_id,
    }
    client_secret_map: dict[SourceType, SecretStr] = {
        SourceType.GOOGLE_CALENDAR: settings.google_client_secret,
        SourceType.GMAIL: settings.google_client_secret,
        SourceType.NOTION: settings.notion_client_secret,
        SourceType.ZOOM: settings.zoom_client_secret,
        SourceType.SLACK: settings.slack_client_secret,
        SourceType.OUTLOOK_MAIL: settings.ms_client_secret,
    }

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri_map.get(source_type, ""),
        "client_id": client_id_map.get(source_type, ""),
        "client_secret": client_secret_map.get(source_type, SecretStr("")).get_secret_value(),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, data=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Token exchange HTTP error: source_type=%s status=%d",
            source_type.value,
            exc.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOKEN_EXCHANGE_FAILED",
                "message": "Failed to exchange authorization code for tokens",
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOKEN_EXCHANGE_NETWORK_ERROR",
                "message": "Network error during token exchange",
            },
        ) from exc

    expires_in = data.get("expires_in")
    expires_at = time.time() + expires_in if expires_in else None

    return OAuthTokens(
        access_token=SecretStr(data["access_token"]),
        refresh_token=SecretStr(data.get("refresh_token", "")),
        token_type=data.get("token_type", "Bearer"),
        expires_at=expires_at,
        scope=data.get("scope"),
    )


# ---------------------------------------------------------------------------
# POST /connectors/{type}/config
# ---------------------------------------------------------------------------


@router.post(
    "/{type}/config",
    response_model=ConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure connector (e.g. Obsidian vault path)",
)
async def configure_connector(
    type: str,
    body: ConfigRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConfigResponse:
    source_type = _resolve_source_type(type)

    if source_type != SourceType.OBSIDIAN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CONFIG_NOT_SUPPORTED",
                "message": f"Connector '{source_type.value}' does not support path configuration",
            },
        )

    # Check for existing connection
    existing_stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.source_type == source_type.value,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONNECTION_EXISTS",
                "message": f"Connection for {source_type.value} already exists",
            },
        )

    # Obsidian doesn't use OAuth; credentials_enc stores a placeholder
    connection = Connection(
        id=uuid.uuid4(),
        user_id=current_user.id,
        source_type=source_type.value,
        status=ConnectionStatus.ACTIVE.value,
        credentials_enc="local",
        config={"vault_path": body.vault_path},
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    await log_event(
        db,
        action=AuditAction.CONNECTION_CREATED,
        user_id=current_user.id,
        resource_type="connection",
        resource_id=connection.id,
        ip_address=get_client_ip(request),
        metadata={"source_type": source_type.value},
    )
    await db.commit()

    logger.info(
        "Obsidian connector configured: user_id=%s connection_id=%s vault_path=%s",
        current_user.id,
        connection.id,
        body.vault_path,
    )

    return ConfigResponse(
        connection_id=connection.id,
        status=ConnectionStatus.ACTIVE.value,
        file_count=0,
    )


# ---------------------------------------------------------------------------
# DELETE /connectors/{type}
# ---------------------------------------------------------------------------


@router.delete(
    "/{type}",
    response_model=DisconnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Disconnect source and cascade-delete data",
)
async def disconnect(
    type: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DisconnectResponse:
    source_type = _resolve_source_type(type)

    # Find connection (owner_id filter!)
    stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.source_type == source_type.value,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONNECTION_NOT_FOUND",
                "message": f"No connection found for {source_type.value}",
            },
        )

    # Count documents before deletion
    doc_count_stmt = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.user_id == current_user.id,
            Document.source_type == source_type.value,
        )
    )
    doc_count_result = await db.execute(doc_count_stmt)
    deleted_doc_count = doc_count_result.scalar() or 0

    # Save connection id before deletion for audit
    connection_id = connection.id

    # Cascade delete: documents (chunks cascade via FK)
    await db.execute(
        delete(Document).where(
            Document.user_id == current_user.id,
            Document.source_type == source_type.value,
        )
    )

    # Delete the connection itself
    await db.delete(connection)
    await db.commit()

    await log_event(
        db,
        action=AuditAction.CONNECTION_DELETED,
        user_id=current_user.id,
        resource_type="connection",
        resource_id=connection_id,
        ip_address=get_client_ip(request),
        metadata={"source_type": source_type.value, "deleted_doc_count": deleted_doc_count},
    )
    await db.commit()

    logger.info(
        "Connector disconnected: user_id=%s source_type=%s deleted_docs=%d",
        current_user.id,
        source_type.value,
        deleted_doc_count,
    )

    return DisconnectResponse(
        message=f"Disconnected {source_type.value}",
        deleted_doc_count=deleted_doc_count,
    )


# ---------------------------------------------------------------------------
# POST /connectors/{type}/sync
# ---------------------------------------------------------------------------


@router.post(
    "/{type}/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual sync",
)
async def trigger_sync(
    type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncResponse:
    source_type = _resolve_source_type(type)

    # Find connection (owner_id filter!)
    stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.source_type == source_type.value,
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONNECTION_NOT_FOUND",
                "message": f"No connection found for {source_type.value}",
            },
        )

    if connection.status != ConnectionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CONNECTION_NOT_ACTIVE",
                "message": f"Connection is in '{connection.status}' state, cannot sync",
            },
        )

    # Rate-limit check: max 1 sync per 5 minutes per connector
    if connection.watermark is not None:
        now = datetime.now(timezone.utc)
        elapsed = (now - connection.watermark.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < 300:
            remaining = int(300 - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "SYNC_RATE_LIMITED",
                    "message": f"Sync rate limit: wait {remaining}s before next sync",
                },
                headers={"Retry-After": str(remaining)},
            )

    # Dispatch connector sync to Celery worker queue
    from pwbs.queue.tasks.ingestion import run_connector

    sync_id = uuid.uuid4()
    run_connector.delay(str(connection.id), str(current_user.id))

    logger.info(
        "Manual sync dispatched to queue: user_id=%s source_type=%s sync_id=%s",
        current_user.id,
        source_type.value,
        sync_id,
    )

    return SyncResponse(sync_id=sync_id, status="started")


# ---------------------------------------------------------------------------
# GET /connectors/{type}/consent
# ---------------------------------------------------------------------------


@router.get(
    "/{type}/consent",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get consent status for a connector type",
)
async def get_consent(
    type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConsentStatusResponse:
    source_type = _resolve_source_type(type)

    stmt = select(ConnectorConsent).where(
        ConnectorConsent.owner_id == current_user.id,
        ConnectorConsent.connector_type == source_type.value,
        ConnectorConsent.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    consent = result.scalar_one_or_none()

    info = _CONSENT_INFO.get(source_type.value, {})

    if consent is None:
        return ConsentStatusResponse(
            connector_type=source_type.value,
            consented=False,
            data_types=info.get("data_types", []),  # type: ignore[arg-type]
            processing_purpose=info.get("processing_purpose", ""),  # type: ignore[arg-type]
            llm_providers=info.get("llm_providers", []),  # type: ignore[arg-type]
        )

    return ConsentStatusResponse(
        connector_type=source_type.value,
        consented=True,
        consent_version=consent.consent_version,
        consented_at=consent.consented_at,
        data_types=info.get("data_types", []),  # type: ignore[arg-type]
        processing_purpose=info.get("processing_purpose", ""),  # type: ignore[arg-type]
        llm_providers=info.get("llm_providers", []),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# POST /connectors/{type}/consent
# ---------------------------------------------------------------------------


@router.post(
    "/{type}/consent",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant consent for a connector type",
)
async def grant_consent(
    type: str,
    body: ConsentGrantRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConsentStatusResponse:
    source_type = _resolve_source_type(type)

    # Check for existing active consent
    stmt = select(ConnectorConsent).where(
        ConnectorConsent.owner_id == current_user.id,
        ConnectorConsent.connector_type == source_type.value,
        ConnectorConsent.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONSENT_ALREADY_GRANTED",
                "message": f"Active consent already exists for {source_type.value}",
            },
        )

    consent = ConnectorConsent(
        owner_id=current_user.id,
        connector_type=source_type.value,
        consent_version=body.consent_version,
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)

    await log_event(
        db,
        action=AuditAction.CONSENT_GRANTED,
        user_id=current_user.id,
        resource_type="connector_consent",
        resource_id=consent.id,
        ip_address=get_client_ip(request),
        metadata={
            "connector_type": source_type.value,
            "consent_version": body.consent_version,
        },
    )
    await db.commit()

    info = _CONSENT_INFO.get(source_type.value, {})
    return ConsentStatusResponse(
        connector_type=source_type.value,
        consented=True,
        consent_version=consent.consent_version,
        consented_at=consent.consented_at,
        data_types=info.get("data_types", []),  # type: ignore[arg-type]
        processing_purpose=info.get("processing_purpose", ""),  # type: ignore[arg-type]
        llm_providers=info.get("llm_providers", []),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# DELETE /connectors/{type}/consent
# ---------------------------------------------------------------------------


@router.delete(
    "/{type}/consent",
    response_model=ConsentRevokeResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke consent and cascade-delete all data for this source",
)
async def revoke_consent(
    type: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConsentRevokeResponse:
    source_type = _resolve_source_type(type)

    # Find active consent
    stmt = select(ConnectorConsent).where(
        ConnectorConsent.owner_id == current_user.id,
        ConnectorConsent.connector_type == source_type.value,
        ConnectorConsent.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    consent = result.scalar_one_or_none()

    if consent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONSENT_NOT_FOUND",
                "message": f"No active consent found for {source_type.value}",
            },
        )

    # Mark consent as revoked
    consent.revoked_at = datetime.now(timezone.utc)

    # Count documents before deletion
    doc_count_stmt = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.user_id == current_user.id,
            Document.source_type == source_type.value,
        )
    )
    doc_count_result = await db.execute(doc_count_stmt)
    deleted_doc_count = doc_count_result.scalar() or 0

    # Cascade delete: documents (chunks cascade via FK)
    await db.execute(
        delete(Document).where(
            Document.user_id == current_user.id,
            Document.source_type == source_type.value,
        )
    )

    # Delete the connection if it exists
    conn_stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.source_type == source_type.value,
    )
    conn_result = await db.execute(conn_stmt)
    connection = conn_result.scalar_one_or_none()
    connection_id = connection.id if connection else None
    if connection is not None:
        await db.delete(connection)

    await db.commit()

    await log_event(
        db,
        action=AuditAction.CONSENT_REVOKED,
        user_id=current_user.id,
        resource_type="connector_consent",
        resource_id=consent.id,
        ip_address=get_client_ip(request),
        metadata={
            "connector_type": source_type.value,
            "deleted_doc_count": deleted_doc_count,
            "connection_deleted": connection_id is not None,
        },
    )
    await db.commit()

    logger.info(
        "Consent revoked: user_id=%s connector_type=%s deleted_docs=%d",
        current_user.id,
        source_type.value,
        deleted_doc_count,
    )

    return ConsentRevokeResponse(
        message=f"Consent revoked for {source_type.value}. All data deleted.",
        deleted_doc_count=deleted_doc_count,
    )


# ---------------------------------------------------------------------------
# Sync history schemas + endpoint (TASK-184)
# ---------------------------------------------------------------------------


class SyncRunItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    document_count: int = 0
    error_count: int = 0
    errors_json: list[dict[str, Any]] | None = None
    duration_seconds: float | None = None


class SyncHistoryResponse(BaseModel):
    runs: list[SyncRunItem]
    total: int
    has_more: bool


@router.get(
    "/{type}/history",
    response_model=SyncHistoryResponse,
    summary="Sync history for a connector",
)
async def get_sync_history(
    type: str,
    offset: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncHistoryResponse:
    """Return paginated sync history for a connector type."""
    source_type = _resolve_source_type(type)

    # Verify the user owns a connection of this type
    conn_stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.source_type == source_type.value,
    )
    conn_result = await db.execute(conn_stmt)
    connection = conn_result.scalar_one_or_none()

    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CONNECTION_NOT_FOUND",
                "message": f"No connection found for {source_type.value}",
            },
        )

    limit = max(1, min(limit, 50))

    # Count
    count_stmt = select(func.count()).where(
        SyncRun.connection_id == connection.id
    )
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginated runs
    runs_stmt = (
        select(SyncRun)
        .where(SyncRun.connection_id == connection.id)
        .order_by(SyncRun.started_at.desc().nulls_last())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(runs_stmt)
    runs = list(result.scalars().all())

    items: list[SyncRunItem] = []
    for run in runs:
        duration: float | None = None
        if run.started_at and run.completed_at:
            duration = (
                run.completed_at - run.started_at
            ).total_seconds()
        items.append(
            SyncRunItem(
                id=run.id,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                document_count=run.document_count,
                error_count=run.error_count,
                errors_json=run.errors_json,
                duration_seconds=duration,
            )
        )

    return SyncHistoryResponse(
        runs=items,
        total=total,
        has_more=(offset + limit) < total,
    )
