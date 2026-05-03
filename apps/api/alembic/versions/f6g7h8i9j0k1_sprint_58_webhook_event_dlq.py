"""Sprint 58 — Webhook event DLQ ledger (T6 / ADR-0010)

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-04-26

Adds the `webhook_events` table — append-only ledger that every
webhook receiver writes to.  Failures route to DLQ
(`outcome = 'dlq'`) and are replayable from the admin endpoint at
`/api/v1/admin/webhooks`.

Distinct from the existing `billing_events` table:
- `billing_events` is the *billing-domain summary* — trimmed payload
  subset, used by the dashboard and the customer-facing audit trail.
- `webhook_events` is the *operational DLQ ledger* — full payload,
  retry bookkeeping, multi-provider (Stripe, Sentry, future).

Both ledgers are written from the same handler invocation; they
serve different consumers and have different retention policies
(billing events — 7 years for tax compliance; webhook events —
90 days rolling).

Closes T6 in `docs/architecture/sprint-55-58-code-side-readiness.md`.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "f6g7h8i9j0k1"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "outcome",
            sa.String(20),
            nullable=False,
            server_default="received",
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    # `(provider, event_id)` is the natural key — same Stripe webhook
    # retried hits the same row instead of creating a duplicate.
    op.create_index(
        "ix_webhook_events_provider_event_id",
        "webhook_events",
        ["provider", "event_id"],
        unique=True,
    )
    # Operational queries: "show me everything in the DLQ" + the time
    # axis on each so the admin dashboard sorts cleanly.
    op.create_index(
        "ix_webhook_events_outcome_created_at",
        "webhook_events",
        ["outcome", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_events_outcome_created_at", table_name="webhook_events")
    op.drop_index("ix_webhook_events_provider_event_id", table_name="webhook_events")
    op.drop_table("webhook_events")
