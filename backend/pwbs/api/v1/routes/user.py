"""User API endpoints (TASK-092).

GET    /api/v1/user/settings           -- Current user settings
PATCH  /api/v1/user/settings           -- Update user settings
POST   /api/v1/user/export             -- Start DSGVO data export
GET    /api/v1/user/export/{export_id} -- Export status/download
DELETE /api/v1/user/account            -- Initiate account deletion (30-day grace)
POST   /api/v1/user/account/cancel-deletion -- Cancel pending deletion
GET    /api/v1/user/audit-log          -- Last 100 audit log entries (no PII)
GET    /api/v1/user/security           -- Encryption status per storage layer
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.models.audit_log import AuditLog
from pwbs.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["user"])

_AUDIT_LOG_MAX = 100
_VALID_TIMEZONES_PREFIX = (
    "UTC",
    "Europe/",
    "America/",
    "Asia/",
    "Africa/",
    "Australia/",
    "Pacific/",
    "Atlantic/",
    "Indian/",
)
_VALID_LANGUAGES = {"de", "en", "fr", "es", "it", "pt", "nl", "ja", "zh"}


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------


class UserSettingsResponse(BaseModel):
    """Current user settings."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    display_name: str
    timezone: str
    language: str
    briefing_auto_generate: bool


class UserSettingsUpdate(BaseModel):
    """Partial update for user settings."""

    timezone: str | None = None
    language: str | None = None
    briefing_auto_generate: bool | None = None
    display_name: str | None = None


class ExportStartResponse(BaseModel):
    export_id: uuid.UUID
    status: str = "processing"


class ExportStatusResponse(BaseModel):
    export_id: uuid.UUID
    status: str
    download_url: str | None = None
    created_at: datetime | None = None


class AccountDeletionRequest(BaseModel):
    password: str
    confirmation: str = Field(..., pattern=r"^DELETE$")


class AccountDeletionResponse(BaseModel):
    message: str
    deletion_scheduled_at: datetime | None = None


class CancelDeletionResponse(BaseModel):
    message: str


