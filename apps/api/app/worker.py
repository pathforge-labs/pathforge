"""
PathForge — ARQ Background Worker
===================================
Async task queue powered by ARQ (Redis-based).

Handles background processing of expensive AI operations:
- Resume parsing & embedding generation
- Job matching pipelines
- CV tailoring

Usage (local):
    python -m arq app.worker.WorkerSettings

Usage (Docker):
    CMD ["python", "-m", "arq", "app.worker.WorkerSettings"]
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Task Functions ─────────────────────────────────────────────


async def generate_embeddings(ctx: dict[str, Any], resume_id: str) -> dict[str, Any]:
    """Generate vector embeddings for a parsed resume."""
    logger.info("Generating embeddings for resume %s", resume_id)

    try:
        # Lazy import to keep worker startup fast
        from app.services.ai_service import AIService

        result = await AIService.generate_embeddings(resume_id)
        logger.info("Embeddings generated for resume %s", resume_id)
        return {"status": "completed", "resume_id": resume_id, "result": result}
    except Exception:
        logger.exception("Failed to generate embeddings for resume %s", resume_id)
        raise  # ARQ will retry based on WorkerSettings


async def process_resume(ctx: dict[str, Any], resume_id: str) -> dict[str, Any]:
    """Parse a resume and extract structured data."""
    logger.info("Processing resume %s", resume_id)

    try:
        from app.services.ai_service import AIService

        result = await AIService.parse_resume(resume_id)
        logger.info("Resume %s processed successfully", resume_id)
        return {"status": "completed", "resume_id": resume_id, "result": result}
    except Exception:
        logger.exception("Failed to process resume %s", resume_id)
        raise


async def run_matching_pipeline(
    ctx: dict[str, Any], user_id: str, job_listing_id: str
) -> dict[str, Any]:
    """Run the AI matching pipeline for a user against a job listing."""
    logger.info("Running matching pipeline: user=%s, job=%s", user_id, job_listing_id)

    try:
        from app.services.ai_service import AIService

        result = await AIService.match_candidate(user_id, job_listing_id)
        logger.info("Matching complete: user=%s, job=%s", user_id, job_listing_id)
        return {
            "status": "completed",
            "user_id": user_id,
            "job_listing_id": job_listing_id,
            "result": result,
        }
    except Exception:
        logger.exception(
            "Matching pipeline failed: user=%s, job=%s", user_id, job_listing_id
        )
        raise


# ── Health Check (Cron) ────────────────────────────────────────


async def worker_health_check(ctx: dict[str, Any]) -> str:
    """Periodic health check — logs that the worker is alive."""
    logger.info("Worker health check: OK")
    return "healthy"


# ── Startup / Shutdown Hooks ──────────────────────────────────


async def startup(ctx: dict[str, Any]) -> None:
    """Called when the worker starts."""
    logger.info("PathForge ARQ worker starting up")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Called when the worker shuts down."""
    logger.info("PathForge ARQ worker shutting down")


# ── Worker Configuration ──────────────────────────────────────


def _parse_redis_settings() -> RedisSettings:
    """Parse the Redis URL from application settings into ARQ RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
        ssl=settings.redis_ssl,
        conn_timeout=settings.redis_socket_timeout,
    )


class WorkerSettings:
    """ARQ worker configuration."""

    functions: ClassVar[list[Any]] = [generate_embeddings, process_resume, run_matching_pipeline]
    cron_jobs: ClassVar[list[Any]] = [
        cron(worker_health_check, minute={0, 15, 30, 45}),
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = _parse_redis_settings()

    # Retry configuration
    max_tries = 3
    job_timeout = timedelta(minutes=5)
    retry_delay = timedelta(seconds=30)

    # Queue settings
    queue_name = "pathforge:default"
    health_check_interval = 60
