"""
Alembic migration — Add Cross-Border Career Passport™ tables
================================================================
Sprint 16: 5 new tables for the Cross-Border Career Passport.
    - credential_mappings
    - country_comparisons
    - visa_assessments
    - career_passport_market_demand
    - career_passport_preferences

Revision ID: 5e6f7g8h9i0j
Revises: 4d5e6f7g8h9i
Create Date: 2026-02-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5e6f7g8h9i0j"
down_revision: str | None = "4d5e6f7g8h9i"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Sprint 16 Career Passport tables."""
    # ── credential_mappings ────────────────────────────────────
    op.create_table(
        "credential_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_qualification", sa.String(500), nullable=False),
        sa.Column("source_country", sa.String(100), nullable=False),
        sa.Column("target_country", sa.String(100), nullable=False),
        sa.Column("equivalent_level", sa.String(500), nullable=False),
        sa.Column("eqf_level", sa.String(10), nullable=False),
        sa.Column("recognition_notes", sa.Text(), nullable=True),
        sa.Column("framework_reference", sa.String(200), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-powered credential equivalency via EQF framework",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "AI-estimated equivalency — verify with official bodies "
                "(ENIC-NARIC, national recognition centers). "
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
            name="ck_credential_mapping_confidence_cap",
        ),
    )
    op.create_index(
        "ix_credential_mappings_career_dna_id",
        "credential_mappings",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_credential_mappings_user_id",
        "credential_mappings",
        ["user_id"],
    )
    op.create_index(
        "ix_credential_mappings_target_country",
        "credential_mappings",
        ["target_country"],
    )
    op.create_index(
        "ix_credential_mappings_eqf_level",
        "credential_mappings",
        ["eqf_level"],
    )

    # ── country_comparisons ────────────────────────────────────
    op.create_table(
        "country_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_country", sa.String(100), nullable=False),
        sa.Column("target_country", sa.String(100), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="active",
        ),
        sa.Column("col_delta_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("salary_delta_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "purchasing_power_delta", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column("tax_impact_notes", sa.Text(), nullable=True),
        sa.Column(
            "market_demand_level", sa.String(20), nullable=False,
            server_default="moderate",
        ),
        sa.Column("detailed_breakdown", sa.JSON(), nullable=True),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-analyzed cost-of-living and salary data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Financial estimates are AI-generated approximations. "
                "Actual costs vary by lifestyle, location within country, and timing. "
                "Consult local resources for current data."
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
            "status IN ('draft', 'active', 'archived')",
            name="ck_comparison_status",
        ),
        sa.CheckConstraint(
            "market_demand_level IN ('low', 'moderate', 'high', 'very_high')",
            name="ck_comparison_demand_level",
        ),
    )
    op.create_index(
        "ix_country_comparisons_career_dna_id",
        "country_comparisons",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_country_comparisons_user_id",
        "country_comparisons",
        ["user_id"],
    )
    op.create_index(
        "ix_country_comparisons_target_country",
        "country_comparisons",
        ["target_country"],
    )

    # ── visa_assessments ───────────────────────────────────────
    op.create_table(
        "visa_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("nationality", sa.String(100), nullable=False),
        sa.Column("target_country", sa.String(100), nullable=False),
        sa.Column("visa_type", sa.String(30), nullable=False),
        sa.Column("eligibility_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("processing_time_weeks", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-assessed visa feasibility based on public immigration data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "This is NOT legal or immigration advice. "
                "Visa requirements change frequently. "
                "Consult official immigration authorities or a licensed advisor. "
                "Maximum eligibility confidence: 85%."
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
            "eligibility_score <= 0.85",
            name="ck_visa_assessment_eligibility_cap",
        ),
        sa.CheckConstraint(
            "visa_type IN ("
            "'free_movement', 'work_permit', 'blue_card', "
            "'skilled_worker', 'investor', 'other'"
            ")",
            name="ck_visa_type",
        ),
    )
    op.create_index(
        "ix_visa_assessments_career_dna_id",
        "visa_assessments",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_visa_assessments_user_id",
        "visa_assessments",
        ["user_id"],
    )
    op.create_index(
        "ix_visa_assessments_target_country",
        "visa_assessments",
        ["target_country"],
    )
    op.create_index(
        "ix_visa_assessments_visa_type",
        "visa_assessments",
        ["visa_type"],
    )

    # ── career_passport_market_demand ──────────────────────────
    op.create_table(
        "career_passport_market_demand",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("role", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(200), nullable=True),
        sa.Column(
            "demand_level", sa.String(20), nullable=False,
            server_default="moderate",
        ),
        sa.Column("open_positions_estimate", sa.Integer(), nullable=True),
        sa.Column("yoy_growth_pct", sa.Float(), nullable=True),
        sa.Column("top_employers", sa.JSON(), nullable=True),
        sa.Column("salary_range_min", sa.Float(), nullable=True),
        sa.Column("salary_range_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default="AI-analyzed market demand from public job data",
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "Market demand estimates are AI-generated approximations. "
                "Actual job availability varies. "
                "Consult local job boards for current openings."
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
            "demand_level IN ('low', 'moderate', 'high', 'very_high')",
            name="ck_market_demand_level",
        ),
    )
    op.create_index(
        "ix_career_passport_market_demand_career_dna_id",
        "career_passport_market_demand",
        ["career_dna_id"],
    )
    op.create_index(
        "ix_career_passport_market_demand_user_id",
        "career_passport_market_demand",
        ["user_id"],
    )
    op.create_index(
        "ix_career_passport_market_demand_country",
        "career_passport_market_demand",
        ["country"],
    )

    # ── career_passport_preferences ────────────────────────────
    op.create_table(
        "career_passport_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("career_dna_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_countries", sa.JSON(), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column(
            "include_visa_info",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "include_col_comparison",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "include_market_demand",
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
        "ix_career_passport_preferences_career_dna_id",
        "career_passport_preferences",
        ["career_dna_id"],
        unique=True,
    )
    op.create_index(
        "ix_career_passport_preferences_user_id",
        "career_passport_preferences",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop Sprint 16 Career Passport tables."""
    op.drop_table("career_passport_preferences")
    op.drop_table("career_passport_market_demand")
    op.drop_table("visa_assessments")
    op.drop_table("country_comparisons")
    op.drop_table("credential_mappings")
