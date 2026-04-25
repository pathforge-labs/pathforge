"""
PathForge — Admin Schemas
===========================
Sprint 34: DTOs for admin dashboard endpoints.
All response schemas include ConfigDict(from_attributes=True) per F20.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── User Management ────────────────────────────────────────────


class AdminUserSummary(BaseModel):
    """Condensed user record for admin listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class AdminUserDetailResponse(BaseModel):
    """Extended user detail for admin inspection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    auth_provider: str
    created_at: datetime
    subscription_tier: str | None = None
    subscription_status: str | None = None
    scans_used: int = 0


class AdminUserListResponse(BaseModel):
    """Paginated user list for admin dashboard."""

    users: list[AdminUserSummary]
    total: int
    page: int
    per_page: int


class AdminUserUpdateRequest(BaseModel):
    """Admin user update request."""

    is_active: bool | None = None
    is_verified: bool | None = None
    role: str | None = Field(default=None, pattern="^(user|admin)$")


# ── Subscription Override ──────────────────────────────────────


class AdminSubscriptionOverrideRequest(BaseModel):
    """Admin override of a user's subscription tier."""

    tier: str = Field(pattern="^(free|pro|premium)$")
    reason: str = Field(min_length=1, max_length=500)


# ── System Health ──────────────────────────────────────────────


class SystemHealthResponse(BaseModel):
    """System health overview for admin dashboard."""

    database: str
    redis: str
    stripe: str
    worker: str


# ── Dashboard Summary ─────────────────────────────────────────


class AdminDashboardSummaryResponse(BaseModel):
    """Aggregate statistics for admin dashboard."""

    total_users: int
    active_users: int
    tier_distribution: dict[str, int]
    total_scans_this_period: int
    waitlist_count: int


# ── Audit Log ──────────────────────────────────────────────────


class AdminAuditLogResponse(BaseModel):
    """Admin audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_user_id: uuid.UUID
    action: str
    target_user_id: uuid.UUID | None
    details: dict[str, str] | None
    ip_address: str | None
    created_at: datetime
