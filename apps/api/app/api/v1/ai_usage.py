"""
PathForge — AI Usage Routes (T4 / Sprint 56, ADR-0008)
========================================================

User-facing **Transparent AI Accounting** endpoint.  Aggregates the
caller's AITransparencyRecord history into per-engine usage rows.

Response carries both call counts and EUR cost so the web layer can
present whichever is appropriate for the caller's tier (sprint plan
§12 default #4 = dual-display).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.ai_usage import EngineUsageResponse, UsageSummaryResponse
from app.services.ai_usage_service import (
    AIUsageService,
    UsagePeriod,
    UsageSummary,
)

router = APIRouter(prefix="/ai-usage", tags=["AI Usage"])


def _resolve_period(period: str) -> UsagePeriod:
    """Map a public period token to a :class:`UsagePeriod`.

    Currently supports ``current_month`` only; future tokens
    (``last_month``, ``current_quarter``, …) extend this lookup
    without changing the endpoint surface.
    """
    if period == "current_month":
        return UsagePeriod.current_month()
    # FastAPI's Literal validation rejects unknown tokens before this
    # function runs, but keep the explicit guard so the type narrowing
    # at the call site is honest.
    raise ValueError(f"Unsupported period: {period!r}")


def _to_response(summary: UsageSummary) -> UsageSummaryResponse:
    return UsageSummaryResponse(
        user_id=summary.user_id,
        period_label=summary.period_label,
        period_start=summary.period_start,
        period_end=summary.period_end,
        total_calls=summary.total_calls,
        total_prompt_tokens=summary.total_prompt_tokens,
        total_completion_tokens=summary.total_completion_tokens,
        total_cost_eur_cents=summary.total_cost_eur_cents,
        has_unpriced_models=summary.has_unpriced_models,
        engines=[
            EngineUsageResponse(
                engine=row.engine,
                calls=row.calls,
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                cost_eur_cents=row.cost_eur_cents,
                avg_latency_ms=row.avg_latency_ms,
                last_call_at=row.last_call_at,
            )
            for row in summary.engines
        ],
    )


@router.get(
    "/summary",
    response_model=UsageSummaryResponse,
    summary="Per-engine AI usage summary for the authenticated user",
    description=(
        "Returns the current user's AI consumption aggregated by engine "
        "(`career_dna`, `threat_radar`, …) for the requested period. "
        "Response carries both call counts (free-tier display) and "
        "estimated EUR cost (premium-tier display); the web layer picks "
        "the presentation per subscription tier."
    ),
)
@limiter.limit("60/minute")
@route_query_budget(max_queries=4)
async def get_summary(
    request: Request,  # required by `@limiter.limit` for client-IP keying
    period: Literal["current_month"] = Query(
        "current_month",
        description="Aggregation window. Today only `current_month` is supported.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageSummaryResponse:
    service = AIUsageService(db)
    summary = await service.summary(
        user_id=current_user.id,
        period=_resolve_period(period),
    )
    return _to_response(summary)


# Silence unused-import warning when the rate limiter ist not invoked
# from a synchronous path.
_ = limiter
