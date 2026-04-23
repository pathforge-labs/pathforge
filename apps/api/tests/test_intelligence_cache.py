"""
Tests for app.core.intelligence_cache.IntelligenceCache.

Covers:
- key() static helper
- get(): miss, hit, Redis-unavailable fail-open, op-error fail-open
- set(): happy path, Redis-unavailable no-op, op-error no-op
- invalidate_user(): deletes matching keys, Redis-unavailable no-op, op-error no-op
- Lazy Redis init: connection reused across calls
- _get_redis() connect failure returns None
- TTL constants have expected values
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.intelligence_cache import (
    IntelligenceCache,
    TTL_CAREER_DNA,
    TTL_THREAT_RADAR,
    TTL_SALARY,
    TTL_SKILL_DECAY,
    TTL_COLLECTIVE,
    TTL_RECOMMENDATIONS,
    TTL_DEFAULT,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


class _FakeRedis:
    """In-memory Redis stub for testing."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int | None] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value
        self._ttls[key] = ex

    async def delete(self, key: str) -> int:
        self._ttls.pop(key, None)
        return 1 if self._store.pop(key, None) is not None else 0

    async def scan_iter(self, pattern: str):
        prefix = pattern.rstrip("*")
        for key in list(self._store):
            if key.startswith(prefix):
                yield key


def _make_cache(fake_redis: _FakeRedis | None = None) -> IntelligenceCache:
    """Return an IntelligenceCache pre-wired with a fake Redis (or None)."""
    cache = IntelligenceCache()
    cache._redis = fake_redis  # type: ignore[assignment]
    return cache


_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_SAMPLE: dict[str, Any] = {"score": 42, "label": "test"}


# ── key() ─────────────────────────────────────────────────────────────────────


def test_key_format() -> None:
    key = IntelligenceCache.key(_USER_ID, "career_dna")
    assert key == f"pathforge:ic:{_USER_ID}:career_dna"


def test_key_different_endpoints_differ() -> None:
    assert IntelligenceCache.key(_USER_ID, "a") != IntelligenceCache.key(_USER_ID, "b")


def test_key_different_users_differ() -> None:
    other = uuid.UUID("00000000-0000-0000-0000-000000000002")
    assert IntelligenceCache.key(_USER_ID, "x") != IntelligenceCache.key(other, "x")


def test_key_prefix_matches_scan_pattern() -> None:
    """Key prefix must be exactly 'pathforge:ic' so scan_iter can match it."""
    from app.core.intelligence_cache import _KEY_PREFIX
    assert _KEY_PREFIX == "pathforge:ic"
    key = IntelligenceCache.key(_USER_ID, "career_dna")
    assert key.startswith(_KEY_PREFIX + ":")


# ── get() ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_miss_returns_none() -> None:
    cache = _make_cache(_FakeRedis())
    result = await cache.get(IntelligenceCache.key(_USER_ID, "career_dna"))
    assert result is None


@pytest.mark.asyncio
async def test_get_hit_returns_dict() -> None:
    fake = _FakeRedis()
    cache = _make_cache(fake)
    key = IntelligenceCache.key(_USER_ID, "career_dna")
    fake._store[key] = json.dumps(_SAMPLE)

    result = await cache.get(key)
    assert result == _SAMPLE


@pytest.mark.asyncio
async def test_get_hit_empty_dict_is_not_none() -> None:
    """An empty cached dict must return {} not None — callers use `is not None`."""
    fake = _FakeRedis()
    cache = _make_cache(fake)
    key = IntelligenceCache.key(_USER_ID, "career_dna")
    fake._store[key] = json.dumps({})

    result = await cache.get(key)
    assert result is not None
    assert result == {}


@pytest.mark.asyncio
async def test_get_redis_unavailable_returns_none() -> None:
    """_redis is None (Redis never connected) → fail-open → None."""
    cache = IntelligenceCache()
    # _redis stays None; _get_redis() will try to connect and fail
    with patch("app.core.intelligence_cache.resolve_redis_url", side_effect=RuntimeError("no redis")):
        result = await cache.get("any:key")
    assert result is None


@pytest.mark.asyncio
async def test_get_op_error_returns_none() -> None:
    """Redis.get() raises mid-operation → fail-open → None."""
    fake = _FakeRedis()
    fake.get = AsyncMock(side_effect=ConnectionError("lost"))  # type: ignore[method-assign]
    cache = _make_cache(fake)

    result = await cache.get(IntelligenceCache.key(_USER_ID, "x"))
    assert result is None


# ── set() ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_stores_serialized_data() -> None:
    fake = _FakeRedis()
    cache = _make_cache(fake)
    key = IntelligenceCache.key(_USER_ID, "salary")

    await cache.set(key, _SAMPLE, ttl=TTL_SALARY)

    assert json.loads(fake._store[key]) == _SAMPLE
    assert fake._ttls[key] == TTL_SALARY


