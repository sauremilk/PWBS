"""Connectors API endpoints (TASK-087).

GET    /api/v1/connectors/              -- List available connector types
GET    /api/v1/connectors/status        -- Status of all connected sources
GET    /api/v1/connectors/{type}/auth-url  -- Generate OAuth2 auth URL
POST   /api/v1/connectors/{type}/callback  -- OAuth2 callback
POST   /api/v1/connectors/{type}/config    -- Configure connector (e.g. Obsidian vault)
DELETE /api/v1/connectors/{type}           -- Disconnect + cascade delete
POST   /api/v1/connectors/{type}/sync      -- Trigger manual sync
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
from pwbs.models.document import Document
from pwbs.models.user import User
from pwbs.schemas.enums import ConnectionStatus, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


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
}

# OAuth2 authorization URLs per provider
_AUTH_URLS: dict[SourceType, str] = {
    SourceType.GOOGLE_CALENDAR: "https://accounts.google.com/o/oauth2/v2/auth",
    SourceType.NOTION: "https://api.notion.com/v1/oauth/authorize",
    SourceType.ZOOM: "https://zoom.us/oauth/authorize",
}

_SCOPES: dict[SourceType, str] = {
    SourceType.GOOGLE_CALENDAR: "https://www.googleapis.com/auth/calendar.readonly",
    SourceType.NOTION: "",
    SourceType.ZOOM: "recording:read",
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


# ---------------------------------------------------------------------------
# Helper: resolve and validate source_type path param
# ---------------------------------------------------------------------------


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
        SourceType.NOTION: settings.notion_oauth_redirect_uri,
        SourceType.ZOOM: getattr(settings, "zoom_oauth_redirect_uri", ""),
    }
    redirect_uri = redirect_uri_map.get(source_type, "")

    # Get client_id
    client_id_map: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: settings.google_client_id,
        SourceType.NOTION: settings.notion_client_id,
        SourceType.ZOOM: settings.zoom_client_id,
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
        SourceType.NOTION: "https://api.notion.com/v1/oauth/token",
        SourceType.ZOOM: "https://zoom.us/oauth/token",
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
        SourceType.NOTION: settings.notion_oauth_redirect_uri,
        SourceType.ZOOM: getattr(settings, "zoom_oauth_redirect_uri", ""),
    }

    client_id_map: dict[SourceType, str] = {
        SourceType.GOOGLE_CALENDAR: settings.google_client_id,
        SourceType.NOTION: settings.notion_client_id,
        SourceType.ZOOM: settings.zoom_client_id,
    }
    client_secret_map: dict[SourceType, SecretStr] = {
        SourceType.GOOGLE_CALENDAR: settings.google_client_secret,
        SourceType.NOTION: settings.notion_client_secret,
        SourceType.ZOOM: settings.zoom_client_secret,
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
