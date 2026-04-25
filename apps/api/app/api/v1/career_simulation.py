"""
PathForge API v1 — Career Simulation Engine™ Endpoints
=========================================================
REST endpoints for the Career Simulation Engine.

11 endpoints at /api/v1/career-simulation:
    GET    /dashboard           — All saved simulations + preferences
    POST   /simulate/role       — Role transition simulation
    POST   /simulate/geo        — Geographic move simulation
    POST   /simulate/skill      — Skill investment simulation
    POST   /simulate/industry   — Industry pivot simulation
    POST   /simulate/seniority  — Seniority jump simulation
    POST   /compare             — Compare up to 5 simulations
    GET    /preferences         — Get simulation preferences
    PUT    /preferences         — Update simulation preferences
    GET    /{simulation_id}     — Get specific simulation
    DELETE /{simulation_id}     — Delete a simulation
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
)

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_gate import require_feature
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.career_simulation import (
    CareerSimulationResponse,
    GeoMoveSimRequest,
    IndustryPivotSimRequest,
    RoleTransitionSimRequest,
    SeniorityJumpSimRequest,
    SimulationCompareRequest,
    SimulationComparisonResponse,
    SimulationDashboardResponse,
    SimulationPreferenceResponse,
    SimulationPreferenceUpdateRequest,
    SimulationSummaryResponse,
    SkillInvestmentSimRequest,
)
from app.services import career_simulation_service
from app.services.billing_service import BillingService

if TYPE_CHECKING:
    from app.models.career_simulation import CareerSimulation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/career-simulation",
    tags=["Career Simulation"],
)


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=SimulationDashboardResponse,
    status_code=HTTP_200_OK,
    summary="Career simulation dashboard",
    description="Retrieve all saved simulations, preferences, and summary statistics.",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> SimulationDashboardResponse:
    """Retrieve all saved simulations and preferences for dashboard."""
    data = await career_simulation_service.get_dashboard(
        database, user_id=current_user.id, page=page, per_page=per_page,
    )

    return SimulationDashboardResponse(
        simulations=[
            SimulationSummaryResponse(
                id=sim.id,
                scenario_type=sim.scenario_type,
                status=sim.status,
                confidence_score=sim.confidence_score,
                salary_impact_percent=sim.salary_impact_percent,
                estimated_months=sim.estimated_months,
                data_source=sim.data_source,
                disclaimer=sim.disclaimer,
                computed_at=sim.computed_at,
            )
            for sim in data["simulations"]
        ],
        preferences=(
            SimulationPreferenceResponse(
                id=data["preferences"].id,
                career_dna_id=data["preferences"].career_dna_id,
                default_scenario_type=data["preferences"].default_scenario_type,
                max_scenarios=data["preferences"].max_scenarios,
                notification_enabled=data["preferences"].notification_enabled,
            )
            if data["preferences"]
            else None
        ),
        total_simulations=data["total_simulations"],
        scenario_type_counts=data["scenario_type_counts"],
    )


# ── Simulate: Role Transition ─────────────────────────────────


@router.post(
    "/simulate/role",
    response_model=CareerSimulationResponse,
    status_code=HTTP_201_CREATED,
    summary="Simulate role transition",
    description="What-if: What happens if I switch to a new role?",
    dependencies=[Depends(require_feature("career_simulation"))],
)
@limiter.limit("5/minute")
async def simulate_role(
    request: Request,
    body: RoleTransitionSimRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSimulationResponse:
    """Run role transition what-if simulation.

    Sprint 38 C1/C2/C5: Feature gating + scan limit + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(database, current_user, "career_simulation")

    simulation = await career_simulation_service.simulate_role_transition(
        database,
        user_id=current_user.id,
        target_role=body.target_role,
        target_industry=body.target_industry,
        target_location=body.target_location,
    )

    # C2: Record usage after successful simulation
    if settings.billing_enabled:
        await BillingService.record_usage(database, current_user, "career_simulation")

    return _build_full_response(simulation)


# ── Simulate: Geo Move ────────────────────────────────────────


