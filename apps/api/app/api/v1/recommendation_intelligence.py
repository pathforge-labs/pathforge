"""
PathForge — Cross-Engine Recommendation Intelligence™ API Routes
==================================================================
REST API endpoints for the Cross-Engine Recommendation Intelligence
system — Intelligence Fusion Engine™.

Endpoints:
    GET  /recommendations/dashboard              — Dashboard with stats
    POST /recommendations/generate               — Generate new batch
    GET  /recommendations                        — List with filters
    GET  /recommendations/{id}                    — Single recommendation
    PUT  /recommendations/{id}/status             — Update lifecycle status
    GET  /recommendations/{id}/correlations       — Correlation map
    GET  /recommendations/batches                 — List batches
    GET  /recommendations/preferences             — Get preferences
    PUT  /recommendations/preferences             — Update preferences
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
from app.schemas.recommendation_intelligence import (
    CrossEngineRecommendationResponse,
    GenerateRecommendationsRequest,
    RecommendationBatchResponse,
    RecommendationCorrelationResponse,
    RecommendationDashboardResponse,
    RecommendationPreferenceResponse,
    RecommendationPreferenceUpdate,
    RecommendationSummary,
    UpdateRecommendationStatusRequest,
)
from app.services.recommendation_intelligence_service import (
    RecommendationIntelligenceService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/recommendations",
    tags=["Cross-Engine Recommendation Intelligence™"],
)


# ── Dashboard ────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=RecommendationDashboardResponse,
    summary="Get Recommendation Intelligence dashboard",
    description=(
        "Intelligence Fusion Engine™ — dashboard with latest batch, "
        "recent recommendations, status counts, and user preferences."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> RecommendationDashboardResponse:
    """Get Recommendation Intelligence dashboard."""
    try:
        data = await RecommendationIntelligenceService.get_dashboard(
            database, user_id=current_user.id,
        )

        latest_batch = data["latest_batch"]
        recent_recs = data["recent_recommendations"]
        preferences = data["preferences"]

        return RecommendationDashboardResponse(
            latest_batch=(
                RecommendationBatchResponse.model_validate(latest_batch)
                if latest_batch else None
            ),
            recent_recommendations=[
                RecommendationSummary(
                    id=rec.id,
                    recommendation_type=rec.recommendation_type,
                    status=rec.status,
                    priority_score=rec.priority_score,
                    effort_level=rec.effort_level,
                    title=rec.title,
                    confidence_score=rec.confidence_score,
                    created_at=rec.created_at,
                )
                for rec in recent_recs
            ],
            total_pending=data["total_pending"],
            total_in_progress=data["total_in_progress"],
            total_completed=data["total_completed"],
            preferences=(
                RecommendationPreferenceResponse.model_validate(preferences)
                if preferences else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Generate Recommendations ─────────────────────────────────


@router.post(
    "/generate",
    response_model=RecommendationBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate cross-engine recommendations",
    description=(
        "Intelligence Fusion Engine™ — trigger recommendation "
        "generation by correlating signals from all 12 engines."
    ),
)
@limiter.limit("3/minute")
async def generate_recommendations(
    request: Request,
    body: GenerateRecommendationsRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> RecommendationBatchResponse:
    """Generate new recommendation batch."""
    try:
        batch = await RecommendationIntelligenceService.generate_recommendations(
            database,
            user_id=current_user.id,
            batch_type=body.batch_type,
            focus_categories=body.focus_categories,
        )
        return RecommendationBatchResponse.model_validate(batch)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── List Recommendations ─────────────────────────────────────


@router.get(
    "",
    response_model=list[RecommendationSummary],
    summary="List recommendations",
    description=(
        "List cross-engine recommendations with optional filters "
        "by status and recommendation type."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def list_recommendations(
    request: Request,
    status_filter: str | None = Query(
        None, alias="status",
        description="Filter by status: pending | in_progress | completed | dismissed",
    ),
    type_filter: str | None = Query(
        None, alias="type",
        description="Filter by type: skill_gap | threat_mitigation | opportunity | ...",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[RecommendationSummary]:
    """List recommendations with filters."""
    recs = await RecommendationIntelligenceService.list_recommendations(
        database,
        user_id=current_user.id,
        status_filter=status_filter,
        type_filter=type_filter,
        limit=limit,
        offset=offset,
    )
    return [
        RecommendationSummary(
            id=rec.id,
            recommendation_type=rec.recommendation_type,
            status=rec.status,
            priority_score=rec.priority_score,
            effort_level=rec.effort_level,
            title=rec.title,
            confidence_score=rec.confidence_score,
            created_at=rec.created_at,
        )
        for rec in recs
    ]


# ── Recommendation Detail ────────────────────────────────────


@router.get(
    "/{recommendation_id}",
    response_model=CrossEngineRecommendationResponse,
    summary="Get recommendation detail",
    description=(
        "Get detailed recommendation including priority breakdown, "
        "source engines, and action items."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def get_recommendation_detail(
    request: Request,
    recommendation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CrossEngineRecommendationResponse:
    """Get single recommendation with details."""
    rec = await RecommendationIntelligenceService.get_recommendation_detail(
        database,
        user_id=current_user.id,
        recommendation_id=recommendation_id,
    )
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found.",
        )
    return CrossEngineRecommendationResponse.model_validate(rec)


# ── Update Status ────────────────────────────────────────────


@router.put(
    "/{recommendation_id}/status",
    response_model=CrossEngineRecommendationResponse,
    summary="Update recommendation status",
    description=(
        "Update recommendation lifecycle: pending → in_progress → completed. "
        "Users can also dismiss recommendations."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_recommendation_status(
    request: Request,
    recommendation_id: uuid.UUID,
    body: UpdateRecommendationStatusRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CrossEngineRecommendationResponse:
    """Update recommendation lifecycle status."""
    try:
        rec = await RecommendationIntelligenceService.update_recommendation_status(
            database,
            user_id=current_user.id,
            recommendation_id=recommendation_id,
            new_status=body.status,
        )
        return CrossEngineRecommendationResponse.model_validate(rec)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Correlations ─────────────────────────────────────────────


@router.get(
    "/{recommendation_id}/correlations",
    response_model=list[RecommendationCorrelationResponse],
    summary="Get Cross-Engine Correlation Map™",
    description=(
        "View which intelligence engines contributed to this "
        "recommendation and with what correlation strength."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def get_correlations(
    request: Request,
    recommendation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[RecommendationCorrelationResponse]:
    """Get engine correlation map for a recommendation."""
    try:
        correlations = await RecommendationIntelligenceService.get_correlations(
            database,
            user_id=current_user.id,
            recommendation_id=recommendation_id,
        )
        return [
            RecommendationCorrelationResponse.model_validate(corr)
            for corr in correlations
        ]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Batches ──────────────────────────────────────────────────


@router.get(
    "/batches",
    response_model=list[RecommendationBatchResponse],
    summary="List recommendation batches",
    description=(
        "List Intelligence Fusion Engine™ analysis batches "
        "in reverse chronological order."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def list_batches(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> list[RecommendationBatchResponse]:
    """List recommendation batches."""
    batches = await RecommendationIntelligenceService.get_batches(
        database,
        user_id=current_user.id,
        limit=limit,
    )
    return [
        RecommendationBatchResponse.model_validate(batch)
        for batch in batches
    ]


# ── Preferences ──────────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=RecommendationPreferenceResponse,
    summary="Get recommendation preferences",
    description="Get user's Recommendation Intelligence filtering preferences.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> RecommendationPreferenceResponse:
    """Get Recommendation Intelligence preferences."""
    pref = await RecommendationIntelligenceService.get_preferences(
        database, user_id=current_user.id,
    )
    if pref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preferences found. Set preferences first.",
        )
    return RecommendationPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=RecommendationPreferenceResponse,
    summary="Update recommendation preferences",
    description=(
        "Update Recommendation Intelligence filtering preferences "
        "including enabled categories, priority thresholds, and limits."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_preferences(
    request: Request,
    body: RecommendationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> RecommendationPreferenceResponse:
    """Update Recommendation Intelligence preferences."""
    try:
        pref = await RecommendationIntelligenceService.update_preferences(
            database,
            user_id=current_user.id,
            updates=body.model_dump(exclude_unset=True),
        )
        return RecommendationPreferenceResponse.model_validate(pref)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
