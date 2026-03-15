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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.audit.audit_service import AuditAction, get_client_ip, log_event
from pwbs.core.config import get_settings
from pwbs.db.postgres import get_db_session
from pwbs.dsgvo import deletion_service, export_service
from pwbs.models.audit_log import AuditLog
from pwbs.models.connection import Connection
from pwbs.models.document import Document
from pwbs.models.llm_audit_log import LlmAuditLog
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.schemas.enums import VerticalProfile

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/user", tags=["user"], responses={**AUTH_RESPONSES, **COMMON_RESPONSES}
)

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
    reminder_frequency: str  # "daily" | "weekly" | "off"
    email_briefing_enabled: bool
    briefing_email_time: str  # HH:MM format
    vertical_profile: str


class UserSettingsUpdate(BaseModel):
    """Partial update for user settings."""

    timezone: str | None = None
    language: str | None = None
    briefing_auto_generate: bool | None = None
    display_name: str | None = None
    reminder_frequency: str | None = None
    email_briefing_enabled: bool | None = None
    briefing_email_time: str | None = None  # HH:MM format
    vertical_profile: str | None = None


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


class BriefingPreferencesUpdate(BaseModel):
    """Update briefing personalisation preferences (TASK-186)."""

    focus_projects: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Prioritised project names to highlight in briefings",
    )
    excluded_sources: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Source types to exclude from briefing context",
    )
    priority_topics: list[str] | None = Field(
        default=None,
        max_length=30,
        description="Topics to prioritise in the briefing",
    )


class BriefingPreferencesResponse(BaseModel):
    """Current briefing preferences."""

    focus_projects: list[str]
    excluded_sources: list[str]
    priority_topics: list[str]


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
    return UserSettingsResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone=user.timezone,
        language=user.language,
        briefing_auto_generate=user.briefing_auto_generate,
        reminder_frequency=user.reminder_frequency,
        email_briefing_enabled=user.email_briefing_enabled,
        briefing_email_time=user.briefing_email_time.strftime("%H:%M"),
        vertical_profile=user.vertical_profile,
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
        user.timezone = update.timezone

    if update.language is not None:
        if update.language not in _VALID_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_LANGUAGE",
                    "message": f"Unsupported language: {update.language}",
                },
            )
        user.language = update.language

    if update.reminder_frequency is not None:
        if update.reminder_frequency not in ("daily", "weekly", "off"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_REMINDER_FREQUENCY",
                    "message": f"Invalid reminder frequency: {update.reminder_frequency}. Must be daily, weekly, or off.",
                },
            )
        user.reminder_frequency = update.reminder_frequency

    if update.briefing_auto_generate is not None:
        user.briefing_auto_generate = update.briefing_auto_generate

    # Validate and update vertical_profile (TASK-154)
    if update.vertical_profile is not None:
        try:
            VerticalProfile(update.vertical_profile)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_VERTICAL_PROFILE",
                    "message": (
                        f"Invalid vertical profile: {update.vertical_profile}. "
                        f"Must be one of: {', '.join(v.value for v in VerticalProfile)}"
                    ),
                },
            )
        user.vertical_profile = update.vertical_profile

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

    # Update email briefing settings
    if update.email_briefing_enabled is not None:
        user.email_briefing_enabled = update.email_briefing_enabled

    if update.briefing_email_time is not None:
        try:
            parts = update.briefing_email_time.split(":")
            from datetime import time as _time

            user.briefing_email_time = _time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INVALID_TIME_FORMAT",
                    "message": "briefing_email_time must be HH:MM format",
                },
            )

    await db.commit()
    await db.refresh(user)

    # Settings columns are now persisted in the User model.
    return UserSettingsResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone=user.timezone,
        language=user.language,
        briefing_auto_generate=user.briefing_auto_generate,
        reminder_frequency=user.reminder_frequency,
        email_briefing_enabled=user.email_briefing_enabled,
        briefing_email_time=user.briefing_email_time.strftime("%H:%M"),
        vertical_profile=user.vertical_profile,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/user/briefing-preferences
# ---------------------------------------------------------------------------


