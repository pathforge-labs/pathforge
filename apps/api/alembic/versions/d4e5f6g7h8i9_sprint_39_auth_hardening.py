"""Sprint 39 — Auth hardening

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-09

Changes:
- Add verification_token (String 128, nullable) to users
- Add verification_sent_at (DateTime with timezone, nullable) to users
- Alter hashed_password from NOT NULL to nullable (F4: OAuth support)
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6g7h8i9"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email verification columns
    op.add_column(
        "users",
        sa.Column("verification_token", sa.String(128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "verification_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # F4: Allow hashed_password to be NULL for OAuth users
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(128),
        nullable=True,
    )


def downgrade() -> None:
    # Restore hashed_password NOT NULL (set empty string for any NULL values first)
    op.execute("UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL")
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(128),
        nullable=False,
    )
    op.drop_column("users", "verification_sent_at")
    op.drop_column("users", "verification_token")
