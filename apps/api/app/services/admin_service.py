"""
PathForge — Admin Service
===========================
Sprint 34: Admin dashboard business logic with RBAC.

Audit findings:
    F5  — Last-admin guard (prevent lockout)
    F28 — Sentry context tagging
    F32 — Aggregate dashboard queries (GROUP BY)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminAuditLog
from app.models.subscription import Subscription, UsageRecord
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class AdminService:
    """Encapsulates admin dashboard business logic."""

    # ── User Management ────────────────────────────────────────

    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        role_filter: str | None = None,
    ) -> dict[str, Any]:
        """Paginated user listing with optional search and role filter."""
        query = select(User)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                User.email.ilike(search_term) | User.full_name.ilike(search_term)
            )

        if role_filter:
            query = query.where(User.role == role_filter)

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginated results
        offset = (page - 1) * per_page
        result = await db.execute(
            query.order_by(User.created_at.desc()).offset(offset).limit(per_page)
        )
        users = list(result.scalars().all())

        return {"users": users, "total": total, "page": page, "per_page": per_page}

    @staticmethod
    async def get_user_detail(
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        """Get detailed user info including subscription and usage."""
        import uuid

        uid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError("User not found")

        # Get subscription
        sub_result = await db.execute(
            select(Subscription).where(Subscription.user_id == uid)
        )
        subscription = sub_result.scalar_one_or_none()

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "auth_provider": user.auth_provider,
            "created_at": user.created_at,
            "subscription_tier": subscription.tier if subscription else None,
            "subscription_status": subscription.status if subscription else None,
            "scans_used": 0,
        }

    @staticmethod
    async def update_user(
        db: AsyncSession,
        admin_user: User,
        target_user_id: str,
        updates: dict[str, Any],
        ip_address: str | None = None,
    ) -> User:
        """Update a user's profile with admin authorization.

        F5: Prevents self-demotion and last-admin lockout.
        """
        import uuid

        uid = uuid.UUID(target_user_id)
        result = await db.execute(select(User).where(User.id == uid))
        target_user = result.scalar_one_or_none()

        if target_user is None:
            raise ValueError("User not found")

        # F5: Self-demotion guard
        new_role = updates.get("role")
        if new_role and str(admin_user.id) == target_user_id and new_role != UserRole.ADMIN:
            raise ValueError("Cannot demote yourself")

        # F5: Last-admin guard
        if new_role and new_role != UserRole.ADMIN and target_user.role == UserRole.ADMIN:
            admin_count_result = await db.execute(
                select(func.count()).where(User.role == UserRole.ADMIN)
            )
            admin_count = admin_count_result.scalar() or 0
            if admin_count <= 1:
                raise ValueError("Cannot remove the last admin")

        # Apply updates
        for field, value in updates.items():
            if value is not None and hasattr(target_user, field):
                setattr(target_user, field, value)

        await db.flush()

        # Audit log
        audit_log = AdminAuditLog(
            admin_user_id=admin_user.id,
            action="user_update",
            target_user_id=uid,
            details=updates,
            ip_address=ip_address,
        )
        db.add(audit_log)
        await db.flush()

        await db.refresh(target_user)
        return target_user

    @staticmethod
    async def override_subscription(
        db: AsyncSession,
        admin_user: User,
        target_user_id: str,
        tier: str,
        reason: str,
        ip_address: str | None = None,
    ) -> Subscription:
        """Admin override of a user's subscription tier."""
        import uuid

        uid = uuid.UUID(target_user_id)

        result = await db.execute(
            select(Subscription).where(Subscription.user_id == uid)
        )
        subscription = result.scalar_one_or_none()

        if subscription is None:
            subscription = Subscription(user_id=uid, tier=tier, status="active")
            db.add(subscription)
        else:
            subscription.tier = tier

        await db.flush()

        # Audit log
        audit_log = AdminAuditLog(
            admin_user_id=admin_user.id,
            action="subscription_override",
            target_user_id=uid,
            details={"tier": tier, "reason": reason},
            ip_address=ip_address,
        )
        db.add(audit_log)
        await db.flush()
        await db.refresh(subscription)

        return subscription

    # ── Dashboard ──────────────────────────────────────────────

    @staticmethod
    async def get_dashboard_summary(
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Aggregate dashboard statistics.

        F32: Uses GROUP BY for tier distribution to avoid N+1.
        """
        # Total users
        total_result = await db.execute(select(func.count()).select_from(User))
        total_users = total_result.scalar() or 0

        # Active users
        active_result = await db.execute(
            select(func.count()).where(User.is_active.is_(True))
        )
        active_users = active_result.scalar() or 0

        # F32: Tier distribution via GROUP BY
        tier_result = await db.execute(
            select(Subscription.tier, func.count())
            .group_by(Subscription.tier)
        )
        tier_distribution: dict[str, int] = {
            str(row[0]): int(row[1]) for row in tier_result.all()
        }

        # Total scans this period
        scan_result = await db.execute(
            select(func.coalesce(func.sum(UsageRecord.scan_count), 0))
        )
        total_scans = scan_result.scalar() or 0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "tier_distribution": tier_distribution,
            "total_scans_this_period": total_scans,
            "waitlist_count": 0,  # Populated after WS-3
        }

    @staticmethod
    async def get_system_health(db: AsyncSession) -> dict[str, str]:
        """Check system component health."""
        health: dict[str, str] = {
            "database": "unknown",
            "redis": "unknown",
            "stripe": "unknown",
            "worker": "unknown",
        }

        # Database
        try:
            await db.execute(select(func.count()).select_from(User))
            health["database"] = "healthy"
        except Exception:
            health["database"] = "unhealthy"

        # Redis
        try:
            from collections.abc import Awaitable
            from typing import cast

            from app.core.token_blacklist import token_blacklist

            redis_conn = await token_blacklist.get_redis()
            # redis.asyncio.Redis.ping() is typed as Awaitable[bool] | bool;
            # we always use the async client, so cast to the awaitable variant.
            await cast(Awaitable[bool], redis_conn.ping())
            health["redis"] = "healthy"
        except Exception:
            health["redis"] = "unhealthy"

        # Stripe
        from app.core.config import settings

        health["stripe"] = "configured" if settings.stripe_secret_key else "not_configured"

        return health

    @staticmethod
    async def list_audit_logs(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
    ) -> list[AdminAuditLog]:
        """List admin audit log entries."""
        offset = (page - 1) * per_page
        result = await db.execute(
            select(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return list(result.scalars().all())

    # ── Admin Promotion ────────────────────────────────────────

    @staticmethod
    async def auto_promote_initial_admin(
        db: AsyncSession,
        email: str,
    ) -> bool:
        """Auto-promote a user to admin during startup (D3)."""
        if not email:
            return False

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            logger.info("Initial admin email not found: %s (will retry on next startup)", email)
            return False

        if user.role == UserRole.ADMIN:
            logger.info("User %s is already admin", email)
            return False

        user.role = UserRole.ADMIN
        await db.flush()
        logger.info("Auto-promoted %s to admin", email)
        return True
