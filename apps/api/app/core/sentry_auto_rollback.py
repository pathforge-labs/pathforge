"""
PathForge API — Sentry Auto-Rollback (T5 / Sprint 57, ADR-0009)
=================================================================

Webhook receiver for Sentry alerts. When a release tag's P0 user
rate crosses the threshold (default 0.1 %), the receiver flips the
associated feature flag back to ``internal_only`` via
:meth:`FeatureFlagProvider.set_rollout`.  The runbook at
``docs/runbooks/canary-rollback.md`` covers manual override.

Why a webhook (not polling)
---------------------------

Sentry already runs the metric-evaluation loop and surfaces the
*event of interest* over webhooks. Polling would either be too slow
(5-minute intervals miss canary windows) or too aggressive (per-second
polling against the Sentry API). The webhook receiver inverts the
control flow: alert fires once → we react.

Threshold rationale (default decision #5)
-----------------------------------------

> P0 rate **> 0.1 % of users** at any 5-minute window during a
> partial rollout (5 % or 25 %) → automatic rollback.

0.1 % at our 10 k-MAU launch target = 10 affected users / 5 min
window. That's the smallest user-cohort cardinality where a real
issue is statistically distinguishable from infrastructure noise
(per the threshold-design discussion in ADR-0009 §"Calibration").
The threshold is **per-window**, not per-release-cumulative — a
slow-burn 0.05 % bug stays under the gate but still surfaces in
the dashboard, and the operator can manually flip via the runbook.

Signature verification
----------------------

Sentry signs every webhook body with HMAC-SHA256 against the
project's webhook secret. We verify in **constant time** via
:func:`hmac.compare_digest` and reject 401 on mismatch — same
posture the Stripe webhook handler uses.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.feature_flags import (
    FeatureFlagProvider,
    InMemoryFlagProvider,
    RolloutStage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/sentry", tags=["Internal — Sentry"])

#: Default P0 user-rate threshold. Module-level so tests can patch
#: without monkeypatching ``settings``.
P0_USER_RATE_THRESHOLD: float = 0.001  # 0.1 %


# ── Provider singleton ────────────────────────────────────────
#
# A single in-memory provider is fine for the pre-GrowthBook launch
# state (sprint plan §12 default decision #1: SaaS free tier ≤ 5
# flags).  Multi-worker deployments will swap to a GrowthBook-backed
# provider via this same accessor — only the implementation changes.

_provider_singleton: FeatureFlagProvider | None = None


def _get_provider() -> FeatureFlagProvider:
    """Lazy singleton accessor.  Tests substitute via monkeypatch."""
    global _provider_singleton
    if _provider_singleton is None:
        _provider_singleton = InMemoryFlagProvider({})
    return _provider_singleton


# ── Signature verification ────────────────────────────────────


def _verify_signature(secret: str, body: bytes, header_value: str) -> bool:
    """Constant-time HMAC-SHA256 verification.  Empty secret or
    missing header → False (fail-closed)."""
    if not secret or not header_value:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_value)


def _extract_metric(payload: dict[str, Any]) -> float | None:
    """Pull the ``p0_user_rate`` metric out of the alert payload, if
    present.  Returns ``None`` for unknown shapes (handler decides)."""
    metric = payload.get("data", {}).get("metric") or {}
    if metric.get("name") != "p0_user_rate":
        return None
    raw = metric.get("value")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _extract_flag_key(payload: dict[str, Any]) -> str | None:
    """Pull the ``feature_flag`` tag out of the alert payload.
    Sentry alerts attach this tag via the alert rule's tag selector.
    """
    tags = payload.get("data", {}).get("tags") or {}
    flag_key = tags.get("feature_flag")
    return str(flag_key) if flag_key else None


# ── Webhook handler ───────────────────────────────────────────


@router.post(
    "/auto-rollback",
    summary="Sentry alert webhook — auto-rollback on P0 spike",
    description=(
        "Receives Sentry alert webhooks and flips the associated "
        "feature flag back to `internal_only` when the P0 user rate "
        "exceeds threshold. Verifies HMAC-SHA256 signature in the "
        "`Sentry-Hook-Signature` header. Returns structured JSON "
        "with the rollback decision; never 5xx on a malformed "
        "payload (Sentry retries cause cascade flapping)."
    ),
)
async def sentry_auto_rollback(
    request: Request,
    sentry_hook_signature: str | None = Header(default=None, alias="Sentry-Hook-Signature"),
) -> dict[str, Any]:
    secret = getattr(settings, "sentry_webhook_secret", "") or ""
    body = await request.body()

    if not sentry_hook_signature or not _verify_signature(secret, body, sentry_hook_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Sentry-Hook-Signature.",
        )

    try:
        payload = await request.json()
    except Exception:
        # Malformed payload — fail open (200 with reason) rather than
        # 5xx so Sentry doesn't retry-storm.
        logger.warning("sentry-auto-rollback: malformed JSON payload")
        return {
            "rolled_back": False,
            "reason": "malformed_payload",
        }

    flag_key = _extract_flag_key(payload)
    if not flag_key:
        return {
            "rolled_back": False,
            "reason": "no_feature_flag_tag",
        }

    rate = _extract_metric(payload)
    if rate is None:
        return {
            "rolled_back": False,
            "reason": "no_p0_user_rate_metric",
        }

    provider = _get_provider()
    current = provider.get(flag_key)
    if current is None:
        # Operator might create the flag later; we don't pre-create
        # it because that would tie the auto-rollback to definition
        # cadence Sentry doesn't know about.
        logger.warning("sentry-auto-rollback: alert references unknown flag %s", flag_key)
        return {
            "rolled_back": False,
            "unknown_flag": True,
            "flag_key": flag_key,
        }

    if rate <= P0_USER_RATE_THRESHOLD:
        return {
            "rolled_back": False,
            "flag_key": flag_key,
            "rate": rate,
            "threshold": P0_USER_RATE_THRESHOLD,
        }

    if current.stage is RolloutStage.internal_only:
        # Already rolled back — likely a duplicate alert. Don't bump
        # the rollout_started_at clock; that would extend the 24 h
        # paying-user delay on the next re-enable for no operational
        # reason.
        return {
            "rolled_back": False,
            "flag_key": flag_key,
            "already_at_internal_only": True,
        }

    provider.set_rollout(flag_key, RolloutStage.internal_only)
    logger.warning(
        "sentry-auto-rollback: flag=%s rolled back from stage=%s "
        "(p0_user_rate=%.4f > threshold=%.4f)",
        flag_key,
        current.stage.value,
        rate,
        P0_USER_RATE_THRESHOLD,
    )
    return {
        "rolled_back": True,
        "flag_key": flag_key,
        "rate": rate,
        "threshold": P0_USER_RATE_THRESHOLD,
        "previous_stage": current.stage.value,
    }


__all__ = [
    "P0_USER_RATE_THRESHOLD",
    "router",
]
