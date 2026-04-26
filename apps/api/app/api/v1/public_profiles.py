"""
PathForge — Public Profile API Routes
=========================================
Sprint 34: Public career profile endpoints.

6 endpoints: own, create, update, publish, unpublish, public view.
F6: X-Robots-Tag: noindex on public profile endpoint.
F29: OpenAPI tags.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.public_profile import (
    CreatePublicProfileRequest,
    PublicProfilePublicResponse,
    PublicProfileResponse,
    UpdatePublicProfileRequest,
)
from app.services.public_profile_service import PublicProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public-profiles", tags=["Public Profiles"])


# ── GET /public-profiles/me ────────────────────────────────────


@router.get(
    "/me",
    response_model=PublicProfileResponse | None,
    summary="Get own public profile",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=4)
async def get_own_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get the authenticated user's public profile."""
    profile = await PublicProfileService.get_own_profile(db, current_user)
    if profile is None:
        return JSONResponse(content=None, status_code=status.HTTP_200_OK)
    return profile


# ── POST /public-profiles ─────────────────────────────────────


@router.post(
    "",
    response_model=PublicProfileResponse,
    summary="Create public profile",
    status_code=status.HTTP_201_CREATED,
)
@route_query_budget(max_queries=4)
async def create_profile(
    body: CreatePublicProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a public career profile with a unique slug."""
    try:
        return await PublicProfileService.create_profile(
            db,
            current_user,
            slug=body.slug,
            headline=body.headline,
            bio=body.bio,
            skills_showcase=body.skills_showcase,
            social_links=body.social_links,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


# ── PATCH /public-profiles/me ──────────────────────────────────


@router.patch(
    "/me",
    response_model=PublicProfileResponse,
    summary="Update public profile",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=4)
async def update_profile(
    body: UpdatePublicProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update the authenticated user's public profile."""
    try:
        updates = body.model_dump(exclude_none=True)
        return await PublicProfileService.update_profile(db, current_user, updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── POST /public-profiles/me/publish ───────────────────────────


@router.post(
    "/me/publish",
    response_model=PublicProfileResponse,
    summary="Publish profile",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=4)
async def publish_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Make the user's profile publicly accessible."""
    try:
        return await PublicProfileService.publish(db, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── POST /public-profiles/me/unpublish ─────────────────────────


@router.post(
    "/me/unpublish",
    response_model=PublicProfileResponse,
    summary="Unpublish profile",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=4)
async def unpublish_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Remove the user's profile from public access."""
    try:
        return await PublicProfileService.unpublish(db, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── GET /public-profiles/{slug} ────────────────────────────────


@router.get(
    "/{slug}",
    response_model=PublicProfilePublicResponse,
    summary="View public profile",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_public_profile)
@route_query_budget(max_queries=4)
async def view_public_profile(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Public endpoint to view a published career profile.

    F6: Includes X-Robots-Tag: noindex to prevent search indexing.
    """
    profile = await PublicProfileService.get_public_profile(db, slug)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # F6: noindex header
    response = JSONResponse(
        content={
            "slug": profile.slug,
            "headline": profile.headline,
            "bio": profile.bio,
            "skills_showcase": profile.skills_showcase,
            "social_links": profile.social_links,
            "view_count": profile.view_count,
        }
    )
    response.headers["X-Robots-Tag"] = "noindex"
    return response