@pytest.mark.asyncio
async def test_set_applies_correct_ttl_per_type() -> None:
    """Each TTL constant must be wired through to Redis ex parameter."""
    fake = _FakeRedis()
    cache = _make_cache(fake)

    for ttl, endpoint in [
        (TTL_CAREER_DNA, "career_dna"),
        (TTL_THREAT_RADAR, "threat_radar"),
        (TTL_RECOMMENDATIONS, "rec_dashboard"),
        (TTL_SKILL_DECAY, "skill_decay"),
    ]:
        key = IntelligenceCache.key(_USER_ID, endpoint)
        await cache.set(key, _SAMPLE, ttl=ttl)
        assert fake._ttls[key] == ttl, f"TTL mismatch for {endpoint}"


@pytest.mark.asyncio
async def test_set_redis_unavailable_is_noop() -> None:
    cache = IntelligenceCache()
    with patch("app.core.intelligence_cache.resolve_redis_url", side_effect=RuntimeError("no redis")):
        await cache.set("any:key", _SAMPLE, ttl=60)  # must not raise


@pytest.mark.asyncio
async def test_set_op_error_is_noop() -> None:
    fake = _FakeRedis()
    fake.set = AsyncMock(side_effect=ConnectionError("lost"))  # type: ignore[method-assign]
    cache = _make_cache(fake)

    await cache.set(IntelligenceCache.key(_USER_ID, "x"), _SAMPLE, ttl=60)  # must not raise


# ── invalidate_user() ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_user_deletes_all_user_keys() -> None:
    fake = _FakeRedis()
    cache = _make_cache(fake)
    uid = _USER_ID
    other = uuid.UUID("00000000-0000-0000-0000-000000000099")

    # Seed two keys for _USER_ID and one for another user
    for ep in ("career_dna", "salary_dashboard"):
        fake._store[IntelligenceCache.key(uid, ep)] = json.dumps({"x": 1})
    fake._store[IntelligenceCache.key(other, "career_dna")] = json.dumps({"y": 2})

    await cache.invalidate_user(uid)

    assert IntelligenceCache.key(uid, "career_dna") not in fake._store
    assert IntelligenceCache.key(uid, "salary_dashboard") not in fake._store
    assert IntelligenceCache.key(other, "career_dna") in fake._store


@pytest.mark.asyncio
async def test_invalidate_user_no_keys_is_noop() -> None:
    fake = _FakeRedis()
    cache = _make_cache(fake)
    await cache.invalidate_user(_USER_ID)  # must not raise


@pytest.mark.asyncio
async def test_invalidate_user_redis_unavailable_is_noop() -> None:
    cache = IntelligenceCache()
    with patch("app.core.intelligence_cache.resolve_redis_url", side_effect=RuntimeError("no redis")):
        await cache.invalidate_user(_USER_ID)  # must not raise


@pytest.mark.asyncio
async def test_invalidate_user_scan_error_is_noop() -> None:
    fake = _FakeRedis()

    async def _bad_scan_iter(pattern: str):  # type: ignore[override]
        raise ConnectionError("lost")
        yield  # make it a generator

    fake.scan_iter = _bad_scan_iter  # type: ignore[method-assign]
    cache = _make_cache(fake)
    await cache.invalidate_user(_USER_ID)  # must not raise


# ── Round-trip: set → get → invalidate ───────────────────────────────────────


@pytest.mark.asyncio
async def test_roundtrip_set_get_invalidate() -> None:
    fake = _FakeRedis()
    cache = _make_cache(fake)
    key = IntelligenceCache.key(_USER_ID, "career_dna")

    await cache.set(key, _SAMPLE, ttl=TTL_CAREER_DNA)
    hit = await cache.get(key)
    assert hit == _SAMPLE

    await cache.invalidate_user(_USER_ID)
    miss = await cache.get(key)
    assert miss is None


# ── Lazy Redis init ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lazy_redis_reuses_connection() -> None:
    """_get_redis() must return the same object on repeated calls."""
    cache = IntelligenceCache()
    fake = _FakeRedis()

    with patch("app.core.intelligence_cache.resolve_redis_url", return_value="redis://localhost:6379"), \
         patch("app.core.intelligence_cache.aioredis.from_url", return_value=fake):
        r1 = await cache._get_redis()
        r2 = await cache._get_redis()

    assert r1 is r2 is fake


@pytest.mark.asyncio
async def test_get_redis_connect_failure_returns_none() -> None:
    cache = IntelligenceCache()
    with patch("app.core.intelligence_cache.resolve_redis_url", side_effect=ValueError("bad url")):
        r = await cache._get_redis()
    assert r is None


# ── TTL constants ─────────────────────────────────────────────────────────────


def test_ttl_constants() -> None:
    assert TTL_CAREER_DNA == 1800
    assert TTL_THREAT_RADAR == 3600
    assert TTL_SALARY == 3600
    assert TTL_SKILL_DECAY == 3600
    assert TTL_COLLECTIVE == 1800
    assert TTL_RECOMMENDATIONS == 900
    assert TTL_DEFAULT == 1800


def test_cache_class_exposes_ttls() -> None:
    """TTL re-exports on the class must match module-level constants."""
    assert IntelligenceCache.TTL_CAREER_DNA == TTL_CAREER_DNA
    assert IntelligenceCache.TTL_RECOMMENDATIONS == TTL_RECOMMENDATIONS
    assert IntelligenceCache.TTL_SKILL_DECAY == TTL_SKILL_DECAY
