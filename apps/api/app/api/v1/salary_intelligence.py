"""
PathForge API — Salary Intelligence Engine™ Routes
=====================================================
REST endpoints for the Salary Intelligence Engine system.

10 endpoints covering:
    - Dashboard (get full salary intelligence state)
    - Full scan (trigger comprehensive salary analysis)
    - Salary estimate (latest personalized range)
    - Skill impacts (per-skill salary contribution)
    - Trajectory (historical salary timeline)
    - Scenarios (list, create, get what-if simulations)
    - Skill what-if (shortcut: add-skill scenario)
    - Location what-if (shortcut: change-location scenario)
    - Preferences (get, update)
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_gate import require_feature
from app.core.intelligence_cache import ic_cache
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.salary_intelligence import (
    LocationWhatIfRequest,
    SalaryDashboardResponse,
    SalaryEstimateResponse,
    SalaryImpactAnalysisResponse,
    SalaryPreferenceResponse,
    SalaryPreferenceUpdateRequest,
    SalaryScanResponse,
    SalaryScenarioRequest,
    SalaryScenarioResponse,
    SalaryTrajectoryResponse,
    SkillSalaryImpactResponse,
    SkillWhatIfRequest,
)
from app.services.billing_service import BillingService
from app.services.salary_intelligence_service import SalaryIntelligenceService

router = APIRouter(
    prefix="/salary-intelligence",
    tags=["Salary Intelligence Engine™"],
)


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=SalaryDashboardResponse,
    summary="Get full Salary Intelligence dashboard",
)
async def get_salary_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryDashboardResponse:
    """Full Salary Intelligence Engine™ dashboard with all components."""
    cache_key = ic_cache.key(current_user.id, "salary_dashboard")
    cached = await ic_cache.get(cache_key)
    if cached is not None:
        return SalaryDashboardResponse.model_validate(cached)

    data: dict[str, Any] = await SalaryIntelligenceService.get_dashboard(
        db, user_id=current_user.id,
    )
    result = SalaryDashboardResponse(**data)
    await ic_cache.set(cache_key, result.model_dump(mode="json"), ttl=ic_cache.TTL_SALARY)
    return result


# ── Full Scan ──────────────────────────────────────────────────


@router.post(
    "/scan",
    response_model=SalaryScanResponse,
    summary="Trigger full salary intelligence scan",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_feature("salary_intelligence"))],
)
@limiter.limit(settings.rate_limit_career_dna)
async def run_salary_scan(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryScanResponse:
    """Execute full salary analysis pipeline: estimate → impacts → history.

    Sprint 38 C1/C2/C5: Feature gating + scan limit + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(db, current_user, "salary_intelligence")

    data: dict[str, Any] = await SalaryIntelligenceService.run_full_scan(
        db, user_id=current_user.id,
    )

    if data.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=data.get("detail", "Salary scan failed"),
        )

    # C2: Record usage after successful scan
    if settings.billing_enabled:
        await BillingService.record_usage(db, current_user, "salary_intelligence")

    await db.commit()
    await ic_cache.invalidate_user(current_user.id)

    return SalaryScanResponse(
        status=data.get("status", "completed"),
        estimate=(
            SalaryEstimateResponse.model_validate(data["estimate"])
            if data.get("estimate") else None
        ),
        skill_impacts=[
            SkillSalaryImpactResponse.model_validate(impact)
            for impact in data.get("skill_impacts", [])
        ],
        history_entry_created=data.get("history_entry_created", False),
    )


# ── Salary Estimate ───────────────────────────────────────────


@router.get(
    "/estimate",
    response_model=SalaryEstimateResponse | None,
    summary="Get latest salary estimate",
)
async def get_salary_estimate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryEstimateResponse | None:
    """Latest personalized salary range estimate."""
    estimate = await SalaryIntelligenceService.get_salary_estimate(
        db, user_id=current_user.id,
    )
    if estimate is None:
        return None
    return SalaryEstimateResponse.model_validate(estimate)


# ── Skill Impacts ─────────────────────────────────────────────


@router.get(
    "/impacts",
    response_model=SalaryImpactAnalysisResponse,
    summary="Get per-skill salary impact analysis",
)
async def get_skill_impacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryImpactAnalysisResponse:
    """Breakdown of each skill's contribution to salary (Skill Premium Mapping™)."""
    impacts = await SalaryIntelligenceService.get_skill_impacts(
        db, user_id=current_user.id,
    )
    impact_responses = [
        SkillSalaryImpactResponse.model_validate(impact)
        for impact in impacts
    ]

    total_amount = sum(
        impact.salary_impact_amount for impact in impact_responses
    )
    total_percent = sum(
        impact.salary_impact_percent for impact in impact_responses
    )
    top_positive = [
        impact.skill_name for impact in impact_responses
        if impact.impact_direction == "positive"
    ][:5]
    top_negative = [
        impact.skill_name for impact in impact_responses
        if impact.impact_direction == "negative"
    ][:3]

    return SalaryImpactAnalysisResponse(
        impacts=impact_responses,
        total_premium_amount=round(total_amount, 2),
        total_premium_percent=round(total_percent, 2),
        top_positive_skills=top_positive,
        top_negative_skills=top_negative,
    )


