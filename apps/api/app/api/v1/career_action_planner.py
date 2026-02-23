"""
PathForge — Career Action Planner™ API Routes
================================================
REST API endpoints for the Career Action Planner feature.

10 endpoints at /api/v1/career-action-planner:
    GET    /dashboard                              — Dashboard with plans + stats
    POST   /scan                                   — Generate new career action plan
    GET    /{plan_id}                               — Get plan detail with milestones
    PUT    /{plan_id}/status                        — Update plan status
    GET    /{plan_id}/milestones                    — List milestones for plan
    PUT    /{plan_id}/milestones/{milestone_id}     — Update milestone
    POST   /{plan_id}/milestones/{milestone_id}/progress — Log progress
    POST   /compare                                — Compare plan scenarios
    GET    /preferences                             — Get preferences
    PUT    /preferences                             — Update preferences
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.career_action_planner import (
    CareerActionPlannerPreferenceResponse,
    CareerActionPlannerPreferenceUpdate,
    CareerActionPlanResponse,
    GeneratePlanRequest,
    LogProgressRequest,
    MilestoneProgressResponse,
    PlanComparisonResponse,
    PlanDashboardResponse,
    PlanMilestoneResponse,
    PlanRecommendationResponse,
    PlanScanResponse,
    PlanStatsResponse,
    PlanSummaryResponse,
    UpdateMilestoneRequest,
    UpdatePlanStatusRequest,
)
from app.services import career_action_planner_service as service

router = APIRouter(
    prefix="/career-action-planner",
    tags=["Career Action Planner™"],
)

# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=PlanDashboardResponse,
    status_code=HTTP_200_OK,
    summary="Get Career Action Planner dashboard",
)
@limiter.limit("20/minute")
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PlanDashboardResponse:
    """Get dashboard with active plans, stats, and recommendations."""
    result = await service.get_dashboard(
        database, user_id=current_user.id,
    )

    active_plans = [
        PlanSummaryResponse(**plan_data)
        for plan_data in result.active_plans
    ]

    pref = result.preferences
    pref_response = (
        CareerActionPlannerPreferenceResponse.model_validate(pref)
        if pref else None
    )


    return PlanDashboardResponse(
        active_plans=active_plans,
        recent_recommendations=[
            PlanRecommendationResponse.model_validate(rec)
            for rec in result.recent_recommendations
        ],
        stats=PlanStatsResponse(**result.stats),
        preferences=pref_response,
    )


# ── Plan Generation (Scan) ────────────────────────────────────


@router.post(
    "/scan",
    response_model=PlanScanResponse,
    status_code=HTTP_201_CREATED,
    summary="Generate a new career action plan",
)
@limiter.limit("2/minute")
async def create_plan_scan(
    request: Request,
    body: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PlanScanResponse:
    """Generate a new career action plan via AI pipeline.

    Career Sprint Methodology™ — creates a personalized, time-bound
    career development plan with milestones and recommendations.
    """
    try:
        result = await service.generate_plan(
            database, user_id=current_user.id, request_data=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PlanScanResponse(
        plan=CareerActionPlanResponse.model_validate(result.plan),
        recommendations=[
            PlanRecommendationResponse.model_validate(rec)
            for rec in result.recommendations
        ],
    )


# ── Plan Detail ────────────────────────────────────────────────


@router.get(
    "/{plan_id}",
    response_model=CareerActionPlanResponse,
    status_code=HTTP_200_OK,
    summary="Get plan detail with milestones",
)
@limiter.limit("20/minute")
async def get_plan_detail(
    request: Request,
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerActionPlanResponse:
    """Retrieve a specific career action plan with milestones and progress."""
    plan = await service.get_plan(
        database, plan_id=plan_id, user_id=current_user.id,
    )
    if not plan:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Plan not found.",
        )
    return CareerActionPlanResponse.model_validate(plan)


# ── Plan Status Update ────────────────────────────────────────


@router.put(
    "/{plan_id}/status",
    response_model=CareerActionPlanResponse,
    status_code=HTTP_200_OK,
    summary="Update plan status",
)
@limiter.limit("10/minute")
async def update_plan_status(
    request: Request,
    plan_id: uuid.UUID,
    body: UpdatePlanStatusRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerActionPlanResponse:
    """Update plan status (activate, pause, complete, archive)."""
    try:
        plan = await service.update_plan_status(
            database,
            plan_id=plan_id,
            user_id=current_user.id,
            new_status=body.status,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CareerActionPlanResponse.model_validate(plan)


# ── Milestones ─────────────────────────────────────────────────


@router.get(
    "/{plan_id}/milestones",
    response_model=list[PlanMilestoneResponse],
    status_code=HTTP_200_OK,
    summary="List milestones for a plan",
)
@limiter.limit("20/minute")
async def list_milestones(
    request: Request,
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[PlanMilestoneResponse]:
    """List all milestones for a career action plan."""
    try:
        milestones = await service.get_milestones(
            database, plan_id=plan_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return [
        PlanMilestoneResponse.model_validate(milestone)
        for milestone in milestones
    ]


@router.put(
    "/{plan_id}/milestones/{milestone_id}",
    response_model=PlanMilestoneResponse,
    status_code=HTTP_200_OK,
    summary="Update a milestone",
)
@limiter.limit("10/minute")
async def update_milestone(
    request: Request,
    plan_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: UpdateMilestoneRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PlanMilestoneResponse:
    """Update a milestone's status, target date, effort, or priority."""
    try:
        milestone = await service.update_milestone(
            database,
            plan_id=plan_id,
            milestone_id=milestone_id,
            user_id=current_user.id,
            update_data=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return PlanMilestoneResponse.model_validate(milestone)


# ── Progress Logging ──────────────────────────────────────────


@router.post(
    "/{plan_id}/milestones/{milestone_id}/progress",
    response_model=MilestoneProgressResponse,
    status_code=HTTP_201_CREATED,
    summary="Log progress against a milestone",
)
@limiter.limit("10/minute")
async def log_milestone_progress(
    request: Request,
    plan_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: LogProgressRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> MilestoneProgressResponse:
    """Log a progress entry against a milestone.

    Auto-updates milestone status:
    - 100% → completed
    - >0% and not_started → in_progress
    """
    try:
        entry = await service.log_progress(
            database,
            plan_id=plan_id,
            milestone_id=milestone_id,
            user_id=current_user.id,
            progress_data=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return MilestoneProgressResponse.model_validate(entry)


# ── Plan Comparison ───────────────────────────────────────────


@router.post(
    "/compare",
    response_model=PlanComparisonResponse,
    status_code=HTTP_200_OK,
    summary="Compare plan scenarios",
)
@limiter.limit("3/minute")
async def compare_plans(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PlanComparisonResponse:
    """Compare all user plans and recommend the best option."""
    result = await service.compare_plans(
        database, user_id=current_user.id,
    )

    plan_responses = [
        CareerActionPlanResponse.model_validate(plan)
        for plan in result.plans
    ]

    return PlanComparisonResponse(
        plans=plan_responses,
        recommended_plan_id=result.recommended_plan_id,
        recommendation_reasoning=result.recommendation_reasoning,
    )


# ── Preferences ────────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=CareerActionPlannerPreferenceResponse | None,
    status_code=HTTP_200_OK,
    summary="Get Career Action Planner preferences",
)
@limiter.limit("30/minute")
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerActionPlannerPreferenceResponse | None:
    """Get user's Career Action Planner preferences."""
    pref = await service.get_preferences(
        database, user_id=current_user.id,
    )
    if not pref:
        return None
    return CareerActionPlannerPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=CareerActionPlannerPreferenceResponse,
    status_code=HTTP_200_OK,
    summary="Update Career Action Planner preferences",
)
@limiter.limit("20/minute")
async def update_preferences(
    request: Request,
    body: CareerActionPlannerPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerActionPlannerPreferenceResponse:
    """Update or create Career Action Planner preferences."""
    try:
        pref = await service.update_preferences(
            database,
            user_id=current_user.id,
            update_data=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CareerActionPlannerPreferenceResponse.model_validate(pref)
