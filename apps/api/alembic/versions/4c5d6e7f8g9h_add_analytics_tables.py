"""
Add analytics tables — funnel_events, market_insights, cv_experiments

Revision ID: 4c5d6e7f8g9h
Revises: 3b4c5d6e7f8g
Create Date: 2026-02-14

Sprint 6b — Analytics (ARCHITECTURE.md §7)
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "4c5d6e7f8g9h"
down_revision = "3b4c5d6e7f8g"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- funnel_events table --
    op.create_table(
        "funnel_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_funnel_events_user_id", "funnel_events", ["user_id"])
    op.create_index("ix_funnel_events_application_id", "funnel_events", ["application_id"])
    op.create_index("ix_funnel_events_stage", "funnel_events", ["stage"])
    op.create_index("ix_funnel_events_created_at", "funnel_events", ["created_at"])

    # -- market_insights table --
    op.create_table(
        "market_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("insight_type", sa.String(30), nullable=False),
        sa.Column("data", JSON, nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_market_insights_user_id", "market_insights", ["user_id"])
    op.create_index("ix_market_insights_insight_type", "market_insights", ["insight_type"])
    op.create_index("ix_market_insights_generated_at", "market_insights", ["generated_at"])

    # -- cv_experiments table --
    op.create_table(
        "cv_experiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_listing_id", UUID(as_uuid=True), sa.ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_a_id", UUID(as_uuid=True), sa.ForeignKey("cv_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_b_id", UUID(as_uuid=True), sa.ForeignKey("cv_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("winner_id", UUID(as_uuid=True), sa.ForeignKey("cv_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("metrics", JSON, nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cv_experiments_user_id", "cv_experiments", ["user_id"])
    op.create_index("ix_cv_experiments_job_listing_id", "cv_experiments", ["job_listing_id"])
    op.create_index("ix_cv_experiments_status", "cv_experiments", ["status"])


def downgrade() -> None:
    op.drop_table("cv_experiments")
    op.drop_table("market_insights")
    op.drop_table("funnel_events")
