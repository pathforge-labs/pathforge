"""
PathForge API — Career Threat Radar™ Routes
===============================================
REST endpoints for the Career Threat Radar™ system.

10 endpoints covering:
    - Overview dashboard (get full threat radar state)
    - Threat scan (trigger comprehensive analysis)
    - Automation risk (get latest ONET + LLM score)
    - Skills Shield™ matrix (shield vs exposure breakdown)
    - Resilience score (CRS™ + Career Moat Score)
    - Alerts (list, update status)
    - Preferences (get, update)
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.database import get_db
from app.core.intelligence_cache import ic_cache
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.threat_radar import (
    AlertPreferenceResponse,
    AlertPreferenceUpdateRequest,
    AutomationRiskResponse,
    CareerResilienceResponse,
    IndustryTrendResponse,
    SkillShieldEntryResponse,
    SkillShieldMatrixResponse,
    ThreatAlertListResponse,
    ThreatAlertResponse,
    ThreatAlertUpdateRequest,
    ThreatRadarOverviewResponse,
    ThreatRadarScanResponse,
)
from app.services.billing_service import BillingService
from app.services.threat_radar_service import ThreatRadarService

if TYPE_CHECKING:
    from app.models.threat_radar import (
        AlertPreference,
        AutomationRisk,
        CareerResilienceSnapshot,
        IndustryTrend,
        SkillShieldEntry,
        ThreatAlert,
    )

router = APIRouter(prefix="/threat-radar", tags=["Career Threat Radar™"])


# ── Overview ───────────────────────────────────────────────────


@router.get(
    "",
    response_model=ThreatRadarOverviewResponse,
    summary="Get full Threat Radar dashboard",
)
@route_query_budget(max_queries=4)
async def get_threat_radar_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreatRadarOverviewResponse:
    """Full Career Threat Radar™ dashboard with all components."""
    cache_key = ic_cache.key(current_user.id, "threat_radar_overview")
    cached = await ic_cache.get(cache_key)
    if cached is not None:
        return ThreatRadarOverviewResponse.model_validate(cached)

    data = await ThreatRadarService.get_overview(
        db,
        user_id=current_user.id,
    )

    if not data:
        return ThreatRadarOverviewResponse()

    result = ThreatRadarOverviewResponse(
        resilience=(_resilience_response(data["snapshot"]) if data.get("snapshot") else None),
        automation_risk=(
            _risk_response(data["automation_risk"]) if data.get("automation_risk") else None
        ),
        skills_shield=(_build_shield_matrix(data.get("shield_entries", []))),
        industry_trends=[_trend_response(trend) for trend in data.get("industry_trends", [])],
        recent_alerts=[_alert_response(alert) for alert in data.get("recent_alerts", [])],
        total_unread_alerts=data.get("total_unread_alerts", 0),
    )
    await ic_cache.set(cache_key, result.model_dump(mode="json"), ttl=ic_cache.TTL_THREAT_RADAR)
    return result


# ── Full Scan ──────────────────────────────────────────────────


@router.post(
    "/scan",
    response_model=ThreatRadarScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger comprehensive threat scan",
)
@limiter.limit(settings.rate_limit_career_dna)
@route_query_budget(max_queries=4)
async def trigger_threat_scan(
    request: Request,
    soc_code: str = Query(
        ...,
        description="ONET SOC code (e.g. '15-1252.00')",
    ),
    industry_name: str = Query(
        ...,
        description="Primary industry (e.g. 'Technology')",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreatRadarScanResponse:
    """Execute full Career Threat Radar™ analysis pipeline.

    Sprint 38 C2/C5: Scan limit enforcement + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(db, current_user, "threat_radar")

    result = await ThreatRadarService.run_full_scan(
        db,
        user_id=current_user.id,
        soc_code=soc_code,
        industry_name=industry_name,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("detail", "Career DNA profile required"),
        )

    # C2: Record usage after successful scan
    if settings.billing_enabled:
        await BillingService.record_usage(db, current_user, "threat_radar")

    await db.commit()
    await ic_cache.invalidate_user(current_user.id)

    return ThreatRadarScanResponse(
        status="completed",
        automation_risk=(
            _risk_response(result["automation_risk"]) if result.get("automation_risk") else None
        ),
        industry_trends=[
            _trend_response(result["industry_trend"]),
        ]
        if result.get("industry_trend")
        else [],
        skills_shield=(_build_shield_matrix(result.get("shield_entries", []))),
        resilience=(_resilience_response(result["snapshot"]) if result.get("snapshot") else None),
        alerts_generated=result.get("alerts_generated", 0),
    )


# ── Automation Risk ────────────────────────────────────────────


