"""Tests for the WebhookReplayService (T6 / Sprint 58, ADR-0010).

The service:

* persists incoming webhook events (idempotent on `(provider,
  event_id)`),
* transitions outcome through ``received → processed`` (on success)
  or ``received → failed → dlq`` (after retries exhausted),
* exposes a replay path for admin tooling to retry DLQ entries.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_event import WebhookEvent, WebhookOutcome
from app.services.webhook_replay_service import (
    MAX_RETRY_ATTEMPTS,
    WebhookReplayError,
    WebhookReplayService,
)


@pytest.mark.asyncio
class TestPersist:
    async def test_persist_creates_received_row(self, db_session: AsyncSession) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_test_12345",
            event_type="invoice.payment_succeeded",
            payload={"id": "evt_test_12345", "type": "invoice.payment_succeeded"},
        )
        await db_session.flush()

        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        assert row.id == ledger_id
        assert row.provider == "stripe"
        assert row.event_id == "evt_test_12345"
        assert row.outcome == WebhookOutcome.received.value
        assert row.retry_count == 0

    async def test_persist_is_idempotent(self, db_session: AsyncSession) -> None:
        """Two persists for the same (provider, event_id) return the
        same ledger ID and don't create a duplicate row."""
        service = WebhookReplayService(db_session)
        first = await service.persist(
            provider="stripe",
            event_id="evt_dup",
            event_type="x.y",
            payload={"id": "evt_dup"},
        )
        await db_session.flush()
        second = await service.persist(
            provider="stripe",
            event_id="evt_dup",
            event_type="x.y",
            payload={"id": "evt_dup"},
        )
        await db_session.flush()
        assert first == second
        rows = (await db_session.execute(select(WebhookEvent))).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
class TestMarkProcessed:
    async def test_marks_outcome_processed(self, db_session: AsyncSession) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_ok",
            event_type="x.y",
            payload={"id": "evt_ok"},
        )
        await db_session.flush()
        await service.mark_processed(ledger_id)
        await db_session.flush()
        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        assert row.outcome == WebhookOutcome.processed.value


@pytest.mark.asyncio
class TestMarkFailed:
    async def test_failed_increments_retry_and_records_error(
        self, db_session: AsyncSession
    ) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_err",
            event_type="x.y",
            payload={"id": "evt_err"},
        )
        await db_session.flush()
        await service.mark_failed(ledger_id, error="boom")
        await db_session.flush()
        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        assert row.outcome == WebhookOutcome.failed.value
        assert row.retry_count == 1
        assert row.last_error is not None
        assert row.last_error.startswith("boom")
        assert row.last_attempt_at is not None

    async def test_after_max_retries_routes_to_dlq(self, db_session: AsyncSession) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_dlq",
            event_type="x.y",
            payload={"id": "evt_dlq"},
        )
        await db_session.flush()
        for _ in range(MAX_RETRY_ATTEMPTS):
            await service.mark_failed(ledger_id, error="boom")
            await db_session.flush()
        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        assert row.outcome == WebhookOutcome.dlq.value
        assert row.retry_count == MAX_RETRY_ATTEMPTS

    async def test_long_error_message_is_truncated(self, db_session: AsyncSession) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_long_err",
            event_type="x.y",
            payload={"id": "evt_long_err"},
        )
        await db_session.flush()
        long_msg = "x" * 5_000
        await service.mark_failed(ledger_id, error=long_msg)
        await db_session.flush()
        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        # Truncation cap is 2000 — assert under that and the
        # tail-marker is present.
        assert row.last_error is not None
        assert len(row.last_error) <= 2_010  # 2000 + ellipsis budget
        assert row.last_error.endswith("…")


@pytest.mark.asyncio
class TestListDlq:
    async def test_returns_only_dlq_entries(self, db_session: AsyncSession) -> None:
        service = WebhookReplayService(db_session)
        ok = await service.persist(
            provider="stripe",
            event_id="evt_ok",
            event_type="x.y",
            payload={"id": "evt_ok"},
        )
        bad = await service.persist(
            provider="stripe",
            event_id="evt_bad",
            event_type="x.y",
            payload={"id": "evt_bad"},
        )
        await db_session.flush()
        await service.mark_processed(ok)
        for _ in range(MAX_RETRY_ATTEMPTS):
            await service.mark_failed(bad, error="boom")
        await db_session.flush()

        dlq_rows = await service.list_dlq()
        assert len(dlq_rows) == 1
        assert dlq_rows[0].event_id == "evt_bad"


@pytest.mark.asyncio
class TestReplay:
    async def test_replay_invokes_handler_and_clears_outcome(
        self, db_session: AsyncSession
    ) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_replay",
            event_type="x.y",
            payload={"id": "evt_replay"},
        )
        await db_session.flush()
        for _ in range(MAX_RETRY_ATTEMPTS):
            await service.mark_failed(ledger_id, error="boom")
        await db_session.flush()

        invoked: list[dict[str, str]] = []

        async def handler(event_type: str, payload: dict[str, str]) -> None:
            invoked.append({"event_type": event_type, **payload})

        await service.replay(ledger_id, handler=handler)
        await db_session.flush()

        assert len(invoked) == 1
        assert invoked[0]["event_type"] == "x.y"
        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        assert row.outcome == WebhookOutcome.processed.value

    async def test_replay_failure_keeps_dlq(self, db_session: AsyncSession) -> None:
        service = WebhookReplayService(db_session)
        ledger_id = await service.persist(
            provider="stripe",
            event_id="evt_replay_fail",
            event_type="x.y",
            payload={"id": "evt_replay_fail"},
        )
        await db_session.flush()
        for _ in range(MAX_RETRY_ATTEMPTS):
            await service.mark_failed(ledger_id, error="boom")
        await db_session.flush()

        async def handler(event_type: str, payload: dict[str, str]) -> None:
            raise RuntimeError("still broken")

        with pytest.raises(WebhookReplayError):
            await service.replay(ledger_id, handler=handler)
        await db_session.flush()
        row = (await db_session.execute(select(WebhookEvent))).scalar_one()
        # Replay failure: outcome stays at dlq; last_error refreshed.
        assert row.outcome == WebhookOutcome.dlq.value
        assert row.last_error is not None
        assert "still broken" in row.last_error
