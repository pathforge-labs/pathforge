"""
PathForge — User Profile & GDPR Data Export API Routes
========================================================
REST API endpoints for user profile management and GDPR exports.

Endpoints:
    GET    /profile               — Get user profile
    POST   /profile               — Create user profile
    PUT    /profile               — Update user profile
    DELETE /profile               — Delete user profile
    GET    /onboarding-status     — Check onboarding completion
    GET    /data-summary          — Get record count per engine
    POST   /exports               — Request GDPR data export
    GET    /exports               — List export requests
    GET    /exports/{export_id}   — Get export status
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.user_profile import (
    DataExportListResponse,
    DataExportRequestCreate,
    DataExportRequestResponse,
    OnboardingStatusResponse,
    UserDataSummaryResponse,
    UserProfileCreateRequest,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.user_profile_service import UserProfileService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user-profile",
    tags=["User Profile & GDPR Export"],
)


# ── Profile CRUD ───────────────────────────────────────────


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get user profile",
    description="Get current user's profile data.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Get user profile."""
    profile = await UserProfileService.get_profile(
        database, user_id=current_user.id,
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create a profile first.",
        )
    return UserProfileResponse.model_validate(profile)


@router.post(
    "/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user profile",
    description="Create a new user profile with initial data.",
)
@limiter.limit(settings.rate_limit_embed)
async def create_profile(
    request: Request,
    body: UserProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Create user profile."""
    # Check if profile already exists
    existing = await UserProfileService.get_profile(
        database, user_id=current_user.id,
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PUT to update.",
        )

    profile = await UserProfileService.create_profile(
        database,
        user_id=current_user.id,
        data=body.model_dump(exclude_unset=True),
    )
    return UserProfileResponse.model_validate(profile)


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update user profile",
    description="Update current user's profile data.",
)
@limiter.limit(settings.rate_limit_embed)
async def update_profile(
    request: Request,
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Update user profile."""
    profile = await UserProfileService.update_profile(
        database,
        user_id=current_user.id,
        updates=body.model_dump(exclude_unset=True),
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create a profile first.",
        )
    return UserProfileResponse.model_validate(profile)


@router.delete(
    "/profile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user profile",
    description="Delete current user's profile data.",
)
@limiter.limit(settings.rate_limit_embed)
async def delete_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> None:
    """Delete user profile."""
    deleted = await UserProfileService.delete_profile(
        database, user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )


# ── Onboarding Status ─────────────────────────────────────


@router.get(
    "/onboarding-status",
    response_model=OnboardingStatusResponse,
    summary="Check onboarding status",
    description="Check user's onboarding completion status.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_onboarding_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Check onboarding completion status."""
    data = await UserProfileService.get_onboarding_status(
        database, user_id=current_user.id,
    )
    return OnboardingStatusResponse(**data)


# ── Data Summary ───────────────────────────────────────────


@router.get(
    "/data-summary",
    response_model=UserDataSummaryResponse,
    summary="Get data summary",
    description=(
        "GDPR data awareness — see how many records are stored "
        "across each engine. Useful before requesting an export."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def get_data_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> UserDataSummaryResponse:
    """Get record count per engine."""
    data = await UserProfileService.get_data_summary(
        database, user_id=current_user.id,
    )
    return UserDataSummaryResponse(**data)


# ── GDPR Export ────────────────────────────────────────────


@router.post(
    "/exports",
    status_code=status.HTTP_201_CREATED,
    summary="Request GDPR data export",
    description=(
        "GDPR Article 20+ — request a full data export with AI "
        "methodology disclosure, data provenance, and SHA-256 "
        "integrity checksum. Rate limited to 1 per 24 hours."
    ),
)
@limiter.limit("2/minute")
async def request_export(
    request: Request,
    body: DataExportRequestCreate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Request a GDPR data export."""
    result = await UserProfileService.request_export(
        database,
        user_id=current_user.id,
        export_type=body.export_type,
        export_format=body.format_,
    )

    if result.get("status") == "rate_limited":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=result.get("detail", "Rate limit exceeded."),
        )

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("detail", "Export failed."),
        )

    return result


@router.get(
    "/exports",
    response_model=DataExportListResponse,
    summary="List export requests",
    description="List all GDPR data export requests.",
)
@limiter.limit(settings.rate_limit_parse)
async def list_exports(
    request: Request,
    page: int = Query(1, ge=1, description="Page number."),
    page_size: int = Query(20, ge=1, le=100, description="Items per page."),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> DataExportListResponse:
    """List paginated export requests."""
    data = await UserProfileService.list_exports(
        database,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return DataExportListResponse(
        exports=[
            DataExportRequestResponse.model_validate(export)
            for export in data["exports"]
        ],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )


@router.get(
    "/exports/{export_id}",
    response_model=DataExportRequestResponse,
    summary="Get export status",
    description="Get the status of a specific GDPR data export request.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_export_status(
    request: Request,
    export_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> DataExportRequestResponse:
    """Get export request status."""
    export = await UserProfileService.get_export_status(
        database,
        user_id=current_user.id,
        export_id=export_id,
    )
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export request not found.",
        )
    return DataExportRequestResponse.model_validate(export)
