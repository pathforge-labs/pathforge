"""
PathForge API — Skill Decay & Growth Tracker Routes
======================================================
REST endpoints for the Skill Decay & Growth Tracker system.

9 endpoints covering:
    - Dashboard (get full skill decay state)
    - Full scan (trigger comprehensive analysis)
    - Freshness scores (per-skill freshness)
    - Market demand (demand + trend data)
    - Velocity map (composite velocity)
    - Reskilling pathways (personalized learning paths)
    - Skill refresh (manual freshness reset)
    - Preferences (get, update)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_gate import require_feature
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.skill_decay import (
    MarketDemandSnapshotResponse,
    ReskillingPathwayResponse,
    SkillDecayDashboardResponse,
    SkillDecayPreferenceResponse,
    SkillDecayPreferenceUpdateRequest,
    SkillDecayScanResponse,
    SkillFreshnessResponse,
    SkillRefreshRequest,
    SkillVelocityEntryResponse,
)
from app.core.intelligence_cache import ic_cache
from app.services.billing_service import BillingService
from app.services.skill_decay_service import SkillDecayService

if TYPE_CHECKING:
    from app.models.skill_decay import (
        MarketDemandSnapshot,
        ReskillingPathway,
        SkillDecayPreference,
        SkillFreshness,
        SkillVelocityEntry,
    )

router = APIRouter(prefix="/skill-decay", tags=["Skill Decay & Growth Tracker"])


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "",
    response_model=SkillDecayDashboardResponse,
    summary="Get full Skill Decay dashboard",
)
async def get_skill_decay_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillDecayDashboardResponse:
    """Full Skill Decay & Growth Tracker dashboard with all components."""
    cache_key = ic_cache.key(current_user.id, "skill_decay_dashboard")
    cached = await ic_cache.get(cache_key)
    if cached is not None:
        return SkillDecayDashboardResponse.model_validate(cached)

    data = await SkillDecayService.get_dashboard(
        db, user_id=current_user.id,
    )

    if not data:
        return SkillDecayDashboardResponse(
            freshness=[],
            freshness_summary={
                "total_skills": 0,
                "average_freshness": 0.0,
                "skills_at_risk": 0,
                "freshest_skill": None,
                "stalest_skill": None,
            },
            market_demand=[],
            velocity=[],
            reskilling_pathways=[],
        )

    result = SkillDecayDashboardResponse(
        freshness=[
            _freshness_response(entry)
            for entry in data.get("freshness", [])
        ],
        freshness_summary=data.get("freshness_summary", {}),
        market_demand=[
            _demand_response(entry)
            for entry in data.get("market_demand", [])
        ],
        velocity=[
            _velocity_response(entry)
            for entry in data.get("velocity", [])
        ],
        reskilling_pathways=[
            _pathway_response(entry)
            for entry in data.get("reskilling_pathways", [])
        ],
        preference=(
            _pref_response(data["preference"])
            if data.get("preference") else None
        ),
        last_scan_at=data.get("last_scan_at"),
    )
    await ic_cache.set(cache_key, result.model_dump(mode="json"), ttl=ic_cache.TTL_SKILL_DECAY)
    return result


# ── Full Scan ──────────────────────────────────────────────────


@router.post(
    "/scan",
    response_model=SkillDecayScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger comprehensive skill decay scan",
    dependencies=[Depends(require_feature("skill_decay"))],
)
@limiter.limit(settings.rate_limit_career_dna)
async def trigger_skill_decay_scan(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillDecayScanResponse:
    """Execute full Skill Decay & Growth Tracker analysis pipeline.

    Sprint 38 C1/C2/C5: Feature gating + scan limit + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(db, current_user, "skill_decay")

    result = await SkillDecayService.run_full_scan(
        db,
        user_id=current_user.id,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("detail", "Career DNA profile required"),
        )

    # C2: Record usage after successful scan
    if settings.billing_enabled:
        await BillingService.record_usage(db, current_user, "skill_decay")

    await db.commit()
    await ic_cache.invalidate_user(current_user.id)

    return SkillDecayScanResponse(
        status="completed",
        skills_analyzed=result.get("skills_analyzed", 0),
        freshness=[
            _freshness_response(entry)
            for entry in result.get("freshness", [])
        ],
        market_demand=[
            _demand_response(entry)
            for entry in result.get("market_demand", [])
        ],
        velocity=[
            _velocity_response(entry)
            for entry in result.get("velocity", [])
        ],
        reskilling_pathways=[
            _pathway_response(entry)
            for entry in result.get("reskilling_pathways", [])
        ],
    )


# ── Freshness Scores ──────────────────────────────────────────


@router.get(
    "/freshness",
    response_model=list[SkillFreshnessResponse],
    summary="Get skill freshness scores",
)
async def get_freshness_scores(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkillFreshnessResponse]:
    """Per-skill freshness scores with exponential decay + contextual analysis."""
    entries = await SkillDecayService.get_freshness_scores(
        db, user_id=current_user.id,
    )
    return [_freshness_response(entry) for entry in entries]


# ── Market Demand ──────────────────────────────────────────────


@router.get(
    "/market-demand",
    response_model=list[MarketDemandSnapshotResponse],
    summary="Get market demand snapshots",
)
async def get_market_demand(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MarketDemandSnapshotResponse]:
    """Per-skill market demand scores with trend projections."""
    entries = await SkillDecayService.get_market_demand(
        db, user_id=current_user.id,
    )
    return [_demand_response(entry) for entry in entries]


# ── Velocity Map ───────────────────────────────────────────────


