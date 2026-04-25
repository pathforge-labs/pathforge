"""
Alembic migration — Add Collective Intelligence Engine™ tables
================================================================
Sprint 17: 5 new tables for the Collective Intelligence Engine.
    - ci_industry_snapshots
    - ci_salary_benchmarks
    - ci_peer_cohort_analyses
    - ci_career_pulse_entries
    - ci_preferences

Revision ID: 6f7g8h9i0j1k
Revises: 5e6f7g8h9i0j
Create Date: 2026-02-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6f7g8h9i0j1k"
down_revision: str | None = "5e6f7g8h9i0j"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Sprint 17 Collective Intelligence Engine tables."""
    # ── ci_industry_snapshots ──────────────────────────────────
    op.create_table(
        "ci_industry_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("industry", sa.String(200), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column(
            "trend_direction", sa.String(20), nullable=False,
            server_default="stable",
        ),
        sa.Column(
            "demand_intensity", sa.String(20), nullable=False,
            server_default="moderate",
        ),
        sa.Column("top_emerging_skills", sa.JSON(), nullable=True),
        sa.Column("declining_skills", sa.JSON(), nullable=True),
        sa.Column("avg_salary_range_min", sa.Float(), nullable=True),
        sa.Column("avg_salary_range_max", sa.Float(), nullable=True),
        sa.Column(
            "currency", sa.String(10), nullable=False,
            server_default="EUR",
        ),
        sa.Column("growth_rate_pct", sa.Float(), nullable=True),
        sa.Column("hiring_volume_trend", sa.Text(), nullable=True),
        sa.Column("key_insights", sa.JSON(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-analyzed industry trends from public market data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Industry trends are AI-generated estimates based on publicly "
                "available data. Actual market conditions may vary by region "
                "and time. Maximum confidence: 85%."
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
            name="ck_ci_industry_confidence_cap",
        ),
    )
    op.create_index(
        "ix_ci_industry_snapshots_career_dna_id",
        "ci_industry_snapshots",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_ci_industry_snapshots_user_id",
        "ci_industry_snapshots",
        ["user_id"],
    )
    op.create_index(
        "ix_ci_industry_snapshots_industry",
        "ci_industry_snapshots",
        ["industry"],
    )

    # ── ci_salary_benchmarks ───────────────────────────────────
    op.create_table(
        "ci_salary_benchmarks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(255), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column(
            "experience_years", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "benchmark_min", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "benchmark_median", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "benchmark_max", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "currency", sa.String(10), nullable=False,
            server_default="EUR",
        ),
        sa.Column("user_percentile", sa.Float(), nullable=True),
        sa.Column("skill_premium_pct", sa.Float(), nullable=True),
        sa.Column("experience_factor", sa.Float(), nullable=True),
        sa.Column("negotiation_insights", sa.JSON(), nullable=True),
        sa.Column("premium_skills", sa.JSON(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-analyzed salary benchmarks from public market data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Salary benchmarks are AI-generated estimates. Actual "
                "compensation varies by company, negotiation, and benefits. "
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
            name="ck_ci_salary_confidence_cap",
        ),
    )
    op.create_index(
        "ix_ci_salary_benchmarks_career_dna_id",
        "ci_salary_benchmarks",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_ci_salary_benchmarks_user_id",
        "ci_salary_benchmarks",
        ["user_id"],
    )
    op.create_index(
        "ix_ci_salary_benchmarks_location",
        "ci_salary_benchmarks",
        ["location"],
    )

    # ── ci_peer_cohort_analyses ────────────────────────────────
    op.create_table(
        "ci_peer_cohort_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("cohort_criteria", sa.JSON(), nullable=False),
        sa.Column(
            "cohort_size", sa.Integer(), nullable=False,
            server_default="10",
        ),
        sa.Column(
            "user_rank_percentile", sa.Float(), nullable=False,
            server_default="50.0",
        ),
        sa.Column(
            "avg_skills_count", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "user_skills_count", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "avg_experience_years", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("common_transitions", sa.JSON(), nullable=True),
        sa.Column("top_differentiating_skills", sa.JSON(), nullable=True),
        sa.Column("skill_gaps_vs_cohort", sa.JSON(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-synthesized peer cohort from anonymized market data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Peer cohort is AI-synthesized from general market data with "
                "k-anonymity (min 10 in cohort). No individual user data is "
                "shared. Maximum confidence: 85%."
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
            name="ck_ci_peer_cohort_confidence_cap",
        ),
        sa.CheckConstraint(
            "cohort_size >= 10",
            name="ck_ci_peer_cohort_k_anonymity",
        ),
    )
    op.create_index(
        "ix_ci_peer_cohort_analyses_career_dna_id",
        "ci_peer_cohort_analyses",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_ci_peer_cohort_analyses_user_id",
        "ci_peer_cohort_analyses",
        ["user_id"],
    )

    # ── ci_career_pulse_entries ─────────────────────────────────
    op.create_table(
        "ci_career_pulse_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "pulse_score", sa.Float(), nullable=False,
            server_default="50.0",
        ),
        sa.Column(
            "pulse_category", sa.String(20), nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "trend_direction", sa.String(20), nullable=False,
            server_default="stable",
        ),
        sa.Column(
            "demand_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "salary_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "skill_relevance_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "trend_component", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("top_opportunities", sa.JSON(), nullable=True),
        sa.Column("risk_factors", sa.JSON(), nullable=True),
        sa.Column("recommended_actions", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-computed Career Pulse Index from market intelligence",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Career Pulse Index is an AI-generated composite score. "
                "It reflects general market trends, not guaranteed outcomes. "
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
            name="ck_ci_pulse_confidence_cap",
        ),
        sa.CheckConstraint(
            "pulse_score >= 0.0 AND pulse_score <= 100.0",
            name="ck_ci_pulse_score_range",
        ),
    )
    op.create_index(
        "ix_ci_career_pulse_entries_career_dna_id",
        "ci_career_pulse_entries",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_ci_career_pulse_entries_user_id",
        "ci_career_pulse_entries",
        ["user_id"],
    )

    # ── ci_preferences ─────────────────────────────────────────
    op.create_table(
        "ci_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.String(), nullable=False, unique=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "include_industry_pulse",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "include_salary_benchmarks",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "include_peer_analysis",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("preferred_industries", sa.JSON(), nullable=True),
        sa.Column("preferred_locations", sa.JSON(), nullable=True),
        sa.Column(
            "preferred_currency", sa.String(10), nullable=False,
            server_default="EUR",
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
        "ix_ci_preferences_career_dna_id",
        "ci_preferences",
        ["career_dna_id"],
        unique=True,
    )
    op.create_index(
        "ix_ci_preferences_user_id",
        "ci_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop Sprint 17 Collective Intelligence Engine tables."""
    op.drop_table("ci_preferences")
    op.drop_table("ci_career_pulse_entries")
    op.drop_table("ci_peer_cohort_analyses")
    op.drop_table("ci_salary_benchmarks")
    op.drop_table("ci_industry_snapshots")
