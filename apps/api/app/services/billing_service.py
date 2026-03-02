"""
PathForge — Billing Service
==============================
Sprint 34: Stripe billing business logic.

Audit findings implemented:
    F1  — Graceful degradation (kill switch)
    F2  — Idempotent webhook dedup (INSERT ON CONFLICT DO NOTHING)
    F3  — Subscription state machine (valid transitions)
    F4  — Lazy usage period reset
    F9  — Lazy Stripe customer creation
    F10 — Stale webhook rejection (timestamp ordering)
    F16 — Fast ack webhook pattern
    F22 — Trimmed event payload
    F25 — SELECT FOR UPDATE on concurrent webhooks
    F28 — Sentry context tagging
    F35 — Raw body reading for webhook signature
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.feature_gate import TIER_SCAN_LIMITS, get_user_tier
from app.models.subscription import (
    VALID_STATUS_TRANSITIONS,
    BillingEvent,
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    UsageRecord,
)
from app.models.user import User

logger = logging.getLogger(__name__)


class BillingService:
    """Encapsulates Stripe billing business logic."""

    # ── Subscription CRUD ──────────────────────────────────────

    @staticmethod
    async def get_or_create_subscription(
        db: AsyncSession,
        user: User,
    ) -> Subscription:
        """Get user's subscription or create a default free one."""
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = result.scalar_one_or_none()

        if subscription is not None:
            return subscription

        subscription = Subscription(
            user_id=user.id,
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
        )
        db.add(subscription)
        await db.flush()
        await db.refresh(subscription)
        return subscription

    # ── Webhook Processing ─────────────────────────────────────

    @staticmethod
    async def process_webhook_event(
        db: AsyncSession,
        event: dict[str, Any],
    ) -> bool:
        """Process a verified Stripe webhook event.

        Returns True if processed, False if duplicate/stale.
        Implements F2 (idempotency), F10 (timestamp ordering),
        F25 (row-level lock), F3 (state machine).
        """
        event_id = event.get("id", "")
        event_type = event.get("type", "")
        event_created = event.get("created", 0)

        # F2: Idempotent dedup — INSERT ON CONFLICT DO NOTHING
        was_logged = await BillingService._log_billing_event(db, event)
        if not was_logged:
            logger.info("Duplicate webhook event skipped: %s", event_id)
            return False

        # Route to handler
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            return await BillingService._sync_subscription_from_event(
                db, event, event_created
            )

        if event_type in ("invoice.payment_succeeded", "invoice.payment_failed"):
            logger.info("Invoice event received: %s %s", event_type, event_id)
            return True

        logger.info("Unhandled webhook event type: %s", event_type)
        return True

    @staticmethod
    async def _sync_subscription_from_event(
        db: AsyncSession,
        event: dict[str, Any],
        event_created: float,
    ) -> bool:
        """Sync subscription state from Stripe webhook data.

        F25: Uses SELECT FOR UPDATE to prevent race conditions.
        F10: Rejects events older than last processed timestamp.
        F3: Validates state transitions.
        """
        data_object = event.get("data", {}).get("object", {})
        stripe_customer_id = data_object.get("customer", "")
        stripe_subscription_id = data_object.get("id", "")
        new_status = data_object.get("status", "")
        cancel_at_period_end = data_object.get("cancel_at_period_end", False)

        # Map Stripe price to our tier
        items = data_object.get("items", {}).get("data", [])
        new_tier = BillingService._resolve_tier_from_items(items)

        # Extract period dates
        current_period_start = data_object.get("current_period_start")
        current_period_end = data_object.get("current_period_end")

        # Find subscription by Stripe customer ID (F25: FOR UPDATE lock)
        result = await db.execute(
            select(Subscription)
            .where(Subscription.stripe_customer_id == stripe_customer_id)
            .with_for_update()
        )
        subscription = result.scalar_one_or_none()

        if subscription is None:
            logger.warning(
                "No subscription found for Stripe customer %s", stripe_customer_id
            )
            return False

        # F10: Reject stale events
        if (
            subscription.last_event_timestamp is not None
            and event_created <= subscription.last_event_timestamp
        ):
            logger.info(
                "Stale event rejected: %s (event=%s, last=%s)",
                event.get("id"),
                event_created,
                subscription.last_event_timestamp,
            )
            return False

        # F3: Validate state transition
        current_status = SubscriptionStatus(subscription.status)
        try:
            target_status = SubscriptionStatus(new_status)
        except ValueError:
            logger.warning("Unknown subscription status from Stripe: %s", new_status)
            return False

        if current_status != target_status:
            valid_targets = VALID_STATUS_TRANSITIONS.get(current_status, set())
            if target_status not in valid_targets:
                logger.warning(
                    "Invalid state transition: %s -> %s (sub=%s)",
                    current_status,
                    target_status,
                    subscription.id,
                )
                return False

        # Apply updates
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.tier = new_tier
        subscription.status = target_status.value
        subscription.cancel_at_period_end = cancel_at_period_end
        subscription.last_event_timestamp = event_created

        if current_period_start:
            subscription.current_period_start = datetime.fromtimestamp(
                current_period_start, tz=UTC
            )
        if current_period_end:
            subscription.current_period_end = datetime.fromtimestamp(
                current_period_end, tz=UTC
            )

        await db.flush()
        logger.info(
            "Subscription synced: user=%s tier=%s status=%s",
            subscription.user_id,
            new_tier,
            target_status.value,
        )
        return True

    @staticmethod
    def _resolve_tier_from_items(items: list[dict[str, Any]]) -> str:
        """Resolve subscription tier from Stripe line items."""
        for item in items:
            price_id = item.get("price", {}).get("id", "")
            if price_id in (
                settings.stripe_premium_price_id,
                settings.stripe_premium_yearly_price_id,
            ):
                return SubscriptionTier.PREMIUM.value
            if price_id in (
                settings.stripe_pro_price_id,
                settings.stripe_pro_yearly_price_id,
            ):
                return SubscriptionTier.PRO.value
        return SubscriptionTier.FREE.value

    # ── Usage Tracking ─────────────────────────────────────────

    @staticmethod
    async def record_usage(
        db: AsyncSession,
        user: User,
        engine: str,
    ) -> UsageRecord:
        """Increment scan count for the current period.

        F4: Lazy period reset — if current period has passed, creates new record.
        """
        subscription = await BillingService.get_or_create_subscription(db, user)
        now = datetime.now(tz=UTC)

        # Find current period record
        result = await db.execute(
            select(UsageRecord)
            .where(
                UsageRecord.user_id == user.id,
                UsageRecord.period_end > now,
            )
            .order_by(UsageRecord.period_start.desc())
        )
        usage = result.scalar_one_or_none()

        if usage is None:
            # F4: Lazy reset — create new period record
            period_start = subscription.current_period_start or now
            period_end = subscription.current_period_end or now.replace(
                month=now.month % 12 + 1 if now.month < 12 else 1,
                year=now.year + (1 if now.month == 12 else 0),
            )
            usage = UsageRecord(
                user_id=user.id,
                subscription_id=subscription.id,
                period_start=period_start,
                period_end=period_end,
                scan_count=0,
                engine_breakdown={},
            )
            db.add(usage)
            await db.flush()

        # Increment
        usage.scan_count += 1
        breakdown = usage.engine_breakdown or {}
        breakdown[engine] = breakdown.get(engine, 0) + 1
        usage.engine_breakdown = breakdown

        await db.flush()
        await db.refresh(usage)
        return usage

    @staticmethod
    async def get_usage_summary(
        db: AsyncSession,
        user: User,
    ) -> dict[str, Any]:
        """Get current period usage summary."""
        subscription = await BillingService.get_or_create_subscription(db, user)
        tier = get_user_tier(user)
        scan_limit = TIER_SCAN_LIMITS.get(tier, 3)
        now = datetime.now(tz=UTC)

        result = await db.execute(
            select(UsageRecord)
            .where(
                UsageRecord.user_id == user.id,
                UsageRecord.period_end > now,
            )
            .order_by(UsageRecord.period_start.desc())
        )
        usage = result.scalar_one_or_none()

        scans_used = usage.scan_count if usage else 0
        scans_remaining = (scan_limit - scans_used) if scan_limit is not None else None

        return {
            "tier": tier,
            "scan_limit": scan_limit,
            "scans_used": scans_used,
            "scans_remaining": scans_remaining,
            "period_start": subscription.current_period_start,
            "period_end": subscription.current_period_end,
            "engine_breakdown": usage.engine_breakdown if usage else None,
        }

    # ── Checkout & Portal ──────────────────────────────────────

    @staticmethod
    async def create_checkout_session(
        db: AsyncSession,
        user: User,
        tier: str,
        annual: bool,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session.

        F1: Blocked when billing_enabled=False.
        F9: Lazy Stripe customer creation.
        """
        if not settings.billing_enabled:
            raise ValueError("Billing is currently disabled")

        import stripe

        stripe.api_key = settings.stripe_secret_key

        # F9: Get or create Stripe customer
        subscription = await BillingService.get_or_create_subscription(db, user)

        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={"pathforge_user_id": str(user.id)},
            )
            subscription.stripe_customer_id = customer.id
            await db.flush()

        # Resolve price ID
        price_id = BillingService._get_price_id(tier, annual)

        session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"pathforge_user_id": str(user.id)},
        )

        return session.url or ""

    @staticmethod
    async def create_portal_session(
        db: AsyncSession,
        user: User,
    ) -> str:
        """Create a Stripe Customer Portal session."""
        if not settings.billing_enabled:
            raise ValueError("Billing is currently disabled")

        import stripe

        stripe.api_key = settings.stripe_secret_key

        subscription = await BillingService.get_or_create_subscription(db, user)

        if not subscription.stripe_customer_id:
            raise ValueError("No billing account found. Please subscribe first.")

        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.frontend_url}/dashboard/settings/billing",  # R1/ADR-035-08
        )

        return session.url

    @staticmethod
    def _get_price_id(tier: str, annual: bool) -> str:
        """Resolve Stripe price ID from tier and billing interval."""
        price_map: dict[tuple[str, bool], str] = {
            ("pro", False): settings.stripe_pro_price_id,
            ("pro", True): settings.stripe_pro_yearly_price_id,
            ("premium", False): settings.stripe_premium_price_id,
            ("premium", True): settings.stripe_premium_yearly_price_id,
        }
        price_id = price_map.get((tier, annual))
        if not price_id:
            raise ValueError(f"Invalid tier/interval: {tier}/{annual}")
        return price_id

    # ── Webhook Helpers ────────────────────────────────────────

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str,
    ) -> dict[str, Any]:
        """Verify Stripe webhook signature and return parsed event.

        F35: Uses raw bytes payload for signature verification.
        """
        import stripe

        stripe.api_key = settings.stripe_secret_key

        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload,
            signature,
            settings.stripe_webhook_secret,
        )
        return dict(event)

    @staticmethod
    async def _log_billing_event(
        db: AsyncSession,
        event: dict[str, Any],
    ) -> bool:
        """Log a billing event idempotently.

        F2: INSERT ON CONFLICT DO NOTHING — returns True if inserted, False if duplicate.
        F22: Stores trimmed payload subset.
        """
        stripe_event_id = event.get("id", "")
        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        # F22: Trimmed payload
        payload_summary = {
            "type": event_type,
            "subscription_id": data_object.get("id", ""),
            "customer_id": data_object.get("customer", ""),
            "status": data_object.get("status", ""),
        }

        # Find user by Stripe customer ID
        customer_id = data_object.get("customer", "")
        user_id = None
        if customer_id:
            result = await db.execute(
                select(Subscription.user_id).where(
                    Subscription.stripe_customer_id == customer_id
                )
            )
            row = result.first()
            if row:
                user_id = row[0]

        stmt = pg_insert(BillingEvent).values(
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            user_id=user_id,
            payload_summary=payload_summary,
        ).on_conflict_do_nothing(index_elements=["stripe_event_id"])

        cursor_result = await db.execute(stmt)
        await db.flush()

        return (cursor_result.rowcount or 0) > 0  # type: ignore[attr-defined]

    # ── Event Listing (Admin) ──────────────────────────────────

    @staticmethod
    async def list_billing_events(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
    ) -> list[BillingEvent]:
        """List billing events for admin dashboard."""
        offset = (page - 1) * per_page
        result = await db.execute(
            select(BillingEvent)
            .order_by(BillingEvent.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return list(result.scalars().all())
