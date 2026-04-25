"""add career simulation tables

Revision ID: 2b3c4d5e6f7g
Revises: 1a2b3c4d5e6f
Create Date: 2026-02-21 00:30:00.000000+01:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "2b3c4d5e6f7g"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create 5 Career Simulation Engine tables."""
    # 1. career_simulations
    op.create_table(
        "career_simulations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "scenario_type",
            sa.String(50),
            nullable=False,
            server_default="role_transition",
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="completed",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "feasibility_rating",
            sa.Float,
            nullable=False,
            server_default="50.0",
        ),
        sa.Column("roi_score", sa.Float, nullable=True),
        sa.Column("salary_impact_percent", sa.Float, nullable=True),
        sa.Column("estimated_months", sa.Integer, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("factors", JSON, nullable=True),
        sa.Column(
            "data_source",
            sa.String(100),
            nullable=False,
            server_default="ai_simulation",
        ),
        sa.Column(
            "disclaimer",
            sa.Text,
            nullable=False,
            server_default=(
                "Simulation results are AI-generated projections based on "
                "aggregated career data. Actual outcomes may vary. This is not "
                "career advice — consult qualified professionals for important "
                "career decisions."
            ),
        ),
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
        sa.CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_simulation_confidence_cap",
        ),
    )

    # 2. simulation_inputs
    op.create_table(
        "simulation_inputs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "simulation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_simulations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("parameter_name", sa.String(255), nullable=False),
        sa.Column("parameter_value", sa.Text, nullable=False),
        sa.Column(
            "parameter_type",
            sa.String(50),
            nullable=False,
            server_default="str",
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

    # 3. simulation_outcomes
    op.create_table(
        "simulation_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "simulation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_simulations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("dimension", sa.String(100), nullable=False),
        sa.Column(
            "current_value",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "projected_value",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("delta", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
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

    # 4. simulation_recommendations
    op.create_table(
        "simulation_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "simulation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_simulations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "priority",
            sa.String(50),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("estimated_weeks", sa.Integer, nullable=True),
        sa.Column(
            "order_index", sa.Integer, nullable=False, server_default="0"
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

    # 5. simulation_preferences
    op.create_table(
        "simulation_preferences",
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
            "default_scenario_type",
            sa.String(50),
            nullable=False,
            server_default="role_transition",
        ),
        sa.Column(
            "max_scenarios",
            sa.Integer,
            nullable=False,
            server_default="50",
        ),
        sa.Column(
            "notification_enabled",
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


def downgrade() -> None:
    """Drop all 5 Career Simulation Engine tables in reverse order."""
    op.drop_table("simulation_preferences")
    op.drop_table("simulation_recommendations")
    op.drop_table("simulation_outcomes")
    op.drop_table("simulation_inputs")
    op.drop_table("career_simulations")