@router.post(
    "/simulate/geo",
    response_model=CareerSimulationResponse,
    status_code=HTTP_201_CREATED,
    summary="Simulate geographic move",
    description="What-if: What happens if I relocate to a new city/country?",
    dependencies=[Depends(require_feature("career_simulation"))],
)
@limiter.limit("5/minute")
async def simulate_geo(
    request: Request,
    body: GeoMoveSimRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSimulationResponse:
    """Run geographic move what-if simulation."""
    simulation = await career_simulation_service.simulate_geo_move(
        database,
        user_id=current_user.id,
        target_location=body.target_location,
        keep_role=body.keep_role,
        target_role=body.target_role,
    )
    return _build_full_response(simulation)


# ── Simulate: Skill Investment ─────────────────────────────────


@router.post(
    "/simulate/skill",
    response_model=CareerSimulationResponse,
    status_code=HTTP_201_CREATED,
    summary="Simulate skill investment",
    description="What-if: What happens if I invest in learning new skills?",
    dependencies=[Depends(require_feature("career_simulation"))],
)
@limiter.limit("5/minute")
async def simulate_skill(
    request: Request,
    body: SkillInvestmentSimRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSimulationResponse:
    """Run skill investment what-if simulation."""
    simulation = await career_simulation_service.simulate_skill_investment(
        database,
        user_id=current_user.id,
        skills=body.skills,
        target_role=body.target_role,
    )
    return _build_full_response(simulation)


# ── Simulate: Industry Pivot ──────────────────────────────────


@router.post(
    "/simulate/industry",
    response_model=CareerSimulationResponse,
    status_code=HTTP_201_CREATED,
    summary="Simulate industry pivot",
    description="What-if: What happens if I move to a different industry?",
    dependencies=[Depends(require_feature("career_simulation"))],
)
@limiter.limit("5/minute")
async def simulate_industry(
    request: Request,
    body: IndustryPivotSimRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSimulationResponse:
    """Run industry pivot what-if simulation."""
    simulation = await career_simulation_service.simulate_industry_pivot(
        database,
        user_id=current_user.id,
        target_industry=body.target_industry,
        target_role=body.target_role,
    )
    return _build_full_response(simulation)


# ── Simulate: Seniority Jump ──────────────────────────────────


@router.post(
    "/simulate/seniority",
    response_model=CareerSimulationResponse,
    status_code=HTTP_201_CREATED,
    summary="Simulate seniority jump",
    description="What-if: What happens if I move up to a higher seniority level?",
    dependencies=[Depends(require_feature("career_simulation"))],
)
@limiter.limit("5/minute")
async def simulate_seniority(
    request: Request,
    body: SeniorityJumpSimRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSimulationResponse:
    """Run seniority jump what-if simulation."""
    simulation = await career_simulation_service.simulate_seniority_jump(
        database,
        user_id=current_user.id,
        target_seniority=body.target_seniority,
        target_role=body.target_role,
    )
    return _build_full_response(simulation)


# ── Compare Simulations ───────────────────────────────────────


@router.post(
    "/compare",
    response_model=SimulationComparisonResponse,
    status_code=HTTP_200_OK,
    summary="Compare simulations",
    description="Compare up to 5 saved simulations side-by-side.",
)
@limiter.limit("3/minute")
async def compare_simulations(
    request: Request,
    body: SimulationCompareRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> SimulationComparisonResponse:
    """Compare multiple simulations."""
    data = await career_simulation_service.compare_simulations(
        database,
        user_id=current_user.id,
        simulation_ids=body.simulation_ids,
    )

    return SimulationComparisonResponse(
        simulations=[
            _build_full_response(sim) for sim in data["simulations"]
        ],
        ranking=data.get("ranking", []),
        trade_off_analysis=data.get("trade_off_analysis"),
    )


# ── Preferences ────────────────────────────────────────────────
# NOTE: Must be defined BEFORE /{simulation_id} to avoid path collision.


@router.get(
    "/preferences",
    response_model=SimulationPreferenceResponse | None,
    status_code=HTTP_200_OK,
    summary="Get simulation preferences",
    description="Retrieve your Career Simulation Engine preferences.",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> SimulationPreferenceResponse | None:
    """Retrieve simulation preferences for the current user."""
    preference = await career_simulation_service.get_preferences(
        database, user_id=current_user.id,
    )
    if not preference:
        return None

    return SimulationPreferenceResponse.model_validate(preference)


@router.put(
    "/preferences",
    response_model=SimulationPreferenceResponse,
    status_code=HTTP_200_OK,
    summary="Update simulation preferences",
    description="Update or create your Career Simulation Engine preferences.",
)
async def update_preferences(
    body: SimulationPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> SimulationPreferenceResponse:
    """Update or create simulation preferences."""
    preference = await career_simulation_service.update_preferences(
        database,
        user_id=current_user.id,
        update_data=body,
    )

    return SimulationPreferenceResponse.model_validate(preference)


# ── Get / Delete Simulation ───────────────────────────────────


@router.get(
    "/{simulation_id}",
    response_model=CareerSimulationResponse,
    status_code=HTTP_200_OK,
    summary="Get simulation detail",
    description="Retrieve a specific simulation with all projections and recommendations.",
    responses={HTTP_404_NOT_FOUND: {"description": "Simulation not found"}},
)
async def get_simulation(
    simulation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSimulationResponse:
    """Retrieve a specific simulation by ID."""
    simulation = await career_simulation_service.get_simulation(
        database,
        simulation_id=simulation_id,
        user_id=current_user.id,
    )
    if not simulation:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )

    return _build_full_response(simulation)


@router.delete(
    "/{simulation_id}",
    status_code=HTTP_204_NO_CONTENT,
    summary="Delete simulation",
    description="Delete a saved simulation and all related data.",
    responses={HTTP_404_NOT_FOUND: {"description": "Simulation not found"}},
)
async def delete_simulation(
    simulation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> None:
    """Delete a simulation."""
    deleted = await career_simulation_service.delete_simulation(
        database,
        simulation_id=simulation_id,
        user_id=current_user.id,
    )
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )


# ── Response Builder ──────────────────────────────────────────


def _build_full_response(simulation: CareerSimulation) -> CareerSimulationResponse:
    """Build a full CareerSimulationResponse from a model instance."""
    return CareerSimulationResponse.model_validate(simulation)

