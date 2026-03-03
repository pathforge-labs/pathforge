"""
Sprint 36 WS-6: Add target_role to growth_vectors + user_activity_logs table
============================================================================
Add user-editable target role column to growth_vectors.
Create user_activity_logs table for tracking user-initiated actions.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "c3d4e5f6g7h8"
down_revision: str | None = "b2c3d4e5f6g7"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add target_role column and user_activity_logs table."""
    # 1. Add target_role column to growth_vectors
    op.add_column(
        "growth_vectors",
        sa.Column("target_role", sa.String(255), nullable=True),
    )

    # 2. Create user_activity_logs table
    op.create_table(
        "user_activity_logs",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 3. Index for efficient activity lookups
    op.create_index(
        "ix_user_activity_logs_action",
        "user_activity_logs",
        ["action"],
    )


def downgrade() -> None:
    """Remove target_role column and user_activity_logs table."""
    op.drop_index("ix_user_activity_logs_action", table_name="user_activity_logs")
    op.drop_table("user_activity_logs")
    op.drop_column("growth_vectors", "target_role")
