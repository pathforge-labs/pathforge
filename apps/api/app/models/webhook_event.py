"""
PathForge — Webhook Event Ledger Model (T6 / Sprint 58, ADR-0010)
===================================================================

Append-only ledger that every webhook receiver (Stripe, Sentry, future)
writes to.  Distinct from :class:`app.models.subscription.BillingEvent`
— that table holds the trimmed billing-domain summary; this one is the
operational DLQ surface for the SRE workflow.

The natural key is ``(provider, event_id)`` — same Stripe webhook
retried hits the same row instead of duplicating. The outcome field is
a string-typed enum (``received`` / ``processed`` / ``failed`` / ``dlq``)
so a future provider can introduce its own outcome without an Alembic
migration to alter the enum type.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WebhookOutcome(enum.StrEnum):
    """Outcome states for a webhook event.

    `StrEnum` subclassing means the column stores plain strings — the
    raw value is filterable from SQL or a non-Python admin tool — while
    Python code still gets the enum guard. Same pattern as
    :class:`app.core.feature_flags.RolloutStage`.
    """

    received = "received"
    processed = "processed"
    failed = "failed"
    dlq = "dlq"


class WebhookEvent(Base, TimestampMixin):
    """Append-only webhook ledger entry."""

    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Webhook provider — 'stripe', 'sentry', etc.",
    )
    event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc=(
            "Provider's event identifier (Stripe `id`, Sentry "
            "`event_id`). Combined with `provider` for uniqueness."
        ),
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Provider's event type (e.g. 'invoice.payment_succeeded').",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        doc=(
            "Full payload as received. Preserved for replay. JSONB so "
            "operators can index/filter by event-shape attrs (e.g. "
            "`payload->>'type'`) without scanning rows."
        ),
    )
    outcome: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WebhookOutcome.received.value,
        server_default=WebhookOutcome.received.value,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        default=0,
        server_default="0",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
        doc="String form of the last exception. Truncated by service layer.",
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # Natural key + idempotency support.
        Index(
            "ix_webhook_events_provider_event_id",
            "provider",
            "event_id",
            unique=True,
        ),
        # Admin DLQ list query.
        Index(
            "ix_webhook_events_outcome_created_at",
            "outcome",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookEvent provider={self.provider!s} "
            f"event_id={self.event_id!s} outcome={self.outcome!s}>"
        )


__all__ = ["WebhookEvent", "WebhookOutcome"]
