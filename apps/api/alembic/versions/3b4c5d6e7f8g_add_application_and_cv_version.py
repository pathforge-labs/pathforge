"""
Add Application and CVVersion tables

Revision ID: 3b4c5d6e7f8g
Revises: 2a3b4c5d6e7f
Create Date: 2026-02-13
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers
revision = "3b4c5d6e7f8g"
down_revision = "2a3b4c5d6e7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- cv_versions table (must exist before applications references it) --
    op.create_table(
        "cv_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("resume_id", UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_listing_id", UUID(as_uuid=True), sa.ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tailored_content", JSON, nullable=True),
        sa.Column("diff_from_base", JSON, nullable=True),
        sa.Column("ats_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generation_log", JSON, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cv_versions_resume_id", "cv_versions", ["resume_id"])
    op.create_index("ix_cv_versions_job_listing_id", "cv_versions", ["job_listing_id"])

    # -- applications table --
    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_listing_id", UUID(as_uuid=True), sa.ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cv_version_id", UUID(as_uuid=True), sa.ForeignKey("cv_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="saved"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "job_listing_id", name="uq_user_job_application"),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])
    op.create_index("ix_applications_job_listing_id", "applications", ["job_listing_id"])
    op.create_index("ix_applications_status", "applications", ["status"])


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("cv_versions")
