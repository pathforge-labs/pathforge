"""
PathForge — Public Profile Schemas
======================================
Sprint 34: DTOs for public career profile endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePublicProfileRequest(BaseModel):
    """Create a public career profile."""

    slug: str = Field(min_length=3, max_length=100, pattern="^[a-z0-9-]+$")
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    skills_showcase: list[str] | None = None
    social_links: dict[str, str] | None = None


class UpdatePublicProfileRequest(BaseModel):
    """Update a public career profile."""

    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    skills_showcase: list[str] | None = None
    social_links: dict[str, str] | None = None


class PublicProfileResponse(BaseModel):
    """Full profile response for owner."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    slug: str
    headline: str | None
    bio: str | None
    is_published: bool
    view_count: int
    skills_showcase: list[str] | None
    social_links: dict[str, str] | None
    created_at: datetime


class PublicProfilePublicResponse(BaseModel):
    """Public-facing profile (no user_id or internal fields)."""

    slug: str
    headline: str | None
    bio: str | None
    skills_showcase: list[str] | None
    social_links: dict[str, str] | None
    view_count: int
