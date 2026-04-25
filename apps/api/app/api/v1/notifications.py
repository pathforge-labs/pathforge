"""
PathForge — Notification Engine™ API Routes
=============================================
REST API endpoints for the Notification Engine.

Endpoints:
    GET    /                    — List notifications (filtered, paginated)
    GET    /count               — Unread count with severity breakdown
    POST   /mark-read           — Mark specific notifications as read
    POST   /mark-all-read       — Mark all notifications as read
    GET    /digests              — List notification digests
    POST   /digests/generate    — Generate a new digest
    GET    /preferences         — Get notification preferences
    PUT    /preferences         — Update notification preferences
    POST   /push-token          — Register device push token
    DELETE /push-token          — Deregister device push token
    GET    /push-status         — Get push registration status
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.notification import (
    CareerNotificationResponse,
    NotificationCountResponse,
    NotificationDigestListResponse,
    NotificationDigestResponse,
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.schemas.push_token import (
    PushTokenDeregister,
    PushTokenRegister,
    PushTokenStatusResponse,
)
from app.services import push_service
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["Notification Engine™"],
)


# ── List Notifications ─────────────────────────────────────


@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="List notifications",
    description=(
        "Career-Aware Notifications™ — list your career notifications "
        "with optional filtering by engine, type, severity, and read state."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def list_notifications(
    request: Request,
    page: int = Query(1, ge=1, description="Page number."),
    page_size: int = Query(20, ge=1, le=100, description="Items per page."),
    source_engine: str | None = Query(None, description="Filter by engine."),
    notification_type: str | None = Query(None, description="Filter by type."),
    severity: str | None = Query(None, description="Filter by severity."),
    is_read: bool | None = Query(None, description="Filter by read state."),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List paginated notifications with optional filters."""
    data = await NotificationService.list_notifications(
        database,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        source_engine=source_engine,
        notification_type=notification_type,
        severity=severity,
        is_read=is_read,
    )
    return NotificationListResponse(
        notifications=[
            CareerNotificationResponse.model_validate(notification)
            for notification in data["notifications"]
        ],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
        has_next=data["has_next"],
    )


# ── Unread Count ───────────────────────────────────────────


@router.get(
    "/count",
    response_model=NotificationCountResponse,
    summary="Get unread notification count",
    description=(
        "Get unread notification count with breakdowns by "
        "severity and source engine."
    ),
)
@limiter.limit(settings.rate_limit_parse)
async def get_unread_count(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NotificationCountResponse:
    """Get unread notification count with severity breakdown."""
    data = await NotificationService.get_unread_count(
        database, user_id=current_user.id,
    )
    return NotificationCountResponse(**data)


# ── Mark Read ──────────────────────────────────────────────


@router.post(
    "/mark-read",
    summary="Mark specific notifications as read",
    description="Mark one or more notifications as read by ID.",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_embed)
async def mark_read(
    request: Request,
    body: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark specific notifications as read."""
    count = await NotificationService.mark_read(
        database,
        user_id=current_user.id,
        notification_ids=body.notification_ids,
    )
    return {"marked_read": count}


@router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
    description="Mark all unread notifications as read.",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_embed)
async def mark_all_read(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Mark all unread notifications as read."""
    count = await NotificationService.mark_all_read(
        database, user_id=current_user.id,
    )
    return {"marked_read": count}


# ── Digests ────────────────────────────────────────────────


@router.get(
    "/digests",
    response_model=NotificationDigestListResponse,
    summary="List notification digests",
    description="List notification digest summaries.",
)
@limiter.limit(settings.rate_limit_parse)
async def list_digests(
    request: Request,
    page: int = Query(1, ge=1, description="Page number."),
    page_size: int = Query(20, ge=1, le=100, description="Items per page."),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NotificationDigestListResponse:
    """List paginated notification digests."""
    data = await NotificationService.list_digests(
        database,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return NotificationDigestListResponse(
        digests=[
            NotificationDigestResponse.model_validate(digest)
            for digest in data["digests"]
        ],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )


@router.post(
    "/digests/generate",
    response_model=NotificationDigestResponse | None,
    status_code=status.HTTP_201_CREATED,
    summary="Generate notification digest",
    description=(
        "Generate a notification digest for the specified period. "
        "Returns null if no notifications in period."
    ),
)
@limiter.limit("3/minute")
async def generate_digest(
    request: Request,
    digest_type: str = Query(
        "weekly", description="Digest type: daily | weekly.",
    ),
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NotificationDigestResponse | None:
    """Generate a notification digest."""
    if digest_type not in ("daily", "weekly"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="digest_type must be 'daily' or 'weekly'.",
        )

    digest = await NotificationService.generate_digest(
        database,
        user_id=current_user.id,
        digest_type=digest_type,
    )

    if digest is None:
        return None

    return NotificationDigestResponse.model_validate(digest)


# ── Preferences ──────────────────────────────────────────


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get notification preferences",
    description="Get current notification preferences.",
)
@limiter.limit(settings.rate_limit_parse)
async def get_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """Get notification preferences."""
    pref = await NotificationService.get_preferences(
        database, user_id=current_user.id,
    )
    if pref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preferences found. Set preferences first.",
        )
    return NotificationPreferenceResponse.model_validate(pref)


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preferences",
    description=(
        "Update notification preferences including engine toggles, "
        "severity threshold, digest schedule, and quiet hours."
    ),
)
@limiter.limit(settings.rate_limit_embed)
async def update_preferences(
    request: Request,
    body: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """Update notification preferences."""
    try:
        pref = await NotificationService.update_preferences(
            database,
            user_id=current_user.id,
            updates=body.model_dump(exclude_unset=True),
        )
        return NotificationPreferenceResponse.model_validate(pref)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Push Token Management ────────────────────────────────────


@router.post(
    "/push-token",
    response_model=PushTokenStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register device push token",
    description="Register or reactivate a device push token (idempotent).",
)
@limiter.limit(settings.rate_limit_push)
async def register_push_token(
    request: Request,
    body: PushTokenRegister,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PushTokenStatusResponse:
    """Register a device push token."""
    token = await push_service.register_token(
        database,
        user_id=current_user.id,
        device_token=body.token,
        platform=body.platform,
    )
    return PushTokenStatusResponse(
        registered=True,
        token=push_service.mask_token(token.device_token),
        platform=token.platform,
    )


@router.delete(
    "/push-token",
    summary="Deregister device push token",
    description="Deactivate the current device push token.",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_push)
async def deregister_push_token(
    request: Request,
    body: PushTokenDeregister,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Deregister a device push token."""
    deactivated = await push_service.deregister_token(
        database, user_id=current_user.id, device_token=body.token,
    )
    if not deactivated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Push token not found.",
        )
    return {"deregistered": True}


@router.get(
    "/push-status",
    response_model=PushTokenStatusResponse,
    summary="Get push registration status",
    description="Check whether the current user has an active push token.",
)
@limiter.limit(settings.rate_limit_push)
async def get_push_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    database: AsyncSession = Depends(get_db),
) -> PushTokenStatusResponse:
    """Check push registration status."""
    data = await push_service.get_status(
        database, user_id=current_user.id,
    )
    return PushTokenStatusResponse(**data)
