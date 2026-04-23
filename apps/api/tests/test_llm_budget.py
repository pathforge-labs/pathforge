"""Unit tests for llm.py budget, rate-limit, and error helpers — no LLM calls."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.core.llm as llm_module
from app.core.llm import (
    BudgetExceededError,
    LLMTier,
    RateLimitExceededError,
    _budget_key,
    _check_budget,
    _check_rpm,
    _record_cost,
    _reset_budget_redis_for_tests,
)

# ── BudgetExceededError ───────────────────────────────────────────────────────

def test_budget_exceeded_error_message():
    exc = BudgetExceededError(spent=45.50, budget=50.0)
    assert exc.spent == 45.50
    assert exc.budget == 50.0
    assert "45.50" in str(exc)
    assert "50.00" in str(exc)


def test_budget_exceeded_error_is_exception():
    exc = BudgetExceededError(0.0, 1.0)
    assert isinstance(exc, Exception)


# ── RateLimitExceededError ────────────────────────────────────────────────────

def test_rate_limit_exceeded_error_message():
    exc = RateLimitExceededError(tier="primary", rpm=60)
    assert exc.tier == "primary"
    assert exc.rpm == 60
    assert "primary" in str(exc)
    assert "60" in str(exc)


def test_rate_limit_exceeded_error_is_exception():
    exc = RateLimitExceededError("fast", 120)
    assert isinstance(exc, Exception)


# ── _budget_key ───────────────────────────────────────────────────────────────

def test_budget_key_format():
    key = _budget_key()
    assert key.startswith("pathforge:llm_cost:")
    # Format: pathforge:llm_cost:YYYY-MM
    parts = key.split(":")
    assert len(parts) == 3
    date_part = parts[2]
    assert len(date_part) == 7  # YYYY-MM
    assert "-" in date_part


def test_budget_key_consistent_in_same_second():
    k1 = _budget_key()
    k2 = _budget_key()
    assert k1 == k2


# ── _reset_budget_redis_for_tests ─────────────────────────────────────────────

def test_reset_budget_redis_for_tests_clears_global():
    # Set a fake redis first
    llm_module._budget_redis = MagicMock()  # type: ignore[assignment]
    _reset_budget_redis_for_tests()
    assert llm_module._budget_redis is None


# ── _check_budget: budget disabled ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_budget_disabled_when_budget_zero(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 0, raising=False)

    spent = await _check_budget()
    assert spent == 0.0


@pytest.mark.asyncio
async def test_check_budget_disabled_when_budget_negative(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", -1, raising=False)

    spent = await _check_budget()
    assert spent == 0.0


# ── _check_budget: Redis unavailable (fail-open) ──────────────────────────────

@pytest.mark.asyncio
async def test_check_budget_redis_unavailable_fail_open(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 100.0, raising=False)
    monkeypatch.setattr(llm_module, "_budget_redis", None, raising=False)

    async def _failing_redis():
        raise ConnectionError("Redis down")

    monkeypatch.setattr(llm_module, "_get_budget_redis", _failing_redis)

    spent = await _check_budget()
    assert spent == 0.0  # fail-open


# ── _check_budget: within budget ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_budget_within_budget(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 100.0, raising=False)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="30.0")

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    spent = await _check_budget()
    assert spent == 30.0


@pytest.mark.asyncio
async def test_check_budget_no_existing_spend(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 100.0, raising=False)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # no key yet

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    spent = await _check_budget()
    assert spent == 0.0


# ── _check_budget: budget exceeded ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_budget_exceeded_raises(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 50.0, raising=False)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="55.0")

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    with pytest.raises(BudgetExceededError) as exc_info:
        await _check_budget()

    assert exc_info.value.spent == 55.0
    assert exc_info.value.budget == 50.0


# ── _check_budget: 80% alert path ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_budget_80pct_alert_new_key(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 100.0, raising=False)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="85.0")  # 85% → triggers alert
    mock_redis.exists = AsyncMock(return_value=0)   # alert key not set yet
    mock_redis.set = AsyncMock(return_value=True)

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    spent = await _check_budget()
    assert spent == 85.0
    mock_redis.set.assert_called_once()  # alert key created


@pytest.mark.asyncio
async def test_check_budget_80pct_alert_already_sent(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 100.0, raising=False)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="85.0")
    mock_redis.exists = AsyncMock(return_value=1)  # alert already sent
    mock_redis.set = AsyncMock(return_value=True)

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    spent = await _check_budget()
    assert spent == 85.0
    mock_redis.set.assert_not_called()  # alert NOT re-sent


@pytest.mark.asyncio
async def test_check_budget_80pct_alert_redis_error_suppressed(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_monthly_budget_usd", 100.0, raising=False)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="85.0")
    mock_redis.exists = AsyncMock(side_effect=ConnectionError("Redis blip"))

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    # Should NOT raise — Redis error in alert path is suppressed
    spent = await _check_budget()
    assert spent == 85.0


# ── _record_cost ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_cost_zero_skips_redis(monkeypatch: pytest.MonkeyPatch):
    mock_redis = AsyncMock()
    mock_redis.incrbyfloat = AsyncMock()

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    await _record_cost(0.0)
    mock_redis.incrbyfloat.assert_not_called()


@pytest.mark.asyncio
async def test_record_cost_negative_skips_redis(monkeypatch: pytest.MonkeyPatch):
    mock_redis = AsyncMock()
    mock_redis.incrbyfloat = AsyncMock()

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    await _record_cost(-0.5)
    mock_redis.incrbyfloat.assert_not_called()


@pytest.mark.asyncio
async def test_record_cost_positive_calls_redis(monkeypatch: pytest.MonkeyPatch):
    mock_redis = AsyncMock()
    mock_redis.incrbyfloat = AsyncMock(return_value=1.5)
    mock_redis.expire = AsyncMock(return_value=True)

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    await _record_cost(1.5)
    mock_redis.incrbyfloat.assert_called_once()
    mock_redis.expire.assert_called_once()


# ── _check_rpm ────────────────────────────────────────────────────────────────

def test_check_rpm_new_window_allows_call():
    # Clear any state from previous tests
    llm_module._rpm_windows.pop(LLMTier.FAST.value, None)
    # Should not raise
    _check_rpm(LLMTier.FAST)


def test_check_rpm_within_limit_allows_call():
    llm_module._rpm_windows.pop(LLMTier.FAST.value, None)
    # Make several calls within the limit
    for _ in range(3):
        _check_rpm(LLMTier.FAST)


def test_check_rpm_exceeded_raises():
    from app.core.config import settings

    tier = LLMTier.FAST
    rpm = settings.llm_fast_rpm
    llm_module._rpm_windows.pop(tier.value, None)

    # Fill the window to the limit
    import collections
    now = time.monotonic()
    llm_module._rpm_windows[tier.value] = collections.deque(
        [now] * rpm
    )

    with pytest.raises(RateLimitExceededError):
        _check_rpm(tier)


def test_check_rpm_evicts_old_timestamps():
    import collections

    tier = LLMTier.PRIMARY
    llm_module._rpm_windows.pop(tier.value, None)

    # Add old timestamps (>60 seconds ago)
    old = time.monotonic() - 120.0
    llm_module._rpm_windows[tier.value] = collections.deque([old] * 5)

    # Should not raise — old timestamps evicted
    _check_rpm(tier)
    # Window should be size 1 (just the new call added)
    assert len(llm_module._rpm_windows[tier.value]) == 1
