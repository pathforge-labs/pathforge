"""
PathForge API — Application Entry Point
=========================================
FastAPI application factory with CORS, routing, and OpenAPI configuration.

Includes: security hardening (RFC 9116, bot trap, docs protection).
Sprint 30: Graceful shutdown, structured rate limit responses.

Run with: uvicorn app.main:app --reload
"""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1 import (
    admin,
    ai,
    ai_transparency,
    analytics,
    applications,
    auth,
    billing,
    blacklist,
    career_action_planner,
    career_command_center,
    career_dna,
    career_passport,
    career_simulation,
    collective_intelligence,
    health,
    hidden_job_market,
    interview_intelligence,
    notifications,
    oauth,
    observability,
    predictive_career,
    public_profiles,
    recommendation_intelligence,
    resumes,
    salary_intelligence,
    skill_decay,
    threat_radar,
    transition_pathways,
    user_profile,
    users,
    waitlist,
    well_known,
    workflow_automation,
)
from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.llm_observability import initialize_observability
from app.core.logging_config import setup_logging
from app.core.middleware import BotTrapMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

# Track process start time for cold_start_time calculation
_PROCESS_START_TIME: float = time.monotonic()


def get_process_start_time() -> float:
    """Return monotonic timestamp of process start."""
    return _PROCESS_START_TIME


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events (Audit C2: graceful shutdown)."""
    # ── Startup ────────────────────────────────────────────────
    setup_logging()
    initialize_observability()

    # Sprint 30 WS-1: Initialize Sentry error tracking
    from app.core.sentry import init_sentry
    init_sentry()

    # ADR-0001 / ADR-0002: Tag every event with the effective DB and
    # Redis TLS posture so post-mortem queries can filter "errors while
    # TLS was off" in one click. Intentionally process-global (isolation
    # scope) because TLS posture is a lifecycle invariant, not
    # request-scoped. Gated on the active Sentry client (not DSN string)
    # so a failed `init_sentry()` doesn't leave a dangling tag attempt.
    try:
        import sentry_sdk
        if sentry_sdk.Hub.current.client is not None:
            sentry_sdk.set_tag(
                "db.ssl", str(settings.database_ssl_enabled).lower(),
            )
            sentry_sdk.set_tag(
                "redis.ssl", str(settings.redis_ssl_enabled).lower(),
            )
    except Exception:
        logger.warning("Failed to set Sentry TLS-posture tags", exc_info=True)

    # Sprint 34: Pin Stripe API version (F15)
    try:
        import stripe
        stripe.api_version = settings.stripe_api_version
        logger.info("Stripe API version pinned: %s", settings.stripe_api_version)
    except ImportError:
        pass

    # Sprint 34: Auto-promote initial admin (D3)
    if settings.initial_admin_email:
        try:
            from app.core.database import async_session_factory
            from app.services.admin_service import AdminService

            async with async_session_factory() as session, session.begin():
                await AdminService.auto_promote_initial_admin(
                    session, settings.initial_admin_email
                )
        except Exception:
            logger.warning("Initial admin promotion skipped (DB may not be ready)")

    logger.info(
        "PathForge API started",
        extra={"version": settings.app_version, "environment": settings.environment},
    )

    yield

    # ── Shutdown (Audit C2) ────────────────────────────────────
    shutdown_start = time.perf_counter()
    logger.info("Initiating graceful shutdown")

    # 1. Flush Sentry events
    try:
        import sentry_sdk
        sentry_sdk.flush(timeout=2)
    except Exception:
        pass  # Sentry may not be initialized

    # 2. Close Redis connection pool
    try:
        from app.core.token_blacklist import token_blacklist
        await token_blacklist.close()
    except Exception:
        logger.warning("Failed to close Redis pool during shutdown")

    # 3. Dispose SQLAlchemy engine
    try:
        from app.core.database import engine
        await engine.dispose()
    except Exception:
        logger.warning("Failed to dispose database engine during shutdown")

    # 4. Close push notification HTTP client (Sprint 33 F7)
    try:
        from app.services import push_service
        await push_service.close_http_client()
    except Exception:
        logger.warning("Failed to close push HTTP client during shutdown")

    shutdown_duration_ms = round((time.perf_counter() - shutdown_start) * 1000, 2)
    logger.info("Graceful shutdown completed", extra={"duration_ms": shutdown_duration_ms})


def _rate_limit_exceeded_response(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Structured 429 response with Retry-After header.

    Returns machine-parseable JSON with request_id for tracing.
    """
    from app.core.middleware import get_request_id

    # Parse retry-after from exception detail (e.g. "5 per 1 minute")
    retry_after = "60"  # Default fallback
    detail = str(exc.detail) if exc.detail else "Rate limit exceeded"

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": detail,
            "request_id": get_request_id(),
        },
        headers={"Retry-After": retry_after},
    )


