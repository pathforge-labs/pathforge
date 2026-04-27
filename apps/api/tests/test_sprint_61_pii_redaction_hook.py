"""
PathForge — Sprint 61 ``_register_pii_redaction_hook`` coverage
================================================================

Closes the last sizeable uncovered region of
``app/core/llm_observability.py`` (lines 881-929 — the LiteLLM
``input_callback`` registration that protects Langfuse traces from
PII leakage).

Why this needs custom-shaped tests
----------------------------------

The hook is a LiteLLM-side effect: it imports the SDK, wraps any
existing ``litellm.input_callback`` in a closure, and re-installs the
list. The pre-existing observability tests patch ``sys.modules`` to
inject a fake ``litellm`` so they can exercise
``initialize_observability`` without the real SDK; we extend the same
pattern to **pull the registered closure back out of the fake** and
drive it directly with synthetic kwargs.

Branches covered (the function's whole 24-line decision tree):

  1. Registration replaces ``litellm.input_callback`` with a single
     callable.
  2. The closure preserves the original ``input_callback`` when one
     was set (chained call).
  3. The closure does **not** chain when no original was set (the
     ``getattr(..., "input_callback", None)`` arm).
  4. ``messages`` redacted on a **deep copy** (the original list is
     left untouched — Sprint 39 audit A-H3 invariant).
  5. ``messages`` absent from kwargs → skipped (no key error).
  6. ``messages`` non-list → skipped (defensive type guard).
  7. ``content`` non-string → skipped (mixed-type message handling).
  8. ``litellm_params`` absent from kwargs → metadata flag still set
     on the per-call dict (the empty-dict default branch).
  9. ``litellm_params.metadata`` already populated → flag merged in
     without trampling pre-existing keys.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# Helpers — install the fake ``litellm`` module + run the registrar
# ─────────────────────────────────────────────────────────────────


def _install_fake_litellm(
    *,
    original_input_callback: Any = None,
) -> MagicMock:
    """Build a fake ``litellm`` whose ``input_callback`` matches the
    requested initial state (LiteLLM 1.x stores a single callable or
    ``None``)."""
    fake = MagicMock()
    fake.input_callback = original_input_callback
    return fake


@contextmanager
def _registered_closure(
    fake: MagicMock,
    *,
    redactor: Callable[[str], str] | None = None,
) -> Any:
    """Context manager that installs the fake LiteLLM, optionally
    swaps in a synthetic ``redact_pii``, runs the registrar, and
    yields the installed closure.

    The redactor must be patched *before* registration because the
    closure does ``from app.core.pii_redactor import redact_pii``
    inside the registrar — once installed, the closure holds the
    captured reference and a later ``patch`` would not reach it.
    """
    from app.core import llm_observability

    redactor_target = redactor or (lambda text: f"<redacted:{text[:8]}>")
    with (
        patch.dict("sys.modules", {"litellm": fake}),
        patch("app.core.pii_redactor.redact_pii", side_effect=redactor_target),
    ):
        llm_observability._register_pii_redaction_hook()
        assert isinstance(fake.input_callback, list)
        assert len(fake.input_callback) == 1
        yield fake.input_callback[0]


# ─────────────────────────────────────────────────────────────────
# 1. Registration shape
# ─────────────────────────────────────────────────────────────────


class TestRegistration:
    async def test_registers_single_callable_on_input_callback(self) -> None:
        fake = _install_fake_litellm()
        with _registered_closure(fake) as closure:
            assert callable(closure)


# ─────────────────────────────────────────────────────────────────
# 2. Redaction semantics
# ─────────────────────────────────────────────────────────────────


class TestRedactionSemantics:
    async def test_messages_are_deep_copied_before_redaction(self) -> None:
        """The original list passed in by LiteLLM must remain
        untouched (Sprint 39 audit A-H3). Pre-fix, the closure
        mutated ``kwargs["messages"]`` in place — meaning if a
        future LiteLLM stopped passing a copy, the upstream LLM
        provider would receive the redacted text and resume parsing
        would degrade silently."""
        fake = _install_fake_litellm()
        original = [
            {"role": "user", "content": "email me at jane@example.com"},
        ]
        kwargs: dict[str, Any] = {"messages": original}
        with _registered_closure(
            fake, redactor=lambda _text: "REDACTED",
        ) as closure:
            closure("model-x", original, kwargs)

        # Sentinel: the *original* list still has the unredacted text.
        assert original[0]["content"] == "email me at jane@example.com"
        # The kwargs got a *new* list with the redacted content.
        assert kwargs["messages"] is not original
        assert kwargs["messages"][0]["content"] == "REDACTED"

    async def test_skips_when_messages_absent(self) -> None:
        fake = _install_fake_litellm()
        kwargs: dict[str, Any] = {}  # no "messages"

        def _no_redactor(_text: str) -> str:
            raise AssertionError("must not be called")

        with _registered_closure(
            fake, redactor=_no_redactor,
        ) as closure:
            closure("model-x", [], kwargs)
        # Reached here without raising → the type guard worked.

    async def test_skips_when_messages_is_not_a_list(self) -> None:
        fake = _install_fake_litellm()
        kwargs: dict[str, Any] = {"messages": "not-a-list"}

        def _no_redactor(_text: str) -> str:
            raise AssertionError("must not be called")

        with _registered_closure(
            fake, redactor=_no_redactor,
        ) as closure:
            closure("model-x", [], kwargs)

    async def test_skips_messages_with_non_string_content(self) -> None:
        """Vision payloads use list-of-parts content. The redactor
        only handles ``str``; the closure must skip non-string
        ``content`` entries rather than raise."""
        fake = _install_fake_litellm()
        kwargs: dict[str, Any] = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "hi"}]},
                {"role": "user"},  # no "content" key at all
            ],
        }

        def _no_redactor(_text: str) -> str:
            raise AssertionError("must not be called")

        with _registered_closure(
            fake, redactor=_no_redactor,
        ) as closure:
            closure("model-x", [], kwargs)
        # ``messages`` got deep-copied (different list identity)
        # but the inner shape is preserved.
        assert kwargs["messages"][0]["content"] == [
            {"type": "text", "text": "hi"},
        ]

    async def test_redacts_only_string_content(self) -> None:
        """Mixed: one string-content message + one list-content."""
        fake = _install_fake_litellm()
        kwargs: dict[str, Any] = {
            "messages": [
                {"role": "user", "content": "phone 555-0100"},
                {"role": "user", "content": [{"type": "text", "text": "hi"}]},
            ],
        }
        with _registered_closure(
            fake, redactor=lambda _text: "<scrubbed>",
        ) as closure:
            closure("model-x", [], kwargs)
        assert kwargs["messages"][0]["content"] == "<scrubbed>"
        # Non-string content untouched.
        assert kwargs["messages"][1]["content"] == [
            {"type": "text", "text": "hi"},
        ]


# ─────────────────────────────────────────────────────────────────
# 3. Metadata flag
# ─────────────────────────────────────────────────────────────────


class TestMetadataFlag:
    async def test_metadata_flag_set_when_litellm_params_present(self) -> None:
        fake = _install_fake_litellm()
        existing_meta = {"trace_id": "abc-123"}
        kwargs: dict[str, Any] = {
            "messages": [],
            "litellm_params": {"metadata": existing_meta},
        }
        with _registered_closure(fake) as closure:
            closure("model-x", [], kwargs)
        # Pre-existing metadata keys preserved + flag merged.
        assert existing_meta["trace_id"] == "abc-123"
        assert existing_meta["pii_redacted"] is True

    async def test_metadata_flag_runs_when_litellm_params_absent(self) -> None:
        """The default-empty-dict arm: if ``litellm_params`` is
        missing the line still executes, just on a throwaway dict.
        We assert the closure does not raise."""
        fake = _install_fake_litellm()
        kwargs: dict[str, Any] = {"messages": []}
        with _registered_closure(fake) as closure:
            closure("model-x", [], kwargs)
        # No exception → branch covered.


# ─────────────────────────────────────────────────────────────────
# 4. Original-callback chaining
# ─────────────────────────────────────────────────────────────────


class TestOriginalCallbackChaining:
    async def test_chains_to_existing_input_callback_when_present(self) -> None:
        original = MagicMock()
        fake = _install_fake_litellm(original_input_callback=original)
        kwargs: dict[str, Any] = {"messages": []}
        with _registered_closure(fake) as closure:
            closure("model-x", [], kwargs)
        original.assert_called_once_with("model-x", [], kwargs)

    async def test_no_chain_when_no_original_input_callback(self) -> None:
        fake = _install_fake_litellm(original_input_callback=None)
        kwargs: dict[str, Any] = {"messages": []}
        # The closure should run cleanly with no ``original_input_hook``
        # in scope. We only assert no exception.
        with _registered_closure(fake) as closure:
            closure("model-x", [], kwargs)

    async def test_non_callable_original_is_skipped(self) -> None:
        """Some LiteLLM versions store a *list* on ``input_callback``;
        the registrar's ``callable(original_input_hook)`` guard
        protects against trying to invoke a list. We pass an int —
        a definitely-non-callable sentinel — and assert the closure
        runs without TypeError."""
        fake = _install_fake_litellm(original_input_callback=42)
        kwargs: dict[str, Any] = {"messages": []}
        with _registered_closure(fake) as closure:
            closure("model-x", [], kwargs)
