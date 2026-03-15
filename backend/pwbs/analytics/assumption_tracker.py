"""Assumption tracker service (TASK-155).

CRUD operations for assumptions / hypotheses with lifecycle management.
Supports timeline queries for the quarterly review briefing.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.core.exceptions import NotFoundError, ValidationError
from pwbs.models.assumption import Assumption

logger = logging.getLogger(__name__)

__all__ = ["AssumptionTrackerService"]

_VALID_STATUSES = {"open", "confirmed", "refuted", "revised"}
_TERMINAL_STATUSES = {"confirmed", "refuted"}


class AssumptionTrackerService:
    """Manages assumption lifecycle: create, update status, query timelines.

    All queries are scoped to ``owner_id`` (DSGVO tenant isolation).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        owner_id: uuid.UUID,
        title: str,
        description: str | None = None,
        source_decision_id: uuid.UUID | None = None,
        source_document_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> Assumption:
        """Create a new assumption in 'open' status."""
        assumption = Assumption(
            id=uuid.uuid4(),
            user_id=owner_id,
            title=title,
            description=description,
            status="open",
            evidence=[],
            source_decision_id=source_decision_id,
            source_document_id=source_document_id,
            expires_at=expires_at,
        )
        self._db.add(assumption)
        await self._db.flush()
        await self._db.refresh(assumption)
        return assumption

    async def get(self, assumption_id: uuid.UUID, owner_id: uuid.UUID) -> Assumption:
        """Get a single assumption by ID, scoped to owner."""
        stmt = select(Assumption).where(
            Assumption.id == assumption_id,
            Assumption.user_id == owner_id,
        )
        result = await self._db.execute(stmt)
        assumption = result.scalar_one_or_none()
        if assumption is None:
            raise NotFoundError(
                f"Assumption {assumption_id} not found",
                code="ASSUMPTION_NOT_FOUND",
            )
        return assumption

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Assumption]:
        """List assumptions for an owner, optionally filtered by status."""
        stmt = (
            select(Assumption)
            .where(Assumption.user_id == owner_id)
            .order_by(Assumption.created_at.desc())
            .limit(min(limit, 100))
            .offset(offset)
        )
        if status is not None:
            if status not in _VALID_STATUSES:
                raise ValidationError(
                    f"Invalid status filter: {status}. "
                    f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
                    code="INVALID_STATUS_FILTER",
                )
            stmt = stmt.where(Assumption.status == status)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        assumption_id: uuid.UUID,
        owner_id: uuid.UUID,
        new_status: str,
        reason: str | None = None,
    ) -> Assumption:
        """Transition assumption to a new status with optional reason."""
        if new_status not in _VALID_STATUSES:
            raise ValidationError(
                f"Invalid status: {new_status}. "
                f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
                code="INVALID_STATUS",
            )
        assumption = await self.get(assumption_id, owner_id)
        if assumption.status in _TERMINAL_STATUSES:
            raise ValidationError(
                f"Cannot change status from '{assumption.status}' (terminal state)",
                code="STATUS_TERMINAL",
            )
        now = datetime.now(timezone.utc)
        assumption.status = new_status
        assumption.status_changed_at = now
        assumption.status_reason = reason
        await self._db.flush()
        await self._db.refresh(assumption)
        return assumption

    async def add_evidence(
        self,
        assumption_id: uuid.UUID,
        owner_id: uuid.UUID,
        note: str,
        source_id: uuid.UUID | None = None,
    ) -> Assumption:
        """Append an evidence entry to the assumption's evidence trail."""
        assumption = await self.get(assumption_id, owner_id)
        entry: dict[str, Any] = {
            "date": datetime.now(timezone.utc).isoformat(),
            "note": note,
        }
        if source_id is not None:
            entry["source_id"] = str(source_id)
        # Create new list to trigger SQLAlchemy change detection
        updated_evidence = list(assumption.evidence) + [entry]
        assumption.evidence = updated_evidence
        await self._db.flush()
        await self._db.refresh(assumption)
        return assumption

    async def get_timeline(
        self,
        owner_id: uuid.UUID,
        months: int = 3,
    ) -> dict[str, Any]:
        """Get assumption statistics for quarterly review.

        Returns counts by status and recently changed assumptions.
        """
        cutoff = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        # Go back N months (approximate)
        for _ in range(months):
            prev = cutoff.replace(day=1) - __import__("datetime").timedelta(days=1)
            cutoff = prev.replace(day=1)

        all_stmt = select(Assumption).where(
            Assumption.user_id == owner_id,
        )
        result = await self._db.execute(all_stmt)
        all_assumptions = list(result.scalars().all())

        status_counts: dict[str, int] = {}
        recently_changed: list[dict[str, Any]] = []

        for a in all_assumptions:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
            if a.status_changed_at and a.status_changed_at >= cutoff:
                recently_changed.append(
                    {
                        "id": str(a.id),
                        "title": a.title,
                        "status": a.status,
                        "changed_at": a.status_changed_at.isoformat(),
                        "reason": a.status_reason,
                    }
                )

        return {
            "total": len(all_assumptions),
            "status_counts": status_counts,
            "recently_changed": sorted(
                recently_changed,
                key=lambda x: x["changed_at"],
                reverse=True,
            ),
            "period_months": months,
        }
