"""add push token infrastructure

Revision ID: 9i0j1k2l3m4n
Revises: 8h9i0j1k2l3m, 0a1b2c3d4e5g, 0c2d3e4f5g6h
Create Date: 2026-03-02 01:50:00.000000+01:00

Sprint 33 — Reliability & Integrity Hardening
Merge migration: consolidates 4 heads into single head.
Creates push_tokens table and adds push_notifications column
to notif_preferences.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "9i0j1k2l3m4n"
down_revision: str | Sequence[str] | None = (
    # Note: 3c4d5e6f7g8h (Interview Intelligence) and 4d5e6f7g8h9i (Hidden Job Market)
    # are reachable through the sub-chain that ends at 0a1b2c3d4e5g.
    "8h9i0j1k2l3m",  # Sprint 20 — AI Transparency
    "0a1b2c3d4e5g",  # Sprint 21 — Career Action Planner (chain: 3c4d→4d5e→5e6f→6f7g→7g8h→0a1b)
    "0c2d3e4f5g6h",  # Sprint 23 — Delivery Layer
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create push_tokens table and add push_notifications column."""
    # ── push_tokens table ──────────────────────────────────────
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_token", sa.String(512), nullable=False, unique=True,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "last_used_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Primary lookup index
    op.create_index(
        "ix_push_tokens_user_id",
        "push_tokens",
        ["user_id"],
    )

    # Composite index for _get_active_tokens() query
    op.create_index(
        "ix_push_tokens_user_active",
        "push_tokens",
        ["user_id", "is_active"],
    )

    # ── push_notifications column on notif_preferences ─────────
    op.add_column(
        "notif_preferences",
        sa.Column(
            "push_notifications",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove push infrastructure."""
    op.drop_column("notif_preferences", "push_notifications")
    op.drop_table("push_tokens")
