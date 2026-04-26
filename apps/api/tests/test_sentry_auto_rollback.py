"""Tests for the Sentry auto-rollback webhook (T5 / Sprint 57)."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.feature_flags import (
    FlagDefinition,
    InMemoryFlagProvider,
    RolloutStage,
)


def _sign(secret: str, body: bytes) -> str:
    """Compute the Sentry HMAC signature header value."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _alert_payload(
    *,
    flag_key: str,
    p0_user_rate: float = 0.002,  # 0.2% — over threshold
    release: str = "pathforge-api@1.42.0",
) -> dict[str, Any]:
    """Sentry alert webhook payload shape (subset we consume).

    See Sentry docs `webhook payload`.  We intentionally accept only
    the fields we need so an extra field added by Sentry never breaks
    schema validation.
    """
    return {
        "action": "triggered",
        "data": {
            "issue_alert": {
                "id": "alert-9001",
                "title": "P0 error rate spike",
                "release": release,
            },
            "metric": {
                "name": "p0_user_rate",
                "value": p0_user_rate,
            },
            "tags": {"feature_flag": flag_key},
            "fired_at": datetime.now(UTC).isoformat(),
        },
    }


@pytest.fixture
def install_test_provider(monkeypatch: pytest.MonkeyPatch) -> InMemoryFlagProvider:
    """Replace the module-level provider with a deterministic stub
    so the test can assert on flag transitions."""
    from app.core import sentry_auto_rollback as module

    provider = InMemoryFlagProvider(
        {
            "engine_v2": FlagDefinition(
                stage=RolloutStage.percent_25,
                major_release=True,
            ),
        }
    )
    monkeypatch.setattr(module, "_get_provider", lambda: provider)
    return provider


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "sentry-test-webhook-secret-32chars!"
    from app.core.config import settings

    monkeypatch.setattr(settings, "sentry_webhook_secret", secret, raising=False)
    return secret


@pytest.mark.asyncio
async def test_webhook_rolls_flag_back_when_threshold_exceeded(
    client: AsyncClient,
    install_test_provider: InMemoryFlagProvider,
    webhook_secret: str,
) -> None:
    body = json.dumps(_alert_payload(flag_key="engine_v2")).encode()
    sig = _sign(webhook_secret, body)

    resp = await client.post(
        "/api/v1/internal/sentry/auto-rollback",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Sentry-Hook-Signature": sig,
        },
    )

    assert resp.status_code == 200
    body_json = resp.json()
    assert body_json["rolled_back"] is True
    assert body_json["flag_key"] == "engine_v2"
    assert install_test_provider.get("engine_v2").stage is RolloutStage.internal_only


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(
    client: AsyncClient,
    install_test_provider: InMemoryFlagProvider,
    webhook_secret: str,
) -> None:
    body = json.dumps(_alert_payload(flag_key="engine_v2")).encode()
    resp = await client.post(
        "/api/v1/internal/sentry/auto-rollback",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Sentry-Hook-Signature": "deadbeef" * 8,  # bogus
        },
    )
    assert resp.status_code == 401
    # Flag stays untouched.
    assert install_test_provider.get("engine_v2").stage is RolloutStage.percent_25


@pytest.mark.asyncio
async def test_webhook_no_op_when_threshold_not_exceeded(
    client: AsyncClient,
    install_test_provider: InMemoryFlagProvider,
    webhook_secret: str,
) -> None:
    body = json.dumps(
        _alert_payload(
            flag_key="engine_v2",
            p0_user_rate=0.0005,  # 0.05 %, under the 0.1 % threshold
        )
    ).encode()
    sig = _sign(webhook_secret, body)

    resp = await client.post(
        "/api/v1/internal/sentry/auto-rollback",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Sentry-Hook-Signature": sig,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["rolled_back"] is False
    assert install_test_provider.get("engine_v2").stage is RolloutStage.percent_25


@pytest.mark.asyncio
async def test_webhook_idempotent_on_already_rolled_back_flag(
    client: AsyncClient,
    install_test_provider: InMemoryFlagProvider,
    webhook_secret: str,
) -> None:
    """A second alert for the same release+flag while it's already at
    internal_only is a no-op success (we don't want repeated alerts to
    cycle the timestamp + spook the next re-enable's 24 h window).
    """
    install_test_provider.set_rollout("engine_v2", RolloutStage.internal_only)
    body = json.dumps(_alert_payload(flag_key="engine_v2")).encode()
    sig = _sign(webhook_secret, body)

    resp = await client.post(
        "/api/v1/internal/sentry/auto-rollback",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Sentry-Hook-Signature": sig,
        },
    )
    assert resp.status_code == 200
    body_json = resp.json()
    assert body_json["rolled_back"] is False
    assert body_json["already_at_internal_only"] is True


@pytest.mark.asyncio
async def test_webhook_rejects_unknown_flag(
    client: AsyncClient,
    install_test_provider: InMemoryFlagProvider,
    webhook_secret: str,
) -> None:
    body = json.dumps(_alert_payload(flag_key="never_defined")).encode()
    sig = _sign(webhook_secret, body)
    resp = await client.post(
        "/api/v1/internal/sentry/auto-rollback",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Sentry-Hook-Signature": sig,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["rolled_back"] is False
    assert resp.json()["unknown_flag"] is True


@pytest.mark.asyncio
async def test_webhook_rejects_missing_signature(
    client: AsyncClient,
    install_test_provider: InMemoryFlagProvider,
    webhook_secret: str,
) -> None:
    body = json.dumps(_alert_payload(flag_key="engine_v2")).encode()
    resp = await client.post(
        "/api/v1/internal/sentry/auto-rollback",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401
