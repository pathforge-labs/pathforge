"""
Alembic migration — Add Hidden Job Market Detector™ tables
============================================================
Sprint 15: 5 new tables for the Hidden Job Market Detector.
    - company_signal
    - signal_match_result
    - outreach_template
    - hidden_opportunity
    - hidden_job_market_preference

Revision ID: 4d5e6f7g8h9i
Revises: 3c4d5e6f7g8h
Create Date: 2026-02-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4d5e6f7g8h9i"
down_revision: str | None = "3c4d5e6f7g8h"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Sprint 15 Hidden Job Market tables."""
    # ── company_signal ─────────────────────────────────────────
    op.create_table(
        "company_signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("source", sa.String(512), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "data_source",
            sa.String(512),
            nullable=False,
            server_default="AI-generated signal intelligence based on public company data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(512),
            nullable=False,
            server_default=(
                "This signal analysis is AI-generated intelligence based on public data, "
                "not a guarantee of hiring intent. Company plans may change. "
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
            "strength BETWEEN 0.0 AND 1.0",
            name="chk_signal_strength",
        ),
        sa.CheckConstraint(
            "confidence_score BETWEEN 0.0 AND 1.0",
            name="chk_signal_confidence",
        ),
        sa.CheckConstraint(
            "signal_type IN ('funding', 'office_expansion', 'key_hire', "
            "'tech_stack_change', 'competitor_layoff', 'revenue_growth')",
            name="chk_signal_type",
        ),
        sa.CheckConstraint(
            "status IN ('detected', 'matched', 'actioned', 'dismissed', 'expired')",
            name="chk_signal_status",
        ),
    )
    op.create_index("ix_company_signal_career_dna_id", "company_signal", ["career_dna_id"])
    op.create_index("ix_company_signal_user_id", "company_signal", ["user_id"])
    op.create_index("ix_company_signal_company_name", "company_signal", ["company_name"])
    op.create_index("ix_company_signal_detected_at", "company_signal", ["detected_at"])

    # ── signal_match_result ────────────────────────────────────
    op.create_table(
        "signal_match_result",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("skill_overlap", sa.Float(), nullable=False),
        sa.Column("role_relevance", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("matched_skills", sa.JSON(), nullable=True),
        sa.Column("relevance_reasoning", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["company_signal.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "match_score BETWEEN 0.0 AND 1.0",
            name="chk_match_score",
        ),
        sa.CheckConstraint(
            "skill_overlap BETWEEN 0.0 AND 1.0",
            name="chk_skill_overlap",
        ),
        sa.CheckConstraint(
            "role_relevance BETWEEN 0.0 AND 1.0",
            name="chk_role_relevance",
        ),
    )
    op.create_index("ix_signal_match_result_signal_id", "signal_match_result", ["signal_id"])

    # ── outreach_template ──────────────────────────────────────
    op.create_table(
        "outreach_template",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("template_type", sa.String(50), nullable=False),
        sa.Column("tone", sa.String(50), nullable=False),
        sa.Column("subject_line", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("personalization_points", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["company_signal.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "confidence BETWEEN 0.0 AND 1.0",
            name="chk_outreach_confidence",
        ),
        sa.CheckConstraint(
            "template_type IN ('introduction', 'referral_request', "
            "'informational_interview', 'direct_application')",
            name="chk_template_type",
        ),
        sa.CheckConstraint(
            "tone IN ('professional', 'casual', 'enthusiastic')",
            name="chk_outreach_tone",
        ),
    )
    op.create_index("ix_outreach_template_signal_id", "outreach_template", ["signal_id"])

    # ── hidden_opportunity ─────────────────────────────────────
    op.create_table(
        "hidden_opportunity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("predicted_role", sa.String(255), nullable=False),
        sa.Column("predicted_seniority", sa.String(50), nullable=True),
        sa.Column("predicted_timeline_days", sa.Integer(), nullable=True),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("salary_range_min", sa.Float(), nullable=True),
        sa.Column("salary_range_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["company_signal.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "probability BETWEEN 0.0 AND 1.0",
            name="chk_opportunity_probability",
        ),
    )
    op.create_index("ix_hidden_opportunity_signal_id", "hidden_opportunity", ["signal_id"])

    # ── hidden_job_market_preference ───────────────────────────
    op.create_table(
        "hidden_job_market_preference",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("min_signal_strength", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("enabled_signal_types", sa.JSON(), nullable=True),
        sa.Column("max_outreach_per_week", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "auto_generate_outreach",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "notification_enabled",
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
        sa.CheckConstraint(
            "min_signal_strength BETWEEN 0.0 AND 1.0",
            name="chk_min_signal_strength",
        ),
    )
    op.create_index(
        "ix_hidden_job_market_preference_career_dna_id",
        "hidden_job_market_preference",
        ["career_dna_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop Sprint 15 Hidden Job Market tables."""
    op.drop_table("hidden_job_market_preference")
    op.drop_table("hidden_opportunity")
    op.drop_table("outreach_template")
    op.drop_table("signal_match_result")
    op.drop_table("company_signal")
