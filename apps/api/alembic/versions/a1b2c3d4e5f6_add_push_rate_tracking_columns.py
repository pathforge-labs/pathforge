"""add push rate tracking columns

Revision ID: a1b2c3d4e5f6
Revises: 9i0j1k2l3m4n
Create Date: 2026-03-02 02:46:00.000000+01:00

Sprint 33 — F4: Rate Limit Redesign
Adds daily_push_count and last_push_date columns to notif_preferences
for dispatch-based (not token-based) push rate limiting.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9i0j1k2l3m4n"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Add push rate tracking columns to notif_preferences."""
    op.add_column(
        "notif_preferences",
        sa.Column(
            "daily_push_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "notif_preferences",
        sa.Column(
            "last_push_date",
            sa.Date(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove push rate tracking columns."""
    op.drop_column("notif_preferences", "last_push_date")
    op.drop_column("notif_preferences", "daily_push_count")
