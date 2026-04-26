"""Integration tests for the admin webhook DLQ routes (T6)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.webhook_replay_service import (
    MAX_RETRY_ATTEMPTS,
    WebhookReplayService,
)


@pytest.fixture
async def admin_client(
    client: AsyncClient,
    db_session: AsyncSession,
) -> AsyncClient:
    """Return a client carrying a JWT for an admin user."""
    from app.core.security import create_access_token, hash_password
    from app.models.user import User as UserModel

    admin = UserModel(
        email="admin-t6@pathforge.eu",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Tester",
        is_verified=True,
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    token = create_access_token(str(admin.id))
    client.headers["Authorization"] = f"Bearer {token}"
    return client


async def _seed_dlq_entry(
    db_session: AsyncSession,
    *,
    event_id: str = "evt_dlq_seed",
) -> uuid.UUID:
    service = WebhookReplayService(db_session)
    ledger_id = await service.persist(
        provider="stripe",
        event_id=event_id,
        event_type="invoice.payment_succeeded",
        payload={
            "object": "event",
            "id": event_id,
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_test_001"}},
        },
    )
    for _ in range(MAX_RETRY_ATTEMPTS):
        await service.mark_failed(ledger_id, error="seed: simulated failure")
    await db_session.commit()
    return ledger_id


@pytest.mark.asyncio
async def test_list_endpoint_requires_admin(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/webhooks?status=dlq")
    # Either 401 (no auth) or 403 (auth but not admin) is acceptable.
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_dlq_returns_seeded_entry(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_dlq_entry(db_session, event_id="evt_dlq_listed")

    resp = await admin_client.get("/api/v1/admin/webhooks?status=dlq")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    event_ids = [item["event_id"] for item in body["items"]]
    assert "evt_dlq_listed" in event_ids
    flagged = next(item for item in body["items"] if item["event_id"] == "evt_dlq_listed")
    assert flagged["outcome"] == "dlq"
    assert flagged["retry_count"] >= MAX_RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_list_filter_to_processed_excludes_dlq(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_dlq_entry(db_session, event_id="evt_for_filter_test")

    resp = await admin_client.get("/api/v1/admin/webhooks?status=processed")
    assert resp.status_code == 200
    event_ids = [item["event_id"] for item in resp.json()["items"]]
    assert "evt_for_filter_test" not in event_ids


@pytest.mark.asyncio
async def test_list_rejects_invalid_status(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/v1/admin/webhooks?status=garbage")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_replay_endpoint_returns_502_on_handler_failure(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger_id = await _seed_dlq_entry(db_session, event_id="evt_replay_502")

    # Patch the dispatcher to raise so we exercise the 502 path
    # without needing a real Stripe BillingService run.
    async def _fail(event_type: str, payload: dict) -> None:
        raise RuntimeError("still broken")

    monkeypatch.setattr("app.api.v1.admin_webhooks._dispatch_replay", _fail)

    resp = await admin_client.post(f"/api/v1/admin/webhooks/{ledger_id}/replay")
    assert resp.status_code == 502
    assert "Replay" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_replay_endpoint_succeeds_when_dispatcher_passes(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger_id = await _seed_dlq_entry(db_session, event_id="evt_replay_ok")

    async def _ok(event_type: str, payload: dict) -> None:
        return None

    monkeypatch.setattr("app.api.v1.admin_webhooks._dispatch_replay", _ok)

    resp = await admin_client.post(f"/api/v1/admin/webhooks/{ledger_id}/replay")
    assert resp.status_code == 200
    body = resp.json()
    assert str(body["id"]) == str(ledger_id)
    assert body["outcome"] == "processed"


# Reference (silence unused import warning).
_ = User
