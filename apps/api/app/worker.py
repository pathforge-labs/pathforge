"""
PathForge — ARQ Background Worker
===================================
Async task queue powered by ARQ (Redis-based).

Handles background processing of expensive AI operations:
- Resume parsing & embedding generation
- Job matching pipelines
- Job aggregation (cron)

Sprint 30: Structured logging, job aggregation cron,
ARQ dead letter queue, configurable pool sizing.

Usage (local):
    python -m arq app.worker.WorkerSettings

Usage (Docker):
    CMD ["python", "-m", "arq", "app.worker.WorkerSettings"]
"""

from __future__ import annotations

import json
import traceback
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings

logger = structlog.get_logger(__name__)


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


# ── Sprint 36 WS-6: Intelligence Recalculation ───────────────


async def recalculate_intelligence(
    ctx: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Recalculate career intelligence after target role change."""
    logger.info("Recalculating intelligence for user %s", user_id)

    try:
        from app.services.career_dna_service import CareerDNAService

        result = await CareerDNAService.recalculate_growth_vector(user_id)
        logger.info(
            "Intelligence recalculation completed for user %s", user_id
        )
        return {"status": "completed", "user_id": user_id, "result": result}
    except Exception:
        logger.exception(
            "Intelligence recalculation failed for user %s", user_id
        )
        raise


# ── Health Check + Job Aggregation (Cron) ─────────────────────


async def worker_health_check(ctx: dict[str, Any]) -> str:
    """Periodic health check — logs that the worker is alive."""
    logger.info("Worker health check: OK")
    return "healthy"


async def run_job_aggregation(ctx: dict[str, Any]) -> dict[str, Any]:
    """Aggregate jobs from external providers (cron task, Sprint 30 WS-7)."""
    logger.info("Starting job aggregation cron")

    try:
        from app.services.jobs_ingestion_service import JobsIngestionService

        service = JobsIngestionService()
        result = await service.aggregate_jobs(
            batch_size=settings.aggregation_batch_size,
        )
        logger.info(
            "Job aggregation completed",
            jobs_processed=result.get("processed", 0),
        )
        return {"status": "completed", **result}
    except Exception:
        logger.exception("Job aggregation cron failed")
        raise


# ── Dead Letter Queue (Sprint 30 WS-7) ───────────────────────

DEAD_LETTER_KEY = "pathforge:dead_letters"


async def on_job_failure(
    ctx: dict[str, Any],
    job_id: str,
    function_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    exception: BaseException,
) -> None:
    """Callback when a job exhausts all retries — push to dead letter queue."""
    redis = ctx.get("redis")
    if redis is None:
        logger.error("Cannot write to DLQ: no Redis connection in context")
        return

    dead_letter = {
        "job_id": job_id,
        "function": function_name,
        "args": [str(a) for a in args],
        "error": str(exception),
        "traceback": traceback.format_exception(exception)[-3:],
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        await redis.rpush(DEAD_LETTER_KEY, json.dumps(dead_letter))
        logger.warning(
            "Job pushed to dead letter queue",
            job_id=job_id,
            function=function_name,
            error=str(exception),
        )
    except Exception:
        logger.exception("Failed to write to dead letter queue")


# ── Startup / Shutdown Hooks ──────────────────────────────────


async def startup(ctx: dict[str, Any]) -> None:
    """Called when the worker starts. Initializes structured logging."""
    from app.core.logging_config import setup_logging

    setup_logging()
    logger.info(
        "PathForge ARQ worker started",
        max_jobs=settings.worker_max_jobs,
        queue="pathforge:default",
    )


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
    """ARQ worker configuration (Sprint 30: configurable pool sizing)."""

    functions: ClassVar[list[Any]] = [
        generate_embeddings,
        process_resume,
        run_matching_pipeline,
        recalculate_intelligence,  # Sprint 36 WS-6
    ]
    cron_jobs: ClassVar[list[Any]] = [
        cron(worker_health_check, minute={0, 15, 30, 45}),
        # Sprint 30 WS-7: Job aggregation cron (4x daily)
        cron(run_job_aggregation, hour={0, 6, 12, 18}, minute={5}),
    ]

    on_startup = startup
    on_shutdown = shutdown
    on_job_failure = on_job_failure  # Sprint 30 WS-7: Dead letter queue

    redis_settings = _parse_redis_settings()

    # Retry configuration
    max_tries = 3
    job_timeout = timedelta(minutes=5)
    retry_delay = timedelta(seconds=30)

    # Pool sizing (Sprint 30 WS-7: configurable concurrency)
    max_jobs = settings.worker_max_jobs
    max_burst_jobs = settings.worker_max_burst_jobs

    # Queue settings
    queue_name = "pathforge:default"
    health_check_interval = 60
