"""Sprint 41 — Separate password reset token from email verification

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-19

Changes:
- Add password_reset_token (String 128, nullable) to users
- Add password_reset_sent_at (DateTime with timezone, nullable) to users

Previously, both email verification and password reset shared the
verification_token column. Requesting one flow overwrote the other's
token (P2 — token collision fix). This migration separates them into
independent columns.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5f6g7h8i9j0"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_reset_token", sa.String(128), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_reset_sent_at")
    op.drop_column("users", "password_reset_token")
