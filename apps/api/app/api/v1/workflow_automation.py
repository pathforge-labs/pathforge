"""
PathForge — Career Workflow Automation Engine™ API Routes
==========================================================
REST API endpoints for the Career Workflow Automation Engine
— Threshold-Triggered Workflows™ and Smart Workflow Templates™.

Endpoints:
    GET  /workflows/dashboard                 — Dashboard with stats
    POST /workflows                           — Create from template/custom
    GET  /workflows                           — List with filters
    GET  /workflows/templates                 — Browse Smart Templates™
    GET  /workflows/{id}                      — Workflow with steps
    PUT  /workflows/{id}/status               — Update lifecycle status
    PUT  /workflows/{id}/steps/{sid}/status    — Complete/skip step
    GET  /workflows/{id}/executions           — Execution history
    GET  /workflows/preferences               — Get preferences
    PUT  /workflows/preferences               — Update preferences
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.workflow_automation import (
    CareerWorkflowResponse,
    CreateWorkflowRequest,
    UpdateStepStatusRequest,
    UpdateWorkflowStatusRequest,
    WorkflowDashboardResponse,
    WorkflowExecutionResponse,
    WorkflowPreferenceResponse,
    WorkflowPreferenceUpdate,
    WorkflowStepResponse,
    WorkflowSummary,
    WorkflowTemplateInfo,
)
from app.services.workflow_automation_service import (
    WorkflowAutomationService,
    _get_template_info_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workflows",
    tags=["Career Workflow Automation Engine™"],
)


# ── Dashboard ────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=WorkflowDashboardResponse,
    summary="Get Workflow Automation dashboard",
    description=(
        "Career Workflow Automation Engine™ — dashboard with active "
        "workflows, available templates, status counts."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> WorkflowDashboardResponse:
    """Get Workflow Automation dashboard."""
    try:
        data = await WorkflowAutomationService.get_dashboard(
            database, user_id=current_user.id,
        )

        active_workflows = data["active_workflows"]
        preferences = data["preferences"]

        return WorkflowDashboardResponse(
            active_workflows=[
                WorkflowSummary(
                    id=wf.id,
                    name=wf.name,
                    workflow_status=wf.workflow_status,
                    trigger_type=wf.trigger_type,
                    total_steps=wf.total_steps,
                    completed_steps=wf.completed_steps,
                    is_template=wf.is_template,
                    created_at=wf.created_at,
                )
                for wf in active_workflows
            ],
            available_templates=[
                WorkflowTemplateInfo(**tmpl)
                for tmpl in data["available_templates"]
            ],
            total_active=data["total_active"],
            total_completed=data["total_completed"],
            total_draft=data["total_draft"],
            preferences=(
                WorkflowPreferenceResponse.model_validate(preferences)
                if preferences else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Create Workflow ──────────────────────────────────────────


@router.post(
    "",
    response_model=CareerWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create career workflow",
    description=(
        "Create a new career workflow from Smart Workflow Templates™ "
        "or as a custom user-defined workflow."
    ),
)
@limiter.limit("5/minute")
async def create_workflow(
    request: Request,
    body: CreateWorkflowRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerWorkflowResponse:
    """Create workflow from template or custom."""
    try:
        workflow = await WorkflowAutomationService.create_workflow(
            database,
            user_id=current_user.id,
            template_id=body.template_id,
            name=body.name,
            trigger_type=body.trigger_type,
            trigger_config=body.trigger_config,
            auto_activate=body.auto_activate,
        )
        return CareerWorkflowResponse.model_validate(workflow)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── List Workflows ───────────────────────────────────────────


@router.get(
    "",
    response_model=list[WorkflowSummary],
    summary="List workflows",
    description="List career workflows with optional status filter.",
)
@limiter.limit(settings.rate_limit_parse)
async def list_workflows(
    request: Request,
    status_filter: str | None = Query(
        None, alias="status",
        description="Filter: draft | active | paused | completed | archived",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[WorkflowSummary]:
    """List workflows with filters."""
    workflows = await WorkflowAutomationService.list_workflows(
        database,
        user_id=current_user.id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return [
        WorkflowSummary(
            id=wf.id,
            name=wf.name,
            workflow_status=wf.workflow_status,
            trigger_type=wf.trigger_type,
            total_steps=wf.total_steps,
            completed_steps=wf.completed_steps,
            is_template=wf.is_template,
            created_at=wf.created_at,
        )
        for wf in workflows
    ]


# ── Templates ────────────────────────────────────────────────


@router.get(
    "/templates",
    response_model=list[WorkflowTemplateInfo],
    summary="Browse Smart Workflow Templates™",
    description=(
        "Browse available Smart Workflow Templates™ — pre-built "
        "career acceleration workflows."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def list_templates(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> list[WorkflowTemplateInfo]:
    """List available workflow templates."""
    templates = _get_template_info_list()
    return [WorkflowTemplateInfo(**tmpl) for tmpl in templates]


# ── Preferences ──────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=WorkflowPreferenceResponse,
    summary="Get workflow preferences",
    description="Get user's Workflow Automation preferences.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> WorkflowPreferenceResponse:
    """Get Workflow Automation preferences."""
    pref = await WorkflowAutomationService.get_preferences(
        database, user_id=current_user.id,
    )
    if pref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preferences found. Set preferences first.",
        )
    return WorkflowPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=WorkflowPreferenceResponse,
    summary="Update workflow preferences",
    description=(
        "Update Workflow Automation preferences including "
        "automation toggles, trigger sensitivity, and limits."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_preferences(
    request: Request,
    body: WorkflowPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> WorkflowPreferenceResponse:
    """Update Workflow Automation preferences."""
    try:
        pref = await WorkflowAutomationService.update_preferences(
            database,
            user_id=current_user.id,
            updates=body.model_dump(exclude_unset=True),
        )
        return WorkflowPreferenceResponse.model_validate(pref)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Workflow Detail ──────────────────────────────────────────


@router.get(
    "/{workflow_id}",
    response_model=CareerWorkflowResponse,
    summary="Get workflow detail",
    description="Get workflow detail including all steps.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_workflow_detail(
    request: Request,
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerWorkflowResponse:
    """Get single workflow with steps."""
    workflow = await WorkflowAutomationService.get_workflow_detail(
        database,
        user_id=current_user.id,
        workflow_id=workflow_id,
    )
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found.",
        )
    return CareerWorkflowResponse.model_validate(workflow)


# ── Update Workflow Status ───────────────────────────────────


@router.put(
    "/{workflow_id}/status",
    response_model=CareerWorkflowResponse,
    summary="Update workflow status",
    description="Update workflow lifecycle: draft → active → completed.",
)
@limiter.limit(settings.rate_limit_embed)
async def update_workflow_status(
    request: Request,
    workflow_id: uuid.UUID,
    body: UpdateWorkflowStatusRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerWorkflowResponse:
    """Update workflow lifecycle status."""
    try:
        workflow = await WorkflowAutomationService.update_workflow_status(
            database,
            user_id=current_user.id,
            workflow_id=workflow_id,
            new_status=body.workflow_status,
        )
        return CareerWorkflowResponse.model_validate(workflow)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Update Step Status ───────────────────────────────────────


@router.put(
    "/{workflow_id}/steps/{step_id}/status",
    response_model=WorkflowStepResponse,
    summary="Complete or skip a workflow step",
    description=(
        "Mark a workflow step as completed or skipped. Auto-completes "
        "the workflow when all steps are done."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_step_status(
    request: Request,
    workflow_id: uuid.UUID,
    step_id: uuid.UUID,
    body: UpdateStepStatusRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> WorkflowStepResponse:
    """Complete or skip a workflow step."""
    try:
        step = await WorkflowAutomationService.update_step_status(
            database,
            user_id=current_user.id,
            workflow_id=workflow_id,
            step_id=step_id,
            action=body.action,
        )
        return WorkflowStepResponse.model_validate(step)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Executions ───────────────────────────────────────────────


@router.get(
    "/{workflow_id}/executions",
    response_model=list[WorkflowExecutionResponse],
    summary="Get workflow execution history",
    description="List execution records for a specific workflow.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_executions(
    request: Request,
    workflow_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[WorkflowExecutionResponse]:
    """List workflow execution records."""
    executions = await WorkflowAutomationService.get_executions(
        database,
        user_id=current_user.id,
        workflow_id=workflow_id,
        limit=limit,
    )
    return [
        WorkflowExecutionResponse.model_validate(ex)
        for ex in executions
    ]
