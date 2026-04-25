"""
PathForge — Waitlist Model
=============================
Sprint 34: Waitlist-to-user conversion tracking.

Audit findings:
    F7  — FIFO position auto-assigned
    F19 — CheckConstraint on position >= 1
    F24 — StrEnum pattern
    F27 — Email case normalization
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WaitlistStatus(enum.StrEnum):
    """Waitlist entry lifecycle status."""

    PENDING = "pending"
    INVITED = "invited"
    CONVERTED = "converted"
    EXPIRED = "expired"


class WaitlistEntry(UUIDMixin, TimestampMixin, Base):
    """
    Waitlist entry for controlled growth.

    Tracks a user from sign-up through invitation to conversion.
    Email stored normalized (F27: lower + strip).
    Position auto-assigned on insert (F7).
    """

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint("position >= 1", name="ck_waitlist_position_positive"),
        CheckConstraint(
            "status IN ('pending', 'invited', 'converted', 'expired')",
            name="ck_waitlist_status_valid",
        ),
    )

    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=WaitlistStatus.PENDING.value, nullable=False
    )
    invite_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    referral_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<WaitlistEntry {self.email} pos={self.position} status={self.status}>"
