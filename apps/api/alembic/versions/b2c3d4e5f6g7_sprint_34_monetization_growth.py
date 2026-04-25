"""sprint_34_monetization_growth

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-02 13:46:00.000000+01:00

Sprint 34 — Monetization & Growth Infrastructure
Adds subscriptions, usage_records, billing_events, admin_audit_logs,
waitlist_entries, public_career_profiles tables.
Updates users table with role column and subscription relationship.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "b2c3d4e5f6g7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Create Sprint 34 tables and add user role column."""

    # ── 1. Add role column to users ────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # ── 2. Subscriptions ───────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stripe_customer_id", sa.String(255), unique=True, nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), unique=True, nullable=True),
        sa.Column("tier", sa.String(20), nullable=False, server_default=sa.text("'free'")),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'active'")),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_timestamp", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "tier IN ('free', 'pro', 'premium')",
            name="ck_subscription_tier_valid",
        ),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"])

    # ── 3. Usage Records ──────────────────────────────────────
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scan_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("engine_breakdown", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "period_start", name="uq_usage_user_period"),
        sa.CheckConstraint("scan_count >= 0", name="ck_usage_scan_count_non_negative"),
    )
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"])

    # ── 4. Billing Events ─────────────────────────────────────
    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stripe_event_id", sa.String(255), unique=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload_summary", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_billing_events_stripe_event_id", "billing_events", ["stripe_event_id"])
    op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"])

    # ── 5. Admin Audit Logs ───────────────────────────────────
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "admin_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column(
            "target_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("details", postgresql.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_audit_logs_admin_user_id", "admin_audit_logs", ["admin_user_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_logs_target_user_id", "admin_audit_logs", ["target_user_id"])

    # ── 6. Waitlist Entries ───────────────────────────────────
    op.create_table(
        "waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("invite_token", sa.String(64), unique=True, nullable=True),
        sa.Column("referral_source", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "converted_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("position >= 1", name="ck_waitlist_position_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'invited', 'converted', 'expired')",
            name="ck_waitlist_status_valid",
        ),
    )
    op.create_index("ix_waitlist_entries_email", "waitlist_entries", ["email"])
    op.create_index("ix_waitlist_entries_invite_token", "waitlist_entries", ["invite_token"])

    # ── 7. Public Career Profiles ────────────────────────────
    op.create_table(
        "public_career_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("headline", sa.String(255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("skills_showcase", postgresql.JSON(), nullable=True),
        sa.Column("social_links", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("view_count >= 0", name="ck_public_profile_view_count_non_negative"),
    )
    op.create_index("ix_public_career_profiles_user_id", "public_career_profiles", ["user_id"])
    op.create_index("ix_public_career_profiles_slug", "public_career_profiles", ["slug"])


def downgrade() -> None:
    """Drop Sprint 34 tables and remove user role column."""
    op.drop_table("public_career_profiles")
    op.drop_table("waitlist_entries")
    op.drop_table("admin_audit_logs")
    op.drop_table("billing_events")
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_index("ix_users_role", "users")
    op.drop_column("users", "role")
