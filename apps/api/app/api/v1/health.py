"""
PathForge API — Health Check Routes
=====================================
System health and readiness checks.

Sprint 30: Enhanced with Redis ping, cold start time,
uptime tracking, and HTTP 503 on dependency failure (Audit C1).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable
from typing import cast

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health"])

# Track process start for cold_start_time and uptime
_FIRST_HEALTH_CHECK_TIME: float | None = None


@router.get("/health", summary="Basic health check (liveness)")
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe — no dependency checks."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/health/ready", summary="Readiness check (includes DB + Redis)")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Deep readiness probe — verifies all critical dependencies.

    Returns HTTP 503 when any dependency is down (Audit C1).
    Used by Railway health check for deployment validation.
    """
    global _FIRST_HEALTH_CHECK_TIME

    # ── Track cold start time ──────────────────────────────────
    from app.main import get_process_start_time

    now = time.monotonic()
    process_start = get_process_start_time()
    uptime_seconds = round(now - process_start, 2)

    cold_start_ms: float | None = None
    if _FIRST_HEALTH_CHECK_TIME is None:
        _FIRST_HEALTH_CHECK_TIME = now
        cold_start_ms = round((now - process_start) * 1000, 2)

    # ── Database check ─────────────────────────────────────────
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"

    # ── Redis check (Audit C1) ─────────────────────────────────
    redis_status = "not_configured"
    if settings.redis_url:
        try:
            from app.core.token_blacklist import token_blacklist

            if token_blacklist._redis is not None:
                await cast("Awaitable[bool]", token_blacklist._redis.ping())
                redis_status = "connected"
            else:
                redis_status = "not_initialized"
        except Exception as exc:
            redis_status = f"error: {exc}"

    # ── Rate limit storage check ───────────────────────────────
    from app.core.rate_limit import RATE_LIMIT_DEGRADED

    rate_limit_status = "degraded (memory://)" if RATE_LIMIT_DEGRADED else "ok"

    # ── Build response ─────────────────────────────────────────
    # Sprint 40 Audit P1-4: Rate limit degradation affects readiness
    all_healthy = (
        db_status == "connected"
        and redis_status in ("connected", "not_configured")
        and not RATE_LIMIT_DEGRADED
    )

    response_body: dict[str, object] = {
        "status": "ok" if all_healthy else "unhealthy",
        "database": db_status,
        "redis": redis_status,
        "rate_limiting": rate_limit_status,
        "app": settings.app_name,
        "version": settings.app_version,
        "uptime_seconds": uptime_seconds,
    }

    if cold_start_ms is not None:
        response_body["cold_start_ms"] = cold_start_ms

    # Return 503 when dependencies are down (Audit C1)
    status_code = 200 if all_healthy else 503

    return JSONResponse(content=response_body, status_code=status_code)