@router.get(
    "/automation-risk",
    response_model=AutomationRiskResponse | None,
    summary="Get latest automation risk assessment",
)
@route_query_budget(max_queries=4)
async def get_automation_risk(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutomationRiskResponse | None:
    """Latest ONET + LLM hybrid automation risk score."""
    data = await ThreatRadarService.get_overview(
        db,
        user_id=current_user.id,
    )
    risk = data.get("automation_risk") if data else None
    return _risk_response(risk) if risk else None


# ── Skills Shield™ ─────────────────────────────────────────────


@router.get(
    "/skills-shield",
    response_model=SkillShieldMatrixResponse,
    summary="Get Skills Shield™ matrix",
)
@route_query_budget(max_queries=4)
async def get_skills_shield(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillShieldMatrixResponse:
    """Skills classified as shields, exposures, or neutral."""
    data = await ThreatRadarService.get_overview(
        db,
        user_id=current_user.id,
    )
    entries = data.get("shield_entries", []) if data else []
    return _build_shield_matrix(entries)


# ── Resilience Score ───────────────────────────────────────────


@router.get(
    "/resilience",
    response_model=CareerResilienceResponse | None,
    summary="Get Career Resilience Score™ and Moat Score",
)
@route_query_budget(max_queries=4)
async def get_resilience_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerResilienceResponse | None:
    """CRS™ (5-factor) + Career Moat Score (4-dimension)."""
    data = await ThreatRadarService.get_overview(
        db,
        user_id=current_user.id,
    )
    snapshot = data.get("snapshot") if data else None
    return _resilience_response(snapshot) if snapshot else None


# ── Resilience History (Sprint 36 WS-5) ────────────────────────


@router.get(
    "/resilience/history",
    summary="Get Career Resilience Score™ historical data",
)
@limiter.limit("20/minute")
@route_query_budget(max_queries=4)
async def get_resilience_history(
    request: Request,
    days: int = Query(90, ge=7, le=365, description="History period in days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Historical resilience scores for trend visualization."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.models.career_dna import CareerDNA
    from app.models.threat_radar import CareerResilienceSnapshot

    # Get user's Career DNA
    career_dna_stmt = select(CareerDNA.id).where(
        CareerDNA.user_id == current_user.id,
    )
    career_dna_result = await db.execute(career_dna_stmt)
    career_dna_id = career_dna_result.scalar_one_or_none()

    if career_dna_id is None:
        return {"data": [], "period_days": days}

    # Query historical snapshots
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    history_stmt = (
        select(CareerResilienceSnapshot)
        .where(
            CareerResilienceSnapshot.career_dna_id == career_dna_id,
            CareerResilienceSnapshot.computed_at >= cutoff,
        )
        .order_by(CareerResilienceSnapshot.computed_at.asc())
    )
    history_result = await db.execute(history_stmt)
    snapshots = history_result.scalars().all()

    # Build data points with delta
    data_points: list[dict[str, Any]] = []
    previous_score: float | None = None

    for snapshot in snapshots:
        score = float(snapshot.overall_score)
        delta = round(score - previous_score, 1) if previous_score is not None else 0.0
        data_points.append(
            {
                "date": snapshot.computed_at.isoformat(),
                "score": round(score, 1),
                "delta": delta,
            }
        )
        previous_score = score

    return {"data": data_points, "period_days": days}


# ── Alerts ─────────────────────────────────────────────────────


@router.get(
    "/alerts",
    response_model=ThreatAlertListResponse,
    summary="Get threat alert feed",
)
@route_query_budget(max_queries=4)
async def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    alert_status: str | None = Query(
        None,
        description="Filter by status: unread, read, dismissed, snoozed",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreatAlertListResponse:
    """Paginated threat alert feed with optional status filtering."""
    result = await ThreatRadarService.get_alerts(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=alert_status,
    )
    return ThreatAlertListResponse(
        alerts=[_alert_response(alert) for alert in result["alerts"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.patch(
    "/alerts/{alert_id}",
    response_model=ThreatAlertResponse,
    summary="Update alert status",
)
@route_query_budget(max_queries=4)
async def update_alert(
    alert_id: uuid.UUID,
    payload: ThreatAlertUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreatAlertResponse:
    """Mark alert as read, dismissed, snoozed, or acted on."""
    alert = await ThreatRadarService.update_alert_status(
        db,
        user_id=current_user.id,
        alert_id=alert_id,
        new_status=payload.status,
        snoozed_until=payload.snoozed_until,
    )
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )
    await db.commit()
    await ic_cache.invalidate_user(current_user.id)
    return _alert_response(alert)


# ── Preferences ────────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=AlertPreferenceResponse | None,
    summary="Get alert notification preferences",
)
@route_query_budget(max_queries=4)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertPreferenceResponse | None:
    """User's alert notification preferences."""
    pref = await ThreatRadarService.get_preferences(
        db,
        user_id=current_user.id,
    )
    return _pref_response(pref) if pref else None


@router.put(
    "/preferences",
    response_model=AlertPreferenceResponse,
    summary="Update alert notification preferences",
)
@route_query_budget(max_queries=4)
async def update_preferences(
    payload: AlertPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertPreferenceResponse:
    """Update or create alert notification preferences."""
    pref = await ThreatRadarService.update_preferences(
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


def _risk_response(risk: AutomationRisk) -> AutomationRiskResponse:
    """Convert ORM AutomationRisk to response schema."""
    return AutomationRiskResponse(
        id=risk.id,
        onet_soc_code=risk.onet_soc_code,
        onet_occupation_title=risk.onet_occupation_title,
        base_automation_probability=risk.base_automation_probability,
        contextual_risk_score=risk.contextual_risk_score,
        risk_level=risk.risk_level,
        vulnerable_tasks=risk.vulnerable_tasks,
        resilient_tasks=risk.resilient_tasks,
        recommended_skills=risk.recommended_skills,
        analysis_reasoning=risk.analysis_reasoning,
        opportunity_inversions=risk.opportunity_inversions,
        analyzed_at=risk.analyzed_at,
    )


def _trend_response(trend: IndustryTrend) -> IndustryTrendResponse:
    """Convert ORM IndustryTrend to response schema."""
    return IndustryTrendResponse(
        id=trend.id,
        industry_name=trend.industry_name,
        trend_direction=trend.trend_direction,
        confidence=trend.confidence,
        key_signals=trend.key_signals,
        impact_on_user=trend.impact_on_user,
        recommended_actions=trend.recommended_actions,
        data_sources=trend.data_sources,
        analyzed_at=trend.analyzed_at,
    )


def _shield_entry_response(
    entry: SkillShieldEntry,
) -> SkillShieldEntryResponse:
    """Convert ORM SkillShieldEntry to response schema."""
    return SkillShieldEntryResponse(
        id=entry.id,
        skill_name=entry.skill_name,
        classification=entry.classification,
        automation_resistance=entry.automation_resistance,
        market_demand_trend=entry.market_demand_trend,
        reasoning=entry.reasoning,
        improvement_path=entry.improvement_path,
    )


def _build_shield_matrix(
    entries: list[SkillShieldEntry],
) -> SkillShieldMatrixResponse:
    """Build the Skills Shield™ matrix response."""
    shields = []
    exposures = []
    neutrals = []

    for entry in entries:
        response = _shield_entry_response(entry)
        if entry.classification == "shield":
            shields.append(response)
        elif entry.classification == "exposure":
            exposures.append(response)
        else:
            neutrals.append(response)

    total = len(entries)
    moat_pct = (len(shields) / max(1, total)) * 100.0

    return SkillShieldMatrixResponse(
        shields=shields,
        exposures=exposures,
        neutrals=neutrals,
        total_skills=total,
        moat_strength_pct=round(moat_pct, 1),
    )


def _resilience_response(
    snapshot: CareerResilienceSnapshot,
) -> CareerResilienceResponse:
    """Convert ORM snapshot to response schema."""
    return CareerResilienceResponse(
        id=snapshot.id,
        overall_score=snapshot.overall_score,
        skill_diversity_index=snapshot.skill_diversity_index,
        automation_resistance=snapshot.automation_resistance,
        growth_velocity=snapshot.growth_velocity,
        industry_stability=snapshot.industry_stability,
        adaptability_signal=snapshot.adaptability_signal,
        moat_score=snapshot.moat_score,
        moat_strength=snapshot.moat_strength,
        explanation=snapshot.explanation,
        improvement_actions=snapshot.improvement_actions,
        computed_at=snapshot.computed_at,
    )


def _alert_response(alert: ThreatAlert) -> ThreatAlertResponse:
    """Convert ORM ThreatAlert to response schema."""
    return ThreatAlertResponse(
        id=alert.id,
        category=alert.category,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        opportunity=alert.opportunity,
        evidence=alert.evidence,
        channel=alert.channel,
        status=alert.status,
        snoozed_until=alert.snoozed_until,
        read_at=alert.read_at,
        created_at=alert.created_at,
    )


def _pref_response(pref: AlertPreference) -> AlertPreferenceResponse:
    """Convert ORM AlertPreference to response schema."""
    return AlertPreferenceResponse(
        id=pref.id,
        enabled_categories=pref.enabled_categories,
        min_severity=pref.min_severity,
        enabled_channels=pref.enabled_channels,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
    )
