"""create career orchestration tables

Revision ID: 0b1c2d3e4f5g
Revises: 9j0k1l2m3n4o
Create Date: 2026-02-24 03:45:00.000000+01:00

Sprint 22 — Phase D: Career Orchestration Layer
Creates 7 tables for:
  - Career Command Center™ (2 tables)
  - Notification Engine™ (3 tables)
  - User Profile & GDPR Export (2 tables)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "0b1c2d3e4f5g"
down_revision = "9j0k1l2m3n4o"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create 7 Career Orchestration Layer tables."""
    # ── 1. cc_career_snapshots (Career Command Center™) ───────
    op.create_table(
        "cc_career_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "career_dna_id",
            sa.String,
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("health_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "health_band",
            sa.String(20),
            nullable=False,
            server_default="attention",
        ),
        sa.Column("engine_statuses", JSON, nullable=True),
        sa.Column("strengths", JSON, nullable=True),
        sa.Column("attention_areas", JSON, nullable=True),
        sa.Column(
            "trend_direction",
            sa.String(20),
            nullable=False,
            server_default="stable",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default=(
                "Career Vitals™ — 12-engine composite health score"
            ),
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Career Health Score is an AI-generated composite metric "
                "derived from 12 intelligence engines. It reflects career "
                "wellness indicators, not guaranteed outcomes. Use alongside "
                "your own judgment."
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "health_score >= 0.0 AND health_score <= 100.0",
            name="ck_cc_snapshot_health_score_range",
        ),
    )

    # ── 2. cc_preferences (Career Command Center™) ────────────
    op.create_table(
        "cc_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("pinned_engines", JSON, nullable=True),
        sa.Column("hidden_engines", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── 3. notif_career_notifications (Notification Engine™) ──
    op.create_table(
        "notif_career_notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_engine", sa.String(100), nullable=False, index=True,
        ),
        sa.Column(
            "notification_type",
            sa.String(30),
            nullable=False,
            server_default="insight",
            index=True,
        ),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default="low",
            index=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column(
            "is_read",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "read_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── 4. notif_preferences (Notification Engine™) ───────────
    op.create_table(
        "notif_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("enabled_engines", JSON, nullable=True),
        sa.Column(
            "min_severity",
            sa.String(20),
            nullable=False,
            server_default="low",
        ),
        sa.Column(
            "digest_enabled",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "digest_frequency",
            sa.String(20),
            nullable=False,
            server_default="weekly",
        ),
        sa.Column("quiet_hours_start", sa.Time, nullable=True),
        sa.Column("quiet_hours_end", sa.Time, nullable=True),
        sa.Column(
            "in_app_notifications",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "email_notifications",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── 5. notif_digests (Notification Engine™) ───────────────
    op.create_table(
        "notif_digests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "digest_type",
            sa.String(20),
            nullable=False,
            server_default="weekly",
        ),
        sa.Column(
            "period_start",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "period_end",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "notification_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("summary", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── 6. user_profiles (User Profile) ───────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("headline", sa.String(300), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column(
            "timezone",
            sa.String(50),
            nullable=False,
            server_default="UTC",
        ),
        sa.Column(
            "language",
            sa.String(10),
            nullable=False,
            server_default="en",
        ),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column(
            "onboarding_completed",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("preferences", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── 7. user_data_export_requests (GDPR Export) ────────────
    op.create_table(
        "user_data_export_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.String,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "export_type",
            sa.String(30),
            nullable=False,
            server_default="full",
        ),
        sa.Column(
            "format",
            sa.String(10),
            nullable=False,
            server_default="json",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("record_count", sa.Integer, nullable=True),
        sa.Column("categories", JSON, nullable=True),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "download_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_downloaded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Drop all 7 Career Orchestration tables in reverse order."""
    op.drop_table("user_data_export_requests")
    op.drop_table("user_profiles")
    op.drop_table("notif_digests")
    op.drop_table("notif_preferences")
    op.drop_table("notif_career_notifications")
    op.drop_table("cc_preferences")
    op.drop_table("cc_career_snapshots")
