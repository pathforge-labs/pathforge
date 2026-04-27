"""
PathForge AI Engine — LLM Observability & AI Trust Layer™
==========================================================
In-memory metrics collector + Langfuse integration for LLM call tracing.
AI Trust Layer™ transparency infrastructure for user-facing explainability.

Env-gated: Langfuse disabled by default. Enable via LLM_OBSERVABILITY_ENABLED=true
and provide LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY in the environment.

Usage:
    from app.core.llm_observability import (
        initialize_observability,
        get_collector,
        get_transparency_log,
        compute_confidence_score,
        TransparencyRecord,
    )

    # At app startup:
    initialize_observability()

    # After each LLM call:
    get_collector().record_call(...)

    # After an AI analysis:
    record = TransparencyRecord(...)
    get_transparency_log().record(user_id=user_id, entry=record)
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


# ── Metrics Data Structures ────────────────────────────────────


@dataclass
class ModelMetrics:
    """Aggregated metrics for a single model/tier combination."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_latency_seconds: float = 0.0
    error_counts: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100.0

    @property
    def avg_latency_seconds(self) -> float:
        """Calculate average latency in seconds."""
        if self.successful_calls == 0:
            return 0.0
        return self.total_latency_seconds / self.successful_calls

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens consumed."""
        return self.total_prompt_tokens + self.total_completion_tokens

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.success_rate, 2),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "avg_latency_seconds": round(self.avg_latency_seconds, 4),
            "total_latency_seconds": round(self.total_latency_seconds, 4),
            "error_counts": dict(self.error_counts),
        }


# ── LLM Metrics Collector ─────────────────────────────────────


class LLMMetricsCollector:
    """Thread-safe in-memory LLM metrics aggregator.

    Collects per-model and per-tier call statistics without
    any external dependencies. Works regardless of whether
    Langfuse is enabled.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_model: dict[str, ModelMetrics] = {}
        self._by_tier: dict[str, ModelMetrics] = {}
        self._global = ModelMetrics()
        self._started_at: float = time.time()

    def record_call(
        self,
        *,
        model: str,
        tier: str,
        latency_seconds: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        success: bool = True,
        error_type: str | None = None,
    ) -> None:
        """Record a single LLM call's metrics.

        Args:
            model: The LLM model identifier (e.g., "anthropic/claude-sonnet-4-20250514").
            tier: The LLM tier used (e.g., "primary", "fast", "deep").
            latency_seconds: Wall-clock time for the call.
            prompt_tokens: Number of prompt tokens consumed.
            completion_tokens: Number of completion tokens generated.
            success: Whether the call succeeded.
            error_type: Error class name if the call failed.
        """
        with self._lock:
            for metrics in (
                self._global,
                self._by_model.setdefault(model, ModelMetrics()),
                self._by_tier.setdefault(tier, ModelMetrics()),
            ):
                metrics.total_calls += 1
                if success:
                    metrics.successful_calls += 1
                    metrics.total_latency_seconds += latency_seconds
                    metrics.total_prompt_tokens += prompt_tokens
                    metrics.total_completion_tokens += completion_tokens
                else:
                    metrics.failed_calls += 1
                    if error_type:
                        metrics.error_counts[error_type] = (
                            metrics.error_counts.get(error_type, 0) + 1
                        )

    def get_metrics(self) -> dict[str, Any]:
        """Return a snapshot of all collected metrics.

        Returns:
            A JSON-serializable dict with global, per-model, and per-tier breakdowns.
        """
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self._started_at, 2),
                "global": self._global.to_dict(),
                "by_model": {
                    model: metrics.to_dict()
                    for model, metrics in self._by_model.items()
                },
                "by_tier": {
                    tier: metrics.to_dict()
                    for tier, metrics in self._by_tier.items()
                },
            }

    def reset(self) -> None:
        """Clear all collected metrics. Useful for testing."""
        with self._lock:
            self._by_model.clear()
            self._by_tier.clear()
            self._global = ModelMetrics()
            self._started_at = time.time()


# ── Singleton Collector ────────────────────────────────────────

_collector: LLMMetricsCollector | None = None


