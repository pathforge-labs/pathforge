"""
PathForge — Public Profile Service Unit Tests
==============================================
Service-layer tests for public_profile_service.py.

Covers:
    - create_profile (happy path, reserved slugs, duplicate profile, duplicate slug)
    - update_profile (happy path, missing profile, partial update, unknown field)
    - publish / unpublish
    - get_public_profile (published only, view counter increment, missing)
    - get_own_profile
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.public_profile import PublicCareerProfile
from app.models.user import User
from app.services.public_profile_service import (
    RESERVED_SLUGS,
    PublicProfileService,
)

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str = "pp_user@pathforge.eu") -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Public Profile Tester",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ── create_profile ────────────────────────────────────────────────


async def test_create_profile_success(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    profile = await PublicProfileService.create_profile(
        db=db_session,
        user=user,
        slug="john-doe",
        headline="Senior Engineer",
        bio="Ten years building distributed systems.",
        skills_showcase=["python", "sqlalchemy"],
        social_links={"github": "https://github.com/jd"},
    )
    assert profile.id is not None
    assert profile.user_id == user.id
    assert profile.slug == "john-doe"
    assert profile.headline == "Senior Engineer"
    assert profile.is_published is False  # F6: default unpublished
    assert profile.view_count == 0
    assert profile.skills_showcase == ["python", "sqlalchemy"]
    assert profile.social_links == {"github": "https://github.com/jd"}


async def test_create_profile_minimal_fields(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    profile = await PublicProfileService.create_profile(
        db=db_session,
        user=user,
        slug="minimal-slug",
    )
    assert profile.headline is None
    assert profile.bio is None
    assert profile.skills_showcase is None
    assert profile.social_links is None
    assert profile.is_published is False


@pytest.mark.parametrize(
    "reserved",
    ["admin", "api", "me", "login", "Dashboard", "PROFILE"],
)
async def test_create_profile_rejects_reserved_slug(
    db_session: AsyncSession, reserved: str,
) -> None:
    user = await _make_user(db_session, email=f"r_{reserved.lower()}@pathforge.eu")
    with pytest.raises(ValueError, match="reserved"):
        await PublicProfileService.create_profile(
            db=db_session, user=user, slug=reserved,
        )


async def test_create_profile_reserved_slugs_frozenset_contents() -> None:
    assert "admin" in RESERVED_SLUGS
    assert "dashboard" in RESERVED_SLUGS
    assert "profile" in RESERVED_SLUGS
    # Non-reserved sanity
    assert "john-doe" not in RESERVED_SLUGS


async def test_create_profile_duplicate_profile_for_same_user(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="first-slug",
    )
    with pytest.raises(ValueError, match="already have a public profile"):
        await PublicProfileService.create_profile(
            db=db_session, user=user, slug="second-slug",
        )


async def test_create_profile_duplicate_slug_different_user(
    db_session: AsyncSession,
) -> None:
    user_a = await _make_user(db_session, email="a@pathforge.eu")
    user_b = await _make_user(db_session, email="b@pathforge.eu")

    await PublicProfileService.create_profile(
        db=db_session, user=user_a, slug="shared-slug",
    )
    with pytest.raises(ValueError, match="already taken"):
        await PublicProfileService.create_profile(
            db=db_session, user=user_b, slug="shared-slug",
        )


# ── update_profile ────────────────────────────────────────────────


async def test_update_profile_success(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="upd-slug", headline="Old",
    )
    updated = await PublicProfileService.update_profile(
        db=db_session,
        user=user,
        updates={"headline": "New Headline", "bio": "Fresh bio"},
    )
    assert updated.headline == "New Headline"
    assert updated.bio == "Fresh bio"


async def test_update_profile_ignores_none_values(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="ignore-none", headline="Keep Me",
    )
    updated = await PublicProfileService.update_profile(
        db=db_session,
        user=user,
        updates={"headline": None, "bio": "Only bio changes"},
    )
    assert updated.headline == "Keep Me"
    assert updated.bio == "Only bio changes"


async def test_update_profile_ignores_unknown_fields(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="unknown-fields",
    )
    updated = await PublicProfileService.update_profile(
        db=db_session,
        user=user,
        updates={"nonexistent_field": "ignored", "headline": "H"},
    )
    assert updated.headline == "H"
    assert not hasattr(updated, "nonexistent_field") or getattr(
        updated, "nonexistent_field", None,
    ) != "ignored"


async def test_update_profile_missing_raises(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    with pytest.raises(ValueError, match="No public profile found"):
        await PublicProfileService.update_profile(
            db=db_session, user=user, updates={"headline": "x"},
        )


async def test_update_profile_updates_skills_and_links(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="skills-links",
    )
    updated = await PublicProfileService.update_profile(
        db=db_session,
        user=user,
        updates={
            "skills_showcase": ["rust", "go"],
            "social_links": {"linkedin": "https://linkedin.com/in/x"},
        },
    )
    assert updated.skills_showcase == ["rust", "go"]
    assert updated.social_links == {"linkedin": "https://linkedin.com/in/x"}


async def test_update_profile_empty_updates_is_noop(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="noop", headline="Same",
    )
    updated = await PublicProfileService.update_profile(
        db=db_session, user=user, updates={},
    )
    assert updated.headline == "Same"


# ── publish / unpublish ───────────────────────────────────────────


async def test_publish_profile_success(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="pub-slug",
    )
    published = await PublicProfileService.publish(db=db_session, user=user)
    assert published.is_published is True


async def test_publish_profile_missing_raises(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    with pytest.raises(ValueError, match="No public profile found"):
        await PublicProfileService.publish(db=db_session, user=user)


async def test_unpublish_profile_success(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="unpub-slug",
    )
    await PublicProfileService.publish(db=db_session, user=user)
    unpublished = await PublicProfileService.unpublish(db=db_session, user=user)
    assert unpublished.is_published is False


async def test_unpublish_profile_missing_raises(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    with pytest.raises(ValueError, match="No public profile found"):
        await PublicProfileService.unpublish(db=db_session, user=user)


async def test_publish_then_unpublish_round_trip(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="round-trip",
    )
    p1 = await PublicProfileService.publish(db=db_session, user=user)
    assert p1.is_published is True
    p2 = await PublicProfileService.unpublish(db=db_session, user=user)
    assert p2.is_published is False
    p3 = await PublicProfileService.publish(db=db_session, user=user)
    assert p3.is_published is True


# ── get_public_profile ────────────────────────────────────────────


async def test_get_public_profile_published_increments_view_count(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="public-view",
    )
    await PublicProfileService.publish(db=db_session, user=user)

    fetched = await PublicProfileService.get_public_profile(
        db=db_session, slug="public-view",
    )
    assert fetched is not None
    assert fetched.view_count == 1

    fetched2 = await PublicProfileService.get_public_profile(
        db=db_session, slug="public-view",
    )
    assert fetched2 is not None
    assert fetched2.view_count == 2


async def test_get_public_profile_unpublished_returns_none(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="draft-slug",
    )
    fetched = await PublicProfileService.get_public_profile(
        db=db_session, slug="draft-slug",
    )
    assert fetched is None


async def test_get_public_profile_nonexistent_slug_returns_none(
    db_session: AsyncSession,
) -> None:
    fetched = await PublicProfileService.get_public_profile(
        db=db_session, slug="does-not-exist",
    )
    assert fetched is None


async def test_get_public_profile_does_not_increment_when_missing(
    db_session: AsyncSession,
) -> None:
    # Create but leave unpublished — should NOT increment view_count
    user = await _make_user(db_session)
    profile = await PublicProfileService.create_profile(
        db=db_session, user=user, slug="no-inc",
    )
    assert profile.view_count == 0
    await PublicProfileService.get_public_profile(db=db_session, slug="no-inc")
    # Reload from DB
    refreshed = await db_session.get(PublicCareerProfile, profile.id)
    assert refreshed is not None
    assert refreshed.view_count == 0


# ── get_own_profile ───────────────────────────────────────────────


async def test_get_own_profile_returns_profile(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    created = await PublicProfileService.create_profile(
        db=db_session, user=user, slug="own-slug",
    )
    fetched = await PublicProfileService.get_own_profile(db=db_session, user=user)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.slug == "own-slug"


async def test_get_own_profile_returns_none_when_missing(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session)
    fetched = await PublicProfileService.get_own_profile(db=db_session, user=user)
    assert fetched is None


async def test_get_own_profile_unpublished_still_returned(
    db_session: AsyncSession,
) -> None:
    """Own profile lookup does not filter by is_published."""
    user = await _make_user(db_session)
    await PublicProfileService.create_profile(
        db=db_session, user=user, slug="own-draft",
    )
    fetched = await PublicProfileService.get_own_profile(db=db_session, user=user)
    assert fetched is not None
    assert fetched.is_published is False


async def test_get_own_profile_scoped_to_user(db_session: AsyncSession) -> None:
    user_a = await _make_user(db_session, email="scope_a@pathforge.eu")
    user_b = await _make_user(db_session, email="scope_b@pathforge.eu")
    await PublicProfileService.create_profile(
        db=db_session, user=user_a, slug="scope-a",
    )

    a_profile = await PublicProfileService.get_own_profile(db=db_session, user=user_a)
    b_profile = await PublicProfileService.get_own_profile(db=db_session, user=user_b)

    assert a_profile is not None
    assert a_profile.slug == "scope-a"
    assert b_profile is None
