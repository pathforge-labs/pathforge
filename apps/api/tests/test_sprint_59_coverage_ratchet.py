"""
PathForge — Sprint 59 Coverage Ratchet (94.36 % → 95 %)
=========================================================

Targeted tests closing the last % gap on post-Sprint-58 main:

  - core/sentry_auto_rollback.py  (21 missing) — multi-worker
    detection, signature/extract helpers, webhook branch coverage
    (no-flag, no-metric, malformed-payload).
  - api/v1/admin_webhooks.py      (15 missing) — replay dispatcher
    (Stripe-shaped + unhandled-shape) and listing filter passthrough.
  - core/feature_flags.py         (3 missing) — tier-canary edges.
  - core/llm_observability.py     (68 missing) — branch coverage on
    `compute_confidence_score` / `confidence_label` /
    `LLMMetricsCollector` / `TransparencyLog` paths.

Each test is independent; no shared mutable fixtures.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


def _signed_payload(secret: str, body_dict: dict[str, Any]) -> tuple[bytes, str]:
    body = json.dumps(body_dict).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, sig


# ═══════════════════════════════════════════════════════════════════════════════
# 1. core/sentry_auto_rollback.py — pure-function helpers
# ═══════════════════════════════════════════════════════════════════════════════


class TestSentryAutoRollbackHelpers:
    def test_detect_multi_worker_returns_false_when_unset(self) -> None:
        from app.core.sentry_auto_rollback import _detect_multi_worker

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WEB_CONCURRENCY", None)
            os.environ.pop("GUNICORN_CMD_ARGS", None)
            assert _detect_multi_worker() is False

    def test_detect_multi_worker_returns_true_for_high_concurrency(self) -> None:
        from app.core.sentry_auto_rollback import _detect_multi_worker

        with patch.dict(os.environ, {"WEB_CONCURRENCY": "4"}):
            assert _detect_multi_worker() is True

    def test_detect_multi_worker_returns_false_for_invalid_env(self) -> None:
        from app.core.sentry_auto_rollback import _detect_multi_worker

        with patch.dict(os.environ, {"WEB_CONCURRENCY": "abc"}):
            assert _detect_multi_worker() is False

    def test_detect_multi_worker_picks_up_gunicorn_workers_arg(self) -> None:
        from app.core.sentry_auto_rollback import _detect_multi_worker

        with patch.dict(
            os.environ,
            {"WEB_CONCURRENCY": "1", "GUNICORN_CMD_ARGS": "--workers=4 --bind=0.0.0.0:8000"},
        ):
            assert _detect_multi_worker() is True

    def test_get_provider_logs_warning_in_multi_worker_context(self) -> None:
        import app.core.sentry_auto_rollback as mod

        mod._provider_singleton = None
        with (
            patch.dict(os.environ, {"WEB_CONCURRENCY": "4"}),
            patch.object(mod.logger, "error") as mock_error,
        ):
            provider = mod._get_provider()
            assert provider is not None
            mock_error.assert_called_once()
            msg = mock_error.call_args.args[0]
            assert "in-memory" in msg.lower()
        mod._provider_singleton = None

    def test_get_provider_caches_singleton(self) -> None:
        import app.core.sentry_auto_rollback as mod

        mod._provider_singleton = None
        first = mod._get_provider()
        second = mod._get_provider()
        assert first is second
        mod._provider_singleton = None

    def test_extract_metric_returns_none_for_wrong_metric_name(self) -> None:
        from app.core.sentry_auto_rollback import _extract_metric

        payload = {"data": {"metric": {"name": "p99_latency", "value": 0.05}}}
        assert _extract_metric(payload) is None

    def test_extract_metric_returns_none_for_missing_value(self) -> None:
        from app.core.sentry_auto_rollback import _extract_metric

        payload = {"data": {"metric": {"name": "p0_user_rate"}}}
        assert _extract_metric(payload) is None

    def test_extract_metric_returns_none_for_unparseable_value(self) -> None:
        from app.core.sentry_auto_rollback import _extract_metric

        payload = {"data": {"metric": {"name": "p0_user_rate", "value": "not-a-number"}}}
        assert _extract_metric(payload) is None

    def test_extract_metric_returns_float_for_valid_payload(self) -> None:
        from app.core.sentry_auto_rollback import _extract_metric

        payload = {"data": {"metric": {"name": "p0_user_rate", "value": "0.0042"}}}
        assert _extract_metric(payload) == pytest.approx(0.0042)

    def test_extract_metric_returns_none_for_empty_payload(self) -> None:
        from app.core.sentry_auto_rollback import _extract_metric

        assert _extract_metric({}) is None
        assert _extract_metric({"data": {}}) is None
        assert _extract_metric({"data": {"metric": None}}) is None

    def test_extract_flag_key_returns_none_for_missing_tags(self) -> None:
        from app.core.sentry_auto_rollback import _extract_flag_key

        assert _extract_flag_key({}) is None
        assert _extract_flag_key({"data": {}}) is None
        assert _extract_flag_key({"data": {"tags": None}}) is None
        assert _extract_flag_key({"data": {"tags": {}}}) is None

    def test_extract_flag_key_returns_string(self) -> None:
        from app.core.sentry_auto_rollback import _extract_flag_key

        payload = {"data": {"tags": {"feature_flag": "engine-v2"}}}
        assert _extract_flag_key(payload) == "engine-v2"

    def test_verify_signature_fail_closed_on_empty_secret(self) -> None:
        from app.core.sentry_auto_rollback import _verify_signature

        assert _verify_signature("", b"body", "any-header") is False

    def test_verify_signature_fail_closed_on_empty_header(self) -> None:
        from app.core.sentry_auto_rollback import _verify_signature

        assert _verify_signature("secret", b"body", "") is False

    def test_verify_signature_passes_with_correct_hmac(self) -> None:
        from app.core.sentry_auto_rollback import _verify_signature

        secret = "some-secret"
        body = b'{"hello":"world"}'
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(secret, body, expected) is True

    def test_verify_signature_rejects_tampered_body(self) -> None:
        from app.core.sentry_auto_rollback import _verify_signature

        secret = "some-secret"
        original_sig = hmac.new(
            secret.encode(), b'{"hello":"world"}', hashlib.sha256,
        ).hexdigest()
        assert _verify_signature(secret, b'{"hello":"forged"}', original_sig) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. core/sentry_auto_rollback.py — webhook integration branches
# ═══════════════════════════════════════════════════════════════════════════════


class TestSentryAutoRollbackWebhookBranches:
    @pytest.fixture
    def secret(self) -> str:
        return "sprint-59-test-secret"

    async def test_webhook_no_flag_tag_returns_no_op(
        self, client: AsyncClient, secret: str
    ) -> None:
        with patch("app.core.config.settings.sentry_webhook_secret", secret):
            body, sig = _signed_payload(
                secret,
                {"data": {"metric": {"name": "p0_user_rate", "value": 0.05}}},
            )
            resp = await client.post(
                "/api/v1/internal/sentry/auto-rollback",
                content=body,
                headers={"Sentry-Hook-Signature": sig, "Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        body_json = resp.json()
        assert body_json["rolled_back"] is False
        assert body_json["reason"] == "no_feature_flag_tag"

    async def test_webhook_no_p0_metric_returns_no_op(
        self, client: AsyncClient, secret: str
    ) -> None:
        with patch("app.core.config.settings.sentry_webhook_secret", secret):
            body, sig = _signed_payload(
                secret, {"data": {"tags": {"feature_flag": "engine-v2"}}},
            )
            resp = await client.post(
                "/api/v1/internal/sentry/auto-rollback",
                content=body,
                headers={"Sentry-Hook-Signature": sig, "Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        body_json = resp.json()
        assert body_json["rolled_back"] is False
        assert body_json["reason"] == "no_p0_user_rate_metric"
        assert body_json["flag_key"] == "engine-v2"

    async def test_webhook_malformed_json_returns_no_op(
        self, client: AsyncClient, secret: str
    ) -> None:
        with patch("app.core.config.settings.sentry_webhook_secret", secret):
            body = b"<not-json>"
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            resp = await client.post(
                "/api/v1/internal/sentry/auto-rollback",
                content=body,
                headers={"Sentry-Hook-Signature": sig, "Content-Type": "application/json"},
            )
        assert resp.status_code == 200
        assert resp.json()["reason"] == "malformed_payload"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. api/v1/admin_webhooks.py — replay dispatcher branches
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdminWebhooksReplayDispatcher:
    async def test_dispatch_replay_unhandled_payload_raises(self) -> None:
        from app.api.v1.admin_webhooks import _dispatch_replay
        from app.services.webhook_replay_service import WebhookReplayError

        with pytest.raises(WebhookReplayError) as exc:
            await _dispatch_replay("custom.event", {"foo": "bar"})
        assert "unhandled" in str(exc.value).lower()

    async def test_dispatch_replay_stripe_invokes_billing_service(self) -> None:
        from app.api.v1.admin_webhooks import _dispatch_replay

        stripe_payload = {
            "object": "event",
            "id": "evt_test_xyz",
            "type": "invoice.paid",
            "data": {"object": {"id": "in_xyz"}},
        }
        with patch(
            "app.services.billing_service.BillingService.process_webhook_event",
            new_callable=AsyncMock,
        ) as mock_proc:
            await _dispatch_replay("invoice.paid", stripe_payload)
        mock_proc.assert_awaited_once()
        called_payload = mock_proc.await_args.args[1]
        assert called_payload["id"] == "evt_test_xyz"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. core/feature_flags.py — tier-canary edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeatureFlagsTierCanary:
    def test_passes_tier_canary_skips_minor_release(self) -> None:
        from app.core.feature_flags import (
            FlagDefinition,
            RolloutStage,
            _passes_tier_canary,
        )

        flag = FlagDefinition(stage=RolloutStage.percent_100, major_release=False)
        assert _passes_tier_canary(flag, {"id": "u1", "tier": "premium"}) is True

    def test_passes_tier_canary_skips_free_tier(self) -> None:
        from app.core.feature_flags import (
            FlagDefinition,
            RolloutStage,
            _passes_tier_canary,
        )

        flag = FlagDefinition(stage=RolloutStage.percent_100, major_release=True)
        assert _passes_tier_canary(flag, {"id": "u1", "tier": "free"}) is True

    def test_passes_tier_canary_blocks_paying_within_delay(self) -> None:
        from app.core.feature_flags import (
            FlagDefinition,
            RolloutStage,
            _passes_tier_canary,
        )

        # Just-started major release → paying users blocked.
        flag = FlagDefinition(
            stage=RolloutStage.percent_100,
            major_release=True,
            rollout_started_at=datetime.now(UTC) - timedelta(hours=2),
        )
        assert _passes_tier_canary(flag, {"id": "u1", "tier": "premium"}) is False

    def test_passes_tier_canary_unblocks_paying_after_delay(self) -> None:
        from app.core.feature_flags import (
            PAYING_USER_DELAY,
            FlagDefinition,
            RolloutStage,
            _passes_tier_canary,
        )

        # 25 h ago → past the 24 h tier delay.
        flag = FlagDefinition(
            stage=RolloutStage.percent_100,
            major_release=True,
            rollout_started_at=datetime.now(UTC) - PAYING_USER_DELAY - timedelta(minutes=10),
        )
        assert _passes_tier_canary(flag, {"id": "u1", "tier": "pro"}) is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. core/llm_observability.py — confidence-score branch coverage
# ═══════════════════════════════════════════════════════════════════════════════


class TestComputeConfidenceScoreBranches:
    """`compute_confidence_score` is the most-branched pure function in
    the module. Cover each retry / latency / token-utilization branch."""

    def test_zero_retries_full_score(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        # Primary tier, no retries, fast latency, low utilization → near 1.0.
        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=0.5,
            completion_tokens=100,
            max_tokens=1000,
        )
        assert 0.90 <= score <= 0.95  # Capped at CONFIDENCE_CAP=0.95

    def test_one_retry_drops_score(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="primary",
            retries=1,
            latency_seconds=0.5,
            completion_tokens=100,
            max_tokens=1000,
        )
        assert 0.80 <= score < 0.92

    def test_multiple_retries_drops_further(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="primary",
            retries=3,
            latency_seconds=0.5,
            completion_tokens=100,
            max_tokens=1000,
        )
        assert score < 0.80

    def test_latency_2_to_5_seconds_factor(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=3.0,
            completion_tokens=100,
            max_tokens=1000,
        )
        # 0.95 latency factor applied.
        assert 0.90 <= score <= 0.95

    def test_latency_5_to_10_seconds_factor(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=7.0,
            completion_tokens=100,
            max_tokens=1000,
        )
        assert 0.80 <= score <= 0.90

    def test_latency_over_10_seconds_factor(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=15.0,
            completion_tokens=100,
            max_tokens=1000,
        )
        assert score <= 0.75

    def test_high_token_utilization_truncation_penalty(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        # 96% utilization → likely truncated, factor 0.80.
        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=0.5,
            completion_tokens=960,
            max_tokens=1000,
        )
        assert score < 0.85

    def test_near_limit_token_utilization(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        # 88% utilization → near-limit, factor 0.90.
        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=0.5,
            completion_tokens=880,
            max_tokens=1000,
        )
        assert 0.83 <= score <= 0.92

    def test_zero_max_tokens_token_factor_passthrough(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=0.5,
            completion_tokens=100,
            max_tokens=0,  # no max → passthrough factor 1.0
        )
        assert score >= 0.90

    def test_unknown_tier_falls_back_to_default(self) -> None:
        from app.core.llm_observability import compute_confidence_score

        score = compute_confidence_score(
            tier="unknown-tier",
            retries=0,
            latency_seconds=0.5,
            completion_tokens=100,
            max_tokens=1000,
        )
        # Default tier factor 0.85.
        assert 0.80 <= score <= 0.90


class TestConfidenceLabelBoundaries:
    def test_high_label(self) -> None:
        from app.core.llm_observability import confidence_label

        assert confidence_label(0.95) == "High"
        assert confidence_label(0.85) == "High"

    def test_medium_label(self) -> None:
        from app.core.llm_observability import confidence_label

        assert confidence_label(0.84) == "Medium"
        assert confidence_label(0.65) == "Medium"

    def test_low_label(self) -> None:
        from app.core.llm_observability import confidence_label

        assert confidence_label(0.64) == "Low"
        assert confidence_label(0.0) == "Low"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. core/llm_observability.py — initialize + collector + transparency log
# ═══════════════════════════════════════════════════════════════════════════════


class TestInitializeObservability:
    def test_initialize_observability_no_op_when_disabled(self) -> None:
        from app.core import llm_observability

        with patch("app.core.config.settings.llm_observability_enabled", False):
            # Returns silently. The in-memory collector + transparency log
            # are still set up.
            llm_observability.initialize_observability()

    def test_initialize_observability_skips_without_credentials(self) -> None:
        from app.core import llm_observability

        with (
            patch("app.core.config.settings.llm_observability_enabled", True),
            patch("app.core.config.settings.langfuse_public_key", ""),
            patch("app.core.config.settings.langfuse_secret_key", ""),
        ):
            # Must not raise; emits a warning log instead.
            llm_observability.initialize_observability()


class TestLLMMetricsCollector:
    def test_get_collector_returns_singleton(self) -> None:
        from app.core.llm_observability import get_collector

        a = get_collector()
        b = get_collector()
        assert a is b

    def test_record_call_increments_counters(self) -> None:
        from app.core.llm_observability import get_collector

        collector = get_collector()
        collector.reset()
        collector.record_call(
            tier="primary",
            model="claude-sonnet-4",
            latency_seconds=0.5,
            prompt_tokens=100,
            completion_tokens=200,
            success=True,
        )
        metrics = collector.get_metrics()
        assert metrics["global"]["total_calls"] >= 1
        assert "claude-sonnet-4" in metrics["by_model"]

    def test_record_call_failure_branch(self) -> None:
        from app.core.llm_observability import get_collector

        collector = get_collector()
        collector.reset()
        collector.record_call(
            tier="primary",
            model="claude-sonnet-4",
            latency_seconds=12.0,
            prompt_tokens=100,
            completion_tokens=0,
            success=False,
            error_type="TimeoutError",
        )
        metrics = collector.get_metrics()
        assert metrics["global"]["total_calls"] >= 1
        assert metrics["global"]["failed_calls"] >= 1


class TestTransparencyLog:
    async def test_get_transparency_log_returns_singleton(self) -> None:
        from app.core.llm_observability import get_transparency_log

        a = get_transparency_log()
        b = get_transparency_log()
        assert a is b

    async def test_record_and_recall(self) -> None:
        from app.core.llm_observability import (
            TransparencyRecord,
            get_transparency_log,
        )

        log = get_transparency_log()
        rec = TransparencyRecord(
            analysis_id="trace-test-sprint59-1",
            analysis_type="career_dna",
            model="claude-sonnet-4",
            tier="primary",
            confidence_score=0.85,
            confidence_label="High",
            prompt_tokens=100,
            completion_tokens=200,
            latency_ms=500,
            success=True,
            retries=0,
        )
        # `record` does fire-and-forget DB persistence — patch out the
        # async DB call so the test stays in-memory only.
        with patch.object(log, "_persist_to_db", new_callable=AsyncMock):
            log.record(user_id="user-sprint59-test", entry=rec)
        recent = await log.get_recent(user_id="user-sprint59-test", limit=5)
        assert any(r.analysis_id == "trace-test-sprint59-1" for r in recent)
