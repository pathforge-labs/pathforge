"""
PathForge — Waitlist Service
================================
Sprint 34: Waitlist management and conversion logic.

Audit findings:
    F7  — FIFO position auto-assigned
    F21 — Waitlist email auto-linking
    F27 — Email case normalization
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.waitlist import WaitlistEntry, WaitlistStatus

logger = logging.getLogger(__name__)


class WaitlistService:
    """Encapsulates waitlist management logic."""

    @staticmethod
    async def join_waitlist(
        db: AsyncSession,
        email: str,
        full_name: str | None = None,
        referral_source: str | None = None,
    ) -> WaitlistEntry:
        """Add an email to the waitlist.

        F27: Email stored as lower().strip() for idempotent matching.
        F7: Position auto-assigned as max(position) + 1.
        """
        normalized_email = email.lower().strip()

        # Check for existing entry
        existing = await db.execute(
            select(WaitlistEntry).where(WaitlistEntry.email == normalized_email)
        )
        entry = existing.scalar_one_or_none()
        if entry is not None:
            return entry

        # F7: Auto-assign position
        max_result = await db.execute(
            select(func.coalesce(func.max(WaitlistEntry.position), 0))
        )
        max_position: int = max_result.scalar() or 0

        entry = WaitlistEntry(
            email=normalized_email,
            full_name=full_name,
            position=max_position + 1,
            status=WaitlistStatus.PENDING.value,
            referral_source=referral_source,
        )
        db.add(entry)
        await db.flush()

        # F21: Auto-link if user already exists
        user_result = await db.execute(
            select(User).where(User.email == normalized_email)
        )
        user = user_result.scalar_one_or_none()
        if user is not None:
            entry.converted_user_id = user.id
            entry.status = WaitlistStatus.CONVERTED.value
            await db.flush()
            logger.info("Waitlist auto-linked: %s → user %s", normalized_email, user.id)

        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_position(
        db: AsyncSession,
        email: str,
    ) -> WaitlistEntry | None:
        """Look up a waitlist entry by email."""
        normalized_email = email.lower().strip()
        result = await db.execute(
            select(WaitlistEntry).where(WaitlistEntry.email == normalized_email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def invite_batch(
        db: AsyncSession,
        count: int,
    ) -> list[WaitlistEntry]:
        """Invite the next N pending entries (FIFO order)."""
        result = await db.execute(
            select(WaitlistEntry)
            .where(WaitlistEntry.status == WaitlistStatus.PENDING.value)
            .order_by(WaitlistEntry.position.asc())
            .limit(count)
        )
        entries = list(result.scalars().all())

        for entry in entries:
            entry.status = WaitlistStatus.INVITED.value
            entry.invite_token = secrets.token_urlsafe(32)

        await db.flush()
        logger.info("Invited %d waitlist entries", len(entries))
        return entries

    @staticmethod
    async def convert_by_token(
        db: AsyncSession,
        invite_token: str,
        user_id: Any,
    ) -> WaitlistEntry | None:
        """Convert a waitlist entry using an invite token."""
        result = await db.execute(
            select(WaitlistEntry).where(WaitlistEntry.invite_token == invite_token)
        )
        entry = result.scalar_one_or_none()

        if entry is None:
            return None

        if entry.status == WaitlistStatus.CONVERTED.value:
            return entry

        entry.status = WaitlistStatus.CONVERTED.value
        entry.converted_user_id = user_id
        await db.flush()
        await db.refresh(entry)

        logger.info("Waitlist converted: %s → user %s", entry.email, user_id)
        return entry

    @staticmethod
    async def convert_by_email(
        db: AsyncSession,
        email: str,
        user_id: Any,
    ) -> WaitlistEntry | None:
        """F21: Auto-link waitlist entry by email during registration."""
        normalized_email = email.lower().strip()
        result = await db.execute(
            select(WaitlistEntry).where(WaitlistEntry.email == normalized_email)
        )
        entry = result.scalar_one_or_none()

        if entry is None:
            return None

        if entry.status == WaitlistStatus.CONVERTED.value:
            return entry

        entry.status = WaitlistStatus.CONVERTED.value
        entry.converted_user_id = user_id
        await db.flush()
        await db.refresh(entry)

        logger.info("Waitlist auto-converted by email: %s → user %s", email, user_id)
        return entry

    @staticmethod
    async def get_stats(
        db: AsyncSession,
    ) -> dict[str, int]:
        """Aggregate waitlist statistics."""
        total_result = await db.execute(
            select(func.count()).select_from(WaitlistEntry)
        )
        total = total_result.scalar() or 0

        status_result = await db.execute(
            select(WaitlistEntry.status, func.count())
            .group_by(WaitlistEntry.status)
        )
        status_counts: dict[str, int] = {
            str(row[0]): int(row[1]) for row in status_result.all()
        }

        return {
            "total": total,
            "pending": status_counts.get(WaitlistStatus.PENDING.value, 0),
            "invited": status_counts.get(WaitlistStatus.INVITED.value, 0),
            "converted": status_counts.get(WaitlistStatus.CONVERTED.value, 0),
            "expired": status_counts.get(WaitlistStatus.EXPIRED.value, 0),
        }

    @staticmethod
    async def list_entries(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        status_filter: str | None = None,
    ) -> list[WaitlistEntry]:
        """Paginated waitlist listing for admin."""
        query = select(WaitlistEntry)

        if status_filter:
            query = query.where(WaitlistEntry.status == status_filter)

        offset = (page - 1) * per_page
        result = await db.execute(
            query.order_by(WaitlistEntry.position.asc()).offset(offset).limit(per_page)
        )
        return list(result.scalars().all())
