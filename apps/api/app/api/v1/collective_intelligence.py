"""
PathForge — Collective Intelligence Engine™ API Routes
=======================================================
REST API endpoints for career market intelligence.

Endpoints:
    POST /industry-snapshot          — Analyze an industry
    POST /salary-benchmark           — Get salary benchmarking
    POST /peer-cohort                — Get peer comparison
    POST /career-pulse               — Get Career Pulse Index™
    GET  /dashboard                  — Aggregated dashboard
    POST /scan                       — Full intelligence scan
    POST /compare-industries         — Multi-industry comparison
    GET  /preferences                — Get user CI preferences
    PUT  /preferences                — Update user CI preferences
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
from app.schemas.collective_intelligence import (
    CareerPulseRequest,
    CareerPulseResponse,
    CollectiveIntelligenceDashboardResponse,
    CollectiveIntelligencePreferenceResponse,
    CollectiveIntelligencePreferenceUpdate,
    IndustryComparisonRequest,
    IndustryComparisonResponse,
    IndustrySnapshotRequest,
    IndustrySnapshotResponse,
    IntelligenceScanRequest,
    IntelligenceScanResponse,
    PeerCohortAnalysisResponse,
    PeerCohortRequest,
    SalaryBenchmarkRequest,
    SalaryBenchmarkResponse,
)
from app.services import collective_intelligence_service as ci_service
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/collective-intelligence",
    tags=["Collective Intelligence Engine™"],
)


# ── Industry Snapshot ──────────────────────────────────────────


@router.post(
    "/industry-snapshot",
    response_model=IndustrySnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze industry health and trends",
    description=(
        "Industry Trend Radar™ — AI-powered analysis of an industry's "
        "hiring trends, emerging skills, salary ranges, and growth "
        "projections, personalized to your Career DNA."
    ),
    dependencies=[Depends(require_feature("collective_intelligence"))],
)
@limiter.limit(settings.rate_limit_career_dna)
async def create_industry_snapshot(
    request: Request,
    body: IndustrySnapshotRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> IndustrySnapshotResponse:
    """Analyze an industry's health and trends.

    Sprint 38 C1/C2/C5: Feature gating + scan limit + usage tracking.
    """
    # C5: Pre-check scan limit before AI call
    if settings.billing_enabled:
        await BillingService.check_scan_limit(database, current_user, "collective_intelligence")

    try:
        snapshot = await ci_service.get_industry_snapshot(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
        )

        # C2: Record usage after successful scan
        if settings.billing_enabled:
            await BillingService.record_usage(database, current_user, "collective_intelligence")

        return IndustrySnapshotResponse.model_validate(snapshot)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Salary Benchmark ──────────────────────────────────────────


@router.post(
    "/salary-benchmark",
    response_model=SalaryBenchmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Get personalized salary benchmark",
    description=(
        "AI-powered salary benchmarking personalized to your Career DNA: "
        "role, skills, experience, and location. Includes percentile "
        "positioning and negotiation insights."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def create_salary_benchmark(
    request: Request,
    body: SalaryBenchmarkRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> SalaryBenchmarkResponse:
    """Get personalized salary benchmarking."""
    try:
        benchmark = await ci_service.get_salary_benchmark(
            database,
            user_id=current_user.id,
            role=body.role,
            location=body.location,
            experience_years=body.experience_years,
            currency=body.currency,
        )
        return SalaryBenchmarkResponse.model_validate(benchmark)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Peer Cohort Analysis ─────────────────────────────────────


@router.post(
    "/peer-cohort",
    response_model=PeerCohortAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Get peer cohort benchmarking",
    description=(
        "Peer Cohort Benchmarking™ — anonymized comparison against "
        "professionals with similar Career DNA profiles. Uses k-anonymity "
        "(minimum 10 in cohort) for privacy."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def create_peer_cohort_analysis(
    request: Request,
    body: PeerCohortRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PeerCohortAnalysisResponse:
    """Get peer cohort benchmarking."""
    try:
        analysis = await ci_service.get_peer_cohort_analysis(
            database,
            user_id=current_user.id,
            role=body.role,
            experience_range_min=body.experience_range_min,
            experience_range_max=body.experience_range_max,
            region=body.region,
        )
        return PeerCohortAnalysisResponse.model_validate(analysis)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Career Pulse ──────────────────────────────────────────────


@router.post(
    "/career-pulse",
    response_model=CareerPulseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Get Career Pulse Index™",
    description=(
        "Career Pulse Index™ — a composite score (0-100) reflecting "
        "the real-time health of your career market segment. "
        "No competitor offers this metric."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def create_career_pulse(
    request: Request,
    body: CareerPulseRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerPulseResponse:
    """Compute Career Pulse Index™."""
    try:
        pulse = await ci_service.get_career_pulse(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
        )
        return CareerPulseResponse.model_validate(pulse)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Dashboard ─────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=CollectiveIntelligenceDashboardResponse,
    summary="Get Collective Intelligence dashboard",
    description=(
        "Aggregated dashboard with latest Career Pulse, industry "
        "snapshots, salary benchmarks, peer analyses, and preferences."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CollectiveIntelligenceDashboardResponse:
    """Get aggregated Collective Intelligence dashboard."""
    try:
        data = await ci_service.get_ci_dashboard(
            database, user_id=current_user.id,
        )
        return CollectiveIntelligenceDashboardResponse(
            latest_pulse=(
                CareerPulseResponse.model_validate(data["latest_pulse"])
                if data["latest_pulse"] else None
            ),
            industry_snapshots=[
                IndustrySnapshotResponse.model_validate(snapshot)
                for snapshot in data["industry_snapshots"]
            ],
            salary_benchmarks=[
                SalaryBenchmarkResponse.model_validate(benchmark)
                for benchmark in data["salary_benchmarks"]
            ],
            peer_cohort_analyses=[
                PeerCohortAnalysisResponse.model_validate(cohort)
                for cohort in data["peer_cohort_analyses"]
            ],
            preferences=(
                CollectiveIntelligencePreferenceResponse.model_validate(
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


# ── Full Intelligence Scan ────────────────────────────────────


@router.post(
    "/scan",
    response_model=IntelligenceScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run full intelligence scan",
    description=(
        "Execute a comprehensive intelligence scan: Career Pulse, "
        "industry snapshot, salary benchmark, and peer cohort — "
        "all in one request."
    ),
)
@limiter.limit("2/minute")
async def run_scan(
    request: Request,
    body: IntelligenceScanRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> IntelligenceScanResponse:
    """Execute full intelligence scan."""
    try:
        data = await ci_service.run_intelligence_scan(
            database,
            user_id=current_user.id,
            industry=body.industry,
            region=body.region,
            currency=body.currency,
        )
        return IntelligenceScanResponse(
            career_pulse=(
                CareerPulseResponse.model_validate(data["career_pulse"])
                if data["career_pulse"] else None
            ),
            industry_snapshot=(
                IndustrySnapshotResponse.model_validate(
                    data["industry_snapshot"],
                )
                if data["industry_snapshot"] else None
            ),
            salary_benchmark=(
                SalaryBenchmarkResponse.model_validate(
                    data["salary_benchmark"],
                )
                if data["salary_benchmark"] else None
            ),
            peer_cohort=(
                PeerCohortAnalysisResponse.model_validate(
                    data["peer_cohort"],
                )
                if data["peer_cohort"] else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Industry Comparison ───────────────────────────────────────


@router.post(
    "/compare-industries",
    response_model=IndustryComparisonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compare multiple industries",
    description=(
        "Compare up to 5 industries side-by-side, with an AI-recommended "
        "best fit based on demand and trend direction."
    ),
)
@limiter.limit(settings.rate_limit_career_dna)
async def compare_industries_endpoint(
    request: Request,
    body: IndustryComparisonRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> IndustryComparisonResponse:
    """Compare industries side-by-side."""
    try:
        data = await ci_service.compare_industries(
            database,
            user_id=current_user.id,
            industries=body.industries,
            region=body.region,
        )
        return IndustryComparisonResponse(
            snapshots=[
                IndustrySnapshotResponse.model_validate(snapshot)
                for snapshot in data["snapshots"]
            ],
            recommended_industry=data.get("recommended_industry"),
            recommendation_reasoning=data.get("recommendation_reasoning"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Preferences ───────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=CollectiveIntelligencePreferenceResponse,
    summary="Get CI preferences",
    description="Get current Collective Intelligence preferences.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CollectiveIntelligencePreferenceResponse:
    """Get user CI preferences."""
    try:
        preference = await ci_service.get_or_update_preferences(
            database, user_id=current_user.id,
        )
        return CollectiveIntelligencePreferenceResponse.model_validate(
            preference,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/preferences",
    response_model=CollectiveIntelligencePreferenceResponse,
    summary="Update CI preferences",
    description=(
        "Update Collective Intelligence preferences such as "
        "included modules, industries, locations, and currency."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_preferences(
    request: Request,
    body: CollectiveIntelligencePreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CollectiveIntelligencePreferenceResponse:
    """Update user CI preferences."""
    try:
        preference = await ci_service.get_or_update_preferences(
            database,
            user_id=current_user.id,
            updates=body.model_dump(exclude_unset=True),
        )
        return CollectiveIntelligencePreferenceResponse.model_validate(
            preference,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