@router.get("/briefing-preferences", response_model=BriefingPreferencesResponse)
async def get_briefing_preferences(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BriefingPreferencesResponse:
    """Return current briefing personalisation preferences."""
    prefs = user.briefing_preferences or {}
    return BriefingPreferencesResponse(
        focus_projects=prefs.get("focus_projects", []),
        excluded_sources=prefs.get("excluded_sources", []),
        priority_topics=prefs.get("priority_topics", []),
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/user/briefing-preferences
# ---------------------------------------------------------------------------


@router.patch("/briefing-preferences", response_model=BriefingPreferencesResponse)
async def update_briefing_preferences(
    update: BriefingPreferencesUpdate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BriefingPreferencesResponse:
    """Update briefing personalisation preferences (TASK-186).

    Accepts focus_projects, excluded_sources, priority_topics.
    Merges with existing preferences (only provided fields are overwritten).
    Default: no filters — all data is considered for briefing generation.
    """
    current = dict(user.briefing_preferences or {})

    if update.focus_projects is not None:
        current["focus_projects"] = [p.strip() for p in update.focus_projects if p.strip()]

    if update.excluded_sources is not None:
        current["excluded_sources"] = [s.strip() for s in update.excluded_sources if s.strip()]

    if update.priority_topics is not None:
        current["priority_topics"] = [t.strip() for t in update.priority_topics if t.strip()]

    user.briefing_preferences = current
    await db.commit()
    await db.refresh(user)

    prefs = user.briefing_preferences or {}
    return BriefingPreferencesResponse(
        focus_projects=prefs.get("focus_projects", []),
        excluded_sources=prefs.get("excluded_sources", []),
        priority_topics=prefs.get("priority_topics", []),
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
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExportStartResponse:
    """Start asynchronous DSGVO data export (Art. 15/20).

    Rate limit: 1 concurrent export per user (429 if already running).
    """
    running = await export_service.check_running_export(user.id, db)
    if running is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "EXPORT_ALREADY_RUNNING",
                "message": "An export is already in progress",
                "export_id": str(running.id),
            },
        )

    export = await export_service.create_export_job(user.id, db)

    await log_event(
        db,
        action=AuditAction.DATA_EXPORTED,
        user_id=user.id,
        resource_type="data_export",
        resource_id=export.id,
        ip_address=get_client_ip(request),
    )
    await db.commit()

    settings = get_settings()
    background_tasks.add_task(
        export_service.run_export,
        export_id=export.id,
        user_id=user.id,
        database_url=settings.database_url,
        export_dir=settings.export_dir,
    )
    return ExportStartResponse(export_id=export.id, status="processing")


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

    Returns download URL once completed; 404 if export not found or expired.
    """
    export = await export_service.get_export(export_id, user.id, db)
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPORT_NOT_FOUND", "message": "Export not found"},
        )

    if export.status == "completed" and export_service.is_export_expired(export):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "EXPORT_EXPIRED", "message": "Export has expired"},
        )

    download_url: str | None = None
    if export.status == "completed" and export.file_path:
        download_url = f"/api/v1/user/export/{export_id}/download"

    return ExportStatusResponse(
        export_id=export.id,
        status=export.status,
        download_url=download_url,
        created_at=export.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/user/export/{export_id}/download — download export ZIP
# ---------------------------------------------------------------------------


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Download a completed DSGVO data export as ZIP."""
    from pathlib import Path as _Path

    export = await export_service.get_export(export_id, user.id, db)
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPORT_NOT_FOUND", "message": "Export not found"},
        )

    if export.status != "completed" or not export.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPORT_NOT_READY", "message": "Export not yet completed"},
        )

    if export_service.is_export_expired(export):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "EXPORT_EXPIRED", "message": "Export has expired"},
        )

    file_path = _Path(export.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPORT_FILE_MISSING", "message": "Export file not found on disk"},
        )

    data = file_path.read_bytes()
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="pwbs-export-{export_id}.zip"'},
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/user/account — initiate account deletion
# ---------------------------------------------------------------------------


