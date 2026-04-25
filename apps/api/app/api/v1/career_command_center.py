"""
PathForge — Career Command Center™ API Routes
================================================
REST API endpoints for the Unified Career Command Center.

Endpoints:
    GET  /dashboard           — Full dashboard with all 12 engines
    GET  /health-summary      — Lightweight health check
    POST /refresh             — Force-refresh Career Vitals™ snapshot
    GET  /engines/{name}      — Engine drill-down detail
    GET  /preferences         — Get display preferences
    PUT  /preferences         — Update display preferences
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.career_command_center import (
    CareerHealthSummaryResponse,
    CareerSnapshotResponse,
    CommandCenterPreferenceResponse,
    CommandCenterPreferenceUpdate,
    DashboardResponse,
    EngineDetailResponse,
    EngineStatusResponse,
)
from app.services.career_command_center_service import (
    ENGINE_REGISTRY,
    CareerCommandCenterService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/command-center",
    tags=["Career Command Center™"],
)


# ── Dashboard ────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get Career Command Center dashboard",
    description=(
        "Unified Career Command Center™ — aggregates all 12 AI "
        "intelligence engines into a single dashboard with Career "
        "Vitals™ composite health score and Engine Heartbeat™."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get the full Career Command Center dashboard."""
    try:
        data = await CareerCommandCenterService.get_dashboard(
            database,
            user_id=current_user.id,
        )
        snapshot = data["snapshot"]
        preferences = data.get("preferences")

        # Build health summary
        health_summary = await CareerCommandCenterService.get_health_summary(
            database,
            user_id=current_user.id,
        )

        # Build engine status list
        engine_statuses_map = (snapshot.engine_statuses if snapshot else {}) or {}
        engine_statuses = [
            EngineStatusResponse(
                engine_name=engine_name,
                display_name=engine_data.get("display_name", engine_name),
                heartbeat=engine_data.get("heartbeat", "never_run"),
                score=engine_data.get("score"),
                last_updated=engine_data.get("last_updated"),
                trend=engine_data.get("trend"),
                summary=engine_data.get("summary"),
            )
            for engine_name, engine_data in engine_statuses_map.items()
            if isinstance(engine_data, dict)
        ]

        return DashboardResponse(
            snapshot=(CareerSnapshotResponse.model_validate(snapshot) if snapshot else None),
            health_summary=CareerHealthSummaryResponse(**health_summary),
            engine_statuses=engine_statuses,
            preferences=(
                CommandCenterPreferenceResponse.model_validate(preferences) if preferences else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Health Summary ─────────────────────────────────────────


@router.get(
    "/health-summary",
    response_model=CareerHealthSummaryResponse,
    summary="Get lightweight career health check",
    description=(
        "Career Vitals™ — lightweight health check returning "
        "composite score, band, trend, and active engine count."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def get_health_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerHealthSummaryResponse:
    """Get lightweight career health summary."""
    try:
        data = await CareerCommandCenterService.get_health_summary(
            database,
            user_id=current_user.id,
        )
        return CareerHealthSummaryResponse(**data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Refresh Snapshot ───────────────────────────────────────


@router.post(
    "/refresh",
    response_model=CareerSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Force-refresh Career Vitals™ snapshot",
    description=(
        "Force re-computation of the Career Vitals™ composite "
        "health score by querying all 12 intelligence engines."
    ),
)
@limiter.limit("3/minute")
async def refresh_snapshot(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CareerSnapshotResponse:
    """Force-refresh Career Vitals™ snapshot."""
    try:
        snapshot = await CareerCommandCenterService.refresh_snapshot(
            database,
            user_id=current_user.id,
        )
        return CareerSnapshotResponse.model_validate(snapshot)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Engine Detail ──────────────────────────────────────────


@router.get(
    "/engines/{engine_name}",
    response_model=EngineDetailResponse,
    summary="Get engine drill-down",
    description=(
        "Engine Heartbeat™ — detailed status for a single "
        "intelligence engine including recent records."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def get_engine_detail(
    request: Request,
    engine_name: str,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> EngineDetailResponse:
    """Get detailed status for a single engine."""
    # Validate engine name
    valid_names = [engine["name"] for engine in ENGINE_REGISTRY]
    if engine_name not in valid_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Engine '{engine_name}' not found. Valid engines: {', '.join(valid_names)}"),
        )

    data = await CareerCommandCenterService.get_engine_detail(
        database,
        user_id=current_user.id,
        engine_name=engine_name,
    )

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{engine_name}' not found.",
        )

    return EngineDetailResponse(**data)


# ── Preferences ──────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=CommandCenterPreferenceResponse,
    summary="Get display preferences",
    description="Get Career Command Center display preferences.",
)
@limiter.limit(settings.rate_limit_parse)
@route_query_budget(max_queries=4)
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CommandCenterPreferenceResponse:
    """Get user display preferences."""
    pref = await CareerCommandCenterService.get_preferences(
        database,
        user_id=current_user.id,
    )
    if pref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preferences found. Set preferences first.",
        )
    return CommandCenterPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=CommandCenterPreferenceResponse,
    summary="Update display preferences",
    description=(
        "Update Career Command Center display preferences including pinned and hidden engines."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_preferences(
    request: Request,
    body: CommandCenterPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> CommandCenterPreferenceResponse:
    """Update display preferences."""
    try:
        pref = await CareerCommandCenterService.update_preferences(
            database,
            user_id=current_user.id,
            updates=body.model_dump(exclude_unset=True),
        )
        return CommandCenterPreferenceResponse.model_validate(pref)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
