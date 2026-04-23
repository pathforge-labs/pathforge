"""
PathForge API — Application Routes
=====================================
CRUD endpoints for application tracking with safety controls.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.application import Application, ApplicationStatus
from app.models.user import User
from app.services.application_service import (
    ApplicationError,
    BlacklistViolation,
    InvalidTransition,
    RateLimitViolation,
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_status,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


# ── Schemas ────────────────────────────────────────────────────


class CreateApplicationRequest(BaseModel):
    """Create a new application."""

    job_listing_id: uuid.UUID = Field(..., description="UUID of the job listing")
    status: str = Field(
        default=ApplicationStatus.SAVED,
        description="Initial status (saved or applied)",
    )
    notes: str | None = Field(None, max_length=2000)


class UpdateStatusRequest(BaseModel):
    """Update application status."""

    status: str = Field(..., description="New status")


class ApplicationResponse(BaseModel):
    """Application response."""

    id: str
    job_listing_id: str
    status: str
    notes: str | None = None
    source_url: str | None = None
    created_at: str
    updated_at: str
    job_title: str | None = None
    job_company: str | None = None


class ApplicationListResponse(BaseModel):
    """Paginated list of applications."""

    items: list[ApplicationResponse]
    total: int
    page: int
    per_page: int


# ── Helpers ────────────────────────────────────────────────────


def _to_response(app: Application) -> ApplicationResponse:
    """Convert Application ORM object to response schema."""
    job = getattr(app, "job_listing", None)
    return ApplicationResponse(
        id=str(app.id),
        job_listing_id=str(app.job_listing_id),
        status=app.status,
        notes=app.notes,
        source_url=app.source_url,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
        job_title=job.title if job else None,
        job_company=job.company if job else None,
    )


def _handle_service_error(exc: ApplicationError) -> HTTPException:
    """Map service exceptions to HTTP status codes."""
    status_map = {
        "BLACKLIST_VIOLATION": 403,
        "RATE_LIMIT_EXCEEDED": 429,
        "INVALID_TRANSITION": 422,
        "NOT_FOUND": 404,
    }
    return HTTPException(
        status_code=status_map.get(exc.code, 400),
        detail=exc.message,
    )


# ── Endpoints ──────────────────────────────────────────────────


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_app_endpoint(
    payload: CreateApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """
    Create a new application for a job listing.

    Enforces blacklist and rate limits. Returns 403 if company is
    blacklisted, 429 if rate limit exceeded.
    """
    try:
        app = await create_application(
            db,
            user_id=current_user.id,
            job_listing_id=payload.job_listing_id,
            status=payload.status,
            notes=payload.notes,
        )
        await db.commit()
        # Re-fetch to load relationships
        refetched = await get_application(db, app.id, current_user.id)
        if refetched is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found after creation")
        return _to_response(refetched)
    except (BlacklistViolation, RateLimitViolation, InvalidTransition, ApplicationError) as exc:
        await db.rollback()
        raise _handle_service_error(exc) from exc


@router.get("", response_model=ApplicationListResponse)
async def list_apps_endpoint(
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationListResponse:
    """List current user's applications with optional status filter."""
    apps, total = await list_applications(
        db, current_user.id, status_filter=status, page=page, per_page=per_page,
    )
    return ApplicationListResponse(
        items=[_to_response(a) for a in apps],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_app_endpoint(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Get a specific application by ID."""
    app = await get_application(db, application_id, current_user.id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return _to_response(app)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_app_status_endpoint(
    application_id: uuid.UUID,
    payload: UpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """
    Update application status. Enforces state machine transitions.

    Valid transitions:
    - saved → applied, withdrawn
    - applied → interviewing, rejected, withdrawn
    - interviewing → offered, rejected, withdrawn
    - offered → withdrawn
    """
    try:
        app = await update_status(
            db, application_id, current_user.id, payload.status,
        )
        await db.commit()
        refetched = await get_application(db, app.id, current_user.id)
        if refetched is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found after update")
        return _to_response(refetched)
    except (InvalidTransition, RateLimitViolation, ApplicationError) as exc:
        await db.rollback()
        raise _handle_service_error(exc) from exc


@router.delete("/{application_id}", status_code=204)
async def delete_app_endpoint(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an application."""
    deleted = await delete_application(db, application_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    await db.commit()
