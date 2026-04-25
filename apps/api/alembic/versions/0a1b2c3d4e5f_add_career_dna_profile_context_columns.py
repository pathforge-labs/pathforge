"""add career_dna profile context columns

Revision ID: 0a1b2c3d4e5f
Revises: 9j0k1l2m3n4o
Create Date: 2026-02-20 04:20:00.000000+01:00
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "0a1b2c3d4e5f"
down_revision = "9j0k1l2m3n4o"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add profile context columns to career_dna table."""
    op.add_column(
        "career_dna",
        sa.Column("primary_industry", sa.String(255), nullable=True),
    )
    op.add_column(
        "career_dna",
        sa.Column("primary_role", sa.String(255), nullable=True),
    )
    op.add_column(
        "career_dna",
        sa.Column("location", sa.String(255), nullable=True),
    )
    op.add_column(
        "career_dna",
        sa.Column("seniority_level", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove profile context columns from career_dna table."""
    op.drop_column("career_dna", "seniority_level")
    op.drop_column("career_dna", "location")
    op.drop_column("career_dna", "primary_role")
    op.drop_column("career_dna", "primary_industry")
