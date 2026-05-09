"""
Tests for `app/main.py` — application entry point and lifespan.

Module-mirror file (`tests/test_<module>.py` ↔ `app/<module>.py`) per
the repository style guide. Lifespan-startup tests live here, not in
`tests/test_health.py`, even when the failure mode they prevent is
visible at the `/health/ready` endpoint.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI

# ── Sprint 55 / Sprint 62 deploy regression ─────────────────────────
# Issue tracked from PR #59 → #60 production deploy of 2026-05-08:
# Railway healthcheck failed because `token_blacklist._redis` was
# never initialised at startup. The Sprint 55 readiness contract
# returns 503 when `redis_status == "not_initialized"`, and the
# original `_redis` only became non-None when an auth request hit
# `get_redis()`. On a freshly-deployed container the very first
# request is the healthcheck itself, so the new container could
# never pass its first probe and Railway never cut traffic over.
# These tests pin the eager-init behaviour into the lifespan.


@pytest.mark.asyncio
async def test_lifespan_eagerly_initialises_redis_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The application lifespan must call `token_blacklist.get_redis()`
    at startup so the Sprint 55 readiness probe finds a live Redis
    client on the very first request (Railway's healthcheck).

    A regression here re-introduces the 2026-05-08 deploy outage:
    healthchecks return 503 with `redis_status="not_initialized"`,
    Railway marks every deploy failed, and traffic never cuts over
    from the previous deployment.
    """
    from app.core import token_blacklist as tb_module
    from app.main import lifespan

    called = {"get_redis": False, "ping": False}

    class _FakeRedis:
        async def ping(self) -> bool:
            called["ping"] = True
            return True

        async def aclose(self) -> None:
            return None

    async def fake_get_redis() -> _FakeRedis:
        called["get_redis"] = True
        return _FakeRedis()

    monkeypatch.setattr(
        tb_module.token_blacklist, "get_redis", fake_get_redis,
    )

    fake_app = FastAPI()
    async with lifespan(fake_app):
        pass

    assert called["get_redis"], (
        "lifespan must call token_blacklist.get_redis() at startup so "
        "the readiness probe sees an initialised Redis client; without "
        "this the new container's first healthcheck returns 503 and "
        "Railway never cuts traffic over."
    )
    assert called["ping"], (
        "lifespan must ping Redis after acquiring the client to verify "
        "connectivity at boot — silently obtaining a client without a "
        "ping would let a misconfigured REDIS_URL slip past startup."
    )


@pytest.mark.asyncio
async def test_lifespan_redis_init_does_not_hang_on_unresponsive_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wedged Redis ping must not stall startup past the bounded
    timeout (gemini-code-assist HIGH review on PR #62).

    `TokenBlacklist.get_redis` configures `socket_connect_timeout` but
    not a general `socket_timeout`, so a server that completes the
    TCP handshake and then never replies to commands could hang
    `redis_client.ping()` indefinitely. The eager-init helper wraps
    the ping in `asyncio.wait_for` to bound the wait — this test
    fails fast (well under the timeout) if the wrap is removed.
    """
    from app.core import token_blacklist as tb_module
    from app.main import _REDIS_STARTUP_PING_TIMEOUT_SECONDS, lifespan

    class _HangingRedis:
        async def ping(self) -> bool:
            # Sleep longer than the startup timeout — without
            # `asyncio.wait_for` the lifespan would hang here.
            await asyncio.sleep(_REDIS_STARTUP_PING_TIMEOUT_SECONDS * 3)
            return True

        async def aclose(self) -> None:
            return None

    async def fake_get_redis() -> _HangingRedis:
        return _HangingRedis()

    monkeypatch.setattr(
        tb_module.token_blacklist, "get_redis", fake_get_redis,
    )

    # Override the timeout to keep the test fast — production uses 5s.
    monkeypatch.setattr(
        "app.main._REDIS_STARTUP_PING_TIMEOUT_SECONDS", 0.1,
    )

    fake_app = FastAPI()
    started = asyncio.get_event_loop().time()
    async with lifespan(fake_app):
        pass
    elapsed = asyncio.get_event_loop().time() - started

    # The ping should be cancelled at ~0.1s; full lifespan finishes
    # within a tight bound. Pad generously so test isn't flaky on slow
    # CI workers, but well below the 0.3s the hanging ping would take.
    assert elapsed < 0.25, (
        f"lifespan took {elapsed:.2f}s — eager-init must wrap the "
        "Redis ping in asyncio.wait_for so a hung server cannot "
        "stall startup past the configured timeout."
    )