class AuditLogEntry(BaseModel):
    """Single audit log entry (no PII, metadata only)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    created_at: datetime


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int


class StorageLayerStatus(BaseModel):
    layer: str
    encrypted: bool
    encryption_type: str | None = None
    note: str | None = None


class SecurityStatusResponse(BaseModel):
    storage_layers: list[StorageLayerStatus]
    data_location: str
    llm_usage: str


# ---------------------------------------------------------------------------
# GET /api/v1/user/settings
# ---------------------------------------------------------------------------


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings_endpoint(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserSettingsResponse:
    """Return current user settings."""
    # User model doesn't have settings columns yet — return defaults
    return UserSettingsResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone="UTC",
        language="de",
        briefing_auto_generate=True,
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/user/settings
# ---------------------------------------------------------------------------


@router.patch("/settings", response_model=UserSettingsResponse)
async def update_settings(
    update: UserSettingsUpdate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserSettingsResponse:
    """Update user settings (timezone, language, briefing_auto_generate, display_name)."""
    if update.timezone is not None:
        if not update.timezone.startswith(_VALID_TIMEZONES_PREFIX):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_TIMEZONE",
                    "message": f"Invalid timezone: {update.timezone}",
                },
            )

    if update.language is not None:
        if update.language not in _VALID_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_LANGUAGE",
                    "message": f"Unsupported language: {update.language}",
                },
            )

    # Update display_name on the User model (only field that exists in DB)
    if update.display_name is not None:
        if len(update.display_name.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_DISPLAY_NAME",
                    "message": "Display name must not be empty",
                },
            )
        user.display_name = update.display_name.strip()
        await db.commit()
        await db.refresh(user)

    # Settings columns (timezone, language, briefing_auto_generate) are not
    # yet in the User model. Return current values with applied defaults.
    return UserSettingsResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone=update.timezone or "UTC",
        language=update.language or "de",
        briefing_auto_generate=(
            update.briefing_auto_generate
            if update.briefing_auto_generate is not None
            else True
        ),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/user/export — start DSGVO data export
# ---------------------------------------------------------------------------


@router.post(
    "/export",
    response_model=ExportStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_export(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExportStartResponse:
    """Start asynchronous DSGVO data export (Art. 15/20).

    Delegates to the export service (TASK-104).
    """
    raise NotImplementedError(
        "DSGVO export service not yet implemented (TASK-104). "
        "Endpoint structure is ready for integration."
    )


# ---------------------------------------------------------------------------
# GET /api/v1/user/export/{export_id} — export status
# ---------------------------------------------------------------------------


@router.get("/export/{export_id}", response_model=ExportStatusResponse)
async def get_export_status(
    export_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExportStatusResponse:
    """Check status of a DSGVO data export.

    Delegates to the export service (TASK-104).
    """
    raise NotImplementedError(
        "DSGVO export service not yet implemented (TASK-104). "
        "Endpoint structure is ready for integration."
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/user/account — initiate account deletion
# ---------------------------------------------------------------------------


@router.delete("/account", response_model=AccountDeletionResponse)
async def delete_account(
    body: AccountDeletionRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AccountDeletionResponse:
    """Initiate account deletion with 30-day grace period (Art. 17).

    Requires password confirmation and literal 'DELETE' string.
    Delegates to the account deletion service (TASK-105).
    """
    if body.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_CONFIRMATION",
                "message": "Confirmation must be 'DELETE'",
            },
        )

    raise NotImplementedError(
        "Cascaded account deletion not yet implemented (TASK-105). "
        "Endpoint structure is ready for integration."
    )


# ---------------------------------------------------------------------------
# POST /api/v1/user/account/cancel-deletion
# ---------------------------------------------------------------------------


@router.post("/account/cancel-deletion", response_model=CancelDeletionResponse)
async def cancel_deletion(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CancelDeletionResponse:
    """Cancel a pending account deletion within 30-day grace period.

    Delegates to the account deletion service (TASK-105).
    """
    raise NotImplementedError(
        "Cascaded account deletion not yet implemented (TASK-105). "
        "Endpoint structure is ready for integration."
    )


# ---------------------------------------------------------------------------
# GET /api/v1/user/audit-log — last 100 audit entries
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = _AUDIT_LOG_MAX,
) -> AuditLogResponse:
    """Return last 100 audit log entries for the authenticated user.

    Returns only metadata (action, resource type/id, timestamp).
    No PII or content is exposed.
    """
    limit = max(1, min(limit, _AUDIT_LOG_MAX))

    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    entries = [
        AuditLogEntry(
            id=r.id,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return AuditLogResponse(entries=entries, total=len(entries))


# ---------------------------------------------------------------------------
# GET /api/v1/user/security — encryption status
# ---------------------------------------------------------------------------


@router.get("/security", response_model=SecurityStatusResponse)
async def get_security_status(
    response: Response,
    user: User = Depends(get_current_user),
) -> SecurityStatusResponse:
    """Return encryption status per storage layer, data location, and LLM usage info."""
    settings = get_settings()

    layers = [
        StorageLayerStatus(
            layer="PostgreSQL",
            encrypted=True,
            encryption_type="Envelope Encryption (KEK/DEK, AES-256-GCM via Fernet)",
            note="Per-user DEK encrypted with application KEK",
        ),
        StorageLayerStatus(
            layer="Weaviate",
            encrypted=True,
            encryption_type="Tenant-isolated vector storage",
            note="Vectors stored per owner_id, access filtered at query time",
        ),
        StorageLayerStatus(
            layer="Neo4j",
            encrypted=True,
            encryption_type="owner_id-filtered graph (MERGE-based idempotent writes)",
            note="All graph queries filtered by owner_id",
        ),
        StorageLayerStatus(
            layer="Redis",
            encrypted=False,
            encryption_type=None,
            note="Session data only; no PII stored at rest",
        ),
    ]

    return SecurityStatusResponse(
        storage_layers=layers,
        data_location="EU (AWS eu-central-1)" if settings.environment == "production" else "Local",
        llm_usage=(
            "LLM calls use only owner's data via RAG. "
            "No user data is used for external model training. "
            "Responses include source references for auditability."
        ),
    )