# ── Trajectory ─────────────────────────────────────────────────


@router.get(
    "/trajectory",
    response_model=SalaryTrajectoryResponse,
    summary="Get historical salary trajectory",
)
async def get_salary_trajectory(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryTrajectoryResponse:
    """Historical salary timeline with projections."""
    data: dict[str, Any] = await SalaryIntelligenceService.get_salary_trajectory(
        db, user_id=current_user.id,
    )
    return SalaryTrajectoryResponse(**data)


# ── Scenarios ──────────────────────────────────────────────────


@router.get(
    "/scenarios",
    response_model=list[SalaryScenarioResponse],
    summary="List previous salary scenarios",
)
async def list_salary_scenarios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SalaryScenarioResponse]:
    """List all saved what-if salary scenarios."""
    scenarios = await SalaryIntelligenceService.get_scenarios(
        db, user_id=current_user.id,
    )
    return [
        SalaryScenarioResponse.model_validate(scenario)
        for scenario in scenarios
    ]


@router.post(
    "/scenarios",
    response_model=SalaryScenarioResponse,
    summary="Run a what-if salary scenario",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_career_dna)
async def run_salary_scenario(
    request: Request,
    body: SalaryScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryScenarioResponse:
    """Simulate a salary change scenario (add skill, move location, etc.)."""
    scenario = await SalaryIntelligenceService.run_scenario(
        db,
        user_id=current_user.id,
        scenario_type=body.scenario_type,
        scenario_label=body.scenario_label,
        scenario_input=body.scenario_input,
    )

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salary scan required before running scenarios. "
            "Call POST /salary-intelligence/scan first.",
        )

    return SalaryScenarioResponse.model_validate(scenario)


@router.get(
    "/scenarios/{scenario_id}",
    response_model=SalaryScenarioResponse,
    summary="Get a specific scenario",
)
async def get_salary_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryScenarioResponse:
    """Retrieve details of a saved what-if scenario."""
    scenario = await SalaryIntelligenceService.get_scenario_by_id(
        db, user_id=current_user.id, scenario_id=scenario_id,
    )
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    return SalaryScenarioResponse.model_validate(scenario)


# ── Quick What-If Shortcuts ────────────────────────────────────


@router.post(
    "/what-if/skill",
    response_model=SalaryScenarioResponse,
    summary="Quick what-if: add a skill",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_career_dna)
async def what_if_add_skill(
    request: Request,
    body: SkillWhatIfRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryScenarioResponse:
    """Shortcut: 'What would my salary be if I added skill X?'"""
    scenario = await SalaryIntelligenceService.run_scenario(
        db,
        user_id=current_user.id,
        scenario_type="add_skill",
        scenario_label=f"What if I learn {body.skill_name}?",
        scenario_input={"skill": body.skill_name},
    )

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salary scan required before running scenarios.",
        )

    return SalaryScenarioResponse.model_validate(scenario)


@router.post(
    "/what-if/location",
    response_model=SalaryScenarioResponse,
    summary="Quick what-if: change location",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_career_dna)
async def what_if_change_location(
    request: Request,
    body: LocationWhatIfRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryScenarioResponse:
    """Shortcut: 'What would my salary be if I moved to location Y?'"""
    scenario = await SalaryIntelligenceService.run_scenario(
        db,
        user_id=current_user.id,
        scenario_type="change_location",
        scenario_label=f"What if I move to {body.location}?",
        scenario_input={"location": body.location},
    )

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salary scan required before running scenarios.",
        )

    return SalaryScenarioResponse.model_validate(scenario)


# ── Preferences ────────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=SalaryPreferenceResponse | None,
    summary="Get salary tracking preferences",
)
async def get_salary_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryPreferenceResponse | None:
    """Get user's salary intelligence configuration."""
    preference = await SalaryIntelligenceService.get_preferences(
        db, user_id=current_user.id,
    )
    if preference is None:
        return None
    return SalaryPreferenceResponse.model_validate(preference)


@router.put(
    "/preferences",
    response_model=SalaryPreferenceResponse,
    summary="Update salary tracking preferences",
)
async def update_salary_preferences(
    body: SalaryPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalaryPreferenceResponse:
    """Update salary intelligence configuration (partial update)."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        preference = await SalaryIntelligenceService.update_preferences(
            db, user_id=current_user.id, updates=updates,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SalaryPreferenceResponse.model_validate(preference)
