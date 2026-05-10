"""Add subscriptions.trial_end column (model/migration drift fix)

The Subscription ORM model declares a `trial_end: Mapped[datetime | None]`
column (apps/api/app/models/subscription.py:132), but the original
Sprint 34 monetization migration (`b2c3d4e5f6g7`) did not include it.
The drift only surfaced once a user authenticated against fresh
production: GET /api/v1/users/me eager-loads Subscription, the SELECT
references `subscriptions.trial_end`, and Postgres rejects with
`UndefinedColumnError` (Sentry: 2026-05-10).

This migration adds the missing column. Nullable=True (matching the
model), no server_default — existing rows (none in fresh prod, but
preserved for any pre-existing rows in dev DBs) get NULL.

Revision ID: ab12cd34ef56
Revises: f6g7h8i9j0k1
Create Date: 2026-05-10
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "ab12cd34ef56"
down_revision = "f6g7h8i9j0k1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "trial_end")
