"""
PathForge API — Application Entry Point
=========================================
FastAPI application factory with CORS, routing, and OpenAPI configuration.

Includes: security hardening (RFC 9116, bot trap, docs protection).
Run with: uvicorn app.main:app --reload
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import (
    ai,
    ai_transparency,
    analytics,
    applications,
    auth,
    blacklist,
    career_action_planner,
    career_dna,
    career_passport,
    career_simulation,
    collective_intelligence,
    health,
    hidden_job_market,
    interview_intelligence,
    observability,
    predictive_career,
    salary_intelligence,
    skill_decay,
    threat_radar,
    transition_pathways,
    users,
    well_known,
)
from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.llm_observability import initialize_observability
from app.core.logging_config import setup_logging
from app.core.middleware import BotTrapMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    # Startup
    setup_logging(debug=settings.debug)
    initialize_observability()
    yield
    # Shutdown


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
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # ── Routes ─────────────────────────────────────────────────
    # Well-known endpoints at root level (no /api/v1 prefix)
    application.include_router(well_known.router)

    # API routes
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(auth.router, prefix="/api/v1")
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
    application.include_router(observability.router, prefix="/api/v1")
    application.include_router(ai_transparency.router, prefix="/api/v1")

    return application


app = create_app()
