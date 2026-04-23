"""
Unit tests for app.worker (ARQ background worker).

Covers:
- worker_health_check
- on_job_failure (no redis, redis success, redis failure)
- startup / shutdown hooks
- _parse_redis_settings (SSL on/off, default hostname/port/db)
- generate_embeddings (success + exception)
- process_resume (success + exception)
- run_matching_pipeline (success + exception)
- run_job_aggregation (success + exception)
- recalculate_intelligence (success + exception)
- WorkerSettings class attributes / configuration surface
"""

from __future__ import annotations

import json

# ── Lazy-import support ──────────────────────────────────────────
#
# The worker module does `from app.services.ai_service import AIService` and
# friends inside function bodies. Those service modules do not currently
# exist in the codebase (they are scaffolded). We stub them into
# sys.modules so the lazy imports resolve to MagicMock classes we control.
import sys
import types
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.connections import RedisSettings

from app import worker as worker_module


def _install_fake_module(dotted_name: str, attrs: dict[str, Any]) -> types.ModuleType:
    """Create (or reuse) a fake module at `dotted_name` with the given attrs."""
    module = sys.modules.get(dotted_name)
    if module is None:
        module = types.ModuleType(dotted_name)
        sys.modules[dotted_name] = module
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


@pytest.fixture
def fake_ai_service() -> Any:
    """Install a fake `app.services.ai_service.AIService` with async methods."""
    ai_service = MagicMock()
    ai_service.generate_embeddings = AsyncMock()
    ai_service.parse_resume = AsyncMock()
    ai_service.match_candidate = AsyncMock()
    _install_fake_module(
        "app.services.ai_service", {"AIService": ai_service},
    )
    yield ai_service
    sys.modules.pop("app.services.ai_service", None)


@pytest.fixture
def fake_jobs_ingestion() -> Any:
    """Install a fake `app.services.jobs_ingestion_service.JobsIngestionService`."""
    instance = MagicMock()
    instance.aggregate_jobs = AsyncMock()
    cls = MagicMock(return_value=instance)
    _install_fake_module(
        "app.services.jobs_ingestion_service",
        {"JobsIngestionService": cls},
    )
    yield cls, instance
    sys.modules.pop("app.services.jobs_ingestion_service", None)
from app.worker import (
    DEAD_LETTER_KEY,
    WorkerSettings,
    _parse_redis_settings,
    generate_embeddings,
    on_job_failure,
    process_resume,
    recalculate_intelligence,
    run_job_aggregation,
    run_matching_pipeline,
    shutdown,
    startup,
    worker_health_check,
)

# ── worker_health_check ──────────────────────────────────────────


class TestWorkerHealthCheck:
    async def test_returns_healthy_string(self) -> None:
        result = await worker_health_check({})
        assert result == "healthy"

    async def test_ignores_ctx_contents(self) -> None:
        result = await worker_health_check({"redis": object(), "foo": "bar"})
        assert result == "healthy"


# ── on_job_failure ───────────────────────────────────────────────


