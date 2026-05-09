"""
Alembic migration — Add Predictive Career Engine™ tables
==========================================================
Sprint 19: 5 new tables for the Predictive Career Engine.
    - pc_emerging_roles
    - pc_disruption_forecasts
    - pc_opportunity_surfaces
    - pc_career_forecasts
    - pc_preferences

Revision ID: 7g8h9i0j1k2l
Revises: 6f7g8h9i0j1k
Create Date: 2026-02-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "7g8h9i0j1k2l"
down_revision: str | None = "6f7g8h9i0j1k"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Sprint 19 Predictive Career Engine tables."""
    # ── pc_emerging_roles ──────────────────────────────────────
    op.create_table(
        "pc_emerging_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role_title", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(200), nullable=False),
        sa.Column(
            "emergence_stage", sa.String(20), nullable=False,
            server_default="nascent",
        ),
        sa.Column(
            "growth_rate_pct", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "skill_overlap_pct", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("time_to_mainstream_months", sa.Integer(), nullable=True),
        sa.Column("required_new_skills", sa.JSON(), nullable=True),
        sa.Column("transferable_skills", sa.JSON(), nullable=True),
        sa.Column("avg_salary_range_min", sa.Float(), nullable=True),
        sa.Column("avg_salary_range_max", sa.Float(), nullable=True),
        sa.Column("key_employers", sa.JSON(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-analyzed emerging role signals from public market data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Emerging role predictions are AI-generated estimates based "
                "on market trends. Actual role emergence timelines may vary. "
                "Maximum confidence: 85%."
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
            "confidence_score <= 0.85",
            name="ck_pc_emerging_role_confidence_cap",
        ),
    )
    op.create_index(
        "ix_pc_emerging_roles_career_dna_id",
        "pc_emerging_roles",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_pc_emerging_roles_user_id",
        "pc_emerging_roles",
        ["user_id"],
    )
    op.create_index(
        "ix_pc_emerging_roles_industry",
        "pc_emerging_roles",
        ["industry"],
    )
    op.create_index(
        "ix_pc_emerging_roles_emergence_stage",
        "pc_emerging_roles",
        ["emergence_stage"],
    )

    # ── pc_disruption_forecasts ────────────────────────────────
    op.create_table(
        "pc_disruption_forecasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("disruption_title", sa.String(255), nullable=False),
        sa.Column(
            "disruption_type", sa.String(30), nullable=False,
            server_default="technology",
        ),
        sa.Column("industry", sa.String(200), nullable=False),
        sa.Column(
            "severity_score", sa.Float(), nullable=False,
            server_default="50.0",
        ),
        sa.Column(
            "timeline_months", sa.Integer(), nullable=False,
            server_default="12",
        ),
        sa.Column("impact_on_user", sa.Text(), nullable=True),
        sa.Column("affected_skills", sa.JSON(), nullable=True),
        sa.Column("mitigation_strategies", sa.JSON(), nullable=True),
        sa.Column("opportunity_from_disruption", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-analyzed disruption signals from industry trend data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Disruption forecasts are AI-generated predictions based on "
                "industry trends. Actual disruption timing and impact may "
                "differ. Maximum confidence: 85%."
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
            "confidence_score <= 0.85",
            name="ck_pc_disruption_confidence_cap",
        ),
    )
    op.create_index(
        "ix_pc_disruption_forecasts_career_dna_id",
        "pc_disruption_forecasts",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_pc_disruption_forecasts_user_id",
        "pc_disruption_forecasts",
        ["user_id"],
    )
    op.create_index(
        "ix_pc_disruption_forecasts_disruption_type",
        "pc_disruption_forecasts",
        ["disruption_type"],
    )

    # ── pc_opportunity_surfaces ────────────────────────────────
    op.create_table(
        "pc_opportunity_surfaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_title", sa.String(255), nullable=False),
        sa.Column(
            "opportunity_type", sa.String(30), nullable=False,
            server_default="emerging_role",
        ),
        sa.Column(
            "source_signal", sa.String(200), nullable=False,
            server_default="market_analysis",
        ),
        sa.Column(
            "relevance_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("action_items", sa.JSON(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("skill_gap_analysis", sa.JSON(), nullable=True),
        sa.Column("time_sensitivity", sa.String(50), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-surfaced opportunity from market and skill signals",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Opportunities are AI-identified based on market signals "
                "and skill matching. Verify opportunities independently "
                "before acting. Maximum confidence: 85%."
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
            "confidence_score <= 0.85",
            name="ck_pc_opportunity_confidence_cap",
        ),
    )
    op.create_index(
        "ix_pc_opportunity_surfaces_career_dna_id",
        "pc_opportunity_surfaces",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_pc_opportunity_surfaces_user_id",
        "pc_opportunity_surfaces",
        ["user_id"],
    )
    op.create_index(
        "ix_pc_opportunity_surfaces_opportunity_type",
        "pc_opportunity_surfaces",
        ["opportunity_type"],
    )

    # ── pc_career_forecasts ────────────────────────────────────
    op.create_table(
        "pc_career_forecasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "outlook_score", sa.Float(), nullable=False,
            server_default="50.0",
        ),
        sa.Column(
            "outlook_category", sa.String(20), nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "forecast_horizon_months", sa.Integer(), nullable=False,
            server_default="12",
        ),
        sa.Column(
            "role_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "disruption_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "opportunity_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "trend_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("top_actions", sa.JSON(), nullable=True),
        sa.Column("key_risks", sa.JSON(), nullable=True),
        sa.Column("key_opportunities", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-computed Career Forecast Index from predictive signals",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Career Forecast Index is an AI-generated composite score. "
                "It reflects predicted market trends, not guaranteed outcomes. "
                "Use alongside your own research. Maximum confidence: 85%."
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
            "confidence_score <= 0.85",
            name="ck_pc_forecast_confidence_cap",
        ),
        sa.CheckConstraint(
            "outlook_score >= 0.0 AND outlook_score <= 100.0",
            name="ck_pc_forecast_outlook_range",
        ),
    )
    op.create_index(
        "ix_pc_career_forecasts_career_dna_id",
        "pc_career_forecasts",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_pc_career_forecasts_user_id",
        "pc_career_forecasts",
        ["user_id"],
    )

    # ── pc_preferences ─────────────────────────────────────────
    op.create_table(
        "pc_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "career_dna_id", UUID(as_uuid=True), nullable=False, unique=True,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "forecast_horizon_months", sa.Integer(), nullable=False,
            server_default="12",
        ),
        sa.Column(
            "include_emerging_roles",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "include_disruption_alerts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "include_opportunities",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "risk_tolerance", sa.String(20), nullable=False,
            server_default="moderate",
        ),
        sa.Column("focus_industries", sa.JSON(), nullable=True),
        sa.Column("focus_regions", sa.JSON(), nullable=True),
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
        "ix_pc_preferences_career_dna_id",
        "pc_preferences",
        ["career_dna_id"],
        unique=True,
    )
    op.create_index(
        "ix_pc_preferences_user_id",
        "pc_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop Sprint 19 Predictive Career Engine tables."""
    op.drop_table("pc_preferences")
    op.drop_table("pc_career_forecasts")
    op.drop_table("pc_opportunity_surfaces")
    op.drop_table("pc_disruption_forecasts")
    op.drop_table("pc_emerging_roles")
