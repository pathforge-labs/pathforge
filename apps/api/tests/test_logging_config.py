"""
Unit tests for the structured logging configuration.

Covers all four processor functions and the setup_logging
entry point (debug vs production path).
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.core.logging_config import (
    REDACTED,
    SENSITIVE_FIELDS,
    _add_correlation_id,
    _add_request_id,
    _add_service_metadata,
    _redact_sensitive_fields,
    setup_logging,
)


# ── Helpers ──────────────────────────────────────────────────────


def _noop_logger() -> MagicMock:
    return MagicMock(spec=logging.Logger)


# ── _add_request_id ───────────────────────────────────────────────


class TestAddRequestId:
    def test_injects_request_id_when_set(self) -> None:
        with patch("app.core.logging_config.get_request_id", return_value="req-123"):
            event_dict: dict = {}
            result = _add_request_id(_noop_logger(), "info", event_dict)
        assert result["request_id"] == "req-123"

    def test_no_key_when_request_id_empty(self) -> None:
        with patch("app.core.logging_config.get_request_id", return_value=""):
            event_dict: dict = {}
            result = _add_request_id(_noop_logger(), "info", event_dict)
        assert "request_id" not in result

    def test_preserves_existing_fields(self) -> None:
        with patch("app.core.logging_config.get_request_id", return_value="xyz"):
            event_dict = {"event": "something happened", "level": "info"}
            result = _add_request_id(_noop_logger(), "info", event_dict)
        assert result["event"] == "something happened"
        assert result["request_id"] == "xyz"

    def test_returns_same_dict(self) -> None:
        with patch("app.core.logging_config.get_request_id", return_value="abc"):
            event_dict: dict = {}
            result = _add_request_id(_noop_logger(), "info", event_dict)
        assert result is event_dict


# ── _add_correlation_id ───────────────────────────────────────────


class TestAddCorrelationId:
    def test_injects_trace_id_when_set(self) -> None:
        with patch("app.core.logging_config.get_correlation_id", return_value="trace-456"):
            event_dict: dict = {}
            result = _add_correlation_id(_noop_logger(), "info", event_dict)
        assert result["trace_id"] == "trace-456"

    def test_no_key_when_correlation_id_empty(self) -> None:
        with patch("app.core.logging_config.get_correlation_id", return_value=""):
            event_dict: dict = {}
            result = _add_correlation_id(_noop_logger(), "info", event_dict)
        assert "trace_id" not in result

    def test_uses_otel_compatible_field_name(self) -> None:
        with patch("app.core.logging_config.get_correlation_id", return_value="otel-id"):
            result = _add_correlation_id(_noop_logger(), "info", {})
        # OTel naming convention: trace_id (not correlation_id)
        assert "trace_id" in result
        assert "correlation_id" not in result


# ── _add_service_metadata ─────────────────────────────────────────


class TestAddServiceMetadata:
    def test_injects_service_name(self) -> None:
        with patch("app.core.config.settings") as s:
            s.app_slug = "pathforge-api"
            s.app_version = "1.0.0"
            s.environment = "production"
            result = _add_service_metadata(_noop_logger(), "info", {})
        assert result["service.name"] == "pathforge-api"

    def test_injects_service_version(self) -> None:
        with patch("app.core.config.settings") as s:
            s.app_slug = "pathforge-api"
            s.app_version = "2.3.1"
            s.environment = "staging"
            result = _add_service_metadata(_noop_logger(), "info", {})
        assert result["service.version"] == "2.3.1"

    def test_injects_environment(self) -> None:
        with patch("app.core.config.settings") as s:
            s.app_slug = "pathforge-api"
            s.app_version = "1.0.0"
            s.environment = "staging"
            result = _add_service_metadata(_noop_logger(), "info", {})
        assert result["deployment.environment"] == "staging"


# ── _redact_sensitive_fields ──────────────────────────────────────


class TestRedactSensitiveFields:
    def test_password_redacted(self) -> None:
        event_dict = {"event": "login", "password": "s3cret"}
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["password"] == REDACTED

    def test_token_redacted(self) -> None:
        event_dict = {"token": "eyJhbGciOi..."}
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["token"] == REDACTED

    def test_api_key_redacted(self) -> None:
        event_dict = {"api_key": "sk-proj-123"}
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["api_key"] == REDACTED

    def test_resume_text_redacted(self) -> None:
        event_dict = {"resume_text": "John Doe, Software Engineer..."}
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["resume_text"] == REDACTED

    def test_non_sensitive_field_preserved(self) -> None:
        event_dict = {"event": "user.login", "user_id": "u-123"}
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["event"] == "user.login"
        assert result["user_id"] == "u-123"

    def test_case_insensitive_matching(self) -> None:
        event_dict = {"PASSWORD": "leaked"}
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["PASSWORD"] == REDACTED

    def test_multiple_sensitive_fields_all_redacted(self) -> None:
        event_dict = {
            "password": "pw",
            "token": "tok",
            "event": "action",
        }
        result = _redact_sensitive_fields(_noop_logger(), "info", event_dict)
        assert result["password"] == REDACTED
        assert result["token"] == REDACTED
        assert result["event"] == "action"

    def test_sensitive_fields_denylist_not_empty(self) -> None:
        assert len(SENSITIVE_FIELDS) > 5

    def test_sentry_dsn_in_denylist(self) -> None:
        assert "sentry_dsn" in SENSITIVE_FIELDS


# ── setup_logging ─────────────────────────────────────────────────


class TestSetupLogging:
    """
    Tests for setup_logging must mock logging.getLogger() to prevent clearing
    pytest's log capture handlers, which would break subsequent tests.
    """

    @pytest.fixture(autouse=True)
    def _isolate_logging(self):
        """Prevent setup_logging from touching the real root logger."""
        mock_root = MagicMock()
        with patch("logging.getLogger", return_value=mock_root):
            yield mock_root

    def test_debug_mode_configures_console_renderer(self, _isolate_logging) -> None:
        with patch("structlog.configure") as mock_configure, \
             patch("structlog.stdlib.ProcessorFormatter"), \
             patch("logging.StreamHandler"):
            setup_logging(debug=True)
        mock_configure.assert_called_once()

    def test_production_mode_configures_json_renderer(self, _isolate_logging) -> None:
        with patch("structlog.configure") as mock_configure, \
             patch("structlog.stdlib.ProcessorFormatter"), \
             patch("logging.StreamHandler"):
            setup_logging(debug=False)
        mock_configure.assert_called_once()

    def test_auto_detect_reads_settings_when_debug_is_none(self, _isolate_logging) -> None:
        with patch("app.core.config.settings") as s, \
             patch("structlog.configure"), \
             patch("structlog.stdlib.ProcessorFormatter"), \
             patch("logging.StreamHandler"):
            s.debug = True
            s.log_level = "INFO"
            setup_logging(debug=None)

    def test_invalid_log_level_falls_back_to_info(self, _isolate_logging) -> None:
        with patch("app.core.config.settings") as s, \
             patch("structlog.configure"), \
             patch("structlog.stdlib.ProcessorFormatter"), \
             patch("logging.StreamHandler"):
            s.debug = False
            s.log_level = "NOTEXISTENT"
            setup_logging(debug=False)
