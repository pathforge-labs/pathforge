"""
PathForge — Circuit Breaker
============================
Lightweight Redis-backed circuit breaker for external API calls.

Prevents cascading failures and wasted compute when external services
(Adzuna, Jooble, Voyage AI) have extended outages.

States:
    CLOSED  → Normal operation. Calls pass through.
    OPEN    → Service is down. Calls are rejected immediately (CircuitOpenError).
    HALF_OPEN → Recovery probe. One call is allowed through to test recovery.

Usage:
    from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError

    breaker = CircuitBreaker(name="adzuna", redis_url=settings.redis_url)

    async with breaker:
        response = await httpx.get("https://api.adzuna.com/...")
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable
from typing import Any, cast

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is in OPEN state."""

    def __init__(self, name: str, recovery_at: float) -> None:
        self.name = name
        self.recovery_at = recovery_at
        remaining = max(0, recovery_at - time.time())
        super().__init__(
            f"Circuit '{name}' is OPEN. Recovery probe in {remaining:.0f}s."
        )


class CircuitBreaker:
    """Redis-backed circuit breaker for external service calls.

    Args:
        name: Identifier for this circuit (e.g., 'adzuna', 'jooble', 'voyage').
        redis_url: Redis connection URL.
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout: Seconds to wait before probing recovery (HALF_OPEN).
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        *,
        name: str,
        redis_url: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._key_prefix = f"pathforge:circuit:{name}"
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Lazy Redis connection."""
        if self._redis is None:
            self._redis = cast(
                aioredis.Redis,
                aioredis.from_url(self._redis_url, decode_responses=True),  # type: ignore[no-untyped-call]
            )
        return self._redis

    async def _get_state(self) -> dict[str, Any]:
        """Read circuit state from Redis."""
        r = await self._get_redis()
        data: dict[Any, Any] = await cast(
            "Awaitable[dict[Any, Any]]", r.hgetall(self._key_prefix)
        )
        return {
            "state": data.get("state", self.STATE_CLOSED),
            "failures": int(data.get("failures", 0)),
            "opened_at": float(data.get("opened_at", 0)),
        }

    async def _set_state(
        self, *, state: str, failures: int = 0, opened_at: float = 0.0
    ) -> None:
        """Persist circuit state to Redis."""
        r = await self._get_redis()
        await cast("Awaitable[int]", r.hset(
            self._key_prefix,
            mapping={
                "state": state,
                "failures": str(failures),
                "opened_at": str(opened_at),
            },
        ))
        # Auto-expire after 1 hour to prevent stale state if worker crashes
        await r.expire(self._key_prefix, 3600)

    async def check(self) -> None:
        """Check if the circuit allows a call. Raises CircuitOpenError if not."""
        current = await self._get_state()
        state = current["state"]

        if state == self.STATE_CLOSED:
            return  # Allow

        if state == self.STATE_OPEN:
            elapsed = time.time() - current["opened_at"]
            if elapsed >= self.recovery_timeout:
                # Transition to HALF_OPEN — allow one probe
                await self._set_state(
                    state=self.STATE_HALF_OPEN,
                    failures=current["failures"],
                    opened_at=current["opened_at"],
                )
                logger.info("Circuit '%s' → HALF_OPEN (probing recovery)", self.name)
                return  # Allow probe
            raise CircuitOpenError(
                self.name, current["opened_at"] + self.recovery_timeout
            )

        # HALF_OPEN — allow (probe in progress)
        return

    async def record_success(self) -> None:
        """Record a successful call. Resets the circuit to CLOSED."""
        current = await self._get_state()
        if current["state"] != self.STATE_CLOSED:
            logger.info("Circuit '%s' → CLOSED (recovered)", self.name)
        await self._set_state(state=self.STATE_CLOSED, failures=0)

    async def record_failure(self) -> None:
        """Record a failed call. May transition to OPEN."""
        current = await self._get_state()
        new_failures = current["failures"] + 1

        if current["state"] == self.STATE_HALF_OPEN:
            # Probe failed — back to OPEN
            logger.warning("Circuit '%s' → OPEN (probe failed)", self.name)
            await self._set_state(
                state=self.STATE_OPEN, failures=new_failures, opened_at=time.time()
            )
            return

        if new_failures >= self.failure_threshold:
            logger.warning(
                "Circuit '%s' → OPEN after %d consecutive failures",
                self.name,
                new_failures,
            )
            await self._set_state(
                state=self.STATE_OPEN, failures=new_failures, opened_at=time.time()
            )
        else:
            await self._set_state(
                state=self.STATE_CLOSED,
                failures=new_failures,
                opened_at=current["opened_at"],
            )

    async def __aenter__(self) -> CircuitBreaker:
        """Context manager entry — checks circuit state."""
        await self.check()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Context manager exit — records success or failure."""
        if exc_type is None:
            await self.record_success()
        else:
            await self.record_failure()
        # Don't suppress the exception
        return False
