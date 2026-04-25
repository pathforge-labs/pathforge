"""
PathForge — Waitlist Schemas
===============================
Sprint 34: DTOs for waitlist endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WaitlistJoinRequest(BaseModel):
    """Public waitlist sign-up request."""

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    referral_source: str | None = Field(default=None, max_length=100)


class WaitlistPositionResponse(BaseModel):
    """Waitlist position confirmation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    position: int
    status: str
    created_at: datetime


class WaitlistStatsResponse(BaseModel):
    """Admin waitlist statistics."""

    total: int
    pending: int
    invited: int
    converted: int
    expired: int


class WaitlistEntryResponse(BaseModel):
    """Full waitlist entry for admin listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    position: int
    status: str
    invite_token: str | None
    referral_source: str | None
    converted_user_id: uuid.UUID | None
    created_at: datetime


class WaitlistInviteRequest(BaseModel):
    """Admin invite batch request."""

    count: int = Field(ge=1, le=100, description="Number of entries to invite")