def get_collector() -> LLMMetricsCollector:
    """Return the singleton LLMMetricsCollector instance.

    Creates the collector on first access (lazy initialization).
    """
    global _collector
    if _collector is None:
        _collector = LLMMetricsCollector()
    return _collector


# ── AI Trust Layer™ — Transparency Infrastructure ─────────────


CONFIDENCE_CAP = 0.95  # Never claim 100% confidence

# Tier confidence factors (primary is highest, fallback tiers slightly lower)
TIER_CONFIDENCE: dict[str, float] = {
    "primary": 1.0,
    "fast": 0.90,
    "deep": 0.95,
}


@dataclass
class TransparencyRecord:
    """Single AI analysis transparency record.

    Captures per-analysis metadata that enables users to understand
    how and why AI reached its conclusions. This is the core data
    structure of PathForge's AI Trust Layer™.
    """

    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    analysis_type: str = ""
    model: str = ""
    tier: str = ""
    confidence_score: float = 0.0
    confidence_label: str = ""
    data_sources: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    success: bool = True
    retries: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type,
            "model": self.model,
            "tier": self.tier,
            "confidence_score": round(self.confidence_score, 3),
            "confidence_label": self.confidence_label,
            "data_sources": list(self.data_sources),
            "tokens_used": self.prompt_tokens + self.completion_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "retries": self.retries,
            "timestamp": self.timestamp,
        }


def compute_confidence_score(
    *,
    tier: str,
    retries: int,
    latency_seconds: float,
    completion_tokens: int,
    max_tokens: int,
) -> float:
    """Compute algorithmic confidence from observable signals.

    PathForge never claims 100% confidence. The score reflects
    how reliably the AI pipeline executed — not the semantic
    correctness of the output (which requires human judgment).

    Factors:
        - Tier factor: primary=1.0, fast=0.90, deep=0.95
        - Retry penalty: 0 retries=1.0, 1=0.90, 2+=0.75
        - Latency factor: <2s=1.0, 2-5s=0.95, 5-10s=0.85, >10s=0.70
        - Token utilization: very high usage may indicate truncation

    Returns:
        Confidence score between 0.0 and CONFIDENCE_CAP (0.95).
    """
    # Factor 1: Model tier
    tier_factor = TIER_CONFIDENCE.get(tier, 0.85)

    # Factor 2: Retry penalty
    if retries == 0:
        retry_factor = 1.0
    elif retries == 1:
        retry_factor = 0.90
    else:
        retry_factor = 0.75

    # Factor 3: Latency
    if latency_seconds < 2.0:
        latency_factor = 1.0
    elif latency_seconds < 5.0:
        latency_factor = 0.95
    elif latency_seconds < 10.0:
        latency_factor = 0.85
    else:
        latency_factor = 0.70

    # Factor 4: Token utilization (high utilization → possible truncation)
    if max_tokens > 0 and completion_tokens > 0:
        utilization = completion_tokens / max_tokens
        if utilization > 0.95:
            token_factor = 0.80  # Likely truncated
        elif utilization > 0.85:
            token_factor = 0.90  # Near limit
        else:
            token_factor = 1.0
    else:
        token_factor = 1.0

    raw_score = tier_factor * retry_factor * latency_factor * token_factor
    return min(round(raw_score, 3), CONFIDENCE_CAP)


def confidence_label(score: float) -> str:
    """Convert numeric confidence to human-readable label.

    Args:
        score: Confidence score between 0.0 and 1.0.

    Returns:
        One of "High", "Medium", or "Low".
    """
    if score >= 0.85:
        return "High"
    if score >= 0.65:
        return "Medium"
    return "Low"


# ── Transparency Log (Per-User Circular Buffer) ───────────────


MAX_RECORDS_PER_USER = 200
MAX_TOTAL_USERS = 1000  # Prevent unbounded memory growth


