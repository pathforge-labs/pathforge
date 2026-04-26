"""
PathForge — Active Session Registry (T1-extension, ADR-0011)
==============================================================

Tracks per-user active session metadata (refresh-token JTIs + last-seen
device fingerprint) in Redis so the user can:

  1. See every device currently signed in to their account.
  2. Revoke any one session (including the current device).
  3. "Sign out of all other devices" — keep the current refresh JTI,
     blacklist all the others.

The registry sits **on top of** :class:`app.core.token_blacklist.TokenBlacklist`:

  - **Blacklist** = "is this individual JTI revoked?" (lookup is O(1)).
  - **Registry** = "what JTIs does this user own right now?" (set per user).

The two together let us answer "show me my sessions" without scanning the
entire blacklist, and "sign out of all others" without inventing a
per-token enumerator.

Why Redis (not a `user_session` table)
--------------------------------------

Sessions are inherently ephemeral and bounded by refresh-token lifetime
(30 days). A relational table would carry permanent rows for transient
state, requiring a periodic cleanup job; Redis's per-key TTL handles that
for free. The same Redis instance already runs the blacklist + rate
limiter, so no new infra dependency.

Data model
----------

  ``session:user:{user_id}``         — Redis SET of refresh JTIs that
                                       are currently active for the user.
                                       TTL refreshed on every login /
                                       refresh; auto-expires when the
                                       longest-lived JTI in the set
                                       would have expired.

  ``session:meta:{jti}``             — Redis HASH with the device-shaped
                                       metadata for a single refresh JTI.
                                       TTL = token's remaining lifetime
                                       (handed in by the caller).

Fields on the meta HASH:

  - ``user_id`` — owning user UUID (denormalised so we can purge the set
    entry on revoke without re-deriving from claims).
  - ``created_at`` — ISO-8601 UTC; first-seen timestamp.
  - ``last_seen_at`` — ISO-8601 UTC; updated on every refresh.
  - ``ip`` — last-seen client IP (best-effort, X-Forwarded-For aware).
  - ``user_agent`` — first 200 chars; longer values truncated.
  - ``device_label`` — derived display name ("Chrome on macOS").

The registry tolerates a missing or unreachable Redis. If Redis is down
we **fail-soft**: session creation is a no-op (the auth flow still
succeeds), listing returns ``[]``, and revoke-by-API returns a 503.
This matches the ``token_blacklist_fail_mode`` semantics without
forcing the auth path to honour a tighter contract than it already
does.

Privacy
-------

The IP is stored verbatim only for the lifetime of the session. There
is no aggregation, no geolocation lookup, no analytics export. GDPR
right-to-erasure is satisfied by the existing account-deletion service
which already calls ``SessionRegistry.purge_user`` (added below).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar

from app.core.config import settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


_USER_SET_PREFIX: str = "session:user:"
_META_PREFIX: str = "session:meta:"
_USER_AGENT_MAX_LEN: int = 200


def _user_set_key(user_id: str) -> str:
    return f"{_USER_SET_PREFIX}{user_id}"


def _meta_key(jti: str) -> str:
    return f"{_META_PREFIX}{jti}"


def _truncate_ua(ua: str | None) -> str:
    """Trim the User-Agent header to a sensible bound to keep meta-hash
    payloads small — UAs can be 500+ characters in the wild."""
    if not ua:
        return ""
    return ua[:_USER_AGENT_MAX_LEN]


def _derive_device_label(user_agent: str) -> str:
    """Best-effort human-readable device label from the UA string.

    Intentionally cheap and approximate — the actual UA is shown in the
    UI tooltip, this is just the headline. Full UA parsing (with
    ua-parser) would pull in 500+ KB of regex; we take a 5-line
    heuristic instead.
    """
    if not user_agent:
        return "Unknown device"
    ua = user_agent.lower()

    # Browser
    if "edg/" in ua:
        browser = "Edge"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"
    elif "okhttp" in ua or "expo" in ua or ("darwin" in ua and "mobile" in ua):
        browser = "Mobile app"
    else:
        browser = "Browser"

    # OS — check iOS / Android *before* macOS because the iOS UA
    # string contains "Mac OS X" (Apple's WebKit fork inherits the
    # base UA from the desktop browser).
    if "iphone" in ua or "ipad" in ua or "ios " in ua:
        os_label = "iOS"
    elif "android" in ua:
        os_label = "Android"
    elif "windows" in ua:
        os_label = "Windows"
    elif "mac os x" in ua or "macintosh" in ua:
        os_label = "macOS"
    elif "linux" in ua:
        os_label = "Linux"
    else:
        os_label = "Unknown OS"

    return f"{browser} on {os_label}"


class SessionRegistry:
    """Async Redis-backed active-session tracker.

    Class-level Redis pool mirrors :class:`TokenBlacklist`. All public
    methods catch Redis-side errors and degrade gracefully — auth must
    not break when the registry is unreachable.
    """

    _redis: ClassVar[Redis | None] = None

    @classmethod
    async def get_redis(cls) -> Redis:
        """Lazy-init Redis with the same TLS-reconciled URL helper the
        blacklist uses (ADR-0002)."""
        if cls._redis is None:
            from redis.asyncio import Redis as _Redis

            from app.core.redis_ssl import resolve_redis_url

            url = resolve_redis_url(
                settings.redis_url,
                settings.redis_ssl_enabled,
                settings.environment,
            )
            cls._redis = _Redis.from_url(  # redis-ssl-exempt: reconciled URL
                url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return cls._redis

    @classmethod
    async def register(
        cls,
        *,
        user_id: str,
        jti: str,
        ttl_seconds: int,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        """Persist a freshly-issued refresh JTI as an active session.

        Called from the auth handlers on login + every refresh rotation.
        Must not raise — the auth flow should not be coupled to the
        registry's availability.
        """
        try:
            redis = await cls.get_redis()
            now = datetime.now(UTC).isoformat()
            ua_trunc = _truncate_ua(user_agent)
            meta = {
                "user_id": user_id,
                "jti": jti,
                "created_at": now,
                "last_seen_at": now,
                "ip": ip or "",
                "user_agent": ua_trunc,
                "device_label": _derive_device_label(ua_trunc),
            }
            pipe = redis.pipeline()
            pipe.sadd(_user_set_key(user_id), jti)
            pipe.expire(_user_set_key(user_id), ttl_seconds)
            pipe.hset(_meta_key(jti), mapping=meta)
            pipe.expire(_meta_key(jti), ttl_seconds)
            await pipe.execute()
        except Exception:
            logger.warning(
                "session.register: registry unreachable — auth proceeds "
                "without session tracking (jti=%s…)",
                jti[:8],
                exc_info=True,
            )

    @classmethod
    async def touch(cls, *, jti: str) -> None:
        """Update `last_seen_at` on the session's meta hash. Called from
        the refresh handler before rotation — gives the operator a
        last-active timestamp on the UI even between hour-long refresh
        cycles."""
        try:
            redis = await cls.get_redis()
            await redis.hset(
                _meta_key(jti), "last_seen_at", datetime.now(UTC).isoformat(),
            )
        except Exception:
            logger.debug("session.touch failed; ignoring", exc_info=True)

    @classmethod
    async def list_for_user(cls, *, user_id: str) -> list[dict[str, str]]:
        """Return all active session meta records for a user.

        Each entry is a dict with the keys documented at module top.
        The list is unsorted by Redis convention — caller may sort by
        ``last_seen_at`` for display. Returns ``[]`` if Redis is
        unreachable or the user has no sessions.
        """
        try:
            redis = await cls.get_redis()
            jtis = await redis.smembers(_user_set_key(user_id))
        except Exception:
            logger.warning(
                "session.list: registry unreachable — returning []",
                exc_info=True,
            )
            return []

        if not jtis:
            return []

        pipe = redis.pipeline()
        for jti in jtis:
            pipe.hgetall(_meta_key(jti))
        results: list[dict[str, str]] = await pipe.execute()

        # Filter dead entries — meta TTL may have expired before the set
        # entry, leaving a dangling jti. We opportunistically clean those
        # up so the next list returns a tighter set.
        sessions: list[dict[str, str]] = []
        dead: list[str] = []
        for jti, meta in zip(jtis, results, strict=False):
            if not meta:
                dead.append(jti)
                continue
            sessions.append(meta)
        if dead:
            try:
                await redis.srem(_user_set_key(user_id), *dead)
            except Exception:
                logger.debug("session.list: failed to GC dead jtis", exc_info=True)
        return sessions

    @classmethod
    async def revoke(cls, *, user_id: str, jti: str, ttl_seconds: int) -> bool:
        """Remove a JTI from the user's active set, delete its meta hash,
        and propagate to the token blacklist so the JWT itself is
        rejected on its next presentation. Returns True on success.

        ``ttl_seconds`` is the JTI's remaining lifetime, used by the
        blacklist to size its entry. Caller derives this from the
        token's ``exp`` claim.
        """
        from app.core.token_blacklist import token_blacklist

        try:
            redis = await cls.get_redis()
            pipe = redis.pipeline()
            pipe.srem(_user_set_key(user_id), jti)
            pipe.delete(_meta_key(jti))
            await pipe.execute()
        except Exception:
            logger.error(
                "session.revoke: registry unreachable — cannot guarantee "
                "session was removed (jti=%s…)",
                jti[:8],
                exc_info=True,
            )
            return False

        # Blacklist propagation is independent: even if the registry-side
        # delete failed, blacklisting still kills the JTI on next use.
        try:
            await token_blacklist.revoke(jti, ttl_seconds=ttl_seconds)
        except Exception:
            logger.error(
                "session.revoke: blacklist propagation failed (jti=%s…)",
                jti[:8],
                exc_info=True,
            )
            return False
        return True

    @classmethod
    async def revoke_others(
        cls, *, user_id: str, current_jti: str, ttl_seconds: int,
    ) -> list[str]:
        """Revoke every active JTI for the user **except** ``current_jti``.

        Returns the list of revoked JTIs (for audit logging). The
        current session is preserved so the user is not logged out of
        the device making the request.
        """
        sessions = await cls.list_for_user(user_id=user_id)
        revoked: list[str] = []
        for sess in sessions:
            jti = sess.get("jti", "")
            if not jti or jti == current_jti:
                continue
            ok = await cls.revoke(
                user_id=user_id, jti=jti, ttl_seconds=ttl_seconds,
            )
            if ok:
                revoked.append(jti)
        return revoked

    @classmethod
    async def purge_user(cls, *, user_id: str) -> None:
        """Drop every session record for a user. Called from the
        account-deletion flow so a deleted account leaves no trailing
        Redis entries."""
        try:
            redis = await cls.get_redis()
            jtis = await redis.smembers(_user_set_key(user_id))
            pipe = redis.pipeline()
            pipe.delete(_user_set_key(user_id))
            for jti in jtis:
                pipe.delete(_meta_key(jti))
            await pipe.execute()
        except Exception:
            logger.warning(
                "session.purge_user: registry unreachable",
                exc_info=True,
            )

    @classmethod
    async def close(cls) -> None:
        """Gracefully close the Redis connection pool."""
        if cls._redis is not None:
            await cls._redis.aclose()
            cls._redis = None


# Module-level convenience handle (mirrors `token_blacklist`).
session_registry = SessionRegistry