@router.get(
    "/velocity",
    response_model=list[SkillVelocityEntryResponse],
    summary="Get skill velocity map",
)
async def get_velocity_map(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkillVelocityEntryResponse]:
    """Composite velocity map combining freshness and demand signals."""
    entries = await SkillDecayService.get_velocity_map(
        db, user_id=current_user.id,
    )
    return [_velocity_response(entry) for entry in entries]


# ── Reskilling Pathways ───────────────────────────────────────


@router.get(
    "/reskilling",
    response_model=list[ReskillingPathwayResponse],
    summary="Get personalized reskilling pathways",
)
async def get_reskilling_pathways(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReskillingPathwayResponse]:
    """Prioritized reskilling pathways: critical → recommended → optional."""
    entries = await SkillDecayService.get_reskilling_paths(
        db, user_id=current_user.id,
    )
    return [_pathway_response(entry) for entry in entries]


# ── Skill Refresh ─────────────────────────────────────────────


@router.post(
    "/refresh",
    response_model=SkillFreshnessResponse,
    summary="Manually refresh a skill",
)
async def refresh_skill(
    payload: SkillRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillFreshnessResponse:
    """Mark a skill as refreshed (reset freshness to 100)."""
    entry = await SkillDecayService.refresh_skill(
        db,
        user_id=current_user.id,
        skill_name=payload.skill_name,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{payload.skill_name}' not found in freshness data.",
        )
    await db.commit()
    await ic_cache.invalidate_user(current_user.id)
    return _freshness_response(entry)


# ── Preferences ────────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=SkillDecayPreferenceResponse | None,
    summary="Get skill decay tracking preferences",
)
async def get_decay_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillDecayPreferenceResponse | None:
    """User's skill decay tracking and notification preferences."""
    pref = await SkillDecayService.get_preferences(
        db, user_id=current_user.id,
    )
    return _pref_response(pref) if pref else None


@router.put(
    "/preferences",
    response_model=SkillDecayPreferenceResponse,
    summary="Update skill decay tracking preferences",
)
async def update_decay_preferences(
    payload: SkillDecayPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillDecayPreferenceResponse:
    """Update or create skill decay tracking preferences."""
    pref = await SkillDecayService.update_preferences(
        db,
        user_id=current_user.id,
        updates=payload.model_dump(exclude_unset=True),
    )
    if pref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career DNA profile required.",
        )
    await db.commit()
    return _pref_response(pref)


# ── Response Builders ──────────────────────────────────────────


def _freshness_response(
    entry: SkillFreshness,
) -> SkillFreshnessResponse:
    """Convert ORM SkillFreshness to response schema."""
    return SkillFreshnessResponse(
        id=entry.id,
        skill_name=entry.skill_name,
        category=entry.category,
        last_active_date=entry.last_active_date,
        freshness_score=entry.freshness_score,
        half_life_days=entry.half_life_days,
        decay_rate=entry.decay_rate,
        days_since_active=entry.days_since_active,
        refresh_urgency=entry.refresh_urgency,
        analysis_reasoning=entry.analysis_reasoning,
        computed_at=entry.computed_at,
    )


def _demand_response(
    entry: MarketDemandSnapshot,
) -> MarketDemandSnapshotResponse:
    """Convert ORM MarketDemandSnapshot to response schema."""
    return MarketDemandSnapshotResponse(
        id=entry.id,
        skill_name=entry.skill_name,
        demand_score=entry.demand_score,
        demand_trend=entry.demand_trend,
        trend_confidence=entry.trend_confidence,
        job_posting_signal=entry.job_posting_signal,
        industry_relevance=entry.industry_relevance,
        growth_projection_6m=entry.growth_projection_6m,
        growth_projection_12m=entry.growth_projection_12m,
        data_sources=entry.data_sources,
        snapshot_date=entry.snapshot_date,
    )


def _velocity_response(
    entry: SkillVelocityEntry,
) -> SkillVelocityEntryResponse:
    """Convert ORM SkillVelocityEntry to response schema."""
    return SkillVelocityEntryResponse(
        id=entry.id,
        skill_name=entry.skill_name,
        velocity_score=entry.velocity_score,
        velocity_direction=entry.velocity_direction,
        freshness_component=entry.freshness_component,
        demand_component=entry.demand_component,
        composite_health=entry.composite_health,
        acceleration=entry.acceleration,
        reasoning=entry.reasoning,
        computed_at=entry.computed_at,
    )


def _pathway_response(
    entry: ReskillingPathway,
) -> ReskillingPathwayResponse:
    """Convert ORM ReskillingPathway to response schema."""
    return ReskillingPathwayResponse(
        id=entry.id,
        target_skill=entry.target_skill,
        current_level=entry.current_level,
        target_level=entry.target_level,
        priority=entry.priority,
        rationale=entry.rationale,
        estimated_effort_hours=entry.estimated_effort_hours,
        prerequisite_skills=entry.prerequisite_skills,
        learning_resources=entry.learning_resources,
        career_impact=entry.career_impact,
        freshness_gain=entry.freshness_gain,
        demand_alignment=entry.demand_alignment,
        created_at=entry.created_at,
    )


def _pref_response(
    pref: SkillDecayPreference,
) -> SkillDecayPreferenceResponse:
    """Convert ORM SkillDecayPreference to response schema."""
    return SkillDecayPreferenceResponse(
        id=pref.id,
        tracking_enabled=pref.tracking_enabled,
        notification_frequency=pref.notification_frequency,
        decay_alert_threshold=pref.decay_alert_threshold,
        focus_categories=pref.focus_categories,
        excluded_skills=pref.excluded_skills,
    )
