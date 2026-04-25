"""
PathForge — Push Notification Service
=======================================
Asynchronous push notification delivery via Expo Push API.

Architecture (Audit Fix #15 + #16):
    - Follows ``_send_digest_email()`` fire-and-forget pattern
    - Hooks into ``emit_notification()`` return path
    - ``asyncio.create_task()`` for non-blocking dispatch

Pipeline:
    emit_notification() → notification persisted
                        → asyncio.create_task(push_dispatch(...))
                        → preference check → quiet hours → rate limit
                        → Expo Push API → retry (3x backoff)
                        → 410 = token invalidation

Safety:
    - Never propagates exceptions (graceful degradation)
    - Structured logging for Sentry observability
    - Server-side rate limit: MAX_PUSH_PER_DAY = 3
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any, cast

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import CareerNotification, NotificationPreference
from app.models.push_token import PushToken

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────

MAX_PUSH_PER_DAY = 3
MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1.0
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


# ── Token Masking (Sprint 33 F6) ──────────────────────────────


def mask_token(token: str) -> str:
    """Mask device token for API responses (Sprint 33 F6).

    Hides all but last 4 characters to prevent token enumeration
    while still allowing users to identify their device.

    Example: ``ExponentPushToken[abc123xyz]`` → ``***xyz]``
    """
    if len(token) <= 4:
        return "***"
    return f"***{token[-4:]}"


# ── HTTP Client (Sprint 33 F7) ────────────────────────────────

_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Lazy singleton for Expo Push API calls (Sprint 33 F7).

    Connection pooling prevents TCP churn at scale.
    Client lifecycle managed by application lifespan.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            ),
        )
    return _http_client


async def close_http_client() -> None:
    """Graceful shutdown — close shared HTTP client."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


# ── Public API ─────────────────────────────────────────────────


async def dispatch(
    db: AsyncSession,
    *,
    notification: CareerNotification,
) -> None:
    """Dispatch a push notification for a career notification.

    Fire-and-forget — never raises. All errors are logged.

    Checks (in order):
        1. User has push_notifications enabled
        2. Not in quiet hours
        3. Daily rate limit not exceeded
        4. At least one active push token exists
    """
    user_id = uuid.UUID(notification.user_id)

    try:
        # 1. Preference check
        pref = await _get_push_preference(db, user_id=user_id)
        if pref is None or not pref.push_notifications:
            logger.debug(
                "Push suppressed: push_notifications disabled for user %s",
                user_id,
            )
            return

        # 2. Quiet hours check
        if _in_quiet_hours(pref):
            logger.debug(
                "Push suppressed: quiet hours active for user %s", user_id,
            )
            return

        # 3. Rate limit check (Sprint 33 F4: count dispatches, not tokens)
        daily_count = _get_daily_push_count(pref)
        if daily_count >= MAX_PUSH_PER_DAY:
            logger.debug(
                "Push suppressed: daily limit (%d/%d) for user %s",
                daily_count, MAX_PUSH_PER_DAY, user_id,
            )
            return

        # 4. Get active tokens
        tokens = await _get_active_tokens(db, user_id=user_id)
        if not tokens:
            logger.debug(
                "Push suppressed: no active tokens for user %s", user_id,
            )
            return

        # Build payload
        payload = _build_payload(notification)

        # Dispatch to each token
        for token in tokens:
            await _send_to_token(
                db,
                push_token=token,
                payload=payload,
            )

        # Increment dispatch counter (Sprint 33 F4)
        await _increment_dispatch_count(db, pref=pref)

    except Exception:
        logger.exception(
            "Push dispatch failed for notification %s", notification.id,
        )


async def register_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    device_token: str,
    platform: str,
) -> PushToken:
    """Register or reactivate a device push token (idempotent upsert).

    If token already exists for another user, it is reassigned
    (device changed hands).
    """
    result = await db.execute(
        select(PushToken).where(PushToken.device_token == device_token),
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        existing.user_id = str(user_id)
        existing.platform = platform
        existing.is_active = True
        existing.last_used_at = datetime.now(UTC)
        await db.flush()
        logger.info(
            "Push token reactivated for user %s (platform=%s)",
            user_id, platform,
        )
        return existing

    token = PushToken(
        user_id=str(user_id),
        device_token=device_token,
        platform=platform,
        is_active=True,
    )
    db.add(token)
    await db.flush()
    logger.info(
        "Push token registered for user %s (platform=%s)",
        user_id, platform,
    )
    return token


async def deregister_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    device_token: str,
) -> bool:
    """Deactivate a device push token. Returns True if found.

    Only deactivates tokens owned by the specified user (Sprint 33
    audit F2: ownership verification).
    """
    result = await db.execute(
        update(PushToken)
        .where(
            PushToken.device_token == device_token,
            PushToken.user_id == str(user_id),
        )
        .values(is_active=False)
    )
    deactivated = cast(int, result.rowcount) > 0  # type: ignore[attr-defined]
    if deactivated:
        logger.info("Push token deregistered: %s...", device_token[:20])
    return deactivated


