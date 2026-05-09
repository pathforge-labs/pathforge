"""
Alembic migration — Add Career Action Planner™ tables
========================================================
Sprint 21: 5 new tables for the Career Action Planner.
    - career_action_plans
    - plan_milestones
    - milestone_progress
    - plan_recommendations
    - career_action_planner_preferences

Revision ID: 0a1b2c3d4e5g
Revises: 7g8h9i0j1k2l
Create Date: 2026-02-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0a1b2c3d4e5g"
down_revision: str | None = "7g8h9i0j1k2l"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Sprint 21 Career Action Planner tables."""
    # ── career_action_plans ────────────────────────────────────
    op.create_table(
        "career_action_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column(
            "plan_type", sa.String(30), nullable=False,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "priority_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "confidence", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(300),
            nullable=False,
            server_default=(
                "AI-powered career action planning "
                "via Career Sprint Methodology™"
            ),
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "AI-generated career action plan — milestones are "
                "suggestions, not guarantees. Timelines are estimates. "
                "Verify with professional career advisors when making "
                "major career decisions. Maximum confidence: 85%."
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["career_dna_id"],
            ["career_dna.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "confidence <= 0.85",
            name="ck_career_action_plan_confidence_cap",
        ),
        sa.CheckConstraint(
            "priority_score >= 0.0 AND priority_score <= 100.0",
            name="ck_career_action_plan_priority_range",
        ),
    )
    op.create_index(
        "ix_career_action_plans_career_dna_id",
        "career_action_plans",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_career_action_plans_user_id",
        "career_action_plans",
        ["user_id"],
    )
    op.create_index(
        "ix_career_action_plans_plan_type",
        "career_action_plans",
        ["plan_type"],
    )
    op.create_index(
        "ix_career_action_plans_status",
        "career_action_plans",
        ["status"],
    )

    # ── plan_milestones ────────────────────────────────────────
    op.create_table(
        "plan_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category", sa.String(30), nullable=False,
        ),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="not_started",
        ),
        sa.Column(
            "effort_hours", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "priority", sa.Integer(), nullable=False,
            server_default="5",
        ),
        sa.Column("evidence_required", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["career_action_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "priority >= 1 AND priority <= 10",
            name="ck_plan_milestone_priority_range",
        ),
        sa.CheckConstraint(
            "effort_hours >= 0",
            name="ck_plan_milestone_effort_positive",
        ),
    )
    op.create_index(
        "ix_plan_milestones_plan_id",
        "plan_milestones",
        ["plan_id"],
    )
    op.create_index(
        "ix_plan_milestones_category",
        "plan_milestones",
        ["category"],
    )
    op.create_index(
        "ix_plan_milestones_status",
        "plan_milestones",
        ["status"],
    )

    # ── milestone_progress ─────────────────────────────────────
    op.create_table(
        "milestone_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "progress_percent", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evidence_url", sa.String(500), nullable=True),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["milestone_id"],
            ["plan_milestones.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "progress_percent >= 0.0 AND progress_percent <= 100.0",
            name="ck_milestone_progress_percent_range",
        ),
    )
    op.create_index(
        "ix_milestone_progress_milestone_id",
        "milestone_progress",
        ["milestone_id"],
    )

    # ── plan_recommendations ───────────────────────────────────
    op.create_table(
        "plan_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_engine", sa.String(40), nullable=False,
        ),
        sa.Column("recommendation_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "urgency", sa.String(20), nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "impact_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("linked_entity_id", sa.String(36), nullable=True),
        sa.Column("context_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["career_action_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "impact_score >= 0.0 AND impact_score <= 100.0",
            name="ck_plan_recommendation_impact_range",
        ),
    )
    op.create_index(
        "ix_plan_recommendations_plan_id",
        "plan_recommendations",
        ["plan_id"],
    )
    op.create_index(
        "ix_plan_recommendations_source_engine",
        "plan_recommendations",
        ["source_engine"],
    )

    # ── career_action_planner_preferences ──────────────────────
    op.create_table(
        "career_action_planner_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "career_dna_id", UUID(as_uuid=True), nullable=False, unique=True,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "preferred_sprint_length_weeks", sa.Integer(), nullable=False,
            server_default="2",
        ),
        sa.Column(
            "max_milestones_per_plan", sa.Integer(), nullable=False,
            server_default="5",
        ),
        sa.Column("focus_areas", sa.JSON(), nullable=True),
        sa.Column(
            "notification_frequency", sa.String(20), nullable=False,
            server_default="weekly",
        ),
        sa.Column(
            "auto_generate_recommendations",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["career_dna_id"],
            ["career_dna.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cap_preferences_career_dna_id",
        "career_action_planner_preferences",
        ["career_dna_id"],
        unique=True,
    )
    op.create_index(
        "ix_cap_preferences_user_id",
        "career_action_planner_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop Sprint 21 Career Action Planner tables."""
    op.drop_table("career_action_planner_preferences")
    op.drop_table("plan_recommendations")
    op.drop_table("milestone_progress")
    op.drop_table("plan_milestones")
    op.drop_table("career_action_plans")
