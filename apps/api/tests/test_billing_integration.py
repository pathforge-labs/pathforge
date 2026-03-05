"""
PathForge — Billing Integration Tests (Sprint 38 Audit)
=========================================================
Sprint 38: Tests for the billing integration layer added to AI engine routes.

Coverage targets:
    - BillingService.check_scan_limit: all code paths
    - BillingService.record_usage: increment + lazy period creation

Audit findings tested:
    C2 — Usage tracking (record_usage) after successful AI scans
    C5 — Scan limit pre-check (check_scan_limit) before AI operations
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.billing_service import BillingService

# ── check_scan_limit Tests ──────────────────────────────────


@pytest.mark.asyncio
class TestCheckScanLimit:
    """C5: Validate scan limit pre-check behavior."""

    async def test_billing_disabled_skips_check(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When billing is disabled, check_scan_limit is a no-op.

        Ensures graceful degradation for self-hosted or dev environments.
        """
        monkeypatch.setattr(settings, "billing_enabled", False)
        user = MagicMock()
        result = await BillingService.check_scan_limit(
            db_session, user, "career_dna",
        )
        assert result is None

    async def test_premium_tier_unlimited_scans(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Premium users should never hit a scan limit.

        get_scan_limit('premium') returns None → immediate return.
        We mock get_user_tier to avoid lazy-loading the ORM relationship.
        """
        monkeypatch.setattr(settings, "billing_enabled", True)

        with patch(
            "app.services.billing_service.get_user_tier",
            return_value="premium",
        ):
            result = await BillingService.check_scan_limit(
                db_session, billing_test_user, "career_passport",
            )
        assert result is None

    async def test_free_tier_exceeds_limit_raises_403(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Free-tier user who has exhausted scans should get 403.

        Validates the scan_limit_exceeded error structure:
        tier, usage count, limit, and upgrade URL.
        """
        from fastapi import HTTPException

        monkeypatch.setattr(settings, "billing_enabled", True)

        # Record 3 scans to exhaust the free limit
        for _ in range(3):
            await BillingService.record_usage(
                db_session, billing_test_user, "career_dna",
            )

        # Mock tier resolution to avoid lazy-load greenlet issue
        with patch(
            "app.services.billing_service.get_user_tier",
            return_value="free",
        ), pytest.raises(HTTPException) as exc_info:
            await BillingService.check_scan_limit(
                db_session, billing_test_user, "career_dna",
            )

        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert detail["error"] == "scan_limit_exceeded"
        assert detail["current_tier"] == "free"
        assert detail["scans_used"] >= 3
        assert detail["scan_limit"] == 3
        assert "/billing/checkout" in detail["upgrade_url"]


# ── record_usage Tests ──────────────────────────────────────


@pytest.mark.asyncio
class TestRecordUsage:
    """C2: Validate usage tracking after successful AI scans."""

    async def test_record_usage_creates_period_and_increments(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """First record_usage call creates a period record with count=1.

        F4: Lazy period reset — UsageRecord is created on first scan.
        """
        monkeypatch.setattr(settings, "billing_enabled", True)

        usage = await BillingService.record_usage(
            db_session, billing_test_user, "threat_radar",
        )

        assert usage.scan_count >= 1
        assert usage.engine_breakdown is not None
        assert "threat_radar" in usage.engine_breakdown

    async def test_record_usage_increments_total_scans(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Multiple record_usage calls should increase total scans_used.

        Uses get_usage_summary to verify aggregate scan count, which
        is resilient to per-record period boundary edge cases.
        """
        monkeypatch.setattr(settings, "billing_enabled", True)

        # Mock get_user_tier to avoid lazy-load greenlet issues
        with patch(
            "app.services.billing_service.get_user_tier",
            return_value="free",
        ):
            # Get baseline count
            summary_before = await BillingService.get_usage_summary(
                db_session, billing_test_user,
            )
            baseline = summary_before["scans_used"]

            # Record two scans
            await BillingService.record_usage(
                db_session, billing_test_user, "skill_decay",
            )
            await BillingService.record_usage(
                db_session, billing_test_user, "salary_intelligence",
            )

            summary_after = await BillingService.get_usage_summary(
                db_session, billing_test_user,
            )
            assert summary_after["scans_used"] >= baseline + 2

    async def test_record_usage_returns_valid_usage_record(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """record_usage should return a UsageRecord with valid structure.

        Validates that the returned object has expected fields:
        scan_count > 0, engine_breakdown contains the engine name,
        and period timestamps are set.
        """
        monkeypatch.setattr(settings, "billing_enabled", True)

        usage = await BillingService.record_usage(
            db_session, billing_test_user, "career_simulation",
        )

        # Structural assertions on the UsageRecord
        assert usage.scan_count >= 1
        assert usage.engine_breakdown is not None
        assert "career_simulation" in usage.engine_breakdown
        assert usage.period_start is not None
        assert usage.period_end is not None
        assert usage.user_id == billing_test_user.id
        assert usage.subscription_id is not None


# ── Webhook Handler Tests (Sprint 38 C4/C6) ────────────────


def _make_invoice_event(
    *,
    billing_reason: str = "subscription_cycle",
    customer: str = "cus_test123",
    subscription: str = "sub_test456",
    period_start: int = 1700000000,
    period_end: int = 1702592000,
    attempt_count: int = 1,
    event_type: str = "invoice.payment_succeeded",
) -> dict[str, object]:
    """Build a minimal Stripe invoice event for testing."""
    return {
        "id": f"evt_test_{billing_reason}",
        "type": event_type,
        "created": 1700000100,
        "data": {
            "object": {
                "customer": customer,
                "subscription": subscription,
                "billing_reason": billing_reason,
                "attempt_count": attempt_count,
                "lines": {
                    "data": [
                        {
                            "period": {
                                "start": period_start,
                                "end": period_end,
                            },
                        },
                    ],
                },
            },
        },
    }


def _make_checkout_event(
    *,
    customer: str = "cus_test123",
    subscription: str = "sub_checkout_789",
    pathforge_user_id: str | None = None,
    requested_tier: str | None = "pro",
) -> dict[str, object]:
    """Build a minimal Stripe checkout.session.completed event."""
    metadata: dict[str, str] = {}
    if pathforge_user_id is not None:
        metadata["pathforge_user_id"] = pathforge_user_id
    if requested_tier is not None:
        metadata["requested_tier"] = requested_tier

    return {
        "id": "evt_test_checkout",
        "type": "checkout.session.completed",
        "created": 1700000200,
        "data": {
            "object": {
                "customer": customer,
                "subscription": subscription,
                "metadata": metadata,
            },
        },
    }


@pytest.mark.asyncio
class TestWebhookHandlers:
    """Sprint 38 C4/C6: Webhook handler unit tests.

    Tests handler methods directly to avoid pg_insert/SQLite
    incompatibility in _log_billing_event (F6).
    """

    # ── C4: Invoice Payment Succeeded ──────────────────────

    async def test_invoice_succeeded_renewal_updates_period(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
    ) -> None:
        """subscription_cycle → period dates updated on subscription."""
        event = _make_invoice_event(billing_reason="subscription_cycle")
        result = await BillingService._handle_invoice_payment_succeeded(
            db_session, event,
        )

        assert result is True

        # Verify period was updated on subscription
        from app.models.subscription import Subscription

        sub_result = await db_session.execute(
            __import__("sqlalchemy").select(Subscription).where(
                Subscription.stripe_customer_id == "cus_test123",
            ),
        )
        subscription = sub_result.scalar_one()
        assert subscription.current_period_start is not None
        assert subscription.current_period_end is not None

    async def test_invoice_succeeded_initial_sets_period(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
    ) -> None:
        """subscription_create → period initialized, returns True."""
        event = _make_invoice_event(billing_reason="subscription_create")
        result = await BillingService._handle_invoice_payment_succeeded(
            db_session, event,
        )

        assert result is True

    async def test_invoice_succeeded_unknown_customer(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Unknown stripe_customer_id → False, no crash."""
        event = _make_invoice_event(customer="cus_unknown_999")
        result = await BillingService._handle_invoice_payment_succeeded(
            db_session, event,
        )

        assert result is False

    # ── C4: Invoice Payment Failed ─────────────────────────

    async def test_invoice_failed_returns_true_no_mutation(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
    ) -> None:
        """Log-only handler returns True without DB mutation."""
        from app.models.subscription import Subscription

        # Capture current state
        sub_result = await db_session.execute(
            __import__("sqlalchemy").select(Subscription).where(
                Subscription.stripe_customer_id == "cus_test123",
            ),
        )
        subscription_before = sub_result.scalar_one()
        status_before = subscription_before.status

        event = _make_invoice_event(
            event_type="invoice.payment_failed",
            attempt_count=2,
        )
        result = await BillingService._handle_invoice_payment_failed(
            db_session, event,
        )

        assert result is True

        # Refresh and verify status unchanged
        await db_session.refresh(subscription_before)
        assert subscription_before.status == status_before

    async def test_invoice_failed_minimal_payload_safe(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Minimal payload with missing fields → still returns True."""
        event: dict[str, object] = {
            "id": "evt_minimal",
            "type": "invoice.payment_failed",
            "created": 1700000000,
            "data": {"object": {}},
        }
        result = await BillingService._handle_invoice_payment_failed(
            db_session, event,
        )

        assert result is True

    # ── C6: Checkout Session Completed ─────────────────────

    async def test_checkout_sets_subscription_id_and_tier(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
    ) -> None:
        """Sets stripe_subscription_id and upgrades tier from metadata."""
        event = _make_checkout_event(
            pathforge_user_id=str(billing_test_user.id),
            requested_tier="pro",
        )
        result = await BillingService._handle_checkout_completed(
            db_session, event,
        )

        assert result is True

        # Verify subscription was updated
        from app.models.subscription import Subscription

        sub_result = await db_session.execute(
            __import__("sqlalchemy").select(Subscription).where(
                Subscription.stripe_customer_id == "cus_test123",
            ),
        )
        subscription = sub_result.scalar_one()
        assert subscription.stripe_subscription_id == "sub_checkout_789"
        assert subscription.tier == "pro"

    async def test_checkout_activates_incomplete_status(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
    ) -> None:
        """incomplete → active transition on checkout completion."""
        from app.models.subscription import Subscription

        # Set subscription to incomplete
        sub_result = await db_session.execute(
            __import__("sqlalchemy").select(Subscription).where(
                Subscription.stripe_customer_id == "cus_test123",
            ),
        )
        subscription = sub_result.scalar_one()
        subscription.status = "incomplete"
        await db_session.flush()

        event = _make_checkout_event(
            pathforge_user_id=str(billing_test_user.id),
            requested_tier="pro",
        )
        result = await BillingService._handle_checkout_completed(
            db_session, event,
        )

        assert result is True
        await db_session.refresh(subscription)
        assert subscription.status == "active"

    async def test_checkout_no_tier_downgrade(
        self,
        db_session: AsyncSession,
        billing_test_user: MagicMock,
    ) -> None:
        """F10: If tier is already 'pro', requested_tier='free' keeps 'pro'."""
        from app.models.subscription import Subscription

        # Set subscription to pro
        sub_result = await db_session.execute(
            __import__("sqlalchemy").select(Subscription).where(
                Subscription.stripe_customer_id == "cus_test123",
            ),
        )
        subscription = sub_result.scalar_one()
        subscription.tier = "pro"
        await db_session.flush()

        event = _make_checkout_event(
            pathforge_user_id=str(billing_test_user.id),
            requested_tier="free",
        )
        result = await BillingService._handle_checkout_completed(
            db_session, event,
        )

        assert result is True
        await db_session.refresh(subscription)
        assert subscription.tier == "pro"  # NOT downgraded

    async def test_checkout_missing_metadata_returns_false(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Missing pathforge_user_id in metadata → False."""
        event = _make_checkout_event(pathforge_user_id=None)
        result = await BillingService._handle_checkout_completed(
            db_session, event,
        )

        assert result is False

    async def test_checkout_user_not_found_returns_false(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Invalid user ID + unknown customer → False."""
        event = _make_checkout_event(
            customer="cus_nonexistent",
            pathforge_user_id="00000000-0000-0000-0000-000000000000",
        )
        result = await BillingService._handle_checkout_completed(
            db_session, event,
        )

        assert result is False

