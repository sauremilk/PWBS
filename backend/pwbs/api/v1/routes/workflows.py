"""Workflow automation API endpoints (TASK-160).

POST   /api/v1/workflows            -- Create workflow rule
GET    /api/v1/workflows            -- List user's workflow rules
GET    /api/v1/workflows/{id}       -- Get single rule
PATCH  /api/v1/workflows/{id}       -- Update rule
DELETE /api/v1/workflows/{id}       -- Delete rule
GET    /api/v1/workflows/{id}/log   -- Execution log for a rule
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.api.dependencies.auth import get_current_user
from pwbs.db.postgres import get_db_session
from pwbs.models.user import User
from pwbs.schemas.common import AUTH_RESPONSES, COMMON_RESPONSES
from pwbs.workflows.models import WorkflowExecution, WorkflowRule
from pwbs.workflows.schemas import (
    WorkflowExecutionListResponse,
    WorkflowExecutionResponse,
    WorkflowRuleCreate,
    WorkflowRuleListResponse,
    WorkflowRuleResponse,
    WorkflowRuleUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["workflows"],
    responses={**AUTH_RESPONSES, **COMMON_RESPONSES},
)


# ── Helpers ────────────────────────────────────────────────────


def _check_rule_ownership(rule: WorkflowRule, user_id: uuid.UUID) -> None:
    """Raise 403 if the rule does not belong to the user."""
    if rule.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Rule does not belong to this user"},
        )


async def _get_rule_or_404(rule_id: uuid.UUID, db: AsyncSession) -> WorkflowRule:
    """Fetch a rule by ID or raise 404."""
    stmt = select(WorkflowRule).where(WorkflowRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Workflow rule {rule_id} not found"},
        )
    return rule


def _rule_to_response(rule: WorkflowRule) -> WorkflowRuleResponse:
    return WorkflowRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_config=rule.trigger_config,
        action_config=rule.action_config,
        is_active=rule.is_active,
        execution_count=rule.execution_count,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────


@router.post(
    "/",
    response_model=WorkflowRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow rule",
)
async def create_workflow_rule(
    body: WorkflowRuleCreate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowRuleResponse:
    """Create a new workflow automation rule for the authenticated user."""
    rule = WorkflowRule(
        user_id=user.id,
        name=body.name,
        description=body.description,
        trigger_config=body.trigger_config.model_dump(),
        action_config=body.action_config.model_dump(),
        is_active=body.is_active,
    )
    db.add(rule)
    await db.flush()
    await db.commit()
    await db.refresh(rule)

    return _rule_to_response(rule)


@router.get(
    "/",
    response_model=WorkflowRuleListResponse,
    summary="List workflow rules",
)
async def list_workflow_rules(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
) -> WorkflowRuleListResponse:
    """List all workflow rules for the authenticated user."""
    count_stmt = (
        select(func.count()).select_from(WorkflowRule).where(WorkflowRule.user_id == user.id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(WorkflowRule)
        .where(WorkflowRule.user_id == user.id)
        .order_by(WorkflowRule.created_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()

    return WorkflowRuleListResponse(
        rules=[_rule_to_response(r) for r in rules],
        total=total,
    )


@router.get(
    "/{rule_id}",
    response_model=WorkflowRuleResponse,
    summary="Get a workflow rule",
)
async def get_workflow_rule(
    rule_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowRuleResponse:
    """Get a single workflow rule by ID."""
    rule = await _get_rule_or_404(rule_id, db)
    _check_rule_ownership(rule, user.id)
    return _rule_to_response(rule)


@router.patch(
    "/{rule_id}",
    response_model=WorkflowRuleResponse,
    summary="Update a workflow rule",
)
async def update_workflow_rule(
    rule_id: uuid.UUID,
    body: WorkflowRuleUpdate,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowRuleResponse:
    """Update a workflow rule (partial update)."""
    rule = await _get_rule_or_404(rule_id, db)
    _check_rule_ownership(rule, user.id)

    if body.name is not None:
        rule.name = body.name
    if body.description is not None:
        rule.description = body.description
    if body.trigger_config is not None:
        rule.trigger_config = body.trigger_config.model_dump()
    if body.action_config is not None:
        rule.action_config = body.action_config.model_dump()
    if body.is_active is not None:
        rule.is_active = body.is_active

    await db.flush()
    await db.commit()
    await db.refresh(rule)

    return _rule_to_response(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a workflow rule",
)
async def delete_workflow_rule(
    rule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a workflow rule and all its execution history."""
    rule = await _get_rule_or_404(rule_id, db)
    _check_rule_ownership(rule, user.id)

    await db.delete(rule)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{rule_id}/log",
    response_model=WorkflowExecutionListResponse,
    summary="Get execution log for a rule",
)
async def get_execution_log(
    rule_id: uuid.UUID,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
) -> WorkflowExecutionListResponse:
    """Get the execution log for a specific workflow rule."""
    rule = await _get_rule_or_404(rule_id, db)
    _check_rule_ownership(rule, user.id)

    count_stmt = (
        select(func.count())
        .select_from(WorkflowExecution)
        .where(WorkflowExecution.rule_id == rule_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(WorkflowExecution)
        .where(WorkflowExecution.rule_id == rule_id)
        .order_by(WorkflowExecution.executed_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
    )
    result = await db.execute(stmt)
    executions = result.scalars().all()

    return WorkflowExecutionListResponse(
        executions=[
            WorkflowExecutionResponse(
                id=e.id,
                rule_id=e.rule_id,
                trigger_event=e.trigger_event,
                trigger_data=e.trigger_data,
                action_result=e.action_result,
                action_data=e.action_data,
                executed_at=e.executed_at,
            )
            for e in executions
        ],
        total=total,
    )
