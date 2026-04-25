"""add salary intelligence tables

Revision ID: 9j0k1l2m3n4o
Revises: 8g9h0i1j2k3l
Create Date: 2026-02-20 03:35:00.000000+01:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "9j0k1l2m3n4o"
down_revision = "8g9h0i1j2k3l"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create 5 Salary Intelligence Engine tables."""
    # 1. salary_estimates
    op.create_table(
        "salary_estimates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role_title", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("seniority_level", sa.String(50), nullable=False),
        sa.Column("industry", sa.String(255), nullable=False),
        sa.Column("estimated_min", sa.Float, nullable=False),
        sa.Column("estimated_max", sa.Float, nullable=False),
        sa.Column("estimated_median", sa.Float, nullable=False),
        sa.Column(
            "currency", sa.String(10), nullable=False, server_default="EUR"
        ),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "data_points_count", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("market_percentile", sa.Float, nullable=True),
        sa.Column("base_salary_factor", sa.Float, nullable=True),
        sa.Column("skill_premium_factor", sa.Float, nullable=True),
        sa.Column("experience_multiplier", sa.Float, nullable=True),
        sa.Column("market_condition_adjustment", sa.Float, nullable=True),
        sa.Column("analysis_reasoning", sa.Text, nullable=True),
        sa.Column("factors_detail", JSON, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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

    # 2. skill_salary_impacts
    op.create_table(
        "skill_salary_impacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column(
            "salary_impact_amount", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "salary_impact_percent", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "demand_premium", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "scarcity_factor", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "impact_direction",
            sa.String(20),
            nullable=False,
            server_default="positive",
        ),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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

    # 3. salary_history_entries
    op.create_table(
        "salary_history_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("estimated_min", sa.Float, nullable=False),
        sa.Column("estimated_max", sa.Float, nullable=False),
        sa.Column("estimated_median", sa.Float, nullable=False),
        sa.Column(
            "currency", sa.String(10), nullable=False, server_default="EUR"
        ),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("market_percentile", sa.Float, nullable=True),
        sa.Column("role_title", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("seniority_level", sa.String(50), nullable=False),
        sa.Column("skills_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("factors_snapshot", JSON, nullable=True),
        sa.Column(
            "snapshot_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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

    # 4. salary_scenarios
    op.create_table(
        "salary_scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("scenario_type", sa.String(50), nullable=False),
        sa.Column("scenario_label", sa.String(255), nullable=False),
        sa.Column("scenario_input", JSON, nullable=False),
        sa.Column("projected_min", sa.Float, nullable=False),
        sa.Column("projected_max", sa.Float, nullable=False),
        sa.Column("projected_median", sa.Float, nullable=False),
        sa.Column(
            "currency", sa.String(10), nullable=False, server_default="EUR"
        ),
        sa.Column(
            "delta_amount", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "delta_percent", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("impact_breakdown", JSON, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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

    # 5. salary_preferences
    op.create_table(
        "salary_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "preferred_currency",
            sa.String(10),
            nullable=False,
            server_default="EUR",
        ),
        sa.Column(
            "include_benefits",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("target_salary", sa.Float, nullable=True),
        sa.Column(
            "target_currency",
            sa.String(10),
            nullable=False,
            server_default="EUR",
        ),
        sa.Column(
            "notification_enabled",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "notification_frequency",
            sa.String(50),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column(
            "comparison_market",
            sa.String(100),
            nullable=False,
            server_default="Netherlands",
        ),
        sa.Column("comparison_industries", JSON, nullable=True),
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
    """Drop all 5 Salary Intelligence tables in reverse order."""
    op.drop_table("salary_preferences")
    op.drop_table("salary_scenarios")
    op.drop_table("salary_history_entries")
    op.drop_table("skill_salary_impacts")
    op.drop_table("salary_estimates")
