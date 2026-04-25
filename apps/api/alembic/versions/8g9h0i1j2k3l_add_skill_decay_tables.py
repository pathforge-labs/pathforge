"""Add Skill Decay & Growth Tracker tables

Revision ID: 8g9h0i1j2k3l
Revises: 7f8g9h0i1j2k
Create Date: 2026-02-20 02:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8g9h0i1j2k3l"
down_revision: str | None = "7f8g9h0i1j2k"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create 5 skill decay tables."""
    # 1. skill_freshness
    op.create_table(
        "skill_freshness",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "career_dna_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("last_active_date", sa.String(50), nullable=True),
        sa.Column("freshness_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("half_life_days", sa.Integer, nullable=False, server_default="1095"),
        sa.Column("decay_rate", sa.String(20), nullable=False, server_default="'moderate'"),
        sa.Column("days_since_active", sa.Integer, nullable=False, server_default="0"),
        sa.Column("refresh_urgency", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("analysis_reasoning", sa.Text, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_skill_freshness_skill_name",
        "skill_freshness",
        ["skill_name"],
    )

    # 2. market_demand_snapshots
    op.create_table(
        "market_demand_snapshots",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "career_dna_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("demand_score", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("demand_trend", sa.String(20), nullable=False, server_default="'stable'"),
        sa.Column("trend_confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("job_posting_signal", sa.JSON, nullable=True),
        sa.Column("industry_relevance", sa.JSON, nullable=True),
        sa.Column("growth_projection_6m", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("growth_projection_12m", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("data_sources", sa.JSON, nullable=True),
        sa.Column(
            "snapshot_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_market_demand_snapshots_skill_name",
        "market_demand_snapshots",
        ["skill_name"],
    )

    # 3. skill_velocity_entries
    op.create_table(
        "skill_velocity_entries",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "career_dna_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("velocity_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "velocity_direction",
            sa.String(20),
            nullable=False,
            server_default="'steady'",
        ),
        sa.Column("freshness_component", sa.Float, nullable=True),
        sa.Column("demand_component", sa.Float, nullable=True),
        sa.Column("composite_health", sa.Float, nullable=False, server_default="50.0"),
        sa.Column("acceleration", sa.Float, nullable=True, server_default="0.0"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_skill_velocity_entries_skill_name",
        "skill_velocity_entries",
        ["skill_name"],
    )

    # 4. reskilling_pathways
    op.create_table(
        "reskilling_pathways",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "career_dna_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("target_skill", sa.String(255), nullable=False),
        sa.Column("current_level", sa.String(50), nullable=False, server_default="'beginner'"),
        sa.Column("target_level", sa.String(50), nullable=False, server_default="'intermediate'"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="'recommended'"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("estimated_effort_hours", sa.Integer, nullable=True),
        sa.Column("prerequisite_skills", sa.JSON, nullable=True),
        sa.Column("learning_resources", sa.JSON, nullable=True),
        sa.Column("career_impact", sa.Text, nullable=True),
        sa.Column("freshness_gain", sa.Float, nullable=True, server_default="0.0"),
        sa.Column("demand_alignment", sa.Float, nullable=True, server_default="0.5"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_reskilling_pathways_target_skill",
        "reskilling_pathways",
        ["target_skill"],
    )

    # 5. skill_decay_preferences
    op.create_table(
        "skill_decay_preferences",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "career_dna_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tracking_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "notification_frequency",
            sa.String(20),
            nullable=False,
            server_default="'weekly'",
        ),
        sa.Column("decay_alert_threshold", sa.Float, nullable=False, server_default="40.0"),
        sa.Column("focus_categories", sa.JSON, nullable=True),
        sa.Column("excluded_skills", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop 5 skill decay tables."""
    op.drop_table("skill_decay_preferences")
    op.drop_table("reskilling_pathways")
    op.drop_table("skill_velocity_entries")
    op.drop_table("market_demand_snapshots")
    op.drop_table("skill_freshness")
