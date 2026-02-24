"""
PathForge — User Profile & GDPR Data Export Schemas
=====================================================
Pydantic request/response schemas for User Profile and GDPR export API.

Response Schemas (6):
    UserProfileResponse               — User profile data
    DataExportRequestResponse         — Export request status
    DataExportListResponse            — Paginated export list
    OnboardingStatusResponse          — Onboarding completion check
    UserDataSummaryResponse           — Record count per engine
    ExportDownloadResponse            — Download metadata

Request Schemas (3):
    UserProfileUpdate                 — Update profile fields
    UserProfileCreateRequest          — Initial profile creation
    DataExportRequestCreate           — Request a new GDPR export
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class UserProfileResponse(BaseModel):
    """User profile data."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str | None = None
    headline: str | None = None
    bio: str | None = None
    location: str | None = None
    timezone: str
    language: str
    avatar_url: str | None = None
    onboarding_completed: bool
    preferences: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class DataExportRequestResponse(BaseModel):
    """GDPR export request status and metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    export_type: str
    format_: str = Field(..., alias="format")
    status: str
    file_size_bytes: int | None = None
    checksum: str | None = None
    record_count: int | None = None
    categories: dict[str, object] | None = None
    expires_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    download_count: int = 0
    last_downloaded_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class DataExportListResponse(BaseModel):
    """Paginated list of export requests."""

    exports: list[DataExportRequestResponse] = Field(
        default_factory=list,
    )
    total: int = 0
    page: int = 1
    page_size: int = 20


class OnboardingStatusResponse(BaseModel):
    """User onboarding completion status."""

    onboarding_completed: bool = False
    profile_exists: bool = False
    career_dna_exists: bool = False
    engines_activated: int = 0
    total_engines: int = 12


class UserDataSummaryResponse(BaseModel):
    """Record count per engine — data summary for GDPR awareness."""

    total_records: int = 0
    engines: dict[str, int] = Field(
        default_factory=dict,
        description="Record count per engine name.",
    )
    profile_data: bool = False
    notification_count: int = 0
    export_count: int = 0


class ExportDownloadResponse(BaseModel):
    """Export download metadata."""

    export_id: uuid.UUID
    filename: str
    file_size_bytes: int
    checksum: str
    content_type: str = "application/json"
    expires_at: datetime


# ── Request Schemas ────────────────────────────────────────────


class UserProfileCreateRequest(BaseModel):
    """Create initial user profile."""

    display_name: str | None = Field(
        None, max_length=200,
        description="Display name.",
    )
    headline: str | None = Field(
        None, max_length=300,
        description="Professional headline.",
    )
    bio: str | None = Field(
        None, max_length=2000,
        description="Bio (max 2000 characters).",
    )
    location: str | None = Field(
        None, max_length=200,
        description="Location (city, country).",
    )
    timezone: str = Field(
        "UTC", max_length=50,
        description="IANA timezone (e.g., Europe/Amsterdam).",
    )
    language: str = Field(
        "en", max_length=10,
        description="Preferred language code (e.g., en, nl).",
    )


class UserProfileUpdate(BaseModel):
    """Update user profile fields."""

    display_name: str | None = Field(
        None, max_length=200,
        description="Display name.",
    )
    headline: str | None = Field(
        None, max_length=300,
        description="Professional headline.",
    )
    bio: str | None = Field(
        None, max_length=2000,
        description="Bio (max 2000 characters).",
    )
    location: str | None = Field(
        None, max_length=200,
        description="Location (city, country).",
    )
    timezone: str | None = Field(
        None, max_length=50,
        description="IANA timezone.",
    )
    language: str | None = Field(
        None, max_length=10,
        description="Preferred language code.",
    )
    avatar_url: str | None = Field(
        None, max_length=500,
        description="Avatar image URL.",
    )


class DataExportRequestCreate(BaseModel):
    """Request a new GDPR data export."""

    export_type: str = Field(
        "full",
        description="Export scope: full | career_dna_only | intelligence_only.",
    )
    format_: str = Field(
        "json", alias="format",
        description="Export format: json.",
    )

    model_config = ConfigDict(populate_by_name=True)
