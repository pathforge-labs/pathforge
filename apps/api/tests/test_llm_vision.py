"""Unit tests for complete_vision — retry, cost recording, fallback chain."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.core.llm as llm_module
from app.core.llm import LLMError, LLMTier, complete_vision


def _make_response(content: str = "parsed text", cost: float = 0.0) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    hidden = MagicMock()
    hidden.response_cost = cost
    response._hidden_params = hidden
    response._response_cost = cost  # prevent MagicMock auto-attr returning mock object
    return response


# ── Success path ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_vision_returns_content(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response("extracted text")

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="vision-model"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", AsyncMock(return_value=response))
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock())

    result = await complete_vision(
        image_bytes=b"imgdata",
        image_mime="image/png",
        prompt="What is in this image?",
    )
    assert result == "extracted text"


@pytest.mark.asyncio
async def test_complete_vision_records_cost_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response("text", cost=0.05)

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="vision-model"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", AsyncMock(return_value=response))
    record_cost = AsyncMock()
    monkeypatch.setattr(llm_module, "_record_cost", record_cost)

    await complete_vision(image_bytes=b"img", image_mime="image/jpeg", prompt="describe")

    record_cost.assert_awaited_once_with(0.05)


@pytest.mark.asyncio
async def test_complete_vision_skips_cost_recording_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response("text", cost=0.0)

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="vision-model"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", AsyncMock(return_value=response))
    record_cost = AsyncMock()
    monkeypatch.setattr(llm_module, "_record_cost", record_cost)

    await complete_vision(image_bytes=b"img", image_mime="image/png", prompt="describe")

    record_cost.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_vision_cost_recording_failure_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response("text", cost=0.01)

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="vision-model"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", AsyncMock(return_value=response))
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock(side_effect=RuntimeError("redis down")))

    result = await complete_vision(image_bytes=b"img", image_mime="image/png", prompt="p")
    assert result == "text"


# ── Retry logic ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_vision_retries_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response("ok")
    call_count = {"n": 0}

    async def flaky(*_args: object, **_kwargs: object) -> MagicMock:
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise RuntimeError("transient")
        return response

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="m"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", flaky)
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock())
    monkeypatch.setattr(llm_module.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 2, raising=False)

    result = await complete_vision(image_bytes=b"img", image_mime="image/png", prompt="p")
    assert result == "ok"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_complete_vision_raises_after_all_retries_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="m"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", AsyncMock(side_effect=RuntimeError("down")))
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock())
    monkeypatch.setattr(llm_module.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 1, raising=False)

    with pytest.raises(LLMError, match="all tiers exhausted"):
        await complete_vision(image_bytes=b"img", image_mime="image/png", prompt="p")


@pytest.mark.asyncio
async def test_complete_vision_retry_uses_exponential_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _make_response("ok")
    attempt = {"n": 0}

    async def flaky(*_a: object, **_kw: object) -> MagicMock:
        attempt["n"] += 1
        if attempt["n"] <= 2:
            raise RuntimeError("fail")
        return response

    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", MagicMock(return_value="m"))
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: []})
    monkeypatch.setattr(llm_module.litellm, "acompletion", flaky)
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock())
    monkeypatch.setattr(llm_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 3, raising=False)

    await complete_vision(image_bytes=b"img", image_mime="image/png", prompt="p")

    assert sleep_calls == [1, 2]  # 2**0=1, 2**1=2


# ── Fallback chain ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_vision_falls_back_to_next_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    called_models: list[str] = []
    response = _make_response("fallback result")

    def resolve(tier: LLMTier) -> str:
        return tier.value

    async def selective(*_a: object, **kw: object) -> MagicMock:
        called_models.append(kw["model"])
        if kw["model"] == LLMTier.FAST.value:
            raise RuntimeError("primary down")
        return response

    monkeypatch.setattr(llm_module, "_check_budget", AsyncMock(return_value=0.0))
    monkeypatch.setattr(llm_module, "_check_rpm", MagicMock())
    monkeypatch.setattr(llm_module, "_resolve_model", resolve)
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock())
    monkeypatch.setattr(llm_module, "_FALLBACK_CHAIN", {LLMTier.FAST: [LLMTier.PRIMARY]})
    monkeypatch.setattr(llm_module.litellm, "acompletion", selective)
    monkeypatch.setattr(llm_module, "_record_cost", AsyncMock())
    monkeypatch.setattr(llm_module.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 0, raising=False)

    result = await complete_vision(image_bytes=b"img", image_mime="image/png", prompt="p")
    assert result == "fallback result"
    assert LLMTier.PRIMARY.value in called_models
