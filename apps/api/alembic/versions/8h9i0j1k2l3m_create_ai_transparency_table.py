"""
Alembic migration — Add AI Transparency Records table
========================================================
Sprint 20 Enhancement R1: Persistence layer for AI Trust Layer™.
    - ai_transparency_records

Revision ID: 8h9i0j1k2l3m
Revises: 7g8h9i0j1k2l
Create Date: 2026-02-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8h9i0j1k2l3m"
down_revision: str | None = "7g8h9i0j1k2l"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create AI Transparency Records table."""
    op.create_table(
        "ai_transparency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.String(36), nullable=False, unique=True),
        sa.Column("analysis_type", sa.String(100), nullable=False),
        sa.Column(
            "model", sa.String(200), nullable=False,
            server_default="",
        ),
        sa.Column(
            "tier", sa.String(20), nullable=False,
            server_default="primary",
        ),
        sa.Column(
            "confidence_score", sa.Float(), nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "confidence_label", sa.String(20), nullable=False,
            server_default="Low",
        ),
        sa.Column(
            "data_sources", sa.JSON(), nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "prompt_tokens", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "latency_ms", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column(
            "success", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "retries", sa.Integer(), nullable=False,
            server_default="0",
        ),
        sa.Column("reasoning", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "confidence_score <= 0.95",
            name="ck_ai_transparency_confidence_cap",
        ),
    )
    # Primary lookup indexes
    op.create_index(
        "ix_ai_transparency_records_user_id",
        "ai_transparency_records",
        ["user_id"],
    )
    op.create_index(
        "ix_ai_transparency_records_analysis_id",
        "ai_transparency_records",
        ["analysis_id"],
        unique=True,
    )
    # Compound index for filtered queries
    op.create_index(
        "ix_ai_transparency_user_type",
        "ai_transparency_records",
        ["user_id", "analysis_type"],
    )
    op.create_index(
        "ix_ai_transparency_created_at",
        "ai_transparency_records",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop AI Transparency Records table."""
    op.drop_table("ai_transparency_records")
