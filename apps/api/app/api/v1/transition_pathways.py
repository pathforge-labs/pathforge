"""
PathForge API v1 — Transition Pathways Endpoints
====================================================
REST endpoints for the Transition Pathways module.

11 endpoints at /api/v1/transition-pathways:
    - GET  /dashboard           — Full dashboard view
    - POST /explore             — Explore transition (full pipeline)
    - POST /what-if             — Quick role exploration
    - GET  /preferences         — Get preferences
    - PUT  /preferences         — Update preferences
    - GET  /                    — List saved transitions
    - GET  /{id}                — Get specific transition
    - DELETE /{id}              — Delete transition
    - GET  /{id}/skill-bridge   — Skill gap analysis
    - GET  /{id}/milestones     — Action plan milestones
    - GET  /{id}/comparison     — Role comparison
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.transition_pathways import (
    RoleWhatIfRequest,
    SkillBridgeEntryResponse,
    TransitionComparisonResponse,
    TransitionDashboardResponse,
    TransitionExploreRequest,
    TransitionMilestoneResponse,
    TransitionPathResponse,
    TransitionPreferenceResponse,
    TransitionPreferenceUpdateRequest,
    TransitionScanResponse,
    TransitionSummaryResponse,
)
from app.services import transition_pathways_service

router = APIRouter(
    prefix="/transition-pathways",
    tags=["Transition Pathways"],
)


# ── Private Helpers ────────────────────────────────────────────


def _build_scan_response(
    result: dict[str, Any],
) -> TransitionScanResponse:
    """Build a TransitionScanResponse from service pipeline result."""
    return TransitionScanResponse(
        transition_path=TransitionPathResponse.model_validate(
            result["transition_path"],
        ),
        skill_bridge=[
            SkillBridgeEntryResponse.model_validate(entry)
            for entry in result["skill_bridge"]
        ],
        milestones=[
            TransitionMilestoneResponse.model_validate(milestone)
            for milestone in result["milestones"]
        ],
        comparisons=[
            TransitionComparisonResponse.model_validate(comp)
            for comp in result["comparisons"]
        ],
    )


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=TransitionDashboardResponse,
    status_code=HTTP_200_OK,
    summary="Get Transition Pathways dashboard",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> TransitionDashboardResponse:
    """Retrieve all saved transitions and preferences for dashboard."""
    result = await transition_pathways_service.get_dashboard(
        database, user_id=current_user.id,
    )
    return TransitionDashboardResponse(
        transitions=[
            TransitionSummaryResponse.model_validate(t)
            for t in result["transitions"]
        ],
        preferences=(
            TransitionPreferenceResponse.model_validate(result["preferences"])
            if result["preferences"]
            else None
        ),
        total_explored=result["total_explored"],
    )


# ── Explore Transition ─────────────────────────────────────────


@router.post(
    "/explore",
    response_model=TransitionScanResponse,
    status_code=HTTP_201_CREATED,
    summary="Explore a career transition",
)
@limiter.limit("3/minute")
async def explore_transition(
    request: Request,
    body: TransitionExploreRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> TransitionScanResponse:
    """Run full exploration pipeline for a target role."""
    try:
        result = await transition_pathways_service.explore_transition(
            database,
            user_id=current_user.id,
            target_role=body.target_role,
            target_industry=body.target_industry,
            target_location=body.target_location,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc

    return _build_scan_response(result)


# ── What-If ────────────────────────────────────────────────────


@router.post(
    "/what-if",
    response_model=TransitionScanResponse,
    status_code=HTTP_201_CREATED,
    summary="Quick: What if I moved to role X?",
)
@limiter.limit("3/minute")
async def what_if(
    request: Request,
    body: RoleWhatIfRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> TransitionScanResponse:
    """Quick exploration shortcut using the full pipeline."""
    try:
        result = await transition_pathways_service.explore_transition(
            database,
            user_id=current_user.id,
            target_role=body.target_role,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc

    return _build_scan_response(result)


# ── Preferences ────────────────────────────────────────────────
# NOTE: Must be defined BEFORE /{transition_id} to avoid path collision.


@router.get(
    "/preferences",
    response_model=TransitionPreferenceResponse | None,
    status_code=HTTP_200_OK,
    summary="Get transition preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> TransitionPreferenceResponse | None:
    """Retrieve transition preferences for the current user."""
    pref = await transition_pathways_service.get_preferences(
        database, user_id=current_user.id,
    )
    if not pref:
        return None
    return TransitionPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=TransitionPreferenceResponse,
    status_code=HTTP_200_OK,
    summary="Update transition preferences",
)
async def update_preferences(
    body: TransitionPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> TransitionPreferenceResponse:
    """Update or create transition preferences."""
    try:
        pref = await transition_pathways_service.update_preferences(
            database, user_id=current_user.id, update_data=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc

    return TransitionPreferenceResponse.model_validate(pref)


# ── List Transitions ──────────────────────────────────────────


@router.get(
    "/",
    response_model=list[TransitionSummaryResponse],
    status_code=HTTP_200_OK,
    summary="List all saved transitions",
)
async def list_transitions(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[TransitionSummaryResponse]:
    """List all transition paths for the current user."""
    transitions = await transition_pathways_service.get_transitions(
        database, user_id=current_user.id,
    )
    return [
        TransitionSummaryResponse.model_validate(t)
        for t in transitions
    ]


# ── Get Transition ─────────────────────────────────────────────


@router.get(
    "/{transition_id}",
    response_model=TransitionPathResponse,
    status_code=HTTP_200_OK,
    summary="Get a specific transition",
)
async def get_transition(
    transition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> TransitionPathResponse:
    """Retrieve a specific transition path by ID."""
    transition = await transition_pathways_service.get_transition(
        database, transition_id=transition_id, user_id=current_user.id,
    )
    if not transition:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Transition path not found",
        )
    return TransitionPathResponse.model_validate(transition)


# ── Delete Transition ──────────────────────────────────────────


@router.delete(
    "/{transition_id}",
    status_code=HTTP_204_NO_CONTENT,
    summary="Delete a saved transition",
)
async def delete_transition(
    transition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> None:
    """Delete a transition path and all related data."""
    deleted = await transition_pathways_service.delete_transition(
        database, transition_id=transition_id, user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Transition path not found",
        )


# ── Skill Bridge ──────────────────────────────────────────────


@router.get(
    "/{transition_id}/skill-bridge",
    response_model=list[SkillBridgeEntryResponse],
    status_code=HTTP_200_OK,
    summary="Get skill gap analysis for a transition",
)
async def get_skill_bridge(
    transition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[SkillBridgeEntryResponse]:
    """Retrieve skill bridge entries for a transition."""
    # Verify ownership
    transition = await transition_pathways_service.get_transition(
        database, transition_id=transition_id, user_id=current_user.id,
    )
    if not transition:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Transition path not found",
        )

    entries = await transition_pathways_service.get_skill_bridge(
        database, transition_id=transition_id,
    )
    return [
        SkillBridgeEntryResponse.model_validate(entry)
        for entry in entries
    ]


# ── Milestones ─────────────────────────────────────────────────


@router.get(
    "/{transition_id}/milestones",
    response_model=list[TransitionMilestoneResponse],
    status_code=HTTP_200_OK,
    summary="Get action plan for a transition",
)
async def get_milestones(
    transition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[TransitionMilestoneResponse]:
    """Retrieve milestones for a transition."""
    transition = await transition_pathways_service.get_transition(
        database, transition_id=transition_id, user_id=current_user.id,
    )
    if not transition:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Transition path not found",
        )

    milestones = await transition_pathways_service.get_milestones(
        database, transition_id=transition_id,
    )
    return [
        TransitionMilestoneResponse.model_validate(m)
        for m in milestones
    ]


# ── Comparison ─────────────────────────────────────────────────


@router.get(
    "/{transition_id}/comparison",
    response_model=list[TransitionComparisonResponse],
    status_code=HTTP_200_OK,
    summary="Get role comparison for a transition",
)
async def get_comparison(
    transition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[TransitionComparisonResponse]:
    """Retrieve dimension comparisons for a transition."""
    transition = await transition_pathways_service.get_transition(
        database, transition_id=transition_id, user_id=current_user.id,
    )
    if not transition:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Transition path not found",
        )

    comparisons = await transition_pathways_service.get_comparisons(
        database, transition_id=transition_id,
    )
    return [
        TransitionComparisonResponse.model_validate(comp)
        for comp in comparisons
    ]
