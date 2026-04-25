"""
PathForge — User Profile & GDPR Data Export Models
====================================================
Domain models for centralized user profile management and
GDPR Article 20+ compliant data export with AI methodology
disclosure, data provenance, and manifest integrity checks.

Models:
    UserProfile         — Extended user profile (supplements User)
    DataExportRequest   — GDPR export request audit trail

Enums:
    ExportType   — full | career_dna_only | intelligence_only
    ExportFormat — json (extensible for csv in Sprint 23)
    ExportStatus — pending | processing | completed | failed | expired

Proprietary Innovations:
    🔥 GDPR Article 20+ — Beyond-compliance export with AI transparency
    🔥 Manifest Integrity — SHA-256 checksums + record counts
    🔥 7-Day Secure Expiry — Auto-expire with download audit trail
"""

from __future__ import annotations

import datetime
import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class ExportType(enum.StrEnum):
    """Type of GDPR data export request."""

    FULL = "full"                          # All user data + AI analyses
    CAREER_DNA_ONLY = "career_dna_only"    # Career DNA + skill genome
    INTELLIGENCE_ONLY = "intelligence_only"  # AI engine results only


class ExportFormat(enum.StrEnum):
    """Export file format (extensible)."""

    JSON = "json"    # Sprint 22: JSON only (GDPR Article 20 standard)


class ExportStatus(enum.StrEnum):
    """Export request lifecycle status."""

    PENDING = "pending"          # Request created
    PROCESSING = "processing"    # Export generation in progress
    COMPLETED = "completed"      # Ready for download
    FAILED = "failed"            # Generation error
    EXPIRED = "expired"          # Past 7-day download window


# ── UserProfile ────────────────────────────────────────────────


class UserProfile(Base, UUIDMixin, TimestampMixin):
    """User Profile — Extended Profile Data.

    Supplements the core User model with optional profile
    information used across the platform: display preferences,
    location, timezone, and onboarding state.

    One-to-one relationship with User (unique constraint on user_id).
    """

    __tablename__ = "user_profiles"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Profile fields ──
    display_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    headline: Mapped[str | None] = mapped_column(
        String(300), nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    location: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    timezone: Mapped[str] = mapped_column(
        String(50), default="UTC", server_default="UTC", nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(10), default="en", server_default="en", nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )

    # ── Onboarding ──
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )

    # ── Preferences (JSON) ──
    preferences: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<UserProfile(user_id={self.user_id}, "
            f"display_name={self.display_name}, "
            f"onboarding={self.onboarding_completed})>"
        )


# ── DataExportRequest ──────────────────────────────────────────


class DataExportRequest(Base, UUIDMixin, TimestampMixin):
    """GDPR Article 20+ — Data Export Request Audit Trail.

    Tracks the full lifecycle of data portability requests:
    pending → processing → completed → (expired after 7 days).

    Beyond GDPR minimum:
    - AI methodology disclosure in export payload
    - Data provenance per record (source engine, version, timestamp)
    - SHA-256 checksum for integrity validation
    - JSON manifest with category counts
    - Auto-expiry with download audit trail
    """

    __tablename__ = "user_data_export_requests"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Export configuration ──
    export_type: Mapped[str] = mapped_column(
        String(30), default=ExportType.FULL.value,
        server_default="full", nullable=False,
    )
    format_: Mapped[str] = mapped_column(
        "format", String(10), default=ExportFormat.JSON.value,
        server_default="json", nullable=False,
    )

    # ── Status tracking ──
    status: Mapped[str] = mapped_column(
        String(20), default=ExportStatus.PENDING.value,
        server_default="pending", nullable=False, index=True,
    )

    # ── File metadata ──
    file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    checksum: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )

    # ── Export metadata ──
    record_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    categories: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Expiry ──
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Completion tracking ──
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Download tracking ──
    download_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False,
    )
    last_downloaded_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<DataExportRequest(user_id={self.user_id}, "
            f"type={self.export_type}, status={self.status})>"
        )
