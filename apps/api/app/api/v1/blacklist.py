"""
PathForge API — Blacklist Routes
==================================
CRUD endpoints for company exclusion list (current employer protection).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.security import get_current_user
from app.models.preference import BlacklistEntry
from app.models.user import User

router = APIRouter(prefix="/blacklist", tags=["Blacklist"])


# ── Schemas ────────────────────────────────────────────────────


class AddBlacklistRequest(BaseModel):
    """Add a company to blacklist."""

    company_name: str = Field(..., min_length=1, max_length=255)
    reason: str | None = Field(None, max_length=1000)
    is_current_employer: bool = False


class BlacklistResponse(BaseModel):
    """Blacklist entry response."""

    id: str
    company_name: str
    reason: str | None = None
    is_current_employer: bool = False
    created_at: str


class BlacklistListResponse(BaseModel):
    """List of blacklisted companies."""

    items: list[BlacklistResponse]
    total: int


# ── Endpoints ──────────────────────────────────────────────────


@router.post("", response_model=BlacklistResponse, status_code=201)
@route_query_budget(max_queries=9)
async def add_to_blacklist(
    payload: AddBlacklistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlacklistResponse:
    """
    Add a company to the user's blacklist.

    Once blacklisted, applications to this company are blocked.
    Mark `is_current_employer=true` for current employer protection.
    """
    # Check for existing entry (case-insensitive)
    result = await db.execute(
        select(BlacklistEntry).where(
            BlacklistEntry.user_id == current_user.id,
            func.lower(BlacklistEntry.company_name) == payload.company_name.strip().lower(),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{payload.company_name}' is already on your blacklist",
        )

    entry = BlacklistEntry(
        user_id=current_user.id,
        company_name=payload.company_name.strip(),
        reason=payload.reason,
        is_current_employer=payload.is_current_employer,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return BlacklistResponse(
        id=str(entry.id),
        company_name=entry.company_name,
        reason=entry.reason,
        is_current_employer=entry.is_current_employer,
        created_at=entry.created_at.isoformat(),
    )


@router.get("", response_model=BlacklistListResponse)
@route_query_budget(max_queries=5)
async def list_blacklist(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlacklistListResponse:
    """List all companies on the user's blacklist with pagination."""
    base = select(BlacklistEntry).where(BlacklistEntry.user_id == current_user.id)

    # Count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = await db.scalar(count_stmt) or 0

    # Fetch
    result = await db.execute(
        base.order_by(BlacklistEntry.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    entries = list(result.scalars().all())

    return BlacklistListResponse(
        items=[
            BlacklistResponse(
                id=str(e.id),
                company_name=e.company_name,
                reason=e.reason,
                is_current_employer=e.is_current_employer,
                created_at=e.created_at.isoformat(),
            )
            for e in entries
        ],
        total=total,
    )


@router.delete("/{entry_id}", status_code=204)
@route_query_budget(max_queries=6)
async def remove_from_blacklist(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a company from the user's blacklist."""
    result = await db.execute(
        select(BlacklistEntry).where(
            BlacklistEntry.id == entry_id,
            BlacklistEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found"
        )

    await db.delete(entry)
    await db.commit()
