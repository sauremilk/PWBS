"""Pydantic v2 schemas for connector / connection management (TASK-035)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from pwbs.schemas.enums import ConnectionStatus, SourceType


class Connection(BaseModel):
    """A user's data-source connection."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID
    user_id: UUID
    source_type: SourceType
    status: ConnectionStatus
    watermark: datetime | None = None
    config: dict[str, Any] = {}
    created_at: datetime