class TestOnJobFailure:
    async def test_returns_early_when_redis_missing(self) -> None:
        ctx: dict[str, Any] = {}
        # Should not raise even though ctx has no "redis" key.
        result = await on_job_failure(
            ctx,
            job_id="job-1",
            function_name="some_fn",
            args=(),
            kwargs={},
            exception=RuntimeError("boom"),
        )
        assert result is None

    async def test_returns_early_when_redis_is_none(self) -> None:
        ctx: dict[str, Any] = {"redis": None}
        result = await on_job_failure(
            ctx,
            job_id="job-2",
            function_name="f",
            args=("a",),
            kwargs={},
            exception=ValueError("bad"),
        )
        assert result is None

    async def test_pushes_to_dead_letter_queue_on_redis_present(self) -> None:
        redis = MagicMock()
        redis.rpush = AsyncMock(return_value=1)
        ctx: dict[str, Any] = {"redis": redis}

        exc = RuntimeError("kaboom")
        await on_job_failure(
            ctx,
            job_id="job-123",
            function_name="process_resume",
            args=("resume-abc",),
            kwargs={"x": 1},
            exception=exc,
        )

        redis.rpush.assert_awaited_once()
        call_args = redis.rpush.call_args
        assert call_args.args[0] == DEAD_LETTER_KEY
        payload = json.loads(call_args.args[1])
        assert payload["job_id"] == "job-123"
        assert payload["function"] == "process_resume"
        assert payload["args"] == ["resume-abc"]
        assert payload["error"] == "kaboom"
        assert "timestamp" in payload
        assert isinstance(payload["traceback"], list)

    async def test_stringifies_non_string_args(self) -> None:
        redis = MagicMock()
        redis.rpush = AsyncMock(return_value=1)
        ctx: dict[str, Any] = {"redis": redis}

        await on_job_failure(
            ctx,
            job_id="job-x",
            function_name="fn",
            args=(42, {"k": "v"}, None),
            kwargs={},
            exception=Exception("e"),
        )

        payload = json.loads(redis.rpush.call_args.args[1])
        assert payload["args"] == ["42", "{'k': 'v'}", "None"]

    async def test_logs_when_rpush_raises(self) -> None:
        redis = MagicMock()
        redis.rpush = AsyncMock(side_effect=RuntimeError("redis down"))
        ctx: dict[str, Any] = {"redis": redis}

        # Should not re-raise; it logs the exception.
        with patch.object(worker_module.logger, "exception") as log_exc:
            result = await on_job_failure(
                ctx,
                job_id="job-err",
                function_name="fn",
                args=(),
                kwargs={},
                exception=Exception("orig"),
            )

        assert result is None
        log_exc.assert_called_once()

    async def test_dead_letter_key_constant(self) -> None:
        assert DEAD_LETTER_KEY == "pathforge:dead_letters"


# ── startup / shutdown ───────────────────────────────────────────


class TestStartup:
    async def test_startup_calls_setup_logging(self) -> None:
        with patch("app.core.logging_config.setup_logging") as mock_setup:
            await startup({})
        mock_setup.assert_called_once()

    async def test_startup_returns_none(self) -> None:
        with patch("app.core.logging_config.setup_logging"):
            result = await startup({})
        assert result is None


class TestShutdown:
    async def test_shutdown_returns_none(self) -> None:
        result = await shutdown({})
        assert result is None

    async def test_shutdown_logs(self) -> None:
        with patch.object(worker_module.logger, "info") as log_info:
            await shutdown({})
        log_info.assert_called_once()


# ── _parse_redis_settings ────────────────────────────────────────


class TestParseRedisSettings:
    def test_returns_redis_settings_instance(self) -> None:
        result = _parse_redis_settings()
        assert isinstance(result, RedisSettings)

    def test_uses_default_hostname_when_missing(self) -> None:
        fake = MagicMock()
        fake.redis_url = "redis:///0"  # no host component
        fake.redis_ssl_enabled = False
        fake.redis_socket_timeout = 5
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.host == "localhost"

    def test_uses_default_port_when_missing(self) -> None:
        fake = MagicMock()
        fake.redis_url = "redis://somehost/0"
        fake.redis_ssl_enabled = False
        fake.redis_socket_timeout = 5
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.port == 6379

    def test_ssl_disabled_when_flag_false(self) -> None:
        fake = MagicMock()
        fake.redis_url = "redis://example.com:6379/0"
        fake.redis_ssl_enabled = False
        fake.redis_socket_timeout = 10
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.ssl is False
        assert result.ssl_check_hostname is False

    def test_ssl_enabled_when_flag_true(self) -> None:
        fake = MagicMock()
        fake.redis_url = "rediss://example.com:6380/1"
        fake.redis_ssl_enabled = True
        fake.redis_socket_timeout = 5
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.ssl is True
        assert result.ssl_check_hostname is True

    def test_parses_password_and_database(self) -> None:
        fake = MagicMock()
        fake.redis_url = "redis://:secret@example.com:6379/3"
        fake.redis_ssl_enabled = False
        fake.redis_socket_timeout = 5
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.password == "secret"
        assert result.database == 3

    def test_parses_host_and_port(self) -> None:
        fake = MagicMock()
        fake.redis_url = "redis://cache.internal:6399/2"
        fake.redis_ssl_enabled = False
        fake.redis_socket_timeout = 5
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.host == "cache.internal"
        assert result.port == 6399
        assert result.database == 2

    def test_conn_timeout_uses_socket_timeout_setting(self) -> None:
        fake = MagicMock()
        fake.redis_url = "redis://localhost:6379/0"
        fake.redis_ssl_enabled = False
        fake.redis_socket_timeout = 17
        with patch("app.worker.settings", fake):
            result = _parse_redis_settings()
        assert result.conn_timeout == 17


