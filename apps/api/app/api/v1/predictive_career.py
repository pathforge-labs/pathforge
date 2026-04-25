"""
PathForge — Predictive Career Engine™ API Routes
==================================================
REST API endpoints for predictive career intelligence.

Endpoints:
    POST /emerging-roles             — Detect emerging roles
    POST /disruption-forecasts       — Predict disruptions
    POST /opportunity-surfaces       — Surface opportunities
    POST /career-forecast            — Get Career Forecast Index™
    GET  /dashboard                  — Aggregated dashboard
    POST /scan                       — Full predictive scan
    GET  /preferences                — Get user PC preferences
    PUT  /preferences                — Update user PC preferences
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.feature_gate import require_feature
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.predictive_career import (
    CareerForecastResponse,
    DisruptionForecastRequest,
    DisruptionForecastResponse,
    EmergingRoleRequest,
    EmergingRoleResponse,
    OpportunitySurfaceRequest,
    OpportunitySurfaceResponse,
    PredictiveCareerDashboardResponse,
    PredictiveCareerPreferenceResponse,
    PredictiveCareerPreferenceUpdate,
    PredictiveCareerScanRequest,
    PredictiveScanResponse,
)
from app.services import predictive_career_service as pc_service
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predictive-career",
    tags=["Predictive Career Engine™"],
)


# ── Emerging Role Radar™ ──────────────────────────────────────


@router.post(
    "/emerging-roles",
    response_model=list[EmergingRoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Detect emerging roles",
    description=(
        "Emerging Role Radar™ — AI-powered detection of nascent "
        "and growing roles that match your Career DNA skill set, "
        "before they appear on mainstream job boards."
    ),
    dependencies=[Depends(require_feature("predictive_career"))],
)
@limiter.limit(settings.rate_limit_career_dna)
async def scan_emerging_roles(
    request: Request,
    body: EmergingRoleRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[EmergingRoleResponse]:
    """Detect emerging roles matching user.

    Sprint 38 C1/C2/C5: Feature gating + scan limit + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(database, current_user, "predictive_career")

    try:
        roles = await pc_service.scan_emerging_roles(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
            min_skill_overlap_pct=body.min_skill_overlap_pct,
        )

        # C2: Record usage after successful scan
        if settings.billing_enabled:
            await BillingService.record_usage(database, current_user, "predictive_career")

        return [
            EmergingRoleResponse.model_validate(role)
            for role in roles
        ]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Disruption Forecast Engine™ ──────────────────────────────


