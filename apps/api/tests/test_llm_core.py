"""Comprehensive tests for app.core.llm — covers complete(), complete_json(),
complete_with_transparency(), complete_json_with_transparency(), complete_vision(),
LLMTier, LLMError, budget guard, and RPM guard.

Mocks ``app.core.llm.litellm.acompletion`` to avoid real API calls.
"""

from __future__ import annotations

import base64
import collections
import json
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

import app.core.llm as llm_module
from app.core.llm import (
    BudgetExceededError,
    LLMError,
    LLMTier,
    RateLimitExceededError,
    _check_budget,
    _check_rpm,
    complete,
    complete_json,
    complete_json_with_transparency,
    complete_vision,
    complete_with_transparency,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_response(
    content: str,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    response_cost: float = 0.0,
) -> SimpleNamespace:
    """Build a fake litellm.acompletion response shaped like openai's."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            ),
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
        _hidden_params=SimpleNamespace(response_cost=response_cost),
    )


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch):
    """Reset RPM windows and disable the monthly budget check by default."""
    llm_module._rpm_windows.clear()
    monkeypatch.setattr(
        llm_module.settings, "llm_monthly_budget_usd", 0, raising=False
    )
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 0, raising=False)
    monkeypatch.setattr(llm_module.settings, "llm_timeout", 30, raising=False)
    yield
    llm_module._rpm_windows.clear()


# ── LLMTier enum ──────────────────────────────────────────────────────────────


def test_llm_tier_primary_exists():
    assert LLMTier.PRIMARY.value == "primary"


def test_llm_tier_fast_exists():
    assert LLMTier.FAST.value == "fast"


def test_llm_tier_deep_exists():
    assert LLMTier.DEEP.value == "deep"


def test_llm_tier_is_str_enum():
    # StrEnum members should compare to their string value
    assert LLMTier.FAST == "fast"


def test_llm_tier_membership():
    values = {t.value for t in LLMTier}
    assert values == {"primary", "fast", "deep"}


# ── LLMError ──────────────────────────────────────────────────────────────────


def test_llm_error_is_exception_subclass():
    assert issubclass(LLMError, Exception)


def test_llm_error_raises_with_message():
    with pytest.raises(LLMError, match="boom"):
        raise LLMError("boom")


def test_budget_exceeded_error_is_exception():
    assert isinstance(BudgetExceededError(1.0, 2.0), Exception)


def test_rate_limit_exceeded_error_is_exception():
    assert isinstance(RateLimitExceededError("fast", 10), Exception)


# ── Budget guard ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_budget_disabled_returns_zero(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        llm_module.settings, "llm_monthly_budget_usd", 0, raising=False
    )
    assert await _check_budget() == 0.0


@pytest.mark.asyncio
async def test_check_budget_raises_when_exceeded(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        llm_module.settings, "llm_monthly_budget_usd", 10.0, raising=False
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="99.0")

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    with pytest.raises(BudgetExceededError):
        await _check_budget()


@pytest.mark.asyncio
async def test_complete_raises_llm_error_when_budget_exceeded(
    monkeypatch: pytest.MonkeyPatch,
):
    """complete() wraps the budget error — it propagates BudgetExceededError directly."""
    monkeypatch.setattr(
        llm_module.settings, "llm_monthly_budget_usd", 10.0, raising=False
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="99.0")

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    with pytest.raises(BudgetExceededError):
        await complete(prompt="hi")


# ── RPM guard ─────────────────────────────────────────────────────────────────


def test_check_rpm_raises_when_limit_hit(monkeypatch: pytest.MonkeyPatch):
    tier = LLMTier.FAST
    rpm = llm_module._TIER_RPM_MAP[tier]
    now = time.monotonic()
    llm_module._rpm_windows[tier.value] = collections.deque([now] * rpm)

    with pytest.raises(RateLimitExceededError):
        _check_rpm(tier)


def test_check_rpm_allows_under_limit():
    # Fresh state from fixture — should not raise
    _check_rpm(LLMTier.FAST)
    assert len(llm_module._rpm_windows[LLMTier.FAST.value]) == 1


# ── complete(): happy path ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_returns_text_from_mock_response():
    fake_response = _make_response("Hello world")

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete(prompt="Say hi")

    assert result == "Hello world"


@pytest.mark.asyncio
async def test_complete_uses_system_prompt():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="hello", system_prompt="be terse")

    kwargs = mock.call_args.kwargs
    messages = kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "be terse"}
    assert messages[1] == {"role": "user", "content": "hello"}


@pytest.mark.asyncio
async def test_complete_omits_system_when_blank():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="hello")

    messages = mock.call_args.kwargs["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


@pytest.mark.asyncio
async def test_complete_passes_response_format():
    fake_response = _make_response('{"a":1}')
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(
            prompt="json please",
            response_format={"type": "json_object"},
        )

    assert mock.call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_complete_passes_temperature_and_max_tokens():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="x", temperature=0.7, max_tokens=128)

    kwargs = mock.call_args.kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_tokens"] == 128


@pytest.mark.asyncio
async def test_complete_none_content_returns_empty_string():
    fake_response = _make_response(None)  # type: ignore[arg-type]

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete(prompt="x")

    assert result == ""


# ── complete(): different tiers ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_primary_tier_uses_primary_model():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="x", tier=LLMTier.PRIMARY)

    assert mock.call_args.kwargs["model"] == llm_module.settings.llm_primary_model


@pytest.mark.asyncio
async def test_complete_fast_tier_uses_fast_model():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="x", tier=LLMTier.FAST)

    assert mock.call_args.kwargs["model"] == llm_module.settings.llm_fast_model


@pytest.mark.asyncio
async def test_complete_deep_tier_uses_deep_model():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="x", tier=LLMTier.DEEP)

    assert mock.call_args.kwargs["model"] == llm_module.settings.llm_deep_model


# ── complete(): fallback + error handling ─────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_all_tiers_fail_raises_llm_error():
    mock = AsyncMock(side_effect=RuntimeError("provider down"))

    with (
        patch("app.core.llm.litellm.acompletion", new=mock),
        pytest.raises(LLMError, match="All LLM tiers exhausted"),
    ):
        await complete(prompt="x", tier=LLMTier.FAST)


@pytest.mark.asyncio
async def test_complete_fallback_recovers_from_first_tier_failure():
    """DEEP tier fails, falls back to PRIMARY which succeeds."""
    call_count = {"n": 0}

    async def _flaky(*args: Any, **kwargs: Any) -> SimpleNamespace:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("deep is down")
        return _make_response("fallback ok")

    with patch("app.core.llm.litellm.acompletion", new=_flaky):
        result = await complete(prompt="x", tier=LLMTier.DEEP)

    assert result == "fallback ok"
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_complete_wraps_litellm_exception_as_llm_error():
    mock = AsyncMock(side_effect=ValueError("bad model"))

    with (
        patch("app.core.llm.litellm.acompletion", new=mock),
        pytest.raises(LLMError),
    ):
        await complete(prompt="x", tier=LLMTier.FAST)


@pytest.mark.asyncio
async def test_complete_fast_tier_no_fallback_chain():
    """FAST has no fallbacks — single failure → LLMError immediately."""
    mock = AsyncMock(side_effect=RuntimeError("fail"))

    with (
        patch("app.core.llm.litellm.acompletion", new=mock),
        pytest.raises(LLMError),
    ):
        await complete(prompt="x", tier=LLMTier.FAST)

    assert mock.call_count == 1


# ── complete_json(): happy path + parsing ─────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_json_parses_valid_json():
    fake_response = _make_response('{"name": "Claude", "ok": true}')

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete_json(prompt="json please")

    assert result == {"name": "Claude", "ok": True}


@pytest.mark.asyncio
async def test_complete_json_strips_markdown_code_fences():
    raw = '```json\n{"key": "value"}\n```'
    fake_response = _make_response(raw)

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete_json(prompt="x")

    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_complete_json_strips_plain_code_fences():
    raw = '```\n{"a": 1}\n```'
    fake_response = _make_response(raw)

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete_json(prompt="x")

    assert result == {"a": 1}


@pytest.mark.asyncio
async def test_complete_json_invalid_json_raises_llm_error():
    fake_response = _make_response("not json at all")

    with (
        patch(
            "app.core.llm.litellm.acompletion",
            new=AsyncMock(return_value=fake_response),
        ),
        pytest.raises(LLMError, match="invalid JSON"),
    ):
        await complete_json(prompt="x")


@pytest.mark.asyncio
async def test_complete_json_sets_json_response_format():
    fake_response = _make_response('{"ok": 1}')
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_json(prompt="x")

    assert mock.call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_complete_json_default_tier_is_fast():
    fake_response = _make_response('{"ok": 1}')
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_json(prompt="x")

    assert mock.call_args.kwargs["model"] == llm_module.settings.llm_fast_model


# ── complete_with_transparency ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_with_transparency_returns_tuple():
    fake_response = _make_response("hi", prompt_tokens=7, completion_tokens=3)

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result, record = await complete_with_transparency(
            prompt="x",
            tier=LLMTier.FAST,
            analysis_type="unit_test",
            data_sources=["source_a"],
        )

    assert result == "hi"
    assert record.analysis_type == "unit_test"
    assert record.tier == "fast"
    assert record.success is True
    assert record.data_sources == ["source_a"]
    assert 0.0 <= record.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_complete_with_transparency_sets_model_name():
    fake_response = _make_response("ok")

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        _result, record = await complete_with_transparency(
            prompt="x", tier=LLMTier.FAST
        )

    assert record.model == llm_module.settings.llm_fast_model


@pytest.mark.asyncio
async def test_complete_with_transparency_failure_reraises_llm_error():
    mock = AsyncMock(side_effect=RuntimeError("boom"))

    with (
        patch("app.core.llm.litellm.acompletion", new=mock),
        pytest.raises(LLMError),
    ):
        await complete_with_transparency(
            prompt="x", tier=LLMTier.FAST, analysis_type="t"
        )


# ── complete_json_with_transparency ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_json_with_transparency_returns_tuple():
    fake_response = _make_response('{"answer": 42}')

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        data, record = await complete_json_with_transparency(
            prompt="x",
            tier=LLMTier.FAST,
            analysis_type="json_test",
        )

    assert data == {"answer": 42}
    assert record.analysis_type == "json_test"
    assert record.tier == "fast"


@pytest.mark.asyncio
async def test_complete_json_with_transparency_strips_fences():
    fake_response = _make_response('```json\n{"x": 1}\n```')

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        data, _record = await complete_json_with_transparency(prompt="x")

    assert data == {"x": 1}


@pytest.mark.asyncio
async def test_complete_json_with_transparency_invalid_json_raises():
    fake_response = _make_response("definitely not JSON")

    with (
        patch(
            "app.core.llm.litellm.acompletion",
            new=AsyncMock(return_value=fake_response),
        ),
        pytest.raises(LLMError, match="invalid JSON"),
    ):
        await complete_json_with_transparency(prompt="x")


@pytest.mark.asyncio
async def test_complete_json_with_transparency_uses_json_response_format():
    fake_response = _make_response('{"ok": 1}')
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_json_with_transparency(prompt="x")

    assert mock.call_args.kwargs["response_format"] == {"type": "json_object"}


# ── complete_vision ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_vision_happy_path():
    fake_response = _make_response("I see a cat")
    image_bytes = b"\x89PNG\r\n\x1a\nfakepngdata"

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete_vision(
            image_bytes=image_bytes,
            image_mime="image/png",
            prompt="What's in this image?",
        )

    assert result == "I see a cat"


@pytest.mark.asyncio
async def test_complete_vision_uses_multimodal_message_format():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)
    image_bytes = b"fakejpegbytes"
    expected_b64 = base64.b64encode(image_bytes).decode("ascii")

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_vision(
            image_bytes=image_bytes,
            image_mime="image/jpeg",
            prompt="describe",
        )

    messages = mock.call_args.kwargs["messages"]
    # Single user message — no system prompt provided
    assert len(messages) == 1
    user_msg = messages[0]
    assert user_msg["role"] == "user"
    content = user_msg["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"] == (
        f"data:image/jpeg;base64,{expected_b64}"
    )
    assert content[1] == {"type": "text", "text": "describe"}


@pytest.mark.asyncio
async def test_complete_vision_includes_system_prompt_when_provided():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_vision(
            image_bytes=b"x",
            image_mime="image/png",
            prompt="describe",
            system_prompt="You are a vision model",
        )

    messages = mock.call_args.kwargs["messages"]
    assert len(messages) == 2
    assert messages[0] == {
        "role": "system",
        "content": "You are a vision model",
    }
    assert messages[1]["role"] == "user"


@pytest.mark.asyncio
async def test_complete_vision_uses_fast_tier_by_default():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_vision(
            image_bytes=b"x",
            image_mime="image/png",
            prompt="p",
        )

    assert mock.call_args.kwargs["model"] == llm_module.settings.llm_fast_model


@pytest.mark.asyncio
async def test_complete_vision_all_tiers_fail_raises_llm_error():
    mock = AsyncMock(side_effect=RuntimeError("vision down"))

    with (
        patch("app.core.llm.litellm.acompletion", new=mock),
        pytest.raises(LLMError, match="Vision LLM"),
    ):
        await complete_vision(
            image_bytes=b"x",
            image_mime="image/png",
            prompt="p",
            tier=LLMTier.FAST,
        )


@pytest.mark.asyncio
async def test_complete_vision_fallback_chain_recovers():
    """DEEP tier fails → PRIMARY succeeds on fallback."""
    call_count = {"n": 0}

    async def _flaky(*args: Any, **kwargs: Any) -> SimpleNamespace:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("deep is down")
        return _make_response("vision fallback ok")

    with patch("app.core.llm.litellm.acompletion", new=_flaky):
        result = await complete_vision(
            image_bytes=b"x",
            image_mime="image/png",
            prompt="p",
            tier=LLMTier.DEEP,
        )

    assert result == "vision fallback ok"
    assert call_count["n"] >= 2


@pytest.mark.asyncio
async def test_complete_vision_respects_budget_guard(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        llm_module.settings, "llm_monthly_budget_usd", 10.0, raising=False
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="99.0")

    async def _fake_redis():
        return mock_redis

    monkeypatch.setattr(llm_module, "_get_budget_redis", _fake_redis)

    with pytest.raises(BudgetExceededError):
        await complete_vision(
            image_bytes=b"x",
            image_mime="image/png",
            prompt="p",
        )


@pytest.mark.asyncio
async def test_complete_vision_base64_encodes_bytes_correctly():
    """Verify the image bytes are base64-encoded — not raw — in the data URL."""
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)
    raw = b"\x00\x01\x02\xff\xfe"

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete_vision(
            image_bytes=raw, image_mime="image/png", prompt="p"
        )

    url = mock.call_args.kwargs["messages"][0]["content"][0]["image_url"]["url"]
    # Decode the data URL payload and verify it matches
    payload = url.split(",", 1)[1]
    assert base64.b64decode(payload) == raw


# ── JSON decoding edge cases ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_json_handles_whitespace_padded_response():
    fake_response = _make_response('   \n{"ok": true}\n   ')

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete_json(prompt="x")

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_complete_json_handles_nested_objects():
    payload = {"a": {"b": [1, 2, 3]}, "c": None}
    fake_response = _make_response(json.dumps(payload))

    with patch(
        "app.core.llm.litellm.acompletion",
        new=AsyncMock(return_value=fake_response),
    ):
        result = await complete_json(prompt="x")

    assert result == payload


# ── Message construction ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_includes_timeout_in_kwargs():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="x")

    assert "timeout" in mock.call_args.kwargs


@pytest.mark.asyncio
async def test_complete_no_response_format_omits_key():
    fake_response = _make_response("ok")
    mock = AsyncMock(return_value=fake_response)

    with patch("app.core.llm.litellm.acompletion", new=mock):
        await complete(prompt="x")

    assert "response_format" not in mock.call_args.kwargs


# ── Miscellaneous invariants ──────────────────────────────────────────────────


def test_tier_model_map_populated():
    assert LLMTier.PRIMARY in llm_module._TIER_MODEL_MAP
    assert LLMTier.FAST in llm_module._TIER_MODEL_MAP
    assert LLMTier.DEEP in llm_module._TIER_MODEL_MAP


def test_fallback_chain_well_formed():
    assert llm_module._FALLBACK_CHAIN[LLMTier.FAST] == []
    assert LLMTier.FAST in llm_module._FALLBACK_CHAIN[LLMTier.PRIMARY]
    assert LLMTier.PRIMARY in llm_module._FALLBACK_CHAIN[LLMTier.DEEP]


def test_resolve_model_returns_configured_name():
    assert (
        llm_module._resolve_model(LLMTier.PRIMARY)
        == llm_module.settings.llm_primary_model
    )
