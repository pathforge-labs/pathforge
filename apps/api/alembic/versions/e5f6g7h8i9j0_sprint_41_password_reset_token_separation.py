"""Sprint 41 — Token separation, global invalidation + audit log FK fix

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-19

Changes:
- Add password_reset_token (String 128, nullable, indexed) to users
- Add password_reset_sent_at (DateTime with timezone, nullable) to users
- Add tokens_invalidated_at (DateTime with timezone, nullable) to users
  (global session invalidation after password reset / security events)
- Change admin_audit_logs.admin_user_id FK from CASCADE to SET NULL
  (audit records must survive user deletion for GDPR compliance)

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
    op.create_index("ix_users_password_reset_token", "users", ["password_reset_token"])
    op.add_column(
        "users",
        sa.Column(
            "password_reset_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "tokens_invalidated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Fix: audit records must survive user deletion (GDPR compliance)
    op.drop_constraint(
        "admin_audit_logs_admin_user_id_fkey",
        "admin_audit_logs",
        type_="foreignkey",
    )
    op.alter_column(
        "admin_audit_logs",
        "admin_user_id",
        nullable=True,
    )
    op.create_foreign_key(
        "admin_audit_logs_admin_user_id_fkey",
        "admin_audit_logs",
        "users",
        ["admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Restore CASCADE FK
    op.drop_constraint(
        "admin_audit_logs_admin_user_id_fkey",
        "admin_audit_logs",
        type_="foreignkey",
    )
    op.execute(
        "UPDATE admin_audit_logs SET admin_user_id = target_user_id "
        "WHERE admin_user_id IS NULL AND target_user_id IS NOT NULL"
    )
    op.alter_column(
        "admin_audit_logs",
        "admin_user_id",
        nullable=False,
    )
    op.create_foreign_key(
        "admin_audit_logs_admin_user_id_fkey",
        "admin_audit_logs",
        "users",
        ["admin_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("users", "tokens_invalidated_at")
    op.drop_column("users", "password_reset_sent_at")
    op.drop_index("ix_users_password_reset_token", "users")
    op.drop_column("users", "password_reset_token")
