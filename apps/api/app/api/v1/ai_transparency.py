"""
PathForge — AI Trust Layer™ API Routes
========================================
User-facing endpoints for AI decision transparency and system health.

Endpoints:
    GET /api/v1/ai-transparency/health      — Public AI system health
    GET /api/v1/ai-transparency/analyses     — User's recent AI analyses
    GET /api/v1/ai-transparency/analyses/{id} — Single analysis detail
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.requests import Request

from app.core.config import settings
from app.core.llm_observability import get_transparency_log
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.ai_transparency import (
    AIAnalysisTransparencyResponse,
    AIHealthResponse,
    RecentAnalysesResponse,
)

router = APIRouter(prefix="/ai-transparency", tags=["AI Transparency"])


@router.get(
    "/health",
    response_model=AIHealthResponse,
    summary="AI System Health Dashboard",
    description=(
        "Public endpoint — no authentication required. "
        "Returns aggregated AI system health metrics as a trust signal. "
        "PathForge is transparent about AI reliability."
    ),
)
@limiter.limit(settings.rate_limit_ai_health)
@route_query_budget(max_queries=4)
async def get_ai_health(request: Request) -> dict[str, Any]:
    """Return AI system health summary.

    Public endpoint — no user-specific data is exposed.
    Shows system status, success rate, and latency aggregates.
    Rate-limited to 30 req/min to prevent scraping.
    """
    transparency_log = get_transparency_log()
    return transparency_log.get_system_health()


@router.get(
    "/analyses",
    response_model=RecentAnalysesResponse,
    summary="Recent AI Analyses",
    description=(
        "Returns recent AI analyses for the authenticated user with "
        "full transparency metadata: confidence scores, data sources, "
        "token usage, and latency."
    ),
)
@limiter.limit(settings.rate_limit_ai_analyses)
@route_query_budget(max_queries=6)
async def get_recent_analyses(
    request: Request,
    current_user: User = Depends(get_current_user),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Number of recent analyses to return",
    ),
) -> dict[str, Any]:
    """Return recent AI analyses for the authenticated user."""
    transparency_log = get_transparency_log()
    user_id = str(current_user.id)
    records = await transparency_log.get_recent(user_id=user_id, limit=limit)

    analyses = [
        {
            "analysis_id": record.analysis_id,
            "analysis_type": record.analysis_type,
            "confidence_score": round(record.confidence_score, 3),
            "confidence_label": record.confidence_label,
            "model_tier": record.tier,
            "tokens_used": record.prompt_tokens + record.completion_tokens,
            "latency_ms": record.latency_ms,
            "data_sources": record.data_sources,
            "timestamp": record.timestamp,
        }
        for record in records
    ]

    return {
        "analyses": analyses,
        "total_count": len(analyses),
        "user_id": user_id,
    }


@router.get(
    "/analyses/{analysis_id}",
    response_model=AIAnalysisTransparencyResponse,
    summary="Analysis Detail",
    description=(
        "Returns detailed transparency metadata for a specific AI analysis. "
        "Users can only access their own analyses."
    ),
)
@limiter.limit(settings.rate_limit_ai_analyses)
@route_query_budget(max_queries=6)
async def get_analysis_detail(
    request: Request,
    analysis_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return transparency detail for a specific analysis.

    Enforces user isolation — users can only access their own
    analysis records.
    """
    transparency_log = get_transparency_log()
    record = await transparency_log.get_by_id(analysis_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    # Verify ownership — users can only see their own analyses
    owner_id = await transparency_log.get_user_for_analysis(analysis_id)
    if owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    return {
        "analysis_id": record.analysis_id,
        "analysis_type": record.analysis_type,
        "confidence_score": round(record.confidence_score, 3),
        "confidence_label": record.confidence_label,
        "model_tier": record.tier,
        "tokens_used": record.prompt_tokens + record.completion_tokens,
        "latency_ms": record.latency_ms,
        "data_sources": record.data_sources,
        "timestamp": record.timestamp,
    }
