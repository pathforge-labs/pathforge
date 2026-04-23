"""
PathForge — Circuit Breaker Tests
====================================
Tests for the Redis-backed CircuitBreaker state machine.

Covers: CLOSED→OPEN→HALF_OPEN transitions, fail_open=True/False,
CircuitOpenError message, and success/failure recording.
All tests use an in-memory Redis stub — no real Redis required.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError


# ── In-memory Redis stub ─────────────────────────────────────────────────────


class _FakeRedis:
    """Minimal in-memory Redis substitute for circuit breaker tests."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._store: dict[str, str] = dict(initial or {})

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._store)

    async def hset(self, key: str, mapping: dict[str, Any]) -> int:
        self._store.update({k: str(v) for k, v in mapping.items()})
        return 1

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _make_breaker(
    *,
    initial_state: str = "closed",
    failures: int = 0,
    opened_at: float = 0.0,
    failure_threshold: int = 3,
    recovery_timeout: int = 300,
    fail_open: bool = True,
) -> tuple[CircuitBreaker, _FakeRedis]:
    """Create a CircuitBreaker backed by a _FakeRedis with preset state."""
    fake_redis = _FakeRedis(
        initial={
            "state": initial_state,
            "failures": str(failures),
            "opened_at": str(opened_at),
        }
        if initial_state != "closed" or failures or opened_at
        else {}
    )
    breaker = CircuitBreaker(
        name="test",
        redis_url="redis://localhost:6379/0",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        fail_open=fail_open,
    )
    breaker._redis = fake_redis  # type: ignore[assignment]
    return breaker, fake_redis


# ── CLOSED state ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_closed_allows_call() -> None:
    """CLOSED circuit should allow calls through without raising."""
    breaker, _ = _make_breaker()
    await breaker.check()  # must not raise


@pytest.mark.asyncio
async def test_success_resets_to_closed() -> None:
    """record_success() should reset state to CLOSED with 0 failures."""
    breaker, fake_redis = _make_breaker(failures=2)
    await breaker.record_success()
    assert fake_redis._store["state"] == "closed"
    assert fake_redis._store["failures"] == "0"


@pytest.mark.asyncio
async def test_failure_below_threshold_stays_closed() -> None:
    """Failures below threshold should not open the circuit."""
    breaker, fake_redis = _make_breaker(failure_threshold=3)
    await breaker.record_failure()
    await breaker.record_failure()
    assert fake_redis._store["state"] == "closed"
    assert fake_redis._store["failures"] == "2"


# ── OPEN state ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_open_after_threshold() -> None:
    """Circuit should open after hitting failure_threshold."""
    breaker, fake_redis = _make_breaker(failure_threshold=3)
    for _ in range(3):
        await breaker.record_failure()
    assert fake_redis._store["state"] == "open"


@pytest.mark.asyncio
async def test_open_circuit_blocks_call() -> None:
    """OPEN circuit should raise CircuitOpenError on check()."""
    breaker, _ = _make_breaker(
        initial_state="open",
        failures=3,
        opened_at=time.time(),
        recovery_timeout=300,
    )
    with pytest.raises(CircuitOpenError, match="OPEN"):
        await breaker.check()


@pytest.mark.asyncio
async def test_circuit_open_error_has_remaining_seconds() -> None:
    """CircuitOpenError message should include seconds remaining."""
    opened_at = time.time() - 10  # opened 10s ago, 290s remaining
    breaker, _ = _make_breaker(
        initial_state="open",
        failures=3,
        opened_at=opened_at,
        recovery_timeout=300,
    )
    with pytest.raises(CircuitOpenError) as exc_info:
        await breaker.check()
    assert "290" in str(exc_info.value) or "289" in str(exc_info.value)


# ── HALF_OPEN state ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_half_open_after_recovery_timeout() -> None:
    """OPEN circuit should transition to HALF_OPEN after recovery_timeout."""
    opened_at = time.time() - 301  # 301s ago > recovery_timeout=300
    breaker, fake_redis = _make_breaker(
        initial_state="open",
        failures=3,
        opened_at=opened_at,
        recovery_timeout=300,
    )
    await breaker.check()  # should NOT raise — HALF_OPEN probe allowed
    assert fake_redis._store["state"] == "half_open"