def create_app() -> FastAPI:
    """Application factory."""
    # Production: disable interactive docs to reduce attack surface
    docs_url = None if settings.is_production else "/docs"
    redoc_url = None if settings.is_production else "/redoc"
    openapi_url = None if settings.is_production else "/openapi.json"

    application = FastAPI(
        title=f"{settings.app_name} API",
        description=f"{settings.app_name} — {settings.app_tagline}. "
        "AI-powered Career Intelligence Platform with Career DNA™ technology, "
        "semantic job matching, CV tailoring, and skill gap analysis.",
        version=settings.app_version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # ── Middleware (order matters: outermost runs first) ────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.effective_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(BotTrapMiddleware)

    # ── Error Handlers ─────────────────────────────────────────
    register_error_handlers(application)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_response)  # type: ignore[arg-type]

    # ── Routes ─────────────────────────────────────────────────
    # Well-known endpoints at root level (no /api/v1 prefix)
    application.include_router(well_known.router)

    # API routes
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(oauth.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    application.include_router(ai.router, prefix="/api/v1")
    application.include_router(applications.router, prefix="/api/v1")
    application.include_router(blacklist.router, prefix="/api/v1")
    application.include_router(analytics.router, prefix="/api/v1")
    application.include_router(career_dna.router, prefix="/api/v1")
    application.include_router(career_passport.router, prefix="/api/v1")
    application.include_router(threat_radar.router, prefix="/api/v1")
    application.include_router(skill_decay.router, prefix="/api/v1")
    application.include_router(salary_intelligence.router, prefix="/api/v1")
    application.include_router(transition_pathways.router, prefix="/api/v1")
    application.include_router(career_simulation.router, prefix="/api/v1")
    application.include_router(interview_intelligence.router, prefix="/api/v1")
    application.include_router(hidden_job_market.router, prefix="/api/v1")
    application.include_router(collective_intelligence.router, prefix="/api/v1")
    application.include_router(predictive_career.router, prefix="/api/v1")
    application.include_router(career_action_planner.router, prefix="/api/v1")
    application.include_router(career_command_center.router, prefix="/api/v1")
    application.include_router(notifications.router, prefix="/api/v1")
    application.include_router(user_profile.router, prefix="/api/v1")
    application.include_router(recommendation_intelligence.router, prefix="/api/v1")
    application.include_router(workflow_automation.router, prefix="/api/v1")
    application.include_router(observability.router, prefix="/api/v1")
    application.include_router(ai_transparency.router, prefix="/api/v1")
    application.include_router(resumes.router, prefix="/api/v1")  # Sprint 50: resume upload

    # Sprint 34: Monetization & Growth routers
    application.include_router(billing.router, prefix="/api/v1")
    application.include_router(billing.webhook_router, prefix="/api/v1")
    application.include_router(admin.router, prefix="/api/v1")
    application.include_router(waitlist.router, prefix="/api/v1")
    application.include_router(public_profiles.router, prefix="/api/v1")

    return application


app = create_app()
