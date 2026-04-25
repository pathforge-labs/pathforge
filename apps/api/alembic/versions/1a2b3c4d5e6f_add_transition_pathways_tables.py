"""add transition pathways tables

Revision ID: 1a2b3c4d5e6f
Revises: 0a1b2c3d4e5f
Create Date: 2026-02-20 22:30:00.000000+01:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "1a2b3c4d5e6f"
down_revision = "0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create 5 Transition Pathways tables."""
    # 1. transition_paths
    op.create_table(
        "transition_paths",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("from_role", sa.String(255), nullable=False, index=True),
        sa.Column("to_role", sa.String(255), nullable=False, index=True),
        sa.Column(
            "confidence_score", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "difficulty",
            sa.String(50),
            nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "skill_overlap_percent",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "skills_to_acquire_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("estimated_duration_months", sa.Integer, nullable=True),
        sa.Column("optimistic_months", sa.Integer, nullable=True),
        sa.Column("realistic_months", sa.Integer, nullable=True),
        sa.Column("conservative_months", sa.Integer, nullable=True),
        sa.Column("salary_impact_percent", sa.Float, nullable=True),
        sa.Column(
            "success_probability",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("factors", JSON, nullable=True),
        sa.Column(
            "data_source",
            sa.String(100),
            nullable=False,
            server_default="ai_analysis",
        ),
        sa.Column("disclaimer", sa.Text, nullable=False),
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

    # 2. skill_bridge_entries
    op.create_table(
        "skill_bridge_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transition_path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transition_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column(
            "category",
            sa.String(100),
            nullable=False,
            server_default="technical",
        ),
        sa.Column(
            "is_already_held",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("current_level", sa.String(50), nullable=True),
        sa.Column("required_level", sa.String(50), nullable=True),
        sa.Column("acquisition_method", sa.String(255), nullable=True),
        sa.Column("estimated_weeks", sa.Integer, nullable=True),
        sa.Column("recommended_resources", JSON, nullable=True),
        sa.Column(
            "priority",
            sa.String(50),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("impact_on_confidence", sa.Float, nullable=True),
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

    # 3. transition_milestones
    op.create_table(
        "transition_milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transition_path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transition_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "phase",
            sa.String(50),
            nullable=False,
            server_default="preparation",
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "target_week", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column(
            "order_index", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "is_completed",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True
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

    # 4. transition_comparisons
    op.create_table(
        "transition_comparisons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transition_path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transition_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("dimension", sa.String(100), nullable=False),
        sa.Column(
            "source_value", sa.Float, nullable=False, server_default="0.0"
        ),
        sa.Column(
            "target_value", sa.Float, nullable=False, server_default="0.0"
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

    # 5. transition_preferences
    op.create_table(
        "transition_preferences",
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
        sa.Column("preferred_industries", JSON, nullable=True),
        sa.Column("excluded_roles", JSON, nullable=True),
        sa.Column(
            "min_confidence",
            sa.Float,
            nullable=False,
            server_default="0.3",
        ),
        sa.Column(
            "max_timeline_months",
            sa.Integer,
            nullable=False,
            server_default="36",
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
    """Drop all 5 Transition Pathways tables in reverse order."""
    op.drop_table("transition_preferences")
    op.drop_table("transition_comparisons")
    op.drop_table("transition_milestones")
    op.drop_table("skill_bridge_entries")
    op.drop_table("transition_paths")
