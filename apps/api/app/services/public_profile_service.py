"""
PathForge — Public Profile Service
======================================
Sprint 34: Public career profile business logic.

Audit findings:
    F6  — X-Robots-Tag: noindex on public profiles
    F26 — Slug reserved words validation
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_profile import PublicCareerProfile
from app.models.user import User

logger = logging.getLogger(__name__)

# F26: Reserved slug words (match existing route prefixes)
RESERVED_SLUGS: frozenset[str] = frozenset({
    "admin", "api", "me", "health", "login", "register",
    "settings", "billing", "waitlist", "auth", "users",
    "docs", "redoc", "openapi", "static", "assets",
    "dashboard", "profile", "account", "webhook", "webhooks",
})


class PublicProfileService:
    """Encapsulates public career profile logic."""

    @staticmethod
    async def create_profile(
        db: AsyncSession,
        user: User,
        slug: str,
        headline: str | None = None,
        bio: str | None = None,
        skills_showcase: list[str] | None = None,
        social_links: dict[str, str] | None = None,
    ) -> PublicCareerProfile:
        """Create a public career profile for a user.

        F26: Rejects reserved slug words.
        """
        # F26: Reserved words check
        if slug.lower() in RESERVED_SLUGS:
            raise ValueError(
                f"Slug '{slug}' is reserved. Please choose a different slug."
            )

        # Check for existing profile
        existing = await db.execute(
            select(PublicCareerProfile).where(
                PublicCareerProfile.user_id == user.id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("You already have a public profile")

        # Check slug uniqueness
        slug_check = await db.execute(
            select(PublicCareerProfile).where(PublicCareerProfile.slug == slug)
        )
        if slug_check.scalar_one_or_none() is not None:
            raise ValueError(f"Slug '{slug}' is already taken")

        profile = PublicCareerProfile(
            user_id=user.id,
            slug=slug,
            headline=headline,
            bio=bio,
            is_published=False,  # F6: default unpublished
            skills_showcase=skills_showcase,
            social_links=social_links,
        )
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user: User,
        updates: dict[str, Any],
    ) -> PublicCareerProfile:
        """Update the authenticated user's public profile."""
        result = await db.execute(
            select(PublicCareerProfile).where(
                PublicCareerProfile.user_id == user.id
            )
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            raise ValueError("No public profile found")

        for field, value in updates.items():
            if value is not None and hasattr(profile, field):
                setattr(profile, field, value)

        await db.flush()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def publish(
        db: AsyncSession,
        user: User,
    ) -> PublicCareerProfile:
        """Publish the user's public profile."""
        result = await db.execute(
            select(PublicCareerProfile).where(
                PublicCareerProfile.user_id == user.id
            )
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            raise ValueError("No public profile found")

        profile.is_published = True
        await db.flush()
        await db.refresh(profile)
        logger.info("Profile published: slug=%s user=%s", profile.slug, user.id)
        return profile

    @staticmethod
    async def unpublish(
        db: AsyncSession,
        user: User,
    ) -> PublicCareerProfile:
        """Unpublish the user's public profile."""
        result = await db.execute(
            select(PublicCareerProfile).where(
                PublicCareerProfile.user_id == user.id
            )
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            raise ValueError("No public profile found")

        profile.is_published = False
        await db.flush()
        await db.refresh(profile)
        logger.info("Profile unpublished: slug=%s user=%s", profile.slug, user.id)
        return profile

    @staticmethod
    async def get_public_profile(
        db: AsyncSession,
        slug: str,
    ) -> PublicCareerProfile | None:
        """Get a published public profile by slug (public access)."""
        result = await db.execute(
            select(PublicCareerProfile).where(
                PublicCareerProfile.slug == slug,
                PublicCareerProfile.is_published.is_(True),
            )
        )
        profile = result.scalar_one_or_none()

        if profile is not None:
            # Increment view count
            profile.view_count += 1
            await db.flush()

        return profile

    @staticmethod
    async def get_own_profile(
        db: AsyncSession,
        user: User,
    ) -> PublicCareerProfile | None:
        """Get the authenticated user's own public profile."""
        result = await db.execute(
            select(PublicCareerProfile).where(
                PublicCareerProfile.user_id == user.id
            )
        )
        return result.scalar_one_or_none()