@router.delete("/account", response_model=AccountDeletionResponse)
async def delete_account(
    body: AccountDeletionRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AccountDeletionResponse:
    """Initiate account deletion with 30-day grace period (Art. 17).

    Requires password confirmation and literal 'DELETE' string.
    """
    if body.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_CONFIRMATION",
                "message": "Confirmation must be 'DELETE'",
            },
        )

    try:
        deletion_at = await deletion_service.schedule_deletion(
            db,
            user,
            body.password,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "Invalid password":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_PASSWORD",
                    "message": "Passwort ist falsch",
                },
            )
        # Already scheduled
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DELETION_ALREADY_SCHEDULED",
                "message": "Account deletion already scheduled",
            },
        )

    ip = get_client_ip(request)
    await log_event(
        db,
        action=AuditAction.USER_DELETED,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip,
        metadata={"deletion_scheduled_at": deletion_at.isoformat()},
    )
    await db.commit()
    return AccountDeletionResponse(
        message="Account deletion scheduled",
        deletion_scheduled_at=deletion_at,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/user/account/cancel-deletion
# ---------------------------------------------------------------------------


@router.post("/account/cancel-deletion", response_model=CancelDeletionResponse)
async def cancel_deletion(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CancelDeletionResponse:
    """Cancel a pending account deletion within 30-day grace period."""
    try:
        await deletion_service.cancel_deletion(db, user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "NO_DELETION_SCHEDULED",
                "message": "No account deletion is currently scheduled",
            },
        )

    ip = get_client_ip(request)
    await log_event(
        db,
        action=AuditAction.USER_DELETED,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip,
        metadata={"action": "deletion_cancelled"},
    )
    await db.commit()
    return CancelDeletionResponse(message="Account deletion cancelled")


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


# ---------------------------------------------------------------------------
# Data-report / LLM-usage schemas
# ---------------------------------------------------------------------------


class SourceStats(BaseModel):
    source_type: str
    document_count: int
    oldest_document: datetime | None = None
    newest_document: datetime | None = None


class ConnectionInfo(BaseModel):
    source_type: str
    status: str
    last_sync: datetime | None = None


class LlmProviderUsage(BaseModel):
    provider: str
    model: str
    total_input_tokens: int
    total_output_tokens: int
    call_count: int


class DataReportResponse(BaseModel):
    total_documents: int
    sources: list[SourceStats]
    connections: list[ConnectionInfo]
    llm_provider_usage: list[LlmProviderUsage]


class LlmUsageEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    purpose: str
    created_at: datetime


class LlmUsageResponse(BaseModel):
    entries: list[LlmUsageEntry]
    total: int


# ---------------------------------------------------------------------------
# GET /api/v1/user/data-report — DSGVO transparency report
# ---------------------------------------------------------------------------

_DATA_REPORT_LIMIT = 100


@router.get("/data-report", response_model=DataReportResponse)
async def get_data_report(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DataReportResponse:
    """DSGVO transparency report: document counts per source, connections, LLM usage."""
    # Document stats per source_type
    doc_stmt = (
        select(
            Document.source_type,
            sa_func.count(Document.id).label("doc_count"),
            sa_func.min(Document.created_at).label("oldest"),
            sa_func.max(Document.created_at).label("newest"),
        )
        .where(Document.user_id == user.id)
        .group_by(Document.source_type)
    )
    doc_result = await db.execute(doc_stmt)
    doc_rows = doc_result.all()

    sources = [
        SourceStats(
            source_type=row.source_type,
            document_count=row.doc_count,
            oldest_document=row.oldest,
            newest_document=row.newest,
        )
        for row in doc_rows
    ]
    total_documents = sum(s.document_count for s in sources)

    # Connection info (last sync = watermark)
    conn_stmt = select(Connection).where(Connection.user_id == user.id)
    conn_result = await db.execute(conn_stmt)
    conn_rows = conn_result.scalars().all()

    connections = [
        ConnectionInfo(
            source_type=c.source_type,
            status=c.status,
            last_sync=c.watermark,
        )
        for c in conn_rows
    ]

    # LLM provider usage aggregation
    llm_stmt = (
        select(
            LlmAuditLog.provider,
            LlmAuditLog.model,
            sa_func.sum(LlmAuditLog.input_tokens).label("total_in"),
            sa_func.sum(LlmAuditLog.output_tokens).label("total_out"),
            sa_func.count(LlmAuditLog.id).label("call_count"),
        )
        .where(LlmAuditLog.owner_id == user.id)
        .group_by(LlmAuditLog.provider, LlmAuditLog.model)
    )
    llm_result = await db.execute(llm_stmt)
    llm_rows = llm_result.all()

    llm_usage = [
        LlmProviderUsage(
            provider=row.provider,
            model=row.model,
            total_input_tokens=row.total_in or 0,
            total_output_tokens=row.total_out or 0,
            call_count=row.call_count,
        )
        for row in llm_rows
    ]

    return DataReportResponse(
        total_documents=total_documents,
        sources=sources,
        connections=connections,
        llm_provider_usage=llm_usage,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/user/llm-usage — LLM audit log entries
# ---------------------------------------------------------------------------

_LLM_USAGE_MAX = 200


@router.get("/llm-usage", response_model=LlmUsageResponse)
async def get_llm_usage(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
) -> LlmUsageResponse:
    """Return LLM audit log entries for the authenticated user.

    Each entry records provider, model, token counts, and purpose.
    """
    limit = max(1, min(limit, _LLM_USAGE_MAX))
    offset = max(0, offset)

    count_stmt = select(sa_func.count(LlmAuditLog.id)).where(LlmAuditLog.owner_id == user.id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(LlmAuditLog)
        .where(LlmAuditLog.owner_id == user.id)
        .order_by(desc(LlmAuditLog.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    entries = [
        LlmUsageEntry(
            id=r.id,
            provider=r.provider,
            model=r.model,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            purpose=r.purpose,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return LlmUsageResponse(entries=entries, total=total)
