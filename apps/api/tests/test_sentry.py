"""
Unit tests for the Sentry integration helpers.

Covers _is_llm_error, _extract_llm_provider, _categorize_llm_error,
_before_send, and init_sentry (no-DSN + import error paths).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.sentry import (
    _before_send,
    _categorize_llm_error,
    _extract_llm_provider,
    _is_llm_error,
    init_sentry,
)


# ── _is_llm_error ─────────────────────────────────────────────────


class TestIsLLMError:
    def test_litellm_in_name_is_llm_error(self) -> None:
        assert _is_llm_error("litellm.BadRequestError", "") is True

    def test_openai_in_message_is_llm_error(self) -> None:
        assert _is_llm_error("APIError", "openai returned 429") is True

    def test_rate_limit_in_message(self) -> None:
        assert _is_llm_error("Exception", "rate_limit exceeded") is True

    def test_quota_in_message(self) -> None:
        assert _is_llm_error("Exception", "quota exceeded for project") is True

    def test_context_length_in_message(self) -> None:
        assert _is_llm_error("Exception", "context_length exceeded") is True

    def test_content_filter_in_message(self) -> None:
        assert _is_llm_error("Exception", "content_filter triggered") is True

    def test_anthropic_in_message(self) -> None:
        assert _is_llm_error("Exception", "anthropic API error") is True

    def test_gemini_in_message(self) -> None:
        assert _is_llm_error("Exception", "gemini service unavailable") is True

    def test_unrelated_exception_is_not_llm_error(self) -> None:
        assert _is_llm_error("ValueError", "invalid literal") is False

    def test_db_error_is_not_llm_error(self) -> None:
        assert _is_llm_error("OperationalError", "database connection failed") is False

    def test_case_insensitive(self) -> None:
        assert _is_llm_error("LITELLM.ERROR", "OPENAI QUOTA") is True


# ── _extract_llm_provider ─────────────────────────────────────────


class TestExtractLLMProvider:
    def test_gemini_maps_to_google(self) -> None:
        assert _extract_llm_provider("gemini quota exceeded") == "google"

    def test_google_maps_to_google(self) -> None:
        assert _extract_llm_provider("google API error") == "google"

    def test_openai_maps_to_openai(self) -> None:
        assert _extract_llm_provider("openai rate limit") == "openai"

    def test_gpt_maps_to_openai(self) -> None:
        assert _extract_llm_provider("gpt-4 context error") == "openai"

    def test_anthropic_maps_to_anthropic(self) -> None:
        assert _extract_llm_provider("anthropic overloaded") == "anthropic"

    def test_claude_maps_to_anthropic(self) -> None:
        assert _extract_llm_provider("claude-3 timeout") == "anthropic"

    def test_litellm_maps_to_litellm_proxy(self) -> None:
        assert _extract_llm_provider("litellm proxy error") == "litellm-proxy"

    def test_unknown_message_returns_unknown(self) -> None:
        assert _extract_llm_provider("some random error") == "unknown"

    def test_case_insensitive(self) -> None:
        assert _extract_llm_provider("GEMINI failed") == "google"


# ── _categorize_llm_error ─────────────────────────────────────────


class TestCategorizeLLMError:
    def test_quota_exceeded(self) -> None:
        assert _categorize_llm_error("quota limit reached") == "quota_exceeded"

    def test_rate_limited_from_rate_limit(self) -> None:
        assert _categorize_llm_error("rate_limit exceeded") == "rate_limited"

    def test_rate_limited_from_rate_limit_space(self) -> None:
        assert _categorize_llm_error("rate limit hit") == "rate_limited"

    def test_rate_limited_from_429(self) -> None:
        assert _categorize_llm_error("HTTP 429 Too Many Requests") == "rate_limited"

    def test_context_overflow(self) -> None:
        assert _categorize_llm_error("context_length exceeded") == "context_overflow"

    def test_content_filtered(self) -> None:
        assert _categorize_llm_error("content_filter blocked") == "content_filtered"

    def test_safety_filtered(self) -> None:
        assert _categorize_llm_error("safety system triggered") == "content_filtered"

    def test_timeout(self) -> None:
        assert _categorize_llm_error("request timeout") == "timeout"

    def test_connection_error(self) -> None:
        assert _categorize_llm_error("connection refused") == "connection_error"

    def test_auth_error_from_authentication(self) -> None:
        assert _categorize_llm_error("authentication failed") == "auth_error"

    def test_auth_error_from_401(self) -> None:
        assert _categorize_llm_error("HTTP 401 Unauthorized") == "auth_error"

    def test_auth_error_from_403(self) -> None:
        assert _categorize_llm_error("HTTP 403 Forbidden") == "auth_error"

    def test_model_not_found(self) -> None:
        assert _categorize_llm_error("model_not_found: gpt-5") == "model_not_found"

    def test_unknown_returns_fallback(self) -> None:
        assert _categorize_llm_error("some unexpected error") == "unknown_llm_error"


# ── _before_send ──────────────────────────────────────────────────


class TestBeforeSend:
    def _make_hint(self, exc_name: str, message: str) -> dict:
        exc_type = type(exc_name, (Exception,), {})
        exc_value = Exception(message)
        return {"exc_info": (exc_type, exc_value, None)}

    def test_service_tags_always_added(self) -> None:
        with patch("app.core.sentry.settings") as s:
            s.app_slug = "pathforge-api"
            s.environment = "production"
            event: dict = {}
            result = _before_send(event, {})
        assert result["tags"]["service"] == "pathforge-api"
        assert result["tags"]["deployment.environment"] == "production"

    def test_llm_error_gets_fingerprint(self) -> None:
        with patch("app.core.sentry.settings") as s:
            s.app_slug = "pathforge-api"
            s.environment = "production"
            hint = self._make_hint("litellmError", "openai quota exceeded")
            event: dict = {}
            result = _before_send(event, hint)
        assert "fingerprint" in result
        assert result["fingerprint"][0] == "llm-error"

    def test_llm_error_adds_provider_tag(self) -> None:
        with patch("app.core.sentry.settings") as s:
            s.app_slug = "pathforge-api"
            s.environment = "production"
            hint = self._make_hint("Error", "anthropic rate_limit exceeded")
            event: dict = {}
            result = _before_send(event, hint)
        assert result["tags"]["llm.provider"] == "anthropic"

    def test_non_llm_error_has_no_fingerprint(self) -> None:
        with patch("app.core.sentry.settings") as s:
            s.app_slug = "pathforge-api"
            s.environment = "production"
            hint = self._make_hint("ValueError", "invalid input")
            event: dict = {}
            result = _before_send(event, hint)
        assert "fingerprint" not in result

    def test_no_hint_no_fingerprint(self) -> None:
        with patch("app.core.sentry.settings") as s:
            s.app_slug = "pathforge-api"
            s.environment = "test"
            event: dict = {}
            result = _before_send(event, {})
        assert "fingerprint" not in result


# ── init_sentry ────────────────────────────────────────────────────


class TestInitSentry:
    def test_no_dsn_returns_early(self) -> None:
        with patch("app.core.sentry.settings") as s:
            s.sentry_dsn = ""
            init_sentry()  # should not raise

    def test_dsn_configured_calls_sdk_init(self) -> None:
        mock_sdk = MagicMock()
        mock_scrubber = MagicMock()
        mock_sdk.scrubber.DEFAULT_DENYLIST = []
        mock_sdk.scrubber.EventScrubber = mock_scrubber

        with patch("app.core.sentry.settings") as s, \
             patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.scrubber": mock_sdk.scrubber}):
            s.sentry_dsn = "https://key@sentry.io/123"
            s.sentry_environment = "production"
            s.sentry_release = "1.0.0"
            s.sentry_traces_sample_rate = 0.1
            s.environment = "production"
            s.app_version = "1.0.0"
            s.app_slug = "pathforge"
            init_sentry()

        mock_sdk.init.assert_called_once()

    def test_import_error_logged_as_warning(self) -> None:
        import sys

        with patch("app.core.sentry.settings") as s, \
             patch.dict("sys.modules", {"sentry_sdk": None}):
            s.sentry_dsn = "https://key@sentry.io/123"
            # sentry_sdk not installed → ImportError on `import sentry_sdk`
            init_sentry()  # should not raise

    def test_init_exception_logged_not_raised(self) -> None:
        mock_sdk = MagicMock()
        mock_sdk.init.side_effect = RuntimeError("Sentry config error")
        mock_sdk.scrubber = MagicMock()
        mock_sdk.scrubber.DEFAULT_DENYLIST = []
        mock_sdk.scrubber.EventScrubber = MagicMock()

        with patch("app.core.sentry.settings") as s, \
             patch.dict("sys.modules", {"sentry_sdk": mock_sdk, "sentry_sdk.scrubber": mock_sdk.scrubber}):
            s.sentry_dsn = "https://key@sentry.io/123"
            s.sentry_environment = "production"
            s.sentry_release = "1.0.0"
            s.sentry_traces_sample_rate = 0.1
            s.environment = "production"
            s.app_version = "1.0.0"
            s.app_slug = "pathforge"
            init_sentry()  # should catch the exception, not re-raise