@router.post(
    "/disruption-forecasts",
    response_model=list[DisruptionForecastResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Predict disruptions",
    description=(
        "Disruption Forecast Engine™ — AI-powered prediction of "
        "industry and technology disruptions that may impact your "
        "career trajectory, with severity and timeline estimates."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def get_disruption_forecasts(
    request: Request,
    body: DisruptionForecastRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[DisruptionForecastResponse]:
    """Predict disruptions affecting user."""
    try:
        forecasts = await pc_service.get_disruption_forecasts(
            database,
            user_id=current_user.id,
            industry=body.industry,
            forecast_horizon_months=body.forecast_horizon_months,
        )
        return [
            DisruptionForecastResponse.model_validate(forecast)
            for forecast in forecasts
        ]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Opportunity Surfacing ────────────────────────────────────


@router.post(
    "/opportunity-surfaces",
    response_model=list[OpportunitySurfaceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Surface opportunities",
    description=(
        "Proactive Opportunity Engine™ — identifies career "
        "opportunities before they become obvious, by combining "
        "skill adjacency, market signals, and Career DNA context."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def get_opportunity_surfaces(
    request: Request,
    body: OpportunitySurfaceRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[OpportunitySurfaceResponse]:
    """Surface proactive career opportunities."""
    try:
        opportunities = await pc_service.get_opportunity_surfaces(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
            include_cross_border=body.include_cross_border,
        )
        return [
            OpportunitySurfaceResponse.model_validate(opp)
            for opp in opportunities
        ]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Career Forecast Index™ ───────────────────────────────────


@router.post(
    "/career-forecast",
    response_model=CareerForecastResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compute Career Forecast Index™",
    description=(
        "Career Forecast Index™ — a composite forward-looking "
        "score (0-100) reflecting predicted career trajectory. "
        "No competitor offers this metric."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def get_career_forecast(
    request: Request,
    body: PredictiveCareerScanRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerForecastResponse:
    """Compute Career Forecast Index™."""
    try:
        forecast = await pc_service.get_career_forecast(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
            forecast_horizon_months=body.forecast_horizon_months,
        )
        return CareerForecastResponse.model_validate(forecast)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Dashboard ────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=PredictiveCareerDashboardResponse,
    summary="Get Predictive Career dashboard",
    description=(
        "Aggregated dashboard with latest Career Forecast, "
        "emerging roles, disruption forecasts, opportunity "
        "surfaces, and preferences."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PredictiveCareerDashboardResponse:
    """Get aggregated Predictive Career dashboard."""
    try:
        data = await pc_service.get_pc_dashboard(
            database, user_id=current_user.id,
        )
        return PredictiveCareerDashboardResponse(
            latest_forecast=(
                CareerForecastResponse.model_validate(
                    data["latest_forecast"],
                )
                if data["latest_forecast"] else None
            ),
            emerging_roles=[
                EmergingRoleResponse.model_validate(role)
                for role in data["emerging_roles"]
            ],
            disruption_forecasts=[
                DisruptionForecastResponse.model_validate(forecast)
                for forecast in data["disruption_forecasts"]
            ],
            opportunity_surfaces=[
                OpportunitySurfaceResponse.model_validate(opp)
                for opp in data["opportunity_surfaces"]
            ],
            preferences=(
                PredictiveCareerPreferenceResponse.model_validate(
                    data["preferences"],
                )
                if data["preferences"] else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Full Predictive Scan ─────────────────────────────────────


@router.post(
    "/scan",
    response_model=PredictiveScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run full predictive scan",
    description=(
        "Execute a comprehensive predictive scan: emerging roles, "
        "disruption forecasts, opportunity surfaces, and Career "
        "Forecast Index™ — all in one request."
    ),
)
@limiter.limit("2/minute")
async def run_scan(
    request: Request,
    body: PredictiveCareerScanRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PredictiveScanResponse:
    """Execute full predictive scan."""
    try:
        data = await pc_service.run_predictive_scan(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
            forecast_horizon_months=body.forecast_horizon_months,
        )
        return PredictiveScanResponse(
            career_forecast=(
                CareerForecastResponse.model_validate(
                    data["career_forecast"],
                )
                if data["career_forecast"] else None
            ),
            emerging_roles=[
                EmergingRoleResponse.model_validate(role)
                for role in data["emerging_roles"]
            ],
            disruption_forecasts=[
                DisruptionForecastResponse.model_validate(forecast)
                for forecast in data["disruption_forecasts"]
            ],
            opportunity_surfaces=[
                OpportunitySurfaceResponse.model_validate(opp)
                for opp in data["opportunity_surfaces"]
            ],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Preferences ──────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=PredictiveCareerPreferenceResponse,
    summary="Get PC preferences",
    description="Get current Predictive Career Engine preferences.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PredictiveCareerPreferenceResponse:
    """Get user PC preferences."""
    try:
        preference = await pc_service.get_or_update_preferences(
            database, user_id=current_user.id,
        )
        return PredictiveCareerPreferenceResponse.model_validate(
            preference,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/preferences",
    response_model=PredictiveCareerPreferenceResponse,
    summary="Update PC preferences",
    description=(
        "Update Predictive Career Engine preferences such as "
        "forecast horizon, risk tolerance, focus industries, "
        "and module selections."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_preferences(
    request: Request,
    body: PredictiveCareerPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PredictiveCareerPreferenceResponse:
    """Update user PC preferences."""
    try:
        preference = await pc_service.get_or_update_preferences(
            database,
            user_id=current_user.id,
            updates=body.model_dump(exclude_unset=True),
        )
        return PredictiveCareerPreferenceResponse.model_validate(
            preference,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
