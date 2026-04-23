"""
PathForge API — Health Check Routes
=====================================
System health and readiness checks.

Sprint 30: Enhanced with Redis ping, cold start time,
uptime tracking, and HTTP 503 on dependency failure (Audit C1).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import cast

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Track process start for cold_start_time and uptime
_FIRST_HEALTH_CHECK_TIME: float | None = None


# ── ADR-0001: cached pg_stat_ssl attestation ────────────────────────
# Without caching, every /health/ready hit fires two DB round-trips
# (SELECT 1 + pg_stat_ssl), doubling the DoS amplification factor on an
# unauthenticated endpoint. Connection pool members all share the engine's
# TLS posture (set once at module import), so a single attestation value
# is ground truth for the process lifetime. A 60s TTL is conservative —
# a redeploy restarts the process and invalidates the cache implicitly.
_ATTEST_CACHE_TTL_SECONDS: float = 60.0


@dataclass
class _AttestEntry:
    """A single pg_stat_ssl measurement bound to a monotonic timestamp."""

    ssl: bool
    cipher: str | None
    version: str | None
    attested_at: float


_attest_cache: _AttestEntry | None = None


def _reset_attest_cache_for_tests() -> None:
    """Test-only hook to clear the attestation cache between tests.

    Not part of the public module API — callers outside the test suite
    should let the TTL expire naturally or rely on a process restart.
    """
    global _attest_cache
    _attest_cache = None


async def _attest_db_ssl(db: AsyncSession) -> _AttestEntry | None:
    """Return a cached or freshly-measured pg_stat_ssl attestation.

    Returns None when the backend does not expose `pg_stat_ssl` (SQLite,
    pgbouncer transaction-pool mode, revoked grants). Exceptions are
    logged at DEBUG only — the endpoint must remain healthy when
    attestation is unavailable.
    """
    global _attest_cache
    now = time.monotonic()
    if (
        _attest_cache is not None
        and (now - _attest_cache.attested_at) < _ATTEST_CACHE_TTL_SECONDS
    ):
        return _attest_cache
    try:
        result = await db.execute(
            text(
                "SELECT ssl, version, cipher "
                "FROM pg_stat_ssl "
                "WHERE pid = pg_backend_pid()",
            ),
        )
        row = result.mappings().first()
        if row is None:
            return None
        entry = _AttestEntry(
            ssl=bool(row["ssl"]),
            cipher=row["cipher"] if row["ssl"] else None,
            version=row["version"] if row["ssl"] else None,
            attested_at=now,
        )
        _attest_cache = entry
        return entry
    except Exception as attest_exc:
        logger.debug(
            "pg_stat_ssl attestation unavailable: %s", attest_exc,
        )
        return None


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
    # Legacy `database` key preserved for back-compat with existing
    # consumers; new structured `db` block (ADR-0001) adds server-side
    # TLS attestation for post-deploy verification and UptimeRobot body
    # checks. `ssl_attested` distinguishes "server confirmed TLS status"
    # from "could not attest" (SQLite tests, pgbouncer transaction-pool,
    # revoked pg_stat_ssl grants) — operators must not assume the
    # config-derived value is ground truth.
    db_ssl_enabled: bool = settings.database_ssl_enabled
    db_ssl_cipher: str | None = None
    db_ssl_version: str | None = None
    db_ssl_attested: bool = False
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
        entry = await _attest_db_ssl(db)
        if entry is not None:
            db_ssl_enabled = entry.ssl
            db_ssl_cipher = entry.cipher
            db_ssl_version = entry.version
            db_ssl_attested = True
    except Exception:
        # Security (ADR-0001): never surface raw driver exceptions to an
        # unauthenticated endpoint. Messages from asyncpg/SQLAlchemy can
        # include host, port, username, and "password authentication
        # failed" text. Log with full context for operators; return a
        # static token to clients.
        logger.warning("Readiness DB probe failed", exc_info=True)
        db_status = "error"

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
        except Exception:
            # Security: same rationale as the DB probe above — raw
            # exceptions can include Redis host, port, and ACL/auth
            # details. Log for operators; return a static token.
            logger.warning("Readiness Redis probe failed", exc_info=True)
            redis_status = "error"

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
        "db": {
            "status": "ok" if db_status == "connected" else "error",
            "ssl": db_ssl_enabled,
            "ssl_attested": db_ssl_attested,
            "ssl_cipher": db_ssl_cipher,
            "ssl_version": db_ssl_version,
        },
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