# ── generate_embeddings ──────────────────────────────────────────


class TestGenerateEmbeddings:
    async def test_success_returns_completed_status(
        self, fake_ai_service: Any,
    ) -> None:
        fake_ai_service.generate_embeddings.return_value = {"dim": 1536}
        result = await generate_embeddings({}, "resume-1")
        assert result == {
            "status": "completed",
            "resume_id": "resume-1",
            "result": {"dim": 1536},
        }
        fake_ai_service.generate_embeddings.assert_awaited_once_with("resume-1")

    async def test_reraises_on_failure(self, fake_ai_service: Any) -> None:
        fake_ai_service.generate_embeddings.side_effect = RuntimeError("llm failed")
        with pytest.raises(RuntimeError, match="llm failed"):
            await generate_embeddings({}, "resume-err")

    async def test_logs_exception_on_failure(
        self, fake_ai_service: Any,
    ) -> None:
        fake_ai_service.generate_embeddings.side_effect = ValueError("bad")
        with patch.object(worker_module.logger, "exception") as log_exc, pytest.raises(ValueError):
            await generate_embeddings({}, "resume-err2")
        log_exc.assert_called_once()


# ── process_resume ───────────────────────────────────────────────


class TestProcessResume:
    async def test_success_returns_completed_status(
        self, fake_ai_service: Any,
    ) -> None:
        fake_ai_service.parse_resume.return_value = {"skills": ["python"]}
        result = await process_resume({}, "resume-2")
        assert result == {
            "status": "completed",
            "resume_id": "resume-2",
            "result": {"skills": ["python"]},
        }
        fake_ai_service.parse_resume.assert_awaited_once_with("resume-2")

    async def test_reraises_on_failure(self, fake_ai_service: Any) -> None:
        fake_ai_service.parse_resume.side_effect = RuntimeError("parse failed")
        with pytest.raises(RuntimeError, match="parse failed"):
            await process_resume({}, "resume-err")


# ── run_matching_pipeline ────────────────────────────────────────


class TestRunMatchingPipeline:
    async def test_success_returns_completed_status(
        self, fake_ai_service: Any,
    ) -> None:
        fake_ai_service.match_candidate.return_value = {"score": 0.92}
        result = await run_matching_pipeline({}, "user-1", "job-1")
        assert result == {
            "status": "completed",
            "user_id": "user-1",
            "job_listing_id": "job-1",
            "result": {"score": 0.92},
        }
        fake_ai_service.match_candidate.assert_awaited_once_with("user-1", "job-1")

    async def test_reraises_on_failure(self, fake_ai_service: Any) -> None:
        fake_ai_service.match_candidate.side_effect = RuntimeError("match failed")
        with pytest.raises(RuntimeError, match="match failed"):
            await run_matching_pipeline({}, "user-e", "job-e")


# ── run_job_aggregation ──────────────────────────────────────────


class TestRunJobAggregation:
    async def test_success_returns_completed_with_result_fields(
        self, fake_jobs_ingestion: Any,
    ) -> None:
        _cls, instance = fake_jobs_ingestion
        instance.aggregate_jobs.return_value = {"processed": 5, "errors": 0}

        result = await run_job_aggregation({})

        assert result["status"] == "completed"
        assert result["processed"] == 5
        assert result["errors"] == 0
        cls.assert_called_once_with()
        instance.aggregate_jobs.assert_awaited_once()

    async def test_uses_configured_batch_size(
        self, fake_jobs_ingestion: Any,
    ) -> None:
        _cls, instance = fake_jobs_ingestion
        instance.aggregate_jobs.return_value = {"processed": 0}

        fake_settings = MagicMock()
        fake_settings.aggregation_batch_size = 42

        with patch("app.worker.settings", fake_settings):
            await run_job_aggregation({})

        instance.aggregate_jobs.assert_awaited_once_with(batch_size=42)

    async def test_reraises_on_failure(
        self, fake_jobs_ingestion: Any,
    ) -> None:
        _cls, instance = fake_jobs_ingestion
        instance.aggregate_jobs.side_effect = RuntimeError("agg failed")
        with pytest.raises(RuntimeError, match="agg failed"):
            await run_job_aggregation({})

    async def test_handles_missing_processed_key(
        self, fake_jobs_ingestion: Any,
    ) -> None:
        _cls, instance = fake_jobs_ingestion
        instance.aggregate_jobs.return_value = {}
        result = await run_job_aggregation({})
        assert result["status"] == "completed"


