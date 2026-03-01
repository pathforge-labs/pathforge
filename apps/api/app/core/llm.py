"""
PathForge AI Engine — LiteLLM Provider Routing
================================================
Tiered multi-provider LLM routing with automatic fallbacks.

Usage:
    from app.core.llm import complete, LLMTier

    result = await complete(
        prompt="Extract skills from this resume...",
        tier=LLMTier.FAST,
    )
"""

from __future__ import annotations

import asyncio
import collections
import enum
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, cast

import litellm
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.llm_observability import (
    TransparencyRecord,
    compute_confidence_score,
    confidence_label,
    get_collector,
)

logger = logging.getLogger(__name__)

# ── Suppress noisy LiteLLM logs in non-debug mode ──────────────
litellm.suppress_debug_info = True
if not settings.debug:
    litellm.set_verbose = False  # type: ignore[attr-defined]


class LLMTier(enum.StrEnum):
    """Model selection tier — maps to config model names."""

    PRIMARY = "primary"
    FAST = "fast"
    DEEP = "deep"


# ── Tier → Model Resolution ────────────────────────────────────

_TIER_MODEL_MAP: dict[LLMTier, str] = {
    LLMTier.PRIMARY: settings.llm_primary_model,
    LLMTier.FAST: settings.llm_fast_model,
    LLMTier.DEEP: settings.llm_deep_model,
}

_FALLBACK_CHAIN: dict[LLMTier, list[LLMTier]] = {
    LLMTier.DEEP: [LLMTier.PRIMARY, LLMTier.FAST],
    LLMTier.PRIMARY: [LLMTier.FAST],
    LLMTier.FAST: [],
}

_TIER_RPM_MAP: dict[LLMTier, int] = {
    LLMTier.PRIMARY: settings.llm_primary_rpm,
    LLMTier.FAST: settings.llm_fast_rpm,
    LLMTier.DEEP: settings.llm_deep_rpm,
}


def _resolve_model(tier: LLMTier) -> str:
    """Resolve a tier to its configured model name."""
    return _TIER_MODEL_MAP[tier]


# ── Budget & Rate Limit Guards (Sprint 29) ─────────────────────


class BudgetExceededError(Exception):
    """Raised when monthly LLM budget is exhausted."""

    def __init__(self, spent: float, budget: float) -> None:
        self.spent = spent
        self.budget = budget
        super().__init__(
            f"Monthly LLM budget exhausted: ${spent:.2f} / ${budget:.2f}"
        )


class RateLimitExceededError(Exception):
    """Raised when per-tier RPM limit is exceeded."""

    def __init__(self, tier: str, rpm: int) -> None:
        self.tier = tier
        self.rpm = rpm
        super().__init__(f"Tier '{tier}' rate limit exceeded: {rpm} RPM")


# Redis-backed monthly budget counter (audit C3)
_budget_redis: aioredis.Redis | None = None


async def _get_budget_redis() -> aioredis.Redis:
    """Lazy Redis connection for budget tracking."""
    global _budget_redis
    if _budget_redis is None:
        _budget_redis = cast(
            aioredis.Redis,
            aioredis.from_url(settings.redis_url, decode_responses=True),  # type: ignore[no-untyped-call]
        )
    return _budget_redis


def _budget_key() -> str:
    """Redis key for current month's LLM cost."""
    month = datetime.now(UTC).strftime("%Y-%m")
    return f"pathforge:llm_cost:{month}"


async def _check_budget() -> float:
    """Check if monthly LLM budget allows another call.

    Returns:
        Current month's spend in USD.

    Raises:
        BudgetExceededError: If budget is exhausted.
    """
    if settings.llm_monthly_budget_usd <= 0:
        return 0.0  # Budget guard disabled

    r = await _get_budget_redis()
    spent_raw = await r.get(_budget_key())
    spent = float(spent_raw) if spent_raw else 0.0

    if spent >= settings.llm_monthly_budget_usd:
        raise BudgetExceededError(spent, settings.llm_monthly_budget_usd)

    return spent


async def _record_cost(response_cost: float) -> None:
    """Increment monthly spend in Redis after a successful LLM call."""
    if response_cost <= 0:
        return

    r = await _get_budget_redis()
    key = _budget_key()
    await r.incrbyfloat(key, response_cost)
    # TTL: 40 days — auto-cleanup after month rolls over
    await r.expire(key, 40 * 86400)


# In-memory sliding window RPM tracker
_rpm_windows: dict[str, collections.deque[float]] = {}