class TransparencyLog:
    """Thread-safe per-user circular buffer for AI analysis records.

    Stores the last MAX_RECORDS_PER_USER transparency records per user,
    enabling the AI Trust Layer™ API to show recent AI analyses with
    full explainability metadata.

    Memory-bounded: caps at MAX_TOTAL_USERS × MAX_RECORDS_PER_USER.

    DB session factory injection
    ----------------------------

    The four DB-fallback methods (``_persist_to_db``,
    ``_load_recent_from_db``, ``_load_by_id_from_db``,
    ``_load_user_for_analysis_from_db``) call
    ``app.core.database.async_session_factory`` by default. Passing an
    explicit ``session_factory`` to ``__init__`` overrides that — used
    by the SQLite round-trip tests so they exercise the real ORM path
    without standing up a Postgres container. Production code never
    sets this argument; the lazy ``import`` at call site preserves
    backward compatibility with the singleton at module bottom.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, list[TransparencyRecord]] = defaultdict(list)
        self._index: dict[str, TransparencyRecord] = {}
        self._total_recorded: int = 0
        self._started_at: float = time.time()
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._persistence_failures: int = 0
        self._session_factory: async_sessionmaker[AsyncSession] | None = (
            session_factory
        )

    def _get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the injected factory, falling back to the production
        singleton. Imported lazily so tests that never touch DB code
        don't pay the import cost."""
        if self._session_factory is not None:
            return self._session_factory
        from app.core.database import async_session_factory

        return async_session_factory

    def record(
        self,
        *,
        user_id: str,
        entry: TransparencyRecord,
    ) -> None:
        """Add a transparency record for a user.

        Maintains a circular buffer — oldest records are evicted
        when the per-user cap is reached.

        Args:
            user_id: The user's UUID as string.
            entry: The transparency record to store.
        """
        with self._lock:
            user_records = self._records[user_id]

            # Evict oldest if at capacity
            if len(user_records) >= MAX_RECORDS_PER_USER:
                evicted = user_records.pop(0)
                self._index.pop(evicted.analysis_id, None)

            # Prevent unbounded user growth
            if (
                user_id not in self._records
                and len(self._records) >= MAX_TOTAL_USERS
            ):
                # Evict the user with the fewest records
                least_user = min(
                    self._records, key=lambda uid: len(self._records[uid]),
                )
                for old_rec in self._records.pop(least_user):
                    self._index.pop(old_rec.analysis_id, None)

            user_records.append(entry)
            self._index[entry.analysis_id] = entry
            self._total_recorded += 1

        # Fire-and-forget DB persistence — never blocks the in-memory path
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self._persist_to_db(user_id=user_id, entry=entry),
            )
            # prevent GC before completion; callback removes on done
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except RuntimeError:
            # No running event loop (e.g., during sync tests)
            logger.debug("No event loop — skipping DB persistence")

    async def _persist_to_db(
        self,
        *,
        user_id: str,
        entry: TransparencyRecord,
    ) -> None:
        """Persist a transparency record to the database.

        Graceful degradation: DB write failures are logged
        but never propagate — the in-memory buffer is the
        primary source during process lifetime.
        """
        try:
            from app.models.ai_transparency import (
                AITransparencyRecord as DBRecord,
            )

            # Synchronise ``created_at`` with the analysis-time
            # ``entry.timestamp`` rather than letting the server
            # default fire at INSERT time. The two were drifting:
            # ``entry.timestamp`` is set when the analysis was
            # captured in memory; ``created_at`` would otherwise be
            # set at the (later, fire-and-forget) DB write. The AI
            # Trust Layer™ surfaces this timestamp to users — a
            # record reconstructed via ``_load_recent_from_db`` would
            # show a *later* timestamp than the same record served
            # from the in-memory buffer. Now the two paths agree.
            async with self._get_session_factory()() as session:
                db_record = DBRecord(
                    user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
                    created_at=datetime.fromisoformat(entry.timestamp),
                    analysis_id=entry.analysis_id,
                    analysis_type=entry.analysis_type,
                    model=entry.model,
                    tier=entry.tier,
                    confidence_score=entry.confidence_score,
                    confidence_label=entry.confidence_label,
                    data_sources=list(entry.data_sources),
                    prompt_tokens=entry.prompt_tokens,
                    completion_tokens=entry.completion_tokens,
                    latency_ms=entry.latency_ms,
                    success=entry.success,
                    retries=entry.retries,
                )
                session.add(db_record)
                await session.commit()
                logger.debug(
                    "Persisted transparency record %s to DB",
                    entry.analysis_id,
                )
        except Exception:
            self._persistence_failures += 1
            logger.warning(
                "Failed to persist transparency record %s — "
                "in-memory record retained (total failures: %d)",
                entry.analysis_id,
                self._persistence_failures,
                exc_info=True,
            )

    async def get_recent(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[TransparencyRecord]:
        """Get most recent analyses for a user.

        Falls back to database query when in-memory buffer
        is empty (e.g., after process restart).

        Args:
            user_id: The user's UUID as string.
            limit: Max records to return (capped at 50).

        Returns:
            List of records, newest first.
        """
        limit = min(limit, 50)
        with self._lock:
            records = self._records.get(user_id, [])
            if records:
                return list(reversed(records[-limit:]))

        # Fallback: query DB for records not yet in memory
        return await self._load_recent_from_db(user_id=user_id, limit=limit)

    async def _load_recent_from_db(
        self,
        *,
        user_id: str,
        limit: int,
    ) -> list[TransparencyRecord]:
        """Load recent transparency records from the database.

        Graceful degradation: returns empty list on DB failure.
        """
        try:
            from sqlalchemy import select

            from app.models.ai_transparency import (
                AITransparencyRecord as DBRecord,
            )

            async with self._get_session_factory()() as session:
                stmt = (
                    select(DBRecord)
                    .where(DBRecord.user_id == uuid.UUID(user_id))
                    .order_by(DBRecord.created_at.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                db_records = result.scalars().all()

                return [
                    TransparencyRecord(
                        analysis_id=str(record.analysis_id),
                        analysis_type=record.analysis_type,
                        model=record.model,
                        tier=record.tier,
                        confidence_score=record.confidence_score,
                        confidence_label=record.confidence_label,
                        data_sources=list(record.data_sources),
                        prompt_tokens=record.prompt_tokens,
                        completion_tokens=record.completion_tokens,
                        latency_ms=record.latency_ms,
                        success=record.success,
                        retries=record.retries,
                        timestamp=record.created_at.isoformat(),
                    )
                    for record in db_records
                ]
        except Exception:
            logger.warning(
                "DB fallback failed for get_recent (user=%s)",
                user_id,
                exc_info=True,
            )
            return []

    async def get_by_id(self, analysis_id: str) -> TransparencyRecord | None:
        """Retrieve a specific analysis by its ID.

        Falls back to database query when the analysis is not
        found in-memory (e.g., after process restart).

        Args:
            analysis_id: The unique analysis identifier.

        Returns:
            The matching TransparencyRecord, or None.
        """
        with self._lock:
            record = self._index.get(analysis_id)
            if record is not None:
                return record

        # Fallback: query DB
        return await self._load_by_id_from_db(analysis_id)

    async def _load_by_id_from_db(
        self,
        analysis_id: str,
    ) -> TransparencyRecord | None:
        """Load a single transparency record from the database by analysis ID."""
        try:
            from sqlalchemy import select

            from app.models.ai_transparency import (
                AITransparencyRecord as DBRecord,
            )

            async with self._get_session_factory()() as session:
                stmt = select(DBRecord).where(
                    DBRecord.analysis_id == analysis_id,
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record is None:
                    return None

                return TransparencyRecord(
                    analysis_id=str(record.analysis_id),
                    analysis_type=record.analysis_type,
                    model=record.model,
                    tier=record.tier,
                    confidence_score=record.confidence_score,
                    confidence_label=record.confidence_label,
                    data_sources=list(record.data_sources),
                    prompt_tokens=record.prompt_tokens,
                    completion_tokens=record.completion_tokens,
                    latency_ms=record.latency_ms,
                    success=record.success,
                    retries=record.retries,
                    timestamp=record.created_at.isoformat(),
                )
        except Exception:
            logger.warning(
                "DB fallback failed for get_by_id (analysis=%s)",
                analysis_id,
                exc_info=True,
            )
            return None

    async def get_user_for_analysis(self, analysis_id: str) -> str | None:
        """Find which user owns a given analysis record.

        Falls back to database query when the analysis is not
        found in-memory.

        Args:
            analysis_id: The unique analysis identifier.

        Returns:
            The user_id string, or None if not found.
        """
        with self._lock:
            for user_id, records in self._records.items():
                for record in records:
                    if record.analysis_id == analysis_id:
                        return user_id

        # Fallback: query DB
        return await self._load_user_for_analysis_from_db(analysis_id)

    async def _load_user_for_analysis_from_db(
        self,
        analysis_id: str,
    ) -> str | None:
        """Look up the user who owns an analysis record from the database."""
        try:
            from sqlalchemy import select

            from app.models.ai_transparency import (
                AITransparencyRecord as DBRecord,
            )

            async with self._get_session_factory()() as session:
                stmt = select(DBRecord.user_id).where(
                    DBRecord.analysis_id == analysis_id,
                )
                result = await session.execute(stmt)
                user_id = result.scalar_one_or_none()
                return str(user_id) if user_id is not None else None
        except Exception:
            logger.warning(
                "DB fallback failed for get_user_for_analysis (analysis=%s)",
                analysis_id,
                exc_info=True,
            )
            return None

    def get_system_health(self) -> dict[str, Any]:
        """Compute AI system health summary.

        Returns aggregated statistics suitable for the public
        health endpoint (no user-specific data exposed).

        Returns:
            Dict with system status, success rate, latency, etc.
        """
        with self._lock:
            all_records: list[TransparencyRecord] = []
            for user_records in self._records.values():
                all_records.extend(user_records)

            total = len(all_records)
            successful = sum(1 for record in all_records if record.success)
            success_rate = (successful / total * 100.0) if total > 0 else 100.0

            avg_latency_ms = 0.0
            if total > 0:
                avg_latency_ms = sum(
                    record.latency_ms for record in all_records
                ) / total

            # Determine system status
            if success_rate >= 95.0:
                status = "operational"
            elif success_rate >= 80.0:
                status = "degraded"
            else:
                status = "unavailable"

            last_analysis: str | None = None
            if all_records:
                last_analysis = max(
                    record.timestamp for record in all_records
                )

            return {
                "system_status": status,
                "total_analyses": self._total_recorded,
                "analyses_in_memory": total,
                "success_rate": round(success_rate, 2),
                "avg_latency_ms": round(avg_latency_ms, 1),
                "uptime_seconds": round(time.time() - self._started_at, 2),
                "last_analysis_at": last_analysis,
                "active_users": len(self._records),
                "pending_persistence_tasks": len(self._background_tasks),
                "persistence_failures": self._persistence_failures,
            }

    @property
    def pending_persistence_count(self) -> int:
        """Number of background DB persistence tasks still running."""
        return len(self._background_tasks)

    async def drain(self, *, timeout_seconds: float = 5.0) -> None:
        """Wait for pending DB persistence tasks to finish.

        Sprint 39 audit A-M2: ``_persist`` schedules fire-and-forget
        background tasks via ``loop.create_task``. Without a drain
        step on shutdown, the engine in ``main.lifespan`` is disposed
        while those tasks are mid-write — they then fail with
        "engine disposed" and the persistence-failure counter spikes
        on every restart.

        Call this from ``lifespan`` *before* ``engine.dispose()``.
        Bounded by ``timeout_seconds`` so a slow DB cannot hold the
        process indefinitely; tasks still pending when the timeout
        fires are cancelled and logged.
        """
        if not self._background_tasks:
            return
        pending = list(self._background_tasks)
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            still_running = [t for t in pending if not t.done()]
            for task in still_running:
                task.cancel()
            logger.warning(
                "TransparencyLog.drain: %d task(s) cancelled after %.1fs timeout",
                len(still_running), timeout_seconds,
            )

    def reset(self) -> None:
        """Clear all records. For testing only."""
        with self._lock:
            self._records.clear()
            self._index.clear()
            self._total_recorded = 0
            self._started_at = time.time()
            self._background_tasks.clear()
            self._persistence_failures = 0


# ── Singleton Transparency Log ─────────────────────────────────

_transparency_log: TransparencyLog | None = None


def get_transparency_log() -> TransparencyLog:
    """Return the singleton TransparencyLog instance.

    Creates the log on first access (lazy initialization).
    """
    global _transparency_log
    if _transparency_log is None:
        _transparency_log = TransparencyLog()
    return _transparency_log


# ── Initialization ─────────────────────────────────────────────


def initialize_observability() -> None:
    """Configure LLM observability at application startup.

    When ``LLM_OBSERVABILITY_ENABLED=true`` and Langfuse credentials
    are provided, this function:

    1. Sets ``LANGFUSE_*`` environment variables (LiteLLM reads these).
    2. Registers Langfuse as a LiteLLM success/failure callback.
    3. Applies production guardrails (Sprint 29):
       - Sampling rate: only trace N% of calls (default 10%)
       - PII redaction: scrub prompts/completions before sending
       - Always-trace-on-error: errors bypass sampling rate
       - Force-trace: x-pathforge-trace header overrides sampling

    When disabled (default), this function is a safe no-op.
    The in-memory collector and transparency log are always initialized.
    """
    # Always initialize in-memory infrastructure
    get_collector()
    get_transparency_log()

    if not settings.llm_observability_enabled:
        logger.info("LLM observability: disabled (default)")
        return

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning(
            "LLM observability: enabled but LANGFUSE_PUBLIC_KEY / "
            "LANGFUSE_SECRET_KEY not set — skipping Langfuse setup"
        )
        return

    # Set env vars for LiteLLM's built-in Langfuse integration
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = settings.langfuse_host

    # Sampling rate: LiteLLM supports LANGFUSE_SAMPLE_RATE env var
    sample_rate = settings.langfuse_sampling_rate
    os.environ["LANGFUSE_SAMPLE_RATE"] = str(sample_rate)

    try:
        import litellm

        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]

        # Register PII redaction pre-call hook if enabled
        if settings.langfuse_pii_redaction:
            _register_pii_redaction_hook()

        logger.info(
            "LLM observability: Langfuse enabled → %s (sample_rate=%.0f%%, pii_redaction=%s)",
            settings.langfuse_host,
            sample_rate * 100,
            settings.langfuse_pii_redaction,
        )
    except ImportError:
        logger.warning(
            "LLM observability: litellm not installed — "
            "Langfuse callbacks not registered"
        )


def _register_pii_redaction_hook() -> None:
    """Register a LiteLLM pre-call hook that redacts PII from messages.

    This ensures no PII reaches Langfuse traces. The redaction
    happens in-flight — the original LLM call uses unredacted text.
    """
    import copy

    import litellm

    from app.core.pii_redactor import redact_pii

    original_input_hook = getattr(litellm, "input_callback", None)

    def _redact_input(model: str, messages: list[dict[str, str]], kwargs: dict[str, Any]) -> None:
        """Redact PII from messages before they are sent to Langfuse.

        Sprint 39 audit A-H3: the previous implementation mutated
        ``kwargs["messages"]`` in place, assuming LiteLLM passes a
        copy to ``input_callback``. That assumption is version-
        specific — if LiteLLM ever stops copying, the redacted strings
        would leak into the actual upstream LLM call and silently
        degrade completion quality (e.g. resume parsing depends on
        seeing real emails/phones to extract structure).
        Defensively deep-copy ``messages`` before redacting; the
        Langfuse trace receives the redacted view, the upstream
        provider receives the originals.
        """
        # Redact message content on a defensive deep copy
        if "messages" in kwargs and isinstance(kwargs["messages"], list):
            redacted_messages = copy.deepcopy(kwargs["messages"])
            for msg in redacted_messages:
                if "content" in msg and isinstance(msg["content"], str):
                    msg["content"] = redact_pii(msg["content"])
            kwargs["messages"] = redacted_messages

        # Tag with redaction metadata (kwargs is callback-local; the
        # ``litellm_params.metadata`` dict however IS shared with the
        # provider call, so we set the flag on a derived copy too —
        # but the boolean flag carries no payload, only a tag).
        metadata = kwargs.get("litellm_params", {}).get("metadata", {})
        metadata["pii_redacted"] = True

        # Call original hook if exists
        if callable(original_input_hook):
            original_input_hook(model, messages, kwargs)

    litellm.input_callback = [_redact_input]
    logger.info("PII redaction hook registered for Langfuse traces")

