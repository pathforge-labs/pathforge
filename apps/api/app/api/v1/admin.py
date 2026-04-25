"""
PathForge — Admin API Routes
================================
Sprint 34: Admin dashboard endpoints with RBAC.

8 endpoints. Rate-limited 30/min (F8). OpenAPI tags (F29).
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
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminAuditLogResponse,
    AdminDashboardSummaryResponse,
    AdminSubscriptionOverrideRequest,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    SystemHealthResponse,
)
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


# ── Admin Dependency ───────────────────────────────────────────


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency for admin-only endpoints."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── GET /admin/dashboard ───────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=AdminDashboardSummaryResponse,
    summary="Dashboard summary",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Any:
    """Aggregate statistics for admin overview."""
    return await AdminService.get_dashboard_summary(db)


# ── GET /admin/users ───────────────────────────────────────────


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List users",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def list_users(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Any:
    """Paginated user listing with search and role filter."""
    return await AdminService.list_users(db, page, per_page, search, role)


# ── GET /admin/users/{user_id} ─────────────────────────────────


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Get user detail",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def get_user_detail(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Any:
    """Detailed user info including subscription and usage."""
    try:
        return await AdminService.get_user_detail(db, user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# ── PATCH /admin/users/{user_id} ───────────────────────────────


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Update user",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def update_user(
    request: Request,
    user_id: str,
    body: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Any:
    """Update user with admin authorization (F5: self-demotion guard)."""
    ip_address = request.client.host if request.client else None
    try:
        updates = body.model_dump(exclude_none=True)
        target_user = await AdminService.update_user(
            db, admin, user_id, updates, ip_address
        )
        return await AdminService.get_user_detail(db, str(target_user.id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


# ── POST /admin/users/{user_id}/subscription ───────────────────


@router.post(
    "/users/{user_id}/subscription",
    summary="Override subscription",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def override_subscription(
    request: Request,
    user_id: str,
    body: AdminSubscriptionOverrideRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    """Admin override of user subscription tier."""
    ip_address = request.client.host if request.client else None
    await AdminService.override_subscription(
        db, admin, user_id, body.tier, body.reason, ip_address
    )
    return {"status": "ok", "tier": body.tier}


# ── GET /admin/health ──────────────────────────────────────────


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="System health check",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def get_system_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Any:
    """System component health for admin monitoring."""
    return await AdminService.get_system_health(db)


# ── GET /admin/audit-logs ──────────────────────────────────────


@router.get(
    "/audit-logs",
    response_model=list[AdminAuditLogResponse],
    summary="Audit log history",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_admin)
async def list_audit_logs(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Any:
    """List admin action audit trail."""
    return await AdminService.list_audit_logs(db, page, per_page)
