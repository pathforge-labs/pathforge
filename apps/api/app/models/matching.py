"""
PathForge — JobListing & MatchResult Models
=============================================
Aggregated job postings (via API) and semantic match results.
"""

from __future__ import annotations

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import EMBEDDING_DIM
from app.models.base import Base, TimestampMixin, UUIDMixin


class JobListing(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "job_listings"

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    salary_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True,
        comment="SHA256 of normalized(title+company+location) for dedup",
    )
    structured_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    # Relationships
    match_results: Mapped[list[MatchResult]] = relationship(
        "MatchResult", back_populates="job_listing", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JobListing {self.title} @ {self.company}>"


class MatchResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "match_results"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensional_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    job_listing: Mapped[JobListing] = relationship("JobListing", back_populates="match_results")

    def __repr__(self) -> str:
        return f"<MatchResult score={self.overall_score:.2f}>"