@pytest.mark.asyncio
async def test_half_open_success_closes_circuit() -> None:
    """Successful HALF_OPEN probe should transition to CLOSED."""
    breaker, fake_redis = _make_breaker(initial_state="half_open", failures=3)
    await breaker.record_success()
    assert fake_redis._store["state"] == "closed"
    assert fake_redis._store["failures"] == "0"


@pytest.mark.asyncio
async def test_half_open_failure_reopens_circuit() -> None:
    """Failed HALF_OPEN probe should return to OPEN."""
    breaker, fake_redis = _make_breaker(initial_state="half_open", failures=3)
    await breaker.record_failure()
    assert fake_redis._store["state"] == "open"


# ── Context manager protocol ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_context_manager_records_success_on_clean_exit() -> None:
    """Exiting the context manager without exception records success."""
    breaker, fake_redis = _make_breaker(failures=2)
    async with breaker:
        pass  # no exception
    assert fake_redis._store.get("failures") == "0"
    assert fake_redis._store.get("state", "closed") == "closed"


@pytest.mark.asyncio
async def test_context_manager_records_failure_on_exception() -> None:
    """Exception inside context manager should record failure."""
    breaker, fake_redis = _make_breaker(failure_threshold=5)

    with pytest.raises(RuntimeError):
        async with breaker:
            raise RuntimeError("service down")

    assert int(fake_redis._store.get("failures", "0")) == 1


@pytest.mark.asyncio
async def test_context_manager_does_not_suppress_exception() -> None:
    """The context manager must not swallow exceptions."""
    breaker, _ = _make_breaker()
    with pytest.raises(ValueError, match="boom"):
        async with breaker:
            raise ValueError("boom")


# ── fail_open behaviour ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fail_open_true_proceeds_when_redis_unavailable() -> None:
    """With fail_open=True, Redis errors should be swallowed and call allowed."""
    breaker, _ = _make_breaker(fail_open=True)

    async def _raise(*_: Any, **__: Any) -> None:
        raise ConnectionError("Redis not provisioned (OPS-4)")

    breaker._redis.hgetall = _raise  # type: ignore[method-assign]

    await breaker.check()  # must NOT raise


@pytest.mark.asyncio
async def test_fail_open_true_skips_state_update_on_redis_error() -> None:
    """With fail_open=True, record_* should swallow Redis errors silently."""
    breaker, _ = _make_breaker(fail_open=True)

    async def _raise(*_: Any, **__: Any) -> None:
        raise ConnectionError("Redis not provisioned (OPS-4)")

    breaker._redis.hgetall = _raise  # type: ignore[method-assign]

    # Neither of these should raise
    await breaker.record_success()
    await breaker.record_failure()


@pytest.mark.asyncio
async def test_fail_open_false_propagates_redis_error() -> None:
    """With fail_open=False, Redis errors should propagate."""
    breaker, _ = _make_breaker(fail_open=False)

    async def _raise(*_: Any, **__: Any) -> None:
        raise ConnectionError("Redis unavailable")

    breaker._redis.hgetall = _raise  # type: ignore[method-assign]

    with pytest.raises(ConnectionError):
        await breaker.check()


# ── Redis lazy initialisation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_redis_initialises_lazily() -> None:
    """_get_redis() should create a Redis connection on first call."""
    breaker = CircuitBreaker(
        name="lazy",
        redis_url="redis://localhost:6379/0",
    )
    assert breaker._redis is None

    import redis.asyncio as aioredis

    with patch.object(aioredis, "from_url", return_value=_FakeRedis()) as mock_from_url:
        await breaker._get_redis()
        mock_from_url.assert_called_once()

    assert breaker._redis is not None


@pytest.mark.asyncio
async def test_get_redis_reuses_connection() -> None:
    """_get_redis() must not create a new connection on every call."""
    breaker = CircuitBreaker(
        name="reuse",
        redis_url="redis://localhost:6379/0",
    )
    import redis.asyncio as aioredis

    with patch.object(aioredis, "from_url", return_value=_FakeRedis()) as mock_from_url:
        await breaker._get_redis()
        await breaker._get_redis()
        assert mock_from_url.call_count == 1
