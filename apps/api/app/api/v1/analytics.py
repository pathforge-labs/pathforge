"""
PathForge API — Analytics Routes
====================================
Funnel pipeline, market intelligence, and CV A/B experiment endpoints.

Sprint 6b — Analytics (ARCHITECTURE.md §7)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    CVExperimentCreate,
    CVExperimentResponse,
    CVExperimentsListResponse,
    ExperimentResultUpdate,
    FunnelEventCreate,
    FunnelEventResponse,
    FunnelMetricsResponse,
    FunnelTimelineResponse,
    InsightGenerateRequest,
    MarketInsightResponse,
    MarketInsightsListResponse,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ── Funnel Pipeline ──────────────────────────────────────────────


@router.post("/funnel/events", response_model=FunnelEventResponse, status_code=201)
@route_query_budget(max_queries=8)
async def record_funnel_event(
    payload: FunnelEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelEventResponse:
    """
    Record a funnel event for the current user.

    Tracks stage transitions in the application lifecycle.
    Each event records when a user viewed, saved, applied, etc.
    """
    event = await analytics_service.record_funnel_event(
        db,
        user_id=current_user.id,
        application_id=payload.application_id,
        stage=payload.stage,
        metadata=payload.metadata,
    )
    return FunnelEventResponse.model_validate(event)


@router.get("/funnel/metrics", response_model=FunnelMetricsResponse)
@route_query_budget(max_queries=4)
async def get_funnel_metrics(
    period: str = Query("30d", description="Time period (e.g. 7d, 30d, 90d)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelMetricsResponse:
    """
    Get aggregated funnel conversion metrics.

    Returns the count and conversion rate for each funnel stage,
    relative to the top-of-funnel (viewed) count.
    """
    metrics = await analytics_service.get_funnel_metrics(
        db,
        user_id=current_user.id,
        period=period,
    )
    return FunnelMetricsResponse(**metrics)


@router.get("/funnel/timeline", response_model=FunnelTimelineResponse)
@route_query_budget(max_queries=4)
async def get_funnel_timeline(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelTimelineResponse:
    """
    Get time-series funnel event data for charts.

    Returns daily event counts grouped by stage for the specified
    number of days. Useful for trend visualization.
    """
    timeline = await analytics_service.get_funnel_timeline(
        db,
        user_id=current_user.id,
        days=days,
    )
    return FunnelTimelineResponse(**timeline)


# ── Market Intelligence ──────────────────────────────────────────


@router.get("/market/insights", response_model=MarketInsightsListResponse)
@route_query_budget(max_queries=4)
async def get_market_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarketInsightsListResponse:
    """
    Get latest market intelligence insights for the current user.

    Returns pre-computed insights on skill demand, salary trends,
    market heat, competition level, and application velocity.
    """
    insights = await analytics_service.get_market_insights(
        db,
        user_id=current_user.id,
    )
    return MarketInsightsListResponse(
        user_id=current_user.id,
        insights=[MarketInsightResponse.model_validate(i) for i in insights],
        count=len(insights),
    )


@router.post(
    "/market/insights/generate",
    response_model=MarketInsightResponse,
    status_code=201,
)
@route_query_budget(max_queries=9)
async def generate_market_insight(
    payload: InsightGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarketInsightResponse:
    """
    Trigger generation of a new market insight.

    Aggregates data from matched jobs, applications, and market
    signals to produce a typed insight snapshot for the given period.
    """
    insight = await analytics_service.generate_market_insight(
        db,
        user_id=current_user.id,
        insight_type=payload.insight_type,
        period=payload.period,
    )
    return MarketInsightResponse.model_validate(insight)


# ── CV A/B Experiments ───────────────────────────────────────────


@router.get("/experiments", response_model=CVExperimentsListResponse)
@route_query_budget(max_queries=4)
async def list_experiments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVExperimentsListResponse:
    """
    List current user's CV A/B experiments.

    Shows all experiments with their status, variants, and results
    for data-driven CV optimization.
    """
    experiments = await analytics_service.get_experiments(
        db,
        user_id=current_user.id,
    )
    return CVExperimentsListResponse(
        user_id=current_user.id,
        experiments=[CVExperimentResponse.model_validate(e) for e in experiments],
        count=len(experiments),
    )


@router.post("/experiments", response_model=CVExperimentResponse, status_code=201)
@route_query_budget(max_queries=4)
async def create_experiment(
    payload: CVExperimentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVExperimentResponse:
    """
    Create a new CV A/B experiment.

    Sets up a comparison between two CV versions (variant A vs B)
    for the same job listing. Tracks which version performs better.
    """
    experiment = await analytics_service.create_cv_experiment(
        db,
        user_id=current_user.id,
        job_listing_id=payload.job_listing_id,
        variant_a_id=payload.variant_a_id,
        variant_b_id=payload.variant_b_id,
        hypothesis=payload.hypothesis,
    )
    return CVExperimentResponse.model_validate(experiment)


@router.patch(
    "/experiments/{experiment_id}/result",
    response_model=CVExperimentResponse,
)
@route_query_budget(max_queries=4)
async def record_experiment_result(
    experiment_id: uuid.UUID,
    payload: ExperimentResultUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CVExperimentResponse:
    """
    Record the result of a CV A/B experiment.

    Marks the experiment as completed, records the winning variant,
    and stores performance metrics.
    """
    try:
        experiment = await analytics_service.record_experiment_result(
            db,
            experiment_id=experiment_id,
            winner_id=payload.winner_id,
            metrics=payload.metrics,
        )
        return CVExperimentResponse.model_validate(experiment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
