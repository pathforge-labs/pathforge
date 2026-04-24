"""
PathForge — Billing Service Extended Tests
===========================================
Branch-focused unit tests for ``app.services.billing_service.BillingService``.

These tests use ``AsyncMock``/``MagicMock`` to exercise branches that are hard
to hit through the full-stack integration tests (e.g. PostgreSQL-specific
``pg_insert`` idempotency, stale-event rejection, state-machine violations).

All database calls are mocked — no SQLite/PostgreSQL engine is required.
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.subscription import (
    SubscriptionStatus,
    SubscriptionTier,
)
from app.services.billing_service import BillingService

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.filterwarnings(
        "ignore::pytest.PytestWarning",
    ),
]


# ── Test Constants ─────────────────────────────────────────────

PRO_MONTHLY = "price_pro_monthly_test"
PRO_YEARLY = "price_pro_yearly_test"
PREMIUM_MONTHLY = "price_premium_monthly_test"
PREMIUM_YEARLY = "price_premium_yearly_test"


@pytest.fixture(autouse=True)
def _patch_price_ids() -> Any:
    """Populate the four Stripe price IDs so tier resolution can match."""
    with (
        patch.object(settings, "stripe_pro_price_id", PRO_MONTHLY),
        patch.object(settings, "stripe_pro_yearly_price_id", PRO_YEARLY),
        patch.object(settings, "stripe_premium_price_id", PREMIUM_MONTHLY),
        patch.object(settings, "stripe_premium_yearly_price_id", PREMIUM_YEARLY),
    ):
        yield


def _install_fake_stripe(fake: MagicMock) -> Any:
    """Install a fake ``stripe`` module so lazy ``import stripe`` inside
    service methods resolves to the mock.
    """
    return patch.dict(sys.modules, {"stripe": fake})


# ── Helpers ────────────────────────────────────────────────────


def _make_user(
    *,
    user_id: uuid.UUID | None = None,
    email: str = "user@example.com",
    full_name: str = "Test User",
    subscription: Any = None,
) -> SimpleNamespace:
    """Create a minimal User stand-in for the billing service."""
    return SimpleNamespace(
        id=user_id or uuid.uuid4(),
        email=email,
        full_name=full_name,
        subscription=subscription,
    )


def _make_subscription(
    *,
    user_id: uuid.UUID | None = None,
    tier: str = SubscriptionTier.FREE.value,
    status: str = SubscriptionStatus.ACTIVE.value,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    last_event_timestamp: float | None = None,
    current_period_start: datetime | None = None,
    current_period_end: datetime | None = None,
    cancel_at_period_end: bool = False,
) -> Any:
    """Create a lightweight subscription stand-in without touching the DB.

    Uses SimpleNamespace (not the ORM class) to avoid SQLAlchemy's
    descriptor machinery that requires a registered mapper session.
    """
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        tier=tier,
        status=status,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        last_event_timestamp=last_event_timestamp,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=cancel_at_period_end,
    )


def _make_usage(
    *,
    scan_count: int = 0,
    engine_breakdown: dict[str, int] | None = None,
) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        subscription_id=uuid.uuid4(),
        period_start=datetime.now(tz=UTC),
        period_end=datetime.now(tz=UTC),
        scan_count=scan_count,
        engine_breakdown=engine_breakdown,
    )


def _make_db() -> AsyncMock:
    """AsyncMock db with ``add`` as a sync MagicMock (matches SQLAlchemy API)."""
    db = AsyncMock()
    db.add = MagicMock()
    return db


def _mock_db_with_result(return_value: Any) -> AsyncMock:
    """Return an AsyncMock db whose ``execute`` yields a scalar_one_or_none result."""
    db = _make_db()
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    db.execute.return_value = result
    return db


def _mock_db_with_results(return_values: list[Any]) -> AsyncMock:
    """Return an AsyncMock db whose sequential ``execute`` calls yield each value."""
    db = _make_db()
    results = []
    for value in return_values:
        result = MagicMock()
        result.scalar_one_or_none.return_value = value
        results.append(result)
    db.execute.side_effect = results
    return db


# ── get_or_create_subscription ─────────────────────────────────


class TestGetOrCreateSubscription:
    async def test_returns_existing_subscription(self) -> None:
        existing = _make_subscription()
        db = _mock_db_with_result(existing)
        user = _make_user(user_id=existing.user_id)

        result = await BillingService.get_or_create_subscription(db, user)

        assert result is existing
        db.add.assert_not_called()
        db.flush.assert_not_called()

    async def test_creates_default_free_subscription_when_missing(self) -> None:
        db = _mock_db_with_result(None)
        user = _make_user()

        result = await BillingService.get_or_create_subscription(db, user)

        assert result.user_id == user.id
        assert result.tier == SubscriptionTier.FREE.value
        assert result.status == SubscriptionStatus.ACTIVE.value
        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.refresh.assert_awaited_once_with(result)


# ── process_webhook_event ──────────────────────────────────────


class TestProcessWebhookEvent:
    async def test_duplicate_event_short_circuits(self) -> None:
        db = _make_db()
        event = {"id": "evt_dup", "type": "customer.subscription.updated", "created": 1}

        with patch.object(BillingService, "_log_billing_event", return_value=False):
            assert await BillingService.process_webhook_event(db, event) is False

    async def test_routes_subscription_created(self) -> None:
        db = _make_db()
        event = {"id": "evt_c", "type": "customer.subscription.created", "created": 10}

        with (
            patch.object(BillingService, "_log_billing_event", return_value=True),
            patch.object(
                BillingService,
                "_sync_subscription_from_event",
                return_value=True,
            ) as sync_mock,
        ):
            assert await BillingService.process_webhook_event(db, event) is True
            sync_mock.assert_awaited_once()

    async def test_routes_subscription_updated(self) -> None:
        db = _make_db()
        event = {"id": "evt_u", "type": "customer.subscription.updated", "created": 11}

        with (
            patch.object(BillingService, "_log_billing_event", return_value=True),
            patch.object(
                BillingService,
                "_sync_subscription_from_event",
                return_value=True,
            ) as sync_mock,
        ):
            assert await BillingService.process_webhook_event(db, event) is True
            sync_mock.assert_awaited_once()

    async def test_routes_subscription_deleted(self) -> None:
        db = _make_db()
        event = {"id": "evt_d", "type": "customer.subscription.deleted", "created": 12}

        with (
            patch.object(BillingService, "_log_billing_event", return_value=True),
            patch.object(
                BillingService,
                "_sync_subscription_from_event",
                return_value=True,
            ) as sync_mock,
        ):
            assert await BillingService.process_webhook_event(db, event) is True
            sync_mock.assert_awaited_once()

    async def test_routes_invoice_payment_succeeded(self) -> None:
        db = _make_db()
        event = {"id": "evt_ips", "type": "invoice.payment_succeeded", "created": 1}

        with (
            patch.object(BillingService, "_log_billing_event", return_value=True),
            patch.object(
                BillingService,
                "_handle_invoice_payment_succeeded",
                return_value=True,
            ) as handler,
        ):
            assert await BillingService.process_webhook_event(db, event) is True
            handler.assert_awaited_once()

    async def test_routes_invoice_payment_failed(self) -> None:
        db = _make_db()
        event = {"id": "evt_ipf", "type": "invoice.payment_failed", "created": 1}

        with (
            patch.object(BillingService, "_log_billing_event", return_value=True),
            patch.object(
                BillingService,
                "_handle_invoice_payment_failed",
                return_value=True,
            ) as handler,
        ):
            assert await BillingService.process_webhook_event(db, event) is True
            handler.assert_awaited_once()

    async def test_routes_checkout_completed(self) -> None:
        db = _make_db()
        event = {"id": "evt_chk", "type": "checkout.session.completed", "created": 1}

        with (
            patch.object(BillingService, "_log_billing_event", return_value=True),
            patch.object(
                BillingService,
                "_handle_checkout_completed",
                return_value=True,
            ) as handler,
        ):
            assert await BillingService.process_webhook_event(db, event) is True
            handler.assert_awaited_once()

    async def test_unhandled_event_type_returns_true(self) -> None:
        db = _make_db()
        event = {"id": "evt_x", "type": "customer.created", "created": 1}

        with patch.object(BillingService, "_log_billing_event", return_value=True):
            assert await BillingService.process_webhook_event(db, event) is True


# ── _sync_subscription_from_event ──────────────────────────────


class TestSyncSubscriptionFromEvent:
    def _event(
        self,
        *,
        customer: str = "cus_1",
        subscription_id: str = "sub_1",
        status: str = "active",
        cancel: bool = False,
        items: list[dict[str, Any]] | None = None,
        period_start: int | None = 1700000000,
        period_end: int | None = 1702592000,
        event_id: str = "evt_1",
    ) -> dict[str, Any]:
        return {
            "id": event_id,
            "data": {
                "object": {
                    "customer": customer,
                    "id": subscription_id,
                    "status": status,
                    "cancel_at_period_end": cancel,
                    "items": {"data": items or []},
                    "current_period_start": period_start,
                    "current_period_end": period_end,
                },
            },
        }

    async def test_customer_not_found_returns_false(self) -> None:
        db = _mock_db_with_result(None)
        event = self._event()
        assert (
            await BillingService._sync_subscription_from_event(db, event, 100.0)
            is False
        )

    async def test_stale_event_rejected(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1", last_event_timestamp=500.0,
        )
        db = _mock_db_with_result(sub)
        event = self._event()

        assert (
            await BillingService._sync_subscription_from_event(db, event, 499.0)
            is False
        )

    async def test_stale_event_equal_timestamp_rejected(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1", last_event_timestamp=500.0,
        )
        db = _mock_db_with_result(sub)
        event = self._event()

        assert (
            await BillingService._sync_subscription_from_event(db, event, 500.0)
            is False
        )

    async def test_unknown_status_returns_false(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_1")
        db = _mock_db_with_result(sub)
        event = self._event(status="bogus_status")

        assert (
            await BillingService._sync_subscription_from_event(db, event, 100.0)
            is False
        )

    async def test_invalid_state_transition_returns_false(self) -> None:
        # canceled -> active is not valid (canceled is terminal)
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            status=SubscriptionStatus.CANCELED.value,
        )
        db = _mock_db_with_result(sub)
        event = self._event(status="active")

        assert (
            await BillingService._sync_subscription_from_event(db, event, 100.0)
            is False
        )

    async def test_same_status_passes_without_transition_check(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(sub)
        event = self._event(status="active")

        assert (
            await BillingService._sync_subscription_from_event(db, event, 100.0)
            is True
        )
        assert sub.last_event_timestamp == 100.0
        assert sub.stripe_subscription_id == "sub_1"

    async def test_valid_transition_applies_all_fields(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(sub)
        event = self._event(
            status="past_due", cancel=True, period_start=1700000000,
            period_end=1702592000,
        )

        assert (
            await BillingService._sync_subscription_from_event(db, event, 200.0)
            is True
        )
        assert sub.status == SubscriptionStatus.PAST_DUE.value
        assert sub.cancel_at_period_end is True
        assert sub.current_period_start is not None
        assert sub.current_period_end is not None
        assert sub.last_event_timestamp == 200.0

    async def test_missing_period_dates_left_unchanged(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            status=SubscriptionStatus.ACTIVE.value,
        )
        sub.current_period_start = None
        sub.current_period_end = None
        db = _mock_db_with_result(sub)
        event = self._event(period_start=None, period_end=None, status="active")

        assert (
            await BillingService._sync_subscription_from_event(db, event, 100.0)
            is True
        )
        assert sub.current_period_start is None
        assert sub.current_period_end is None


# ── _resolve_tier_from_items ───────────────────────────────────


class TestResolveTierFromItems:
    def test_premium_monthly_matches(self) -> None:
        items = [{"price": {"id": PREMIUM_MONTHLY}}]
        assert (
            BillingService._resolve_tier_from_items(items)
            == SubscriptionTier.PREMIUM.value
        )

    def test_premium_yearly_matches(self) -> None:
        items = [{"price": {"id": PREMIUM_YEARLY}}]
        assert (
            BillingService._resolve_tier_from_items(items)
            == SubscriptionTier.PREMIUM.value
        )

    def test_pro_monthly_matches(self) -> None:
        items = [{"price": {"id": PRO_MONTHLY}}]
        assert (
            BillingService._resolve_tier_from_items(items)
            == SubscriptionTier.PRO.value
        )

    def test_pro_yearly_matches(self) -> None:
        items = [{"price": {"id": PRO_YEARLY}}]
        assert (
            BillingService._resolve_tier_from_items(items)
            == SubscriptionTier.PRO.value
        )

    def test_unknown_price_falls_back_to_free(self) -> None:
        items = [{"price": {"id": "price_unknown"}}]
        assert (
            BillingService._resolve_tier_from_items(items)
            == SubscriptionTier.FREE.value
        )

    def test_empty_items_returns_free(self) -> None:
        assert (
            BillingService._resolve_tier_from_items([])
            == SubscriptionTier.FREE.value
        )


# ── check_scan_limit ───────────────────────────────────────────


class TestCheckScanLimit:
    async def test_noop_when_billing_disabled(self) -> None:
        db = _make_db()
        user = _make_user()
        with patch.object(settings, "billing_enabled", False):
            # Should return silently, not touch the db
            await BillingService.check_scan_limit(db, user, "career_dna")
        db.execute.assert_not_called()

    async def test_unlimited_tier_passes(self) -> None:
        db = _make_db()
        sub = _make_subscription(
            tier=SubscriptionTier.PREMIUM.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        user = _make_user(subscription=sub)
        with patch.object(settings, "billing_enabled", True):
            await BillingService.check_scan_limit(db, user, "career_dna")
        # Premium = None limit — no summary lookup required
        db.execute.assert_not_called()

    async def test_raises_403_when_limit_exceeded(self) -> None:
        sub = _make_subscription(
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        user = _make_user(subscription=sub)
        summary = {"scans_used": 3, "tier": "free"}

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService,
                "get_usage_summary",
                return_value=summary,
            ),
            pytest.raises(HTTPException) as excinfo,
        ):
            await BillingService.check_scan_limit(AsyncMock(), user, "career_dna")
        assert excinfo.value.status_code == 403
        assert excinfo.value.detail["error"] == "scan_limit_exceeded"

    async def test_passes_when_below_limit(self) -> None:
        sub = _make_subscription(
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        user = _make_user(subscription=sub)
        summary = {"scans_used": 1, "tier": "free"}

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService,
                "get_usage_summary",
                return_value=summary,
            ),
        ):
            await BillingService.check_scan_limit(AsyncMock(), user, "career_dna")


# ── record_usage ───────────────────────────────────────────────


class TestRecordUsage:
    async def test_increments_existing_usage_record(self) -> None:
        sub = _make_subscription()
        usage = _make_usage(scan_count=2, engine_breakdown={"career_dna": 2})
        db = _mock_db_with_result(usage)
        user = _make_user()

        with patch.object(
            BillingService, "get_or_create_subscription", return_value=sub,
        ):
            result = await BillingService.record_usage(db, user, "career_dna")

        assert result is usage
        assert usage.scan_count == 3
        assert usage.engine_breakdown == {"career_dna": 3}

    async def test_creates_new_usage_when_none_exists(self) -> None:
        sub = _make_subscription(
            current_period_start=datetime.now(tz=UTC),
            current_period_end=datetime.now(tz=UTC).replace(year=2099),
        )
        db = _mock_db_with_result(None)
        user = _make_user()

        with patch.object(
            BillingService, "get_or_create_subscription", return_value=sub,
        ):
            result = await BillingService.record_usage(db, user, "career_dna")

        assert result.scan_count == 1
        assert result.engine_breakdown == {"career_dna": 1}
        db.add.assert_called_once()

    async def test_new_usage_defaults_period_when_subscription_lacks_dates(
        self,
    ) -> None:
        sub = _make_subscription(
            current_period_start=None, current_period_end=None,
        )
        db = _mock_db_with_result(None)
        user = _make_user()

        with patch.object(
            BillingService, "get_or_create_subscription", return_value=sub,
        ):
            result = await BillingService.record_usage(db, user, "threat_radar")

        assert result.scan_count == 1
        assert result.period_start is not None
        assert result.period_end is not None

    async def test_new_usage_defaults_december_period_rolls_over_year(self) -> None:
        sub = _make_subscription(
            current_period_start=None, current_period_end=None,
        )
        db = _mock_db_with_result(None)
        user = _make_user()

        fixed_now = datetime(2024, 12, 15, tzinfo=UTC)

        class _FakeDT(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:
                return fixed_now

        with (
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            patch("app.services.billing_service.datetime", _FakeDT),
        ):
            result = await BillingService.record_usage(db, user, "career_dna")

        # December wraps to January of next year
        assert result.period_end.year == 2025
        assert result.period_end.month == 1

    async def test_tracks_engine_breakdown_per_engine(self) -> None:
        sub = _make_subscription()
        usage = _make_usage(scan_count=1, engine_breakdown={"career_dna": 1})
        db = _mock_db_with_result(usage)
        user = _make_user()

        with patch.object(
            BillingService, "get_or_create_subscription", return_value=sub,
        ):
            await BillingService.record_usage(db, user, "threat_radar")

        assert usage.engine_breakdown == {"career_dna": 1, "threat_radar": 1}
        assert usage.scan_count == 2

    async def test_record_usage_handles_missing_breakdown_gracefully(self) -> None:
        sub = _make_subscription()
        usage = _make_usage(scan_count=0, engine_breakdown=None)
        db = _mock_db_with_result(usage)
        user = _make_user()

        with patch.object(
            BillingService, "get_or_create_subscription", return_value=sub,
        ):
            await BillingService.record_usage(db, user, "career_dna")

        assert usage.engine_breakdown == {"career_dna": 1}


# ── get_usage_summary ──────────────────────────────────────────


class TestGetUsageSummary:
    async def test_summary_with_usage(self) -> None:
        sub = _make_subscription(
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=datetime.now(tz=UTC),
            current_period_end=datetime.now(tz=UTC),
        )
        usage = _make_usage(scan_count=2, engine_breakdown={"career_dna": 2})
        db = _mock_db_with_result(usage)
        user = _make_user(subscription=sub)

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
        ):
            summary = await BillingService.get_usage_summary(db, user)

        assert summary["tier"] == "free"
        assert summary["scans_used"] == 2
        assert summary["scans_remaining"] == 1
        assert summary["engine_breakdown"] == {"career_dna": 2}

    async def test_summary_without_usage_returns_zero(self) -> None:
        sub = _make_subscription(
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(None)
        user = _make_user(subscription=sub)

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
        ):
            summary = await BillingService.get_usage_summary(db, user)

        assert summary["scans_used"] == 0
        assert summary["engine_breakdown"] is None

    async def test_summary_unlimited_tier_no_remaining_count(self) -> None:
        sub = _make_subscription(
            tier=SubscriptionTier.PREMIUM.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(None)
        user = _make_user(subscription=sub)

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
        ):
            summary = await BillingService.get_usage_summary(db, user)

        assert summary["scan_limit"] is None
        assert summary["scans_remaining"] is None


# ── create_checkout_session ───────────────────────────────────


class TestCreateCheckoutSession:
    async def test_raises_when_billing_disabled(self) -> None:
        db = _make_db()
        user = _make_user()
        with (
            patch.object(settings, "billing_enabled", False),
            pytest.raises(ValueError, match="disabled"),
        ):
            await BillingService.create_checkout_session(
                db, user, "pro", False, "https://ok", "https://no",
            )

    async def test_reuses_existing_stripe_customer(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_existing")
        user = _make_user()
        db = _make_db()

        fake_stripe = MagicMock()
        fake_stripe.checkout.Session.create.return_value = SimpleNamespace(
            url="https://checkout.stripe.com/s/abc",
        )

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            _install_fake_stripe(fake_stripe),
        ):
            url = await BillingService.create_checkout_session(
                db, user, "pro", False, "https://ok", "https://no",
            )

        assert url == "https://checkout.stripe.com/s/abc"
        fake_stripe.Customer.create.assert_not_called()

    async def test_creates_stripe_customer_when_missing(self) -> None:
        sub = _make_subscription(stripe_customer_id=None)
        user = _make_user()
        db = _make_db()

        fake_stripe = MagicMock()
        fake_stripe.Customer.create.return_value = SimpleNamespace(id="cus_new")
        fake_stripe.checkout.Session.create.return_value = SimpleNamespace(
            url="https://checkout.stripe.com/s/new",
        )

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            _install_fake_stripe(fake_stripe),
        ):
            url = await BillingService.create_checkout_session(
                db, user, "premium", True, "https://ok", "https://no",
            )

        fake_stripe.Customer.create.assert_called_once()
        assert sub.stripe_customer_id == "cus_new"
        db.flush.assert_awaited()
        assert url == "https://checkout.stripe.com/s/new"

    async def test_invalid_tier_raises(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_1")
        user = _make_user()
        db = _make_db()

        fake_stripe = MagicMock()

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            _install_fake_stripe(fake_stripe),
            pytest.raises(ValueError, match="Invalid tier/interval"),
        ):
            await BillingService.create_checkout_session(
                db, user, "diamond", False, "https://ok", "https://no",
            )

    async def test_returns_empty_string_when_session_url_none(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_1")
        user = _make_user()
        db = _make_db()

        fake_stripe = MagicMock()
        fake_stripe.checkout.Session.create.return_value = SimpleNamespace(url=None)

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            _install_fake_stripe(fake_stripe),
        ):
            url = await BillingService.create_checkout_session(
                db, user, "pro", False, "https://ok", "https://no",
            )
        assert url == ""


# ── create_portal_session ─────────────────────────────────────


class TestCreatePortalSession:
    async def test_raises_when_billing_disabled(self) -> None:
        db = _make_db()
        user = _make_user()
        with (
            patch.object(settings, "billing_enabled", False),
            pytest.raises(ValueError, match="disabled"),
        ):
            await BillingService.create_portal_session(db, user)

    async def test_raises_when_no_customer_id(self) -> None:
        sub = _make_subscription(stripe_customer_id=None)
        user = _make_user()
        db = _make_db()

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            pytest.raises(ValueError, match="No billing account"),
        ):
            await BillingService.create_portal_session(db, user)

    async def test_returns_session_url_on_success(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_42")
        user = _make_user()
        db = _make_db()

        fake_stripe = MagicMock()
        fake_stripe.billing_portal.Session.create.return_value = SimpleNamespace(
            url="https://billing.stripe.com/p/xyz",
        )

        with (
            patch.object(settings, "billing_enabled", True),
            patch.object(
                BillingService, "get_or_create_subscription", return_value=sub,
            ),
            _install_fake_stripe(fake_stripe),
        ):
            url = await BillingService.create_portal_session(db, user)

        assert url == "https://billing.stripe.com/p/xyz"
        fake_stripe.billing_portal.Session.create.assert_called_once()


# ── _get_price_id ──────────────────────────────────────────────


class TestGetPriceId:
    def test_pro_monthly(self) -> None:
        assert BillingService._get_price_id("pro", False) == PRO_MONTHLY

    def test_pro_annual(self) -> None:
        assert BillingService._get_price_id("pro", True) == PRO_YEARLY

    def test_premium_monthly(self) -> None:
        assert BillingService._get_price_id("premium", False) == PREMIUM_MONTHLY

    def test_premium_annual(self) -> None:
        assert BillingService._get_price_id("premium", True) == PREMIUM_YEARLY

    def test_invalid_tier_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid tier/interval"):
            BillingService._get_price_id("enterprise", False)

    def test_invalid_free_tier_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid tier/interval"):
            BillingService._get_price_id("free", False)


# ── _handle_invoice_payment_succeeded ──────────────────────────


class TestHandleInvoicePaymentSucceeded:
    async def test_returns_false_when_customer_unknown(self) -> None:
        db = _mock_db_with_result(None)
        event = {
            "data": {
                "object": {
                    "customer": "cus_unknown",
                    "subscription": "sub_x",
                    "billing_reason": "subscription_cycle",
                    "lines": {
                        "data": [
                            {"period": {"start": 1700000000, "end": 1702592000}},
                        ],
                    },
                },
            },
        }
        assert (
            await BillingService._handle_invoice_payment_succeeded(db, event)
            is False
        )

    async def test_updates_period_dates_from_invoice(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_1")
        db = _mock_db_with_result(sub)
        event = {
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "billing_reason": "subscription_cycle",
                    "lines": {
                        "data": [
                            {"period": {"start": 1700000000, "end": 1702592000}},
                        ],
                    },
                },
            },
        }

        result = await BillingService._handle_invoice_payment_succeeded(db, event)

        assert result is True
        assert sub.current_period_start is not None
        assert sub.current_period_end is not None

    async def test_succeeds_with_no_lines(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_1")
        db = _mock_db_with_result(sub)
        event = {
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "billing_reason": "subscription_create",
                    "lines": {"data": []},
                },
            },
        }
        assert (
            await BillingService._handle_invoice_payment_succeeded(db, event)
            is True
        )

    async def test_partial_period_data_updates_only_provided(self) -> None:
        sub = _make_subscription(stripe_customer_id="cus_1")
        original_end = sub.current_period_end
        db = _mock_db_with_result(sub)
        event = {
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "billing_reason": "subscription_cycle",
                    "lines": {
                        "data": [{"period": {"start": 1700000000}}],
                    },
                },
            },
        }
        assert (
            await BillingService._handle_invoice_payment_succeeded(db, event)
            is True
        )
        assert sub.current_period_start is not None
        assert sub.current_period_end == original_end


# ── _handle_invoice_payment_failed ─────────────────────────────


class TestHandleInvoicePaymentFailed:
    async def test_always_returns_true(self) -> None:
        db = _make_db()
        event = {
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "attempt_count": 2,
                },
            },
        }
        assert (
            await BillingService._handle_invoice_payment_failed(db, event) is True
        )

    async def test_empty_event_still_returns_true(self) -> None:
        db = _make_db()
        assert (
            await BillingService._handle_invoice_payment_failed(db, {}) is True
        )


# ── _handle_checkout_completed ─────────────────────────────────


class TestHandleCheckoutCompleted:
    async def test_missing_user_metadata_returns_false(self) -> None:
        db = _make_db()
        event = {
            "id": "evt_chk",
            "created": 100,
            "data": {"object": {"customer": "cus_1", "metadata": {}}},
        }
        assert (
            await BillingService._handle_checkout_completed(db, event) is False
        )

    async def test_customer_found_updates_subscription(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            status=SubscriptionStatus.INCOMPLETE.value,
            tier=SubscriptionTier.FREE.value,
        )
        db = _mock_db_with_result(sub)
        user_id = str(uuid.uuid4())
        event = {
            "id": "evt_chk",
            "created": 100,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "metadata": {
                        "pathforge_user_id": user_id,
                        "requested_tier": "premium",
                    },
                },
            },
        }

        assert (
            await BillingService._handle_checkout_completed(db, event) is True
        )
        assert sub.stripe_subscription_id == "sub_1"
        assert sub.tier == SubscriptionTier.PREMIUM.value
        assert sub.status == SubscriptionStatus.ACTIVE.value
        assert sub.last_event_timestamp == 100.0

    async def test_fallback_by_user_id_when_customer_missing(self) -> None:
        sub = _make_subscription(
            stripe_customer_id=None,
            status=SubscriptionStatus.INCOMPLETE.value,
        )
        db = _mock_db_with_results([None, sub])
        user_id = str(uuid.uuid4())
        event = {
            "id": "evt_chk",
            "created": 100,
            "data": {
                "object": {
                    "customer": "cus_new",
                    "subscription": "sub_new",
                    "metadata": {
                        "pathforge_user_id": user_id,
                        "requested_tier": "pro",
                    },
                },
            },
        }

        assert (
            await BillingService._handle_checkout_completed(db, event) is True
        )
        assert sub.stripe_subscription_id == "sub_new"
        assert sub.status == SubscriptionStatus.ACTIVE.value

    async def test_invalid_user_uuid_returns_false(self) -> None:
        db = _mock_db_with_results([None])
        event = {
            "id": "evt_chk",
            "created": 100,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "metadata": {
                        "pathforge_user_id": "not-a-uuid",
                        "requested_tier": "pro",
                    },
                },
            },
        }

        assert (
            await BillingService._handle_checkout_completed(db, event) is False
        )

    async def test_no_downgrade_when_current_tier_higher(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            tier=SubscriptionTier.PREMIUM.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(sub)
        event = {
            "id": "evt_chk",
            "created": 100,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "metadata": {
                        "pathforge_user_id": str(uuid.uuid4()),
                        "requested_tier": "pro",
                    },
                },
            },
        }

        assert (
            await BillingService._handle_checkout_completed(db, event) is True
        )
        # Tier stays premium (no downgrade)
        assert sub.tier == SubscriptionTier.PREMIUM.value

    async def test_active_status_not_demoted(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            tier=SubscriptionTier.PRO.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(sub)
        event = {
            "id": "evt_chk",
            "created": 200,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "metadata": {
                        "pathforge_user_id": str(uuid.uuid4()),
                        "requested_tier": "pro",
                    },
                },
            },
        }

        assert (
            await BillingService._handle_checkout_completed(db, event) is True
        )
        assert sub.status == SubscriptionStatus.ACTIVE.value

    async def test_updates_last_event_timestamp(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.INCOMPLETE.value,
        )
        db = _mock_db_with_result(sub)
        event = {
            "id": "evt_chk",
            "created": 9999,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_1",
                    "metadata": {
                        "pathforge_user_id": str(uuid.uuid4()),
                        "requested_tier": "pro",
                    },
                },
            },
        }

        await BillingService._handle_checkout_completed(db, event)
        assert sub.last_event_timestamp == 9999.0

    async def test_preserves_existing_subscription_id(self) -> None:
        sub = _make_subscription(
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_original",
            tier=SubscriptionTier.PRO.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        db = _mock_db_with_result(sub)
        event = {
            "id": "evt_chk",
            "created": 500,
            "data": {
                "object": {
                    "customer": "cus_1",
                    "subscription": "sub_incoming",
                    "metadata": {
                        "pathforge_user_id": str(uuid.uuid4()),
                        "requested_tier": "pro",
                    },
                },
            },
        }
        await BillingService._handle_checkout_completed(db, event)
        # Existing sub id preserved, not overwritten
        assert sub.stripe_subscription_id == "sub_original"

    async def test_neither_customer_nor_user_found_returns_false(self) -> None:
        db = _mock_db_with_results([None, None])
        event = {
            "id": "evt_chk",
            "created": 100,
            "data": {
                "object": {
                    "customer": "cus_unknown",
                    "subscription": "sub_x",
                    "metadata": {
                        "pathforge_user_id": str(uuid.uuid4()),
                        "requested_tier": "pro",
                    },
                },
            },
        }
        assert (
            await BillingService._handle_checkout_completed(db, event) is False
        )


# ── verify_webhook_signature ───────────────────────────────────


class TestVerifyWebhookSignature:
    def test_delegates_to_stripe_construct_event(self) -> None:
        fake_event = {"id": "evt_1", "type": "customer.subscription.updated"}
        fake_stripe = MagicMock()
        fake_stripe.Webhook.construct_event.return_value = fake_event

        with _install_fake_stripe(fake_stripe):
            result = BillingService.verify_webhook_signature(
                b"payload-bytes", "t=1,v1=sig",
            )

        assert result == fake_event
        fake_stripe.Webhook.construct_event.assert_called_once_with(
            b"payload-bytes",
            "t=1,v1=sig",
            settings.stripe_webhook_secret,
        )


# ── _log_billing_event ─────────────────────────────────────────


class TestLogBillingEvent:
    async def test_duplicate_returns_false(self) -> None:
        db = _make_db()
        customer_lookup = MagicMock()
        customer_lookup.first.return_value = None
        insert_cursor = MagicMock(rowcount=0)
        db.execute.side_effect = [customer_lookup, insert_cursor]

        event = {
            "id": "evt_dup",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_1",
                    "customer": "cus_1",
                    "status": "active",
                },
            },
        }
        assert await BillingService._log_billing_event(db, event) is False

    async def test_new_event_returns_true(self) -> None:
        db = _make_db()
        customer_lookup = MagicMock()
        customer_lookup.first.return_value = (uuid.uuid4(),)
        insert_cursor = MagicMock(rowcount=1)
        db.execute.side_effect = [customer_lookup, insert_cursor]

        event = {
            "id": "evt_new",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_1",
                    "customer": "cus_1",
                    "status": "active",
                },
            },
        }
        assert await BillingService._log_billing_event(db, event) is True
        db.flush.assert_awaited_once()

    async def test_no_customer_id_skips_user_lookup(self) -> None:
        db = _make_db()
        insert_cursor = MagicMock(rowcount=1)
        db.execute.return_value = insert_cursor

        event = {
            "id": "evt_no_cust",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_1", "status": "active"}},
        }
        assert await BillingService._log_billing_event(db, event) is True
        # Only one execute (the insert) — no customer lookup
        assert db.execute.await_count == 1

    async def test_rowcount_none_returns_false(self) -> None:
        db = _make_db()
        customer_lookup = MagicMock()
        customer_lookup.first.return_value = None
        insert_cursor = MagicMock(rowcount=None)
        db.execute.side_effect = [customer_lookup, insert_cursor]

        event = {
            "id": "evt_none",
            "type": "customer.subscription.updated",
            "data": {"object": {"customer": "cus_1"}},
        }
        assert await BillingService._log_billing_event(db, event) is False


# ── list_billing_events ────────────────────────────────────────


class TestListBillingEvents:
    async def test_paginated_results(self) -> None:
        db = _make_db()
        result = MagicMock()
        scalars = MagicMock()
        fake_events = [MagicMock(), MagicMock(), MagicMock()]
        scalars.all.return_value = fake_events
        result.scalars.return_value = scalars
        db.execute.return_value = result

        events = await BillingService.list_billing_events(db, page=1, per_page=20)
        assert events == fake_events
        db.execute.assert_awaited_once()

    async def test_second_page_uses_correct_offset(self) -> None:
        db = _make_db()
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        db.execute.return_value = result

        events = await BillingService.list_billing_events(db, page=3, per_page=10)
        assert events == []
        # Verify the select statement was executed once
        db.execute.assert_awaited_once()

    async def test_empty_list_returned_when_no_events(self) -> None:
        db = _make_db()
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        db.execute.return_value = result

        events = await BillingService.list_billing_events(db)
        assert events == []
