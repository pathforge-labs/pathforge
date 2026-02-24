"""
PathForge — Notification Engine™ Schemas
=========================================
Pydantic request/response schemas for the Notification Engine API.

Response Schemas (5):
    CareerNotificationResponse        — Individual notification
    NotificationListResponse          — Paginated notification list
    NotificationCountResponse         — Unread count by severity
    NotificationPreferenceResponse    — User notification settings
    NotificationDigestResponse        — Digest summary

Request Schemas (3):
    NotificationMarkReadRequest       — Mark specific notifications read
    NotificationFilterParams          — Filter/pagination params
    NotificationPreferenceUpdate      — Update notification preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ───────────────────────────────────────────


class CareerNotificationResponse(BaseModel):
    """Individual career notification."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    source_engine: str
    notification_type: str
    severity: str
    title: str
    body: str
    action_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    metadata_: dict[str, object] | None = Field(None, alias="metadata")
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class NotificationListResponse(BaseModel):
    """Paginated notification list."""

    notifications: list[CareerNotificationResponse] = Field(
        default_factory=list,
    )
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False


class NotificationCountResponse(BaseModel):
    """Unread notification count breakdown."""

    total_unread: int = 0
    by_severity: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        },
    )
    by_engine: dict[str, int] = Field(default_factory=dict)


class NotificationPreferenceResponse(BaseModel):
    """User notification preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    enabled_engines: list[str] | None = None
    min_severity: str
    digest_enabled: bool
    digest_frequency: str
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    in_app_notifications: bool
    email_notifications: bool
    created_at: datetime
    updated_at: datetime


class NotificationDigestResponse(BaseModel):
    """Notification digest summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    digest_type: str
    period_start: datetime
    period_end: datetime
    notification_count: int
    summary: dict[str, object] | None = None
    created_at: datetime


class NotificationDigestListResponse(BaseModel):
    """Paginated list of digests."""

    digests: list[NotificationDigestResponse] = Field(
        default_factory=list,
    )
    total: int = 0
    page: int = 1
    page_size: int = 20


# ── Request Schemas ────────────────────────────────────────────


class NotificationMarkReadRequest(BaseModel):
    """Mark specific notifications as read."""

    notification_ids: list[uuid.UUID] = Field(
        ..., min_length=1, max_length=100,
        description="IDs of notifications to mark as read.",
    )


class NotificationFilterParams(BaseModel):
    """Filter and pagination parameters for notification list."""

    page: int = Field(1, ge=1, description="Page number.")
    page_size: int = Field(20, ge=1, le=100, description="Items per page.")
    source_engine: str | None = Field(
        None,
        description="Filter by source engine name.",
    )
    notification_type: str | None = Field(
        None,
        description="Filter by type: threat | opportunity | milestone | insight | action_required.",
    )
    severity: str | None = Field(
        None,
        description="Filter by severity: low | medium | high | critical.",
    )
    is_read: bool | None = Field(
        None,
        description="Filter by read state.",
    )


class NotificationPreferenceUpdate(BaseModel):
    """Update notification preferences."""

    enabled_engines: list[str] | None = Field(
        None, max_length=12,
        description="Engines to receive notifications from.",
    )
    min_severity: str | None = Field(
        None,
        description="Minimum severity: low | medium | high | critical.",
    )
    digest_enabled: bool | None = None
    digest_frequency: str | None = Field(
        None,
        description="Digest frequency: daily | weekly.",
    )
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    in_app_notifications: bool | None = None
    email_notifications: bool | None = None
