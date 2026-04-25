"""
PathForge — Public Career Profile Model
==========================================
Sprint 34: Opt-in public career profiles with slug-based access.

Audit findings:
    F6  — Default unpublished, noindex
    F19 — CheckConstraint on view_count >= 0
    F26 — Reserved slug validation (in service, not model)
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PublicCareerProfile(UUIDMixin, TimestampMixin, Base):
    """
    Opt-in public career profile.

    Unpublished by default (F6). Accessible via unique slug when published.
    View counter tracks anonymized profile visits.
    """

    __tablename__ = "public_career_profiles"
    __table_args__ = (
        CheckConstraint("view_count >= 0", name="ck_public_profile_view_count_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    view_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    skills_showcase: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    social_links: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<PublicCareerProfile slug={self.slug} published={self.is_published}>"