def _check_rpm(tier: LLMTier) -> None:
    """Check if tier's RPM limit allows another call.

    Uses a 60-second sliding window with in-memory timestamps.
    Resets conservatively on restart (safe default).

    Raises:
        RateLimitExceededError: If RPM is exceeded.
    """
    rpm_limit = _TIER_RPM_MAP.get(tier, 60)
    now = time.monotonic()
    window_key = tier.value

    if window_key not in _rpm_windows:
        _rpm_windows[window_key] = collections.deque()

    window = _rpm_windows[window_key]

    # Evict timestamps older than 60 seconds
    while window and (now - window[0]) > 60.0:
        window.popleft()

    if len(window) >= rpm_limit:
        raise RateLimitExceededError(tier.value, rpm_limit)

    window.append(now)


# ── Core Completion Function ───────────────────────────────────

async def complete(
    *,
    prompt: str,
    system_prompt: str = "",
    tier: LLMTier = LLMTier.PRIMARY,
    response_format: dict[str, Any] | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """
    Send a completion request through the tiered LLM routing layer.

    Features:
    - Automatic model selection by tier
    - Fallback chain: Deep → Primary → Fast
    - Retry with exponential backoff (configurable)
    - Structured JSON output via response_format
    - Timeout enforcement
    - Token usage logging

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system-level instructions.
        tier: Which model tier to use (PRIMARY, FAST, DEEP).
        response_format: Optional JSON schema for structured output.
        temperature: Sampling temperature (0.0-1.0). Default 0.1 for determinism.
        max_tokens: Maximum tokens in response.

    Returns:
        The model's response text.

    Raises:
        LLMError: If all tiers in the fallback chain fail.
    """
    tiers_to_try = [tier, *_FALLBACK_CHAIN.get(tier, [])]
    last_error: Exception | None = None

    # Budget check (audit C3) — fail fast before attempting any call
    await _check_budget()

    for attempt_tier in tiers_to_try:
        model = _resolve_model(attempt_tier)
        try:
            # RPM check — per-tier sliding window
            _check_rpm(attempt_tier)

            result = await _call_with_retry(
                model=model,
                tier=attempt_tier.value,
                prompt=prompt,
                system_prompt=system_prompt,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if attempt_tier != tier:
                logger.warning(
                    "LLM fallback activated: %s → %s",
                    tier.value,
                    attempt_tier.value,
                )
            return result
        except Exception as exc:
            last_error = exc
            logger.warning(
                "LLM tier %s (%s) failed: %s. Trying fallback...",
                attempt_tier.value,
                model,
                str(exc)[:200],
            )

    raise LLMError(
        f"All LLM tiers exhausted. Last error: {last_error}"
    ) from last_error


async def complete_json(
    *,
    prompt: str,
    system_prompt: str = "",
    tier: LLMTier = LLMTier.FAST,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """
    Convenience wrapper that requests JSON output and parses it.

    Returns:
        Parsed JSON dict from the model's response.

    Raises:
        LLMError: If the response is not valid JSON after retries.
    """
    raw = await complete(
        prompt=prompt,
        system_prompt=system_prompt,
        tier=tier,
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Strip markdown code fences if present (some models wrap JSON)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (```json and ```)
        cleaned = "\n".join(lines[1:-1]).strip()

    try:
        result: dict[str, Any] = json.loads(cleaned)
        return result
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"LLM returned invalid JSON: {str(exc)[:200]}"
        ) from exc



# ── AI Trust Layer™ — Transparency Wrappers ────────────────────


async def complete_with_transparency(
    *,
    prompt: str,
    system_prompt: str = "",
    tier: LLMTier = LLMTier.PRIMARY,
    response_format: dict[str, Any] | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    analysis_type: str = "",
    data_sources: list[str] | None = None,
) -> tuple[str, TransparencyRecord]:
    """Call complete() and return both the result and transparency metadata.

    This wrapper captures latency, token usage, retry count, and computes
    an algorithmic confidence score — enabling the AI Trust Layer™ to
    show users how and why AI reached its conclusions.

    Args:
        prompt: The user prompt.
        system_prompt: Optional system prompt.
        tier: Which model tier to use.
        response_format: Optional JSON schema for structured output.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in response.
        analysis_type: Human-readable analysis label (e.g., 'career_dna.hidden_skills').
        data_sources: List of data sources feeding this analysis.

    Returns:
        Tuple of (response_text, TransparencyRecord).
    """
    collector = get_collector()
    calls_before = collector._global.total_calls

    start = time.monotonic()
    try:
        result = await complete(
            prompt=prompt,
            system_prompt=system_prompt,
            tier=tier,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed = time.monotonic() - start
        success = True
    except LLMError:
        elapsed = time.monotonic() - start
        success = False
        raise
    finally:
        # Calculate retries from how many new calls the collector tracked
        calls_after = collector._global.total_calls
        retries = max(0, (calls_after - calls_before) - 1)

    # Extract token usage from the collector's latest metrics
    metrics = collector.get_metrics()
    tier_metrics = metrics.get("by_tier", {}).get(tier.value, {})
    prompt_tokens = tier_metrics.get("total_prompt_tokens", 0)
    completion_tokens = tier_metrics.get("total_completion_tokens", 0)

    # Compute confidence
    score = compute_confidence_score(
        tier=tier.value,
        retries=retries,
        latency_seconds=elapsed,
        completion_tokens=completion_tokens,
        max_tokens=max_tokens,
    )

    record = TransparencyRecord(
        analysis_type=analysis_type,
        model=_resolve_model(tier),
        tier=tier.value,
        confidence_score=score,
        confidence_label=confidence_label(score),
        data_sources=data_sources or [],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=int(elapsed * 1000),
        success=success,
        retries=retries,
    )

    return result, record


async def complete_json_with_transparency(
    *,
    prompt: str,
    system_prompt: str = "",
    tier: LLMTier = LLMTier.FAST,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    analysis_type: str = "",
    data_sources: list[str] | None = None,
) -> tuple[dict[str, Any], TransparencyRecord]:
    """Call complete_json() and return both the result and transparency metadata.

    Convenience wrapper for JSON responses with the AI Trust Layer™.

    Args:
        prompt: The user prompt.
        system_prompt: Optional system prompt.
        tier: Which model tier to use.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in response.
        analysis_type: Human-readable analysis label.
        data_sources: List of data sources feeding this analysis.

    Returns:
        Tuple of (parsed_json_dict, TransparencyRecord).
    """
    raw_result, record = await complete_with_transparency(
        prompt=prompt,
        system_prompt=system_prompt,
        tier=tier,
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
        analysis_type=analysis_type,
        data_sources=data_sources,
    )

    # Strip markdown code fences if present
    cleaned = raw_result.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]).strip()

    try:
        parsed: dict[str, Any] = json.loads(cleaned)
        return parsed, record
    except json.JSONDecodeError as exc:
        raise LLMError(
            f"LLM returned invalid JSON: {str(exc)[:200]}"
        ) from exc


# ── Internal Retry Logic ───────────────────────────────────────

async def _call_with_retry(
    *,
    model: str,
    tier: str,
    prompt: str,
    system_prompt: str,
    response_format: dict[str, Any] | None,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call LiteLLM with exponential backoff retries."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_error: Exception | None = None
    max_retries = settings.llm_max_retries

    for attempt in range(max_retries + 1):
        try:
            start = time.monotonic()

            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": settings.llm_timeout,
            }
            if response_format is not None:
                kwargs["response_format"] = response_format

            response = await litellm.acompletion(**kwargs)
            elapsed = time.monotonic() - start

            # Extract response text
            content = response.choices[0].message.content or ""

            # Log usage + record metrics
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0

            if usage:
                logger.info(
                    "LLM [%s] %d prompt + %d completion tokens, %.2fs",
                    model,
                    prompt_tokens,
                    completion_tokens,
                    elapsed,
                )
            else:
                logger.info("LLM [%s] completed in %.2fs", model, elapsed)

            # Record success metrics
            get_collector().record_call(
                model=model,
                tier=tier,
                latency_seconds=elapsed,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                success=True,
            )

            # Record cost in Redis (audit C3)
            response_cost = getattr(
                getattr(response, "_hidden_params", None),
                "response_cost", 0.0
            )
            if not response_cost:
                # Fallback: estimate from litellm cost tracker
                response_cost = getattr(response, "_response_cost", 0.0) or 0.0
            if response_cost > 0:
                try:
                    await _record_cost(response_cost)
                except Exception:
                    logger.warning("Failed to record LLM cost in Redis")

            return content

        except Exception as exc:
            elapsed = time.monotonic() - start
            last_error = exc

            # Record failure metrics
            get_collector().record_call(
                model=model,
                tier=tier,
                latency_seconds=elapsed,
                success=False,
                error_type=type(exc).__name__,
            )

            if attempt < max_retries:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "LLM retry %d/%d for %s after error: %s (wait %ds)",
                    attempt + 1,
                    max_retries,
                    model,
                    str(exc)[:100],
                    wait,
                )
                await asyncio.sleep(wait)

    raise last_error  # type: ignore[misc]


# ── Custom Exceptions ──────────────────────────────────────────

class LLMError(Exception):
    """Raised when LLM completion fails after all retries and fallbacks."""
