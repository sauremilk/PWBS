"""Multi-modal ingestion API endpoints (TASK-159).

POST   /api/v1/multimodal/upload        -- Upload image/audio for processing
GET    /api/v1/multimodal/jobs/{job_id}  -- Poll job status
"""

from __future__ import annotations

import logging
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field

from pwbs.api.dependencies.auth import get_current_user
from pwbs.models.user import User
from pwbs.processing.multimodal.models import MIME_TO_MEDIA_TYPE, MediaType
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/multimodal",
    tags=["multimodal"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)

# In-memory job store (replaced by Redis/DB in production)
_jobs: dict[str, dict[str, object]] = {}

ALLOWED_CONTENT_TYPES = frozenset(m.value for m in MediaType)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Response after successful file upload."""

    job_id: str = Field(..., description="Job ID for polling status")
    file_name: str
    media_type: str
    status: str = "pending"


class JobStatusResponse(BaseModel):
    """Job status for polling."""

    job_id: str
    status: str
    file_name: str | None = None
    document_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an image or audio file for processing",
)
async def upload_multimodal_file(
    file: UploadFile,
    response: Response,
    user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload an image (JPEG/PNG/PDF) or audio file (MP3/WAV/M4A/WebM).

    The file is saved to a temporary location and dispatched to the
    processing queue. Use the returned job_id to poll for status.
    """
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": f"Content type '{content_type}' is not supported. "
                f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
            },
        )

    file_name = file.filename or "unnamed"

    # Read file content with size limit
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)} MB",
            },
        )

    # Determine file extension from media type
    media_type = MIME_TO_MEDIA_TYPE[content_type]
    ext_map: dict[MediaType, str] = {
        MediaType.JPEG: ".jpg",
        MediaType.PNG: ".png",
        MediaType.PDF: ".pdf",
        MediaType.MP3: ".mp3",
        MediaType.WAV: ".wav",
        MediaType.M4A: ".m4a",
        MediaType.WEBM: ".webm",
    }
    suffix = ext_map.get(media_type, "")

    # Save to temp file (persists until Celery task processes it)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="pwbs_mm_")
    tmp.write(content)
    tmp.close()

    job_id = str(uuid.uuid4())

    _jobs[job_id] = {
        "status": "pending",
        "file_name": file_name,
    }

    # Dispatch to Celery queue
    from pwbs.queue.tasks.multimodal import process_multimodal_file

    process_multimodal_file.delay(  # type: ignore[attr-defined]
        file_path=tmp.name,
        mime_type=content_type,
        owner_id=str(user.id),
        file_name=file_name,
        job_id=job_id,
    )

    logger.info(
        "Multimodal upload queued: job=%s file=%s type=%s user=%s",
        job_id,
        file_name,
        content_type,
        user.id,
    )

    return UploadResponse(
        job_id=job_id,
        file_name=file_name,
        media_type=content_type,
        status="pending",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get processing job status",
)
async def get_job_status(
    job_id: str,
    response: Response,
    user: User = Depends(get_current_user),
) -> JobStatusResponse:
    """Poll for the status of a multi-modal processing job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found"},
        )

    return JobStatusResponse(
        job_id=job_id,
        status=str(job.get("status", "unknown")),
        file_name=str(job.get("file_name")) if job.get("file_name") else None,
        document_id=str(job["document_id"]) if job.get("document_id") else None,
        error=str(job["error"]) if job.get("error") else None,
    )
