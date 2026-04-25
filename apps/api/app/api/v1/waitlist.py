"""
PathForge — Waitlist API Routes
==================================
Sprint 34: Waitlist management endpoints.

5 endpoints: join, position, stats, list, invite.
OpenAPI tags (F29).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.waitlist import (
    WaitlistEntryResponse,
    WaitlistInviteRequest,
    WaitlistJoinRequest,
    WaitlistPositionResponse,
    WaitlistStatsResponse,
)
from app.services.waitlist_service import WaitlistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


# ── POST /waitlist/join ────────────────────────────────────────


@router.post(
    "/join",
    response_model=WaitlistPositionResponse,
    summary="Join the waitlist",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_waitlist)
async def join_waitlist(
    request: Request,
    body: WaitlistJoinRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Public endpoint to join the PathForge waitlist."""
    entry = await WaitlistService.join_waitlist(
        db,
        email=body.email,
        full_name=body.full_name,
        referral_source=body.referral_source,
    )
    return entry


# ── GET /waitlist/position ─────────────────────────────────────


@router.get(
    "/position",
    response_model=WaitlistPositionResponse,
    summary="Check waitlist position",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_waitlist)
async def check_position(
    request: Request,
    email: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Check waitlist position by email."""
    entry = await WaitlistService.get_position(db, email)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found on waitlist",
        )
    return entry


# ── GET /waitlist/stats (Admin) ────────────────────────────────


@router.get(
    "/stats",
    response_model=WaitlistStatsResponse,
    summary="Waitlist statistics",
    status_code=status.HTTP_200_OK,
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
) -> Any:
    """Aggregate waitlist statistics. Admin only."""
    from app.api.v1.admin import require_admin as _check_admin
    await _check_admin(admin)
    return await WaitlistService.get_stats(db)


# ── GET /waitlist/entries (Admin) ──────────────────────────────


@router.get(
    "/entries",
    response_model=list[WaitlistEntryResponse],
    summary="List waitlist entries",
    status_code=status.HTTP_200_OK,
)
async def list_entries(
    page: int = 1,
    per_page: int = 20,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
) -> Any:
    """Paginated waitlist listing. Admin only."""
    from app.api.v1.admin import require_admin as _check_admin
    await _check_admin(admin)
    return await WaitlistService.list_entries(db, page, per_page, status_filter)


# ── POST /waitlist/invite (Admin) ──────────────────────────────


@router.post(
    "/invite",
    response_model=list[WaitlistEntryResponse],
    summary="Invite waitlist batch",
    status_code=status.HTTP_200_OK,
)
async def invite_batch(
    body: WaitlistInviteRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
) -> Any:
    """Invite the next N pending entries. Admin only."""
    from app.api.v1.admin import require_admin as _check_admin
    await _check_admin(admin)
    return await WaitlistService.invite_batch(db, body.count)