async def get_status(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get push registration status for a user."""
    result = await db.execute(
        select(PushToken)
        .where(
            PushToken.user_id == str(user_id),
            PushToken.is_active.is_(True),
        )
        .limit(1),
    )
    token = result.scalar_one_or_none()

    if token is None:
        return {"registered": False, "token": None, "platform": None}

    return {
        "registered": True,
        "token": mask_token(token.device_token),
        "platform": token.platform,
    }


# ── Internal Helpers ───────────────────────────────────────────


async def _get_push_preference(
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


def _in_quiet_hours(pref: NotificationPreference) -> bool:
    """Check if current time is within user's quiet hours."""
    if pref.quiet_hours_start is None or pref.quiet_hours_end is None:
        return False

    now_time = datetime.now(UTC).time()
    start = pref.quiet_hours_start
    end = pref.quiet_hours_end

    if start <= end:
        return start <= now_time <= end
    # Overnight window (e.g. 22:00 → 07:00)
    return now_time >= start or now_time <= end


def _get_daily_push_count(pref: NotificationPreference) -> int:
    """Read daily push count from preference (Sprint 33 F4).

    Pure function — no DB query. Reads counter from the preference
    object, treating stale dates as zero.
    """
    if pref.last_push_date != date.today():
        return 0
    return pref.daily_push_count


async def _increment_dispatch_count(
    db: AsyncSession,
    *,
    pref: NotificationPreference,
) -> None:
    """Increment dispatch counter, reset on new day (Sprint 33 F4)."""
    today = date.today()
    if pref.last_push_date != today:
        pref.daily_push_count = 1
    else:
        pref.daily_push_count += 1
    pref.last_push_date = today
    await db.flush()


async def _get_active_tokens(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[PushToken]:
    """Get all active push tokens for a user."""
    result = await db.execute(
        select(PushToken).where(
            PushToken.user_id == str(user_id),
            PushToken.is_active.is_(True),
        ),
    )
    return list(result.scalars().all())


def _build_payload(notification: CareerNotification) -> dict[str, Any]:
    """Build Expo Push API payload from a notification."""
    return {
        "title": notification.title,
        "body": notification.body[:200] if notification.body else "",
        "data": {
            "notification_id": str(notification.id),
            "type": notification.notification_type,
            "severity": notification.severity,
            "action_url": notification.action_url or "",
        },
        "sound": "default",
        "priority": (
            "high" if notification.severity in ("critical", "high")
            else "normal"
        ),
    }


async def _send_to_token(
    db: AsyncSession,
    *,
    push_token: PushToken,
    payload: dict[str, Any],
) -> None:
    """Send push notification to a single token with retry.

    Retries up to MAX_RETRY_ATTEMPTS with exponential backoff.
    Invalidates token on HTTP 410 (Gone = expired token).
    Uses shared httpx client for connection pooling (Sprint 33 F7).
    """
    message = {
        "to": push_token.device_token,
        **payload,
    }

    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            client = await get_http_client()
            response = await client.post(
                EXPO_PUSH_URL,
                json=message,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 410:
                # Token expired — deactivate
                push_token.is_active = False
                await db.flush()
                logger.info(
                    "Push token invalidated (410): %s...",
                    push_token.device_token[:20],
                )
                return

            response.raise_for_status()

            # Update last_used_at
            push_token.last_used_at = datetime.now(UTC)
            await db.flush()

            logger.info(
                "Push delivered to token %s... (attempt %d)",
                push_token.device_token[:20], attempt + 1,
            )
            return

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                # Client error — don't retry
                logger.warning(
                    "Push delivery failed (client error %d) for token %s...",
                    exc.response.status_code,
                    push_token.device_token[:20],
                )
                return
            # Server error — retry
            logger.warning(
                "Push delivery failed (attempt %d/%d): %s",
                attempt + 1, MAX_RETRY_ATTEMPTS, exc,
            )

        except Exception as exc:
            logger.warning(
                "Push delivery error (attempt %d/%d): %s",
                attempt + 1, MAX_RETRY_ATTEMPTS, exc,
            )

        # Exponential backoff
        if attempt < MAX_RETRY_ATTEMPTS - 1:
            delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
            await asyncio.sleep(delay)

    logger.error(
        "Push delivery exhausted retries for token %s...",
        push_token.device_token[:20],
    )
