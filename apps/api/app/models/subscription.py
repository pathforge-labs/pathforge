"""
PathForge — Subscription & Billing Models
==========================================
Sprint 34: Stripe Billing infrastructure.

Models: Subscription (1:1 user), UsageRecord (per-period), BillingEvent (idempotent log).

Audit findings:
    F2 — stripe_event_id unique (idempotent webhook dedup)
    F3 — SubscriptionStatus StrEnum (state machine)
    F10 — last_event_timestamp (stale event rejection)
    F19 — CheckConstraint on scan_count
    F22 — payload_summary (trimmed, not full event)
    F23 — compound index on (user_id, period_start)
    F24 — StrEnum pattern (matches 70+ existing)
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class SubscriptionTier(enum.StrEnum):
    """Pricing tier classification."""

    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class SubscriptionStatus(enum.StrEnum):
    """Stripe subscription lifecycle status."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


# State machine: valid transitions (F3)
VALID_STATUS_TRANSITIONS: dict[SubscriptionStatus, set[SubscriptionStatus]] = {
    SubscriptionStatus.INCOMPLETE: {SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELED},
    SubscriptionStatus.TRIALING: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.CANCELED,
    },
    SubscriptionStatus.ACTIVE: {SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELED},
    SubscriptionStatus.PAST_DUE: {SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELED},
    SubscriptionStatus.CANCELED: set(),  # terminal state
}


# ── Subscription ───────────────────────────────────────────────


class Subscription(UUIDMixin, TimestampMixin, Base):
    """
    User subscription record linked to Stripe.

    One subscription per user. Free tier is the implicit default when no
    Stripe subscription exists. 'last_event_timestamp' supports stale
    webhook rejection (F10).
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('free', 'pro', 'premium')",
            name="ck_subscription_tier_valid",
        ),
        CheckConstraint(
            "status IN ('active', 'past_due', 'canceled', 'trialing', 'incomplete')",
            name="ck_subscription_status_valid",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    tier: Mapped[str] = mapped_column(
        String(20), default=SubscriptionTier.FREE.value, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SubscriptionStatus.ACTIVE.value, nullable=False
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    trial_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_event_timestamp: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="subscription")
    usage_records: Mapped[list[UsageRecord]] = relationship(
        "UsageRecord", back_populates="subscription", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subscription user={self.user_id} tier={self.tier} status={self.status}>"


# ── Usage Record ───────────────────────────────────────────────


class UsageRecord(UUIDMixin, TimestampMixin, Base):
    """
    Per-period AI scan usage for a subscription.

    Tracks total scans consumed during a billing period, with per-engine
    breakdown in JSON. Period is lazy-reset on access (F4).
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_usage_user_period"),
        CheckConstraint("scan_count >= 0", name="ck_usage_scan_count_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scan_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engine_breakdown: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    subscription: Mapped[Subscription] = relationship(
        "Subscription", back_populates="usage_records"
    )

    def __repr__(self) -> str:
        return f"<UsageRecord user={self.user_id} scans={self.scan_count}>"


# ── Billing Event ──────────────────────────────────────────────


class BillingEvent(UUIDMixin, TimestampMixin, Base):
    """
    Idempotent Stripe webhook event log.

    Stores trimmed payload subset (F22) with unique stripe_event_id (F2)
    for duplicate rejection via INSERT ON CONFLICT DO NOTHING.
    """

    __tablename__ = "billing_events"

    stripe_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload_summary: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BillingEvent {self.stripe_event_id} type={self.event_type}>"
