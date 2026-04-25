"""add interview intelligence tables

Revision ID: 3c4d5e6f7g8h
Revises: 2b3c4d5e6f7g
Create Date: 2026-02-21 16:25:00.000000+01:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "3c4d5e6f7g8h"
down_revision = "2b3c4d5e6f7g"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create 5 Interview Intelligence tables."""
    # 1. interview_preps (hub entity)
    op.create_table(
        "interview_preps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "career_dna_id",
            UUID(as_uuid=True),
            sa.ForeignKey("career_dna.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("target_role", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="completed",
            index=True,
        ),
        sa.Column(
            "prep_depth",
            sa.String(20),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("culture_alignment_score", sa.Float, nullable=True),
        sa.Column("interview_format", sa.Text, nullable=True),
        sa.Column("company_brief", sa.Text, nullable=True),
        sa.Column(
            "data_source",
            sa.String(200),
            nullable=False,
            server_default=(
                "AI-generated interview intelligence based on "
                "Career DNA and market data"
            ),
        ),
        sa.Column(
            "disclaimer",
            sa.String(500),
            nullable=False,
            server_default=(
                "This interview preparation is AI-generated intelligence, "
                "not a guarantee. Actual interview questions and company "
                "culture may differ from predictions. Maximum confidence: 85%."
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
            name="ck_interview_prep_confidence_cap",
        ),
    )

    # 2. company_insights
    op.create_table(
        "company_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "interview_prep_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interview_preps.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "insight_type",
            sa.String(30),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", JSON, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column(
            "confidence",
            sa.Float,
            nullable=False,
            server_default="0.5",
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

    # 3. interview_questions
    op.create_table(
        "interview_questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "interview_prep_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interview_preps.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "category",
            sa.String(30),
            nullable=False,
            index=True,
        ),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("suggested_answer", sa.Text, nullable=True),
        sa.Column("answer_strategy", sa.Text, nullable=True),
        sa.Column(
            "frequency_weight",
            sa.Float,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column("difficulty_level", sa.String(20), nullable=True),
        sa.Column(
            "order_index",
            sa.Integer,
            nullable=False,
            server_default="0",
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

    # 4. star_examples
    op.create_table(
        "star_examples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "interview_prep_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interview_preps.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "question_id",
            UUID(as_uuid=True),
            sa.ForeignKey("interview_questions.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("situation", sa.Text, nullable=False),
        sa.Column("task", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("result", sa.Text, nullable=False),
        sa.Column(
            "career_dna_dimension", sa.String(100), nullable=True
        ),
        sa.Column("source_experience", sa.Text, nullable=True),
        sa.Column(
            "relevance_score",
            sa.Float,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "order_index",
            sa.Integer,
            nullable=False,
            server_default="0",
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

    # 5. interview_preferences
    op.create_table(
        "interview_preferences",
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
        sa.Column("default_prep_depth", sa.String(30), nullable=True),
        sa.Column(
            "max_saved_preps",
            sa.Integer,
            nullable=False,
            server_default="50",
        ),
        sa.Column(
            "include_salary_negotiation",
            sa.Boolean,
            nullable=False,
            server_default="true",
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
    """Drop all 5 Interview Intelligence tables in reverse order."""
    op.drop_table("interview_preferences")
    op.drop_table("star_examples")
    op.drop_table("interview_questions")
    op.drop_table("company_insights")
    op.drop_table("interview_preps")
