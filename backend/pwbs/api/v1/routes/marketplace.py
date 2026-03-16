"""Marketplace API routes (TASK-151).

Endpoints for browsing, publishing, installing, and configuring
community plugins.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.marketplace import marketplace_service
from pwbs.models.user import User

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PluginSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    version: str
    name: str
    description: str
    plugin_type: str
    is_verified: bool
    install_count: int
    icon_url: str | None = None
    published_at: datetime | None = None


class PluginDetail(PluginSummary):
    manifest: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    entry_point: str
    repository_url: str | None = None
    rating_sum: int = 0
    rating_count: int = 0
    status: str
    created_at: datetime
    updated_at: datetime


class PluginListResponse(BaseModel):
    plugins: list[PluginSummary]
    total: int
    offset: int
    limit: int


class PublishPluginRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    version: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    plugin_type: str
    entry_point: str = Field(..., min_length=3)
    manifest: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    icon_url: str | None = None
    repository_url: str | None = None


class InstallPluginRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class UpdateConfigRequest(BaseModel):
    config: dict[str, Any]


class TogglePluginRequest(BaseModel):
    enabled: bool


class InstalledPluginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plugin_id: uuid.UUID
    config: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool
    installed_at: datetime
    plugin: PluginSummary


class ReviewPluginRequest(BaseModel):
    status: str
    notes: str | None = None


# ---------------------------------------------------------------------------
# Browse endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/plugins",
    response_model=PluginListResponse,
    summary="Browse marketplace plugins",
)
async def list_plugins(
    plugin_type: str | None = Query(None, description="Filter by plugin type"),
    search: str | None = Query(None, description="Search in name and description"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> PluginListResponse:
    plugins, total = await marketplace_service.list_plugins(
        db,
        plugin_type=plugin_type,
        search_query=search,
        offset=offset,
        limit=limit,
    )
    return PluginListResponse(
        plugins=[PluginSummary.model_validate(p) for p in plugins],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/plugins/{plugin_id}",
    response_model=PluginDetail,
    summary="Get plugin details",
)
async def get_plugin(
    plugin_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> PluginDetail:
    plugin = await marketplace_service.get_plugin_detail(db, plugin_id=plugin_id)
    return PluginDetail.model_validate(plugin)


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


@router.post(
    "/plugins",
    response_model=PluginDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a new plugin (submit for review)",
)
async def publish_plugin(
    body: PublishPluginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PluginDetail:
    plugin = await marketplace_service.publish_plugin(
        db,
        author_id=current_user.id,
        slug=body.slug,
        version=body.version,
        name=body.name,
        description=body.description,
        plugin_type=body.plugin_type,
        entry_point=body.entry_point,
        manifest=body.manifest,
        permissions=body.permissions,
        icon_url=body.icon_url,
        repository_url=body.repository_url,
    )
    await db.commit()
    return PluginDetail.model_validate(plugin)


# ---------------------------------------------------------------------------
# Install / Uninstall / Configure
# ---------------------------------------------------------------------------


@router.post(
    "/plugins/{plugin_id}/install",
    response_model=InstalledPluginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install a plugin",
)
async def install_plugin(
    plugin_id: uuid.UUID,
    body: InstallPluginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> InstalledPluginResponse:
    installation = await marketplace_service.install_plugin(
        db, user_id=current_user.id, plugin_id=plugin_id, config=body.config,
    )
    await db.commit()
    return InstalledPluginResponse.model_validate(installation)


@router.delete(
    "/plugins/{plugin_id}/uninstall",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Uninstall a plugin",
)
async def uninstall_plugin(
    plugin_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    await marketplace_service.uninstall_plugin(
        db, user_id=current_user.id, plugin_id=plugin_id,
    )
    await db.commit()


@router.put(
    "/plugins/{plugin_id}/config",
    response_model=InstalledPluginResponse,
    summary="Update plugin configuration",
)
async def update_config(
    plugin_id: uuid.UUID,
    body: UpdateConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> InstalledPluginResponse:
    installation = await marketplace_service.update_plugin_config(
        db, user_id=current_user.id, plugin_id=plugin_id, config=body.config,
    )
    await db.commit()
    return InstalledPluginResponse.model_validate(installation)


@router.patch(
    "/plugins/{plugin_id}/toggle",
    response_model=InstalledPluginResponse,
    summary="Enable or disable an installed plugin",
)
async def toggle_plugin(
    plugin_id: uuid.UUID,
    body: TogglePluginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> InstalledPluginResponse:
    installation = await marketplace_service.toggle_plugin(
        db, user_id=current_user.id, plugin_id=plugin_id, enabled=body.enabled,
    )
    await db.commit()
    return InstalledPluginResponse.model_validate(installation)


@router.get(
    "/installed",
    response_model=list[InstalledPluginResponse],
    summary="List my installed plugins",
)
async def list_installed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[InstalledPluginResponse]:
    installations = await marketplace_service.list_installed_plugins(
        db, user_id=current_user.id,
    )
    return [InstalledPluginResponse.model_validate(i) for i in installations]


# ---------------------------------------------------------------------------
# Review (admin-only in future, for now any authenticated user)
# ---------------------------------------------------------------------------


@router.patch(
    "/plugins/{plugin_id}/review",
    response_model=PluginDetail,
    summary="Review a plugin (approve/reject)",
)
async def review_plugin(
    plugin_id: uuid.UUID,
    body: ReviewPluginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PluginDetail:
    plugin = await marketplace_service.review_plugin(
        db,
        plugin_id=plugin_id,
        new_status=body.status,
        reviewer_notes=body.notes,
    )
    await db.commit()
    return PluginDetail.model_validate(plugin)