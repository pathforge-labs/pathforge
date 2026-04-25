"""add job fingerprint and external_id

Revision ID: 2a3b4c5d6e7f
Revises: 120561739a8a
Create Date: 2026-02-13 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a3b4c5d6e7f"
down_revision: str | None = "120561739a8a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add fingerprint column with unique constraint for deduplication
    op.add_column(
        "job_listings",
        sa.Column(
            "fingerprint",
            sa.String(64),
            nullable=True,
            unique=True,
            comment="SHA256 of normalized(title+company+location) for dedup",
        ),
    )
    op.create_index("ix_job_listings_fingerprint", "job_listings", ["fingerprint"])

    # Add external_id for source-specific job identifiers
    op.add_column(
        "job_listings",
        sa.Column("external_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_job_listings_external_id", "job_listings", ["external_id"])

    # Drop unique constraint on source_url (dedup is now via fingerprint)
    op.drop_constraint("job_listings_source_url_key", "job_listings", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("job_listings_source_url_key", "job_listings", ["source_url"])
    op.drop_index("ix_job_listings_external_id", table_name="job_listings")
    op.drop_column("job_listings", "external_id")
    op.drop_index("ix_job_listings_fingerprint", table_name="job_listings")
    op.drop_column("job_listings", "fingerprint")
