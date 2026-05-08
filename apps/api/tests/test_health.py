"""
PathForge API — Health Endpoint Tests
========================================
Tests for /api/v1/health and /api/v1/health/ready.

Sprint 30: Updated to validate new fields (redis, rate_limiting,
uptime_seconds, cold_start_ms) and HTTP 503 behavior.

ADR-0001: regression tests for error-redaction and attestation caching.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /api/v1/health returns 200 with app info."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "PathForge"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """GET /api/v1/health/ready returns structured readiness response.

    In test environment (no Redis), the endpoint returns status based
    on available dependencies. Database should always be connected.
    """
    response = await client.get("/api/v1/health/ready")

    # Accept both 200 (all deps ok) and 503 (Redis not available)
    assert response.status_code in (200, 503)

    data = response.json()
    assert data["status"] in ("ok", "unhealthy")
    assert data["database"] == "connected"
    assert "redis" in data
    assert "rate_limiting" in data
    assert "uptime_seconds" in data
    assert data["app"] == "PathForge"
    assert "version" in data

    # ADR-0001: structured db block with TLS attestation
    assert isinstance(data["db"], dict)
    assert data["db"]["status"] == "ok"
    assert isinstance(data["db"]["ssl"], bool)
    # In tests we run on SQLite → pg_stat_ssl is unavailable, so cipher/
    # version fall back to None and ssl_attested must be False.
    assert "ssl_cipher" in data["db"]
    assert "ssl_version" in data["db"]
    assert data["db"]["ssl_attested"] is False

    # ADR-0002: structured redis_detail block with client-side TLS
    # introspection. Tests run without a live Redis connection, so
    # ssl_attested is False and ssl falls back to the config-derived value.
    assert isinstance(data["redis_detail"], dict)
    assert "status" in data["redis_detail"]
    assert isinstance(data["redis_detail"]["ssl"], bool)
    assert data["redis_detail"]["ssl_attested"] is False
    assert "scheme" in data["redis_detail"]


# ── ADR-0001 security-review follow-ups ─────────────────────────────

@pytest.mark.asyncio
async def test_db_probe_error_is_redacted(
    client: AsyncClient, caplog: pytest.LogCaptureFixture,
) -> None:
    """M1 regression: when the DB probe fails, the response body must NOT
    include driver exception text (host, port, username, 'password
    authentication failed', etc.). Logs should capture the full exception
    with `exc_info`; the response carries a static `"error"` token only.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    sentinel = "host=prod-db.example.internal user=leakuser password=leakpass"

    async def _boom(*_args: object, **_kwargs: object) -> None:
        raise OperationalError(
            statement="SELECT 1",
            params={},
            orig=Exception(sentinel),
        )

    import logging as _logging
    with (
        patch.object(AsyncSession, "execute", side_effect=_boom),
        caplog.at_level(_logging.WARNING, logger="app.api.v1.health"),
    ):
        response = await client.get("/api/v1/health/ready")

    data = response.json()
    # Endpoint reports the failure without interpolating raw details.
    assert data["database"] == "error"
    assert data["db"]["status"] == "error"

    # The sentinel must not appear anywhere in the rendered JSON body.
    import json as _json
    body = _json.dumps(data)
    for fragment in ("prod-db.example.internal", "leakuser", "leakpass", sentinel):
        assert fragment not in body, (
            f"Credential-leak regression: {fragment!r} reached the HTTP "
            f"response body: {body!r}"
        )


@pytest.mark.asyncio
async def test_attestation_cache_short_circuits_second_query() -> None:
    """M2 regression: a second call within TTL must NOT re-issue
    `SELECT … FROM pg_stat_ssl …`. Prevents the DoS amplification path
    flagged in the /security-review.
    """
    from app.api.v1 import health as health_module

    health_module._reset_attest_cache_for_tests()

    call_count = 0

    async def _fake_execute(*_args: object, **_kwargs: object) -> object:
        nonlocal call_count
        call_count += 1

        class _Result:
            def mappings(self) -> object:
                class _M:
                    def first(self) -> dict[str, object]:
                        return {
                            "ssl": True,
                            "cipher": "TLS_AES_256_GCM_SHA384",
                            "version": "TLSv1.3",
                        }
                return _M()

        return _Result()

    from sqlalchemy.ext.asyncio import AsyncSession

    # Also bypass the dialect guard — the test uses a bare AsyncSession
    # without a bound engine, which would normally short-circuit.
    with (
        patch.object(AsyncSession, "execute", side_effect=_fake_execute),
        patch.object(health_module, "_is_postgres_session", return_value=True),
    ):
        db = AsyncSession.__new__(AsyncSession)
        first = await health_module._attest_db_ssl(db)  # type: ignore[arg-type]
        second = await health_module._attest_db_ssl(db)  # type: ignore[arg-type]
        third = await health_module._attest_db_ssl(db)  # type: ignore[arg-type]

    assert first is not None
    assert first.ssl is True
    assert first.cipher == "TLS_AES_256_GCM_SHA384"
    # All subsequent calls return the SAME cached entry.
    assert first is second
    assert first is third
    # Only one database round-trip, not three.
    assert call_count == 1


@pytest.mark.asyncio
async def test_attestation_short_circuits_on_non_postgres_dialect() -> None:
    """@gemini-code-assist regression: non-PostgreSQL backends must not
    issue the `pg_stat_ssl` query at all. Previously the query ran and
    raised, logging a DEBUG line on every `/health/ready` hit under
    SQLite (test-mode) — cheap but noisy and needlessly exercised the
    exception path. The dialect guard skips the round-trip.
    """
    from app.api.v1 import health as health_module

    health_module._reset_attest_cache_for_tests()

    execute_calls = 0

    async def _should_not_be_called(*_args: object, **_kwargs: object) -> object:
        nonlocal execute_calls
        execute_calls += 1
        raise AssertionError("attestation query reached a non-Postgres session")

    from sqlalchemy.ext.asyncio import AsyncSession

    with (
        patch.object(AsyncSession, "execute", side_effect=_should_not_be_called),
        patch.object(health_module, "_is_postgres_session", return_value=False),
    ):
        db = AsyncSession.__new__(AsyncSession)
        entry = await health_module._attest_db_ssl(db)  # type: ignore[arg-type]

    assert entry is None
    assert execute_calls == 0, (
        "Dialect guard failed: pg_stat_ssl query executed against a "
        "non-Postgres session"
    )


@pytest.mark.asyncio
async def test_attestation_cache_does_not_cache_failures() -> None:
    """Failures must NOT poison the cache — a transient pg_stat_ssl error
    (cold-start race, temporary grant issue) must not lock the endpoint
    into `ssl_attested=False` for 60s.
    """
    from app.api.v1 import health as health_module

    health_module._reset_attest_cache_for_tests()

    call_count = 0
    should_fail = True

    async def _toggle(*_args: object, **_kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        if should_fail:
            raise RuntimeError("attestation unavailable")

        class _Result:
            def mappings(self) -> object:
                class _M:
                    def first(self) -> dict[str, object]:
                        return {"ssl": True, "cipher": "x", "version": "y"}
                return _M()

        return _Result()

    from sqlalchemy.ext.asyncio import AsyncSession

    with (
        patch.object(AsyncSession, "execute", side_effect=_toggle),
        patch.object(health_module, "_is_postgres_session", return_value=True),
    ):
        db = AsyncSession.__new__(AsyncSession)
        first = await health_module._attest_db_ssl(db)  # type: ignore[arg-type]
        assert first is None
        # Flip to success — next call should retry, not reuse the miss.
        should_fail = False
        second = await health_module._attest_db_ssl(db)  # type: ignore[arg-type]

    assert second is not None
    assert second.ssl is True
    assert call_count == 2


# ── Sprint 55 / Sprint 62 deploy regression ─────────────────────────
# Issue tracked from PR #59 → #60 production deploy of 2026-05-08:
# Railway healthcheck failed because `token_blacklist._redis` was
# never initialised at startup. The Sprint 55 readiness contract
# returns 503 when `redis_status == "not_initialized"`, and the
# original `_redis` only became non-None when an auth request hit
# `get_redis()`. On a freshly-deployed container the very first
# request is the healthcheck itself, so the new container could
# never pass its first probe and Railway never cut traffic over.
# This test pins the eager-init behaviour into the lifespan.

@pytest.mark.asyncio
async def test_lifespan_eagerly_initialises_redis_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The application lifespan must call `token_blacklist.get_redis()`
    at startup so the Sprint 55 readiness probe finds a live Redis
    client on the very first request (Railway's healthcheck).

    A regression here re-introduces the 2026-05-08 deploy outage:
    healthchecks return 503 with `redis_status=\"not_initialized\"`,
    Railway marks every deploy failed, and traffic never cuts over
    from the previous deployment.
    """
    from fastapi import FastAPI

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
