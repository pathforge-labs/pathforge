"""
PathForge API v1 — Hidden Job Market Detector™ Endpoints
==========================================================
REST endpoints for the Hidden Job Market Detector.

11 endpoints at /api/v1/hidden-job-market:
    GET    /dashboard           — Dashboard: all signals + preferences + stats
    POST   /scan/company        — Scan a company for growth signals
    POST   /scan/industry       — Scan an industry for growth signals
    GET    /preferences         — Get monitoring preferences
    PUT    /preferences         — Update monitoring preferences
    POST   /compare             — Compare signals side-by-side
    GET    /opportunities       — Aggregated opportunity radar
    POST   /opportunities/surface — Surface hidden opportunities
    GET    /{signal_id}         — Signal detail with match + outreach
    POST   /{signal_id}/outreach — Generate outreach template
    POST   /{signal_id}/dismiss  — Dismiss or action a signal
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)

from app.core.config import settings
from app.core.database import get_db
from app.core.feature_gate import require_feature
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.hidden_job_market import (
    CompanySignalResponse,
    CompanySignalSummaryResponse,
    DismissSignalRequest,
    GenerateOutreachRequest,
    HiddenJobMarketDashboardResponse,
    HiddenJobMarketPreferenceResponse,
    HiddenJobMarketPreferenceUpdateRequest,
    OpportunityRadarResponse,
    ScanCompanyRequest,
    ScanIndustryRequest,
    SignalCompareRequest,
    SignalComparisonResponse,
)
from app.services import hidden_job_market_service
from app.services.billing_service import BillingService

router = APIRouter(
    prefix="/hidden-job-market",
    tags=["Hidden Job Market"],
)


# ── Dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=HiddenJobMarketDashboardResponse,
    status_code=HTTP_200_OK,
    summary="Get signal dashboard",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> HiddenJobMarketDashboardResponse:
    """Retrieve all detected signals, preferences, and summary stats."""
    dashboard = await hidden_job_market_service.get_dashboard(
        database, user_id=current_user.id,
    )
    signal_summaries: list[CompanySignalSummaryResponse] = []
    for signal in dashboard["signals"]:
        signal_summaries.append(
            CompanySignalSummaryResponse.model_validate(signal)
        )

    pref_response = None
    if dashboard["preferences"]:
        pref_response = HiddenJobMarketPreferenceResponse.model_validate(
            dashboard["preferences"],
        )

    return HiddenJobMarketDashboardResponse(
        signals=signal_summaries,
        preferences=pref_response,
        total_signals=dashboard["total_signals"],
        active_signals=dashboard["active_signals"],
        matched_signals=dashboard["matched_signals"],
        dismissed_signals=dashboard["dismissed_signals"],
        total_opportunities=dashboard["total_opportunities"],
    )


# ── Scan Company ──────────────────────────────────────────────


@router.post(
    "/scan/company",
    response_model=list[CompanySignalResponse],
    status_code=HTTP_201_CREATED,
    summary="Scan company for signals",
    dependencies=[Depends(require_feature("hidden_job_market"))],
)
@limiter.limit("3/minute")
async def scan_company(
    request: Request,
    body: ScanCompanyRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[CompanySignalResponse]:
    """Scan a specific company for growth and hiring signals."""
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(database, current_user, "hidden_job_market")

    try:
        signals = await hidden_job_market_service.scan_company(
            database,
            user_id=current_user.id,
            company_name=body.company_name,
            industry=body.industry,
            focus_signal_types=body.focus_signal_types,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    # C2: Record usage after successful scan
    if settings.billing_enabled:
        await BillingService.record_usage(database, current_user, "hidden_job_market")


    return [
        CompanySignalResponse.model_validate(signal)
        for signal in signals
    ]


# ── Scan Industry ─────────────────────────────────────────────


@router.post(
    "/scan/industry",
    response_model=list[CompanySignalResponse],
    status_code=HTTP_201_CREATED,
    summary="Scan industry for signals",
)
@limiter.limit("3/minute")
async def scan_industry(
    request: Request,
    body: ScanIndustryRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[CompanySignalResponse]:
    """Scan an industry for growth and hiring signals across companies."""
    # For industry scan, we scan the industry as a "company" context
    try:
        signals = await hidden_job_market_service.scan_company(
            database,
            user_id=current_user.id,
            company_name=f"{body.industry} industry leaders",
            industry=body.industry,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [
        CompanySignalResponse.model_validate(signal)
        for signal in signals
    ]


# ── Preferences ────────────────────────────────────────────────
# NOTE: Must be defined BEFORE /{signal_id} to avoid path collision.


@router.get(
    "/preferences",
    response_model=HiddenJobMarketPreferenceResponse | None,
    status_code=HTTP_200_OK,
    summary="Get monitoring preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> HiddenJobMarketPreferenceResponse | None:
    """Retrieve hidden job market monitoring preferences."""
    preference = await hidden_job_market_service.get_preferences(
        database, user_id=current_user.id,
    )
    if not preference:
        return None
    return HiddenJobMarketPreferenceResponse.model_validate(preference)


@router.put(
    "/preferences",
    response_model=HiddenJobMarketPreferenceResponse,
    status_code=HTTP_200_OK,
    summary="Update monitoring preferences",
)
async def update_preferences(
    body: HiddenJobMarketPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> HiddenJobMarketPreferenceResponse:
    """Update or create monitoring preferences."""
    try:
        preference = await hidden_job_market_service.update_preferences(
            database,
            user_id=current_user.id,
            update_data=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return HiddenJobMarketPreferenceResponse.model_validate(preference)


# ── Compare Signals ───────────────────────────────────────────


@router.post(
    "/compare",
    response_model=SignalComparisonResponse,
    status_code=HTTP_200_OK,
    summary="Compare signals side-by-side",
)
@limiter.limit("3/minute")
async def compare_signals(
    request: Request,
    body: SignalCompareRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> SignalComparisonResponse:
    """Compare multiple detected signals side-by-side."""
    try:
        comparison = await hidden_job_market_service.compare_signals(
            database,
            user_id=current_user.id,
            signal_ids=body.signal_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    signal_responses = [
        CompanySignalResponse.model_validate(signal)
        for signal in comparison["signals"]
    ]

    return SignalComparisonResponse(
        signals=signal_responses,
        comparison_summary=comparison.get("comparison_summary"),
        recommended_signal_id=comparison.get("recommended_signal_id"),
    )


# ── Opportunity Radar ─────────────────────────────────────────


@router.get(
    "/opportunities",
    response_model=OpportunityRadarResponse,
    status_code=HTTP_200_OK,
    summary="Aggregated opportunity radar",
)
async def get_opportunities(
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> OpportunityRadarResponse:
    """Get aggregated opportunity landscape from all signals."""
    radar = await hidden_job_market_service.get_opportunity_radar(
        database, user_id=current_user.id,
    )
    return OpportunityRadarResponse(**radar)


@router.post(
    "/opportunities/surface",
    response_model=list[CompanySignalResponse],
    status_code=HTTP_201_CREATED,
    summary="Surface hidden opportunities",
)
@limiter.limit("3/minute")
async def surface_opportunities(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[CompanySignalResponse]:
    """Surface hidden opportunities from existing detected signals."""
    try:
        signals = await hidden_job_market_service.surface_opportunities(
            database, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [
        CompanySignalResponse.model_validate(signal)
        for signal in signals
    ]


# ── Get / Dismiss / Outreach for Signal ────────────────────────


@router.get(
    "/{signal_id}",
    response_model=CompanySignalResponse,
    status_code=HTTP_200_OK,
    summary="Get signal detail",
)
async def get_signal(
    signal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CompanySignalResponse:
    """Retrieve a specific signal with match results and outreach."""
    signal = await hidden_job_market_service.get_signal(
        database, signal_id=signal_id, user_id=current_user.id,
    )
    if not signal:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Signal not found.",
        )
    return CompanySignalResponse.model_validate(signal)


@router.post(
    "/{signal_id}/outreach",
    response_model=CompanySignalResponse,
    status_code=HTTP_201_CREATED,
    summary="Generate outreach template",
)
@limiter.limit("3/minute")
async def generate_outreach(
    request: Request,
    signal_id: uuid.UUID,
    body: GenerateOutreachRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CompanySignalResponse:
    """Generate a personalized outreach template for a detected signal."""
    signal = await hidden_job_market_service.generate_outreach(
        database,
        signal_id=signal_id,
        user_id=current_user.id,
        request=body,
    )
    if not signal:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Signal not found.",
        )
    return CompanySignalResponse.model_validate(signal)


@router.post(
    "/{signal_id}/dismiss",
    response_model=CompanySignalResponse,
    status_code=HTTP_200_OK,
    summary="Dismiss or action a signal",
)
async def dismiss_signal(
    signal_id: uuid.UUID,
    body: DismissSignalRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CompanySignalResponse:
    """Dismiss or mark a signal as actioned."""
    signal = await hidden_job_market_service.dismiss_signal(
        database,
        signal_id=signal_id,
        user_id=current_user.id,
        request=body,
    )
    if not signal:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="Signal not found.",
        )
    return CompanySignalResponse.model_validate(signal)
