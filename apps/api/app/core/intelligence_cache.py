"""
PathForge — Intelligence Response Cache
=========================================
Redis-backed response cache for the 12 intelligence endpoints.

Design:
- Fail-open: if Redis is unavailable the call proceeds uncached
  (same philosophy as circuit_breaker.py fail_open=True).
- Cache keys: pathforge:ic:{user_id}:{endpoint}
- TTLs calibrated to data volatility (see constants below).
- Invalidation: call invalidate_user() when a user regenerates their
  Career DNA or uploads a new resume, which makes all cached responses
  stale.

Usage in a route handler:

    cached = await ic_cache.get(ic_cache.key(current_user.id, "career_dna"))
    if cached:
        return CareerDNAResponse.model_validate(cached)

    result = _build_full_response(career_dna)
    await ic_cache.set(
        ic_cache.key(current_user.id, "career_dna"),
        result.model_dump(mode="json"),
        ttl=ic_cache.TTL_CAREER_DNA,
    )
    return result
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, cast

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.redis_ssl import resolve_redis_url

logger = logging.getLogger(__name__)

# ── TTL constants (seconds) ───────────────────────────────────────────────────

# Career DNA: changes when resume is updated or dimensions are regenerated.
TTL_CAREER_DNA = 1800         # 30 min

# Market-based analyses: external data refreshed at most hourly.
TTL_THREAT_RADAR = 3600       # 60 min
TTL_SALARY = 3600             # 60 min
TTL_SKILL_DECAY = 3600        # 60 min
TTL_COLLECTIVE = 1800         # 30 min — community data refreshes more often

# Recommendation engines: job listings refresh frequently.
TTL_RECOMMENDATIONS = 900     # 15 min

# Default for endpoints not listed above.
TTL_DEFAULT = 1800            # 30 min

_KEY_PREFIX = "pathforge:ic"


class IntelligenceCache:
    """Redis-backed cache for intelligence endpoint responses.

    All operations are fail-open: a Redis connection failure logs a warning
    and returns None/no-op, so the route handler falls through to the live
    computation path.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    # ── Constants (re-exported for convenience) ───────────────────────────────

    TTL_CAREER_DNA = TTL_CAREER_DNA
    TTL_THREAT_RADAR = TTL_THREAT_RADAR
    TTL_SALARY = TTL_SALARY
    TTL_SKILL_DECAY = TTL_SKILL_DECAY
    TTL_COLLECTIVE = TTL_COLLECTIVE
    TTL_RECOMMENDATIONS = TTL_RECOMMENDATIONS
    TTL_DEFAULT = TTL_DEFAULT

    # ── Key helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def key(user_id: uuid.UUID, endpoint: str) -> str:
        """Generate a cache key for a user + endpoint combination."""
        return f"{_KEY_PREFIX}:{user_id}:{endpoint}"

    # ── Redis connection ──────────────────────────────────────────────────────

    async def _get_redis(self) -> aioredis.Redis | None:
        """Lazy Redis connection; returns None if unavailable (fail-open)."""
        if self._redis is not None:
            return self._redis
        try:
            url = resolve_redis_url(
                settings.redis_url,
                settings.redis_ssl_enabled,
                settings.environment,
            )
            self._redis = cast(
                aioredis.Redis,
                aioredis.from_url(url, decode_responses=True),  # redis-ssl-exempt: url already resolved by resolve_redis_url above
            )
            return self._redis
        except Exception as exc:
            logger.warning(
                "IntelligenceCache: failed to connect to Redis (%s), caching disabled",
                type(exc).__name__,
            )
            return None

    # ── Public API ────────────────────────────────────────────────────────────

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        """Return cached response dict, or None on miss / Redis unavailable."""
        r = await self._get_redis()
        if r is None:
            return None
        try:
            raw = await r.get(cache_key)
            if raw is None:
                return None
            return json.loads(raw)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.warning(
                "IntelligenceCache.get(%s) failed (%s), proceeding uncached",
                cache_key, type(exc).__name__,
            )
            return None

    async def set(self, cache_key: str, data: dict[str, Any], ttl: int) -> None:
        """Store response dict in Redis. Silently skips on failure."""
        r = await self._get_redis()
        if r is None:
            return
        try:
            await r.set(cache_key, json.dumps(data), ex=ttl)
        except Exception as exc:
            logger.warning(
                "IntelligenceCache.set(%s) failed (%s), response not cached",
                cache_key, type(exc).__name__,
            )

    async def invalidate_user(self, user_id: uuid.UUID) -> None:
        """Delete all cached responses for a user (e.g. on resume update).

        Uses SCAN to find keys matching pathforge:ic:{user_id}:* — avoids
        KEYS which blocks the Redis event loop.
        """
        r = await self._get_redis()
        if r is None:
            return
        pattern = f"{_KEY_PREFIX}:{user_id}:*"
        try:
            deleted = 0
            async for key in r.scan_iter(pattern):
                await r.delete(key)
                deleted += 1
            if deleted:
                logger.info(
                    "IntelligenceCache: invalidated %d key(s) for user %s",
                    deleted, user_id,
                )
        except Exception as exc:
            logger.warning(
                "IntelligenceCache.invalidate_user(%s) failed (%s)",
                user_id, type(exc).__name__,
            )


# Module-level singleton — shared across all requests in a worker process.
ic_cache = IntelligenceCache()
