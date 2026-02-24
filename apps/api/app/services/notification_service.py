"""
PathForge — Notification Engine™ Service
=========================================
Event-driven career notification system with severity-based filtering,
digest scheduling, and preference management.

Pipeline flow (emit notification):
    1. Validate source engine exists in registry
    2. Check user preferences (engine enabled, severity threshold)
    3. Persist notification record
    4. Return notification for API delivery

Digest flow:
    1. Query unread notifications for period
    2. Aggregate by engine and severity
    3. Persist digest record
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    CareerNotification,
    DigestFrequency,
    NotificationDigest,
    NotificationPreference,
    Severity,
)

logger = logging.getLogger(__name__)

# Severity ordering for threshold comparison
SEVERITY_ORDER: dict[str, int] = {
    Severity.LOW.value: 0,
    Severity.MEDIUM.value: 1,
    Severity.HIGH.value: 2,
    Severity.CRITICAL.value: 3,
}


class NotificationService:
    """Event-driven career notification service.

    Handles notification creation, retrieval, filtering,
    read/unread management, digest generation, and preference
    management.
    """

    # ── Emit Notification ──────────────────────────────────────

    @staticmethod
    async def emit_notification(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        source_engine: str,
        notification_type: str,
        severity: str,
        title: str,
        body: str,
        action_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CareerNotification | None:
        """Emit a new career notification.

        Checks user preferences before persisting:
        - Engine must be enabled (or no preference = all enabled)
        - Severity must meet minimum threshold

        Returns None if notification is suppressed by preferences.
        """
        # Check preferences
        preferences = await NotificationService.get_preferences(
            db, user_id=user_id,
        )

        if preferences is not None:
            # Engine toggle check
            enabled = preferences.enabled_engines
            if enabled is not None and source_engine not in enabled:
                logger.debug(
                    "Notification suppressed: engine %s disabled for user %s",
                    source_engine, user_id,
                )
                return None

            # Severity threshold check
            min_severity = preferences.min_severity or Severity.LOW.value
            if SEVERITY_ORDER.get(severity, 0) < SEVERITY_ORDER.get(
                min_severity, 0,
            ):
                logger.debug(
                    "Notification suppressed: severity %s below threshold %s",
                    severity, min_severity,
                )
                return None

        notification = CareerNotification(
            user_id=str(user_id),
            source_engine=source_engine,
            notification_type=notification_type,
            severity=severity,
            title=title,
            body=body,
            action_url=action_url,
            metadata_=metadata,
        )
        db.add(notification)
        await db.flush()

        return notification

    # ── List Notifications ─────────────────────────────────────

    @staticmethod
    async def list_notifications(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        source_engine: str | None = None,
        notification_type: str | None = None,
        severity: str | None = None,
        is_read: bool | None = None,
    ) -> dict[str, Any]:
        """List paginated notifications with optional filters."""
        conditions = [CareerNotification.user_id == str(user_id)]

        if source_engine is not None:
            conditions.append(
                CareerNotification.source_engine == source_engine,
            )
        if notification_type is not None:
            conditions.append(
                CareerNotification.notification_type == notification_type,
            )
        if severity is not None:
            conditions.append(CareerNotification.severity == severity)
        if is_read is not None:
            conditions.append(CareerNotification.is_read == is_read)

        # Count total
        count_query = select(func.count(CareerNotification.id)).where(
            and_(*conditions),
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Get page
        offset = (page - 1) * page_size
        query = (
            select(CareerNotification)
            .where(and_(*conditions))
            .order_by(CareerNotification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        notifications = list(result.scalars().all())

        return {
            "notifications": notifications,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": (offset + page_size) < total,
        }

    # ── Unread Count ───────────────────────────────────────────

    @staticmethod
    async def get_unread_count(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get unread notification count with severity breakdown."""
        conditions = [
            CareerNotification.user_id == str(user_id),
            CareerNotification.is_read.is_(False),
        ]

        # Total unread
        total_query = select(func.count(CareerNotification.id)).where(
            and_(*conditions),
        )
        total_result = await db.execute(total_query)
        total_unread = total_result.scalar() or 0

        # Breakdown by severity
        severity_query = (
            select(
                CareerNotification.severity,
                func.count(CareerNotification.id),
            )
            .where(and_(*conditions))
            .group_by(CareerNotification.severity)
        )
        severity_result = await db.execute(severity_query)
        by_severity = {
            "critical": 0, "high": 0, "medium": 0, "low": 0,
        }
        for row in severity_result:
            if row[0] in by_severity:
                by_severity[row[0]] = row[1]

        # Breakdown by engine
        engine_query = (
            select(
                CareerNotification.source_engine,
                func.count(CareerNotification.id),
            )
            .where(and_(*conditions))
            .group_by(CareerNotification.source_engine)
        )
        engine_result = await db.execute(engine_query)
        by_engine = {row[0]: row[1] for row in engine_result}

        return {
            "total_unread": total_unread,
            "by_severity": by_severity,
            "by_engine": by_engine,
        }

    # ── Mark Read ──────────────────────────────────────────────

    @staticmethod
    async def mark_read(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        notification_ids: list[uuid.UUID],
    ) -> int:
        """Mark specific notifications as read. Returns count updated."""
        now = datetime.now(UTC)
        str_ids = [str(nid) for nid in notification_ids]

        stmt = (
            update(CareerNotification)
            .where(
                and_(
                    CareerNotification.user_id == str(user_id),
                    CareerNotification.id.in_(str_ids),
                    CareerNotification.is_read.is_(False),
                ),
            )
            .values(is_read=True, read_at=now)
        )
        cursor = await db.execute(stmt)
        return cast(int, cursor.rowcount)  # type: ignore[attr-defined]

    @staticmethod
    async def mark_all_read(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> int:
        """Mark all unread notifications as read. Returns count."""
        now = datetime.now(UTC)
        stmt = (
            update(CareerNotification)
            .where(
                and_(
                    CareerNotification.user_id == str(user_id),
                    CareerNotification.is_read.is_(False),
                ),
            )
            .values(is_read=True, read_at=now)
        )
        cursor = await db.execute(stmt)
        return cast(int, cursor.rowcount)  # type: ignore[attr-defined]

    # ── Digest Generation ──────────────────────────────────────

    @staticmethod
    async def generate_digest(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        digest_type: str = DigestFrequency.WEEKLY.value,
    ) -> NotificationDigest | None:
        """Generate a notification digest for the specified period.

        Returns None if there are no unread notifications.
        """
        now = datetime.now(UTC)

        if digest_type == DigestFrequency.DAILY.value:
            period_start = now - timedelta(days=1)
        else:
            period_start = now - timedelta(weeks=1)

        # Query notifications in period
        conditions = [
            CareerNotification.user_id == str(user_id),
            CareerNotification.created_at >= period_start,
            CareerNotification.created_at <= now,
        ]

        count_query = select(func.count(CareerNotification.id)).where(
            and_(*conditions),
        )
        count_result = await db.execute(count_query)
        notification_count = count_result.scalar() or 0

        if notification_count == 0:
            return None

        # Build summary
        severity_query = (
            select(
                CareerNotification.severity,
                func.count(CareerNotification.id),
            )
            .where(and_(*conditions))
            .group_by(CareerNotification.severity)
        )
        severity_result = await db.execute(severity_query)
        by_severity = {row[0]: row[1] for row in severity_result}

        engine_query = (
            select(
                CareerNotification.source_engine,
                func.count(CareerNotification.id),
            )
            .where(and_(*conditions))
            .group_by(CareerNotification.source_engine)
        )
        engine_result = await db.execute(engine_query)
        by_engine = {row[0]: row[1] for row in engine_result}

        summary: dict[str, Any] = {
            "by_severity": by_severity,
            "by_engine": by_engine,
            "period": digest_type,
        }

        digest = NotificationDigest(
            user_id=str(user_id),
            digest_type=digest_type,
            period_start=period_start,
            period_end=now,
            notification_count=notification_count,
            summary=summary,
        )
        db.add(digest)
        await db.flush()

        return digest

    # ── Digest List ────────────────────────────────────────────

    @staticmethod
    async def list_digests(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List paginated digests."""
        conditions = [NotificationDigest.user_id == str(user_id)]

        count_query = select(func.count(NotificationDigest.id)).where(
            and_(*conditions),
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(NotificationDigest)
            .where(and_(*conditions))
            .order_by(NotificationDigest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        digests = list(result.scalars().all())

        return {
            "digests": digests,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Preferences ────────────────────────────────────────────

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> NotificationPreference | None:
        """Get user's notification preferences."""
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == str(user_id),
            ),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> NotificationPreference:
        """Update or create notification preferences."""
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == str(user_id),
            ),
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = NotificationPreference(user_id=str(user_id))
            db.add(pref)

        for key, value in updates.items():
            if value is not None and hasattr(pref, key):
                setattr(pref, key, value)

        await db.flush()
        return pref