# ── recalculate_intelligence ─────────────────────────────────────


class _FakeAsyncSessionCM:
    """Async context manager stand-in for async_session_factory()."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def __aenter__(self) -> Any:
        return self._session

    async def __aexit__(self, *exc: Any) -> None:
        return None


class TestRecalculateIntelligence:
    async def test_success_returns_completed_status(self) -> None:
        session = MagicMock()
        session.commit = AsyncMock()

        career_dna = MagicMock()
        career_dna.version = 7

        with patch(
            "app.core.database.async_session_factory",
            return_value=_FakeAsyncSessionCM(session),
        ), patch(
            "app.services.career_dna_service.CareerDNAService.generate_full_profile",
            new_callable=AsyncMock,
            return_value=career_dna,
        ) as mock_gen:
            user_id = "11111111-1111-1111-1111-111111111111"
            result = await recalculate_intelligence({}, user_id)

        assert result["status"] == "completed"
        assert result["user_id"] == user_id
        assert result["result"]["recalculated"] == ["growth_vector"]
        assert result["result"]["version"] == 7
        session.commit.assert_awaited_once()
        mock_gen.assert_awaited_once()

    async def test_handles_none_career_dna_version(self) -> None:
        session = MagicMock()
        session.commit = AsyncMock()

        with patch(
            "app.core.database.async_session_factory",
            return_value=_FakeAsyncSessionCM(session),
        ), patch(
            "app.services.career_dna_service.CareerDNAService.generate_full_profile",
            new_callable=AsyncMock,
            return_value=None,
        ):
            user_id = "22222222-2222-2222-2222-222222222222"
            result = await recalculate_intelligence({}, user_id)
        assert result["result"]["version"] == 0

    async def test_invalid_uuid_raises(self) -> None:
        with pytest.raises(ValueError):
            await recalculate_intelligence({}, "not-a-uuid")

    async def test_reraises_service_exception(self) -> None:
        session = MagicMock()
        session.commit = AsyncMock()

        with patch(
            "app.core.database.async_session_factory",
            return_value=_FakeAsyncSessionCM(session),
        ), patch(
            "app.services.career_dna_service.CareerDNAService.generate_full_profile",
            new_callable=AsyncMock,
            side_effect=RuntimeError("service failed"),
        ):
            user_id = "33333333-3333-3333-3333-333333333333"
            with pytest.raises(RuntimeError, match="service failed"):
                await recalculate_intelligence({}, user_id)


# ── WorkerSettings class-level configuration ─────────────────────


class TestWorkerSettings:
    def test_functions_list_includes_all_tasks(self) -> None:
        assert generate_embeddings in WorkerSettings.functions
        assert process_resume in WorkerSettings.functions
        assert run_matching_pipeline in WorkerSettings.functions
        assert recalculate_intelligence in WorkerSettings.functions

    def test_cron_jobs_is_non_empty_list(self) -> None:
        assert isinstance(WorkerSettings.cron_jobs, list)
        assert len(WorkerSettings.cron_jobs) >= 2

    def test_lifecycle_hooks_wired(self) -> None:
        assert WorkerSettings.on_startup is startup
        assert WorkerSettings.on_shutdown is shutdown
        assert WorkerSettings.on_job_failure is on_job_failure

    def test_redis_settings_is_arq_type(self) -> None:
        assert isinstance(WorkerSettings.redis_settings, RedisSettings)

    def test_retry_configuration_defaults(self) -> None:
        assert WorkerSettings.max_tries == 3
        assert WorkerSettings.job_timeout == timedelta(minutes=5)
        assert WorkerSettings.retry_delay == timedelta(seconds=30)

    def test_queue_and_health_check(self) -> None:
        assert WorkerSettings.queue_name == "pathforge:default"
        assert WorkerSettings.health_check_interval == 60

    def test_pool_sizing_matches_settings(self) -> None:
        # These are bound at class-definition time to settings.*.
        assert isinstance(WorkerSettings.max_jobs, int)
        assert isinstance(WorkerSettings.max_burst_jobs, int)
