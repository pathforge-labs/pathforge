"""
PathForge - Email Service Tests
=================================
Unit tests for the transactional email service:
- Token generation and verification (hash-based)
- HTML template loading with placeholder substitution
- send_verification_email / send_password_reset_email / send_welcome_email
- Expiry helper functions for password reset and email verification
- Graceful degradation when RESEND_API_KEY is absent
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services import email_service as email_service_module
from app.services.email_service import (
    EmailService,
    _load_template,
    generate_token,
    get_token_expiry_email_verification,
    get_token_expiry_password_reset,
    verify_token_hash,
)

# --- generate_token -------------------------------------------------


class TestGenerateToken:
    """Tests for generate_token()."""

    def test_returns_tuple_of_two_strings(self) -> None:
        raw, hashed = generate_token()
        assert isinstance(raw, str)
        assert isinstance(hashed, str)

    def test_hash_matches_sha256_of_raw(self) -> None:
        raw, hashed = generate_token()
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert hashed == expected

    def test_hash_is_64_hex_chars(self) -> None:
        _, hashed = generate_token()
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_tokens_are_unique(self) -> None:
        tokens = {generate_token()[0] for _ in range(50)}
        assert len(tokens) == 50

    def test_raw_token_is_url_safe(self) -> None:
        raw, _ = generate_token()
        # token_urlsafe uses only A-Z, a-z, 0-9, -, _
        allowed = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
        )
        assert set(raw).issubset(allowed)


# --- verify_token_hash ----------------------------------------------


class TestVerifyTokenHash:
    """Tests for verify_token_hash()."""

    def test_returns_true_for_matching_token(self) -> None:
        raw, hashed = generate_token()
        assert verify_token_hash(raw, hashed) is True

    def test_returns_false_for_mismatched_token(self) -> None:
        _, hashed = generate_token()
        other_raw, _ = generate_token()
        assert verify_token_hash(other_raw, hashed) is False

    def test_returns_false_for_empty_raw_token(self) -> None:
        _, hashed = generate_token()
        assert verify_token_hash("", hashed) is False

    def test_returns_false_for_bogus_hash(self) -> None:
        raw, _ = generate_token()
        assert verify_token_hash(raw, "deadbeef") is False


# --- _load_template -------------------------------------------------


class TestLoadTemplate:
    """Tests for the private _load_template() helper."""

    def test_returns_string_for_existing_template(self) -> None:
        result = _load_template("welcome.html", name="Alice", app_name="PathForge")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_fallback_for_missing_template(self) -> None:
        result = _load_template("does_not_exist.html", subject="Hello")
        assert result == "<p>Hello</p>"

    def test_fallback_uses_default_subject(self) -> None:
        result = _load_template("missing.html")
        assert result == "<p>PathForge Notification</p>"

    def test_substitutes_placeholder_variables(self, tmp_path: Path) -> None:
        template_file = tmp_path / "custom.html"
        template_file.write_text(
            "<h1>Hello {{name}}</h1><p>App: {{app_name}}</p>",
            encoding="utf-8",
        )
        with patch.object(email_service_module, "_TEMPLATE_DIR", tmp_path):
            result = _load_template(
                "custom.html",
                name="Bob",
                app_name="PathForge",
            )
        assert "Hello Bob" in result
        assert "App: PathForge" in result
        assert "{{" not in result

    def test_leaves_unreplaced_placeholders_intact(self, tmp_path: Path) -> None:
        template_file = tmp_path / "partial.html"
        template_file.write_text("Hi {{name}} {{missing}}", encoding="utf-8")
        with patch.object(email_service_module, "_TEMPLATE_DIR", tmp_path):
            result = _load_template("partial.html", name="Carol")
        assert "Hi Carol" in result
        assert "{{missing}}" in result


# --- EmailService._is_configured / _send ---------------------------


class TestEmailServiceConfiguration:
    """Tests for configuration-gated send behaviour."""

    def test_is_configured_false_when_key_blank(self) -> None:
        original = settings.resend_api_key
        try:
            object.__setattr__(settings, "resend_api_key", "")
            assert EmailService._is_configured() is False
        finally:
            object.__setattr__(settings, "resend_api_key", original)

    def test_is_configured_true_when_key_set(self) -> None:
        original = settings.resend_api_key
        try:
            object.__setattr__(settings, "resend_api_key", "re_test_key")
            assert EmailService._is_configured() is True
        finally:
            object.__setattr__(settings, "resend_api_key", original)

    def test_send_returns_false_when_not_configured(self) -> None:
        original = settings.resend_api_key
        try:
            object.__setattr__(settings, "resend_api_key", "")
            result = EmailService._send(
                to="user@example.com",
                subject="Hi",
                html="<p>body</p>",
            )
            assert result is False
        finally:
            object.__setattr__(settings, "resend_api_key", original)

    def test_send_returns_true_on_successful_dispatch(self) -> None:
        original = settings.resend_api_key
        try:
            object.__setattr__(settings, "resend_api_key", "re_test_key")
            with patch.object(
                email_service_module.resend.Emails,
                "send",
                return_value={"id": "mock-id"},
            ) as mock_send:
                result = EmailService._send(
                    to="user@example.com",
                    subject="Hello",
                    html="<p>body</p>",
                )
            assert result is True
            mock_send.assert_called_once()
            payload = mock_send.call_args[0][0]
            assert payload["to"] == ["user@example.com"]
            assert payload["subject"] == "Hello"
            assert payload["html"] == "<p>body</p>"
            assert payload["from"] == settings.digest_from_email
        finally:
            object.__setattr__(settings, "resend_api_key", original)

    def test_send_returns_false_on_sdk_exception(self) -> None:
        original = settings.resend_api_key
        try:
            object.__setattr__(settings, "resend_api_key", "re_test_key")
            with patch.object(
                email_service_module.resend.Emails,
                "send",
                side_effect=RuntimeError("boom"),
            ):
                result = EmailService._send(
                    to="user@example.com",
                    subject="Hello",
                    html="<p>body</p>",
                )
            assert result is False
        finally:
            object.__setattr__(settings, "resend_api_key", original)


# --- send_verification_email ----------------------------------------


class TestSendVerificationEmail:
    """Tests for EmailService.send_verification_email()."""

    def test_calls_send_with_verification_subject(self) -> None:
        mock_send = MagicMock(return_value=True)
        with patch.object(EmailService, "_send", mock_send):
            ok = EmailService.send_verification_email(
                to="user@example.com",
                token="abc123",
                name="Alice",
            )
        assert ok is True
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        assert kwargs["to"] == "user@example.com"
        assert "Verify your" in kwargs["subject"]
        assert settings.app_name in kwargs["subject"]

    def test_includes_token_in_verify_url(self) -> None:
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            EmailService.send_verification_email(
                to="user@example.com",
                token="tok-XYZ",
                name="Alice",
            )
        html = mock_send.call_args.kwargs["html"]
        assert "tok-XYZ" in html
        # F34 (Sprint 39 audit): verify URL now carries both ``token``
        # and ``email`` query params so the verify-email page can
        # offer one-click resend if the link expires. The recipient
        # already controls this address, so re-including it in the
        # URL is not an information disclosure.
        assert "token=tok-XYZ" in html
        assert "email=user%40example.com" in html
        assert "/verify-email?" in html

    def test_verify_url_url_encodes_email_with_special_chars(self) -> None:
        """Plus-sign aliases (e.g. user+tag@…) must round-trip safely."""
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            EmailService.send_verification_email(
                to="user+tag@example.com",
                token="abc",
                name="Alice",
            )
        html = mock_send.call_args.kwargs["html"]
        # ``+`` must be percent-encoded as ``%2B`` to survive the
        # query-string parser on the frontend; raw ``+`` would be
        # decoded to a space.
        assert "email=user%2Btag%40example.com" in html

    def test_returns_false_when_not_configured(self) -> None:
        original = settings.resend_api_key
        try:
            object.__setattr__(settings, "resend_api_key", "")
            result = EmailService.send_verification_email(
                to="user@example.com",
                token="abc",
                name="Alice",
            )
            assert result is False
        finally:
            object.__setattr__(settings, "resend_api_key", original)


# --- send_password_reset_email --------------------------------------


class TestSendPasswordResetEmail:
    """Tests for EmailService.send_password_reset_email()."""

    def test_calls_send_with_reset_subject(self) -> None:
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            ok = EmailService.send_password_reset_email(
                to="user@example.com",
                token="reset-abc",
                name="Bob",
            )
        assert ok is True
        kwargs = mock_send.call_args.kwargs
        assert "Reset your" in kwargs["subject"]
        assert settings.app_name in kwargs["subject"]

    def test_includes_reset_url_with_token(self) -> None:
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            EmailService.send_password_reset_email(
                to="user@example.com",
                token="reset-token-42",
                name="Bob",
            )
        html = mock_send.call_args.kwargs["html"]
        assert "/reset-password?token=reset-token-42" in html

    def test_includes_expire_minutes_in_body(self) -> None:
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            EmailService.send_password_reset_email(
                to="user@example.com",
                token="tok",
                name="Bob",
            )
        html = mock_send.call_args.kwargs["html"]
        assert str(settings.password_reset_token_expire_minutes) in html

    def test_propagates_failure_from_send(self) -> None:
        with patch.object(EmailService, "_send", return_value=False):
            result = EmailService.send_password_reset_email(
                to="user@example.com",
                token="tok",
                name="Bob",
            )
        assert result is False


# --- send_welcome_email ---------------------------------------------


class TestSendWelcomeEmail:
    """Tests for EmailService.send_welcome_email()."""

    def test_calls_send_with_welcome_subject(self) -> None:
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            ok = EmailService.send_welcome_email(
                to="user@example.com",
                name="Carol",
            )
        assert ok is True
        kwargs = mock_send.call_args.kwargs
        assert "Welcome to" in kwargs["subject"]
        assert settings.app_name in kwargs["subject"]

    def test_includes_dashboard_url(self) -> None:
        with patch.object(EmailService, "_send", return_value=True) as mock_send:
            EmailService.send_welcome_email(
                to="user@example.com",
                name="Carol",
            )
        html = mock_send.call_args.kwargs["html"]
        assert "/dashboard" in html


# --- Expiry helpers -------------------------------------------------


class TestTokenExpiryHelpers:
    """Tests for the expiry helper functions."""

    def test_password_reset_expiry_is_in_future(self) -> None:
        before = datetime.now(UTC)
        expiry = get_token_expiry_password_reset()
        after = datetime.now(UTC)
        assert expiry > before
        expected_min = before + timedelta(
            minutes=settings.password_reset_token_expire_minutes,
        )
        expected_max = after + timedelta(
            minutes=settings.password_reset_token_expire_minutes,
        )
        assert expected_min <= expiry <= expected_max

    def test_password_reset_expiry_is_timezone_aware(self) -> None:
        expiry = get_token_expiry_password_reset()
        assert expiry.tzinfo is not None

    def test_email_verification_expiry_is_in_future(self) -> None:
        before = datetime.now(UTC)
        expiry = get_token_expiry_email_verification()
        after = datetime.now(UTC)
        assert expiry > before
        expected_min = before + timedelta(
            hours=settings.email_verification_token_expire_hours,
        )
        expected_max = after + timedelta(
            hours=settings.email_verification_token_expire_hours,
        )
        assert expected_min <= expiry <= expected_max

    def test_email_verification_expiry_is_timezone_aware(self) -> None:
        expiry = get_token_expiry_email_verification()
        assert expiry.tzinfo is not None

    def test_email_verification_expiry_is_longer_than_password_reset(self) -> None:
        """By default: 24h verification >> 30min password reset."""
        verify = get_token_expiry_email_verification()
        reset = get_token_expiry_password_reset()
        assert verify > reset


# --- Integration-style smoke test -----------------------------------


@pytest.mark.asyncio
async def test_send_verification_end_to_end_with_mocked_sdk() -> None:
    """End-to-end happy path: mocks Resend SDK, verifies send payload."""
    original = settings.resend_api_key
    try:
        object.__setattr__(settings, "resend_api_key", "re_test_key")
        with patch.object(
            email_service_module.resend.Emails,
            "send",
            return_value={"id": "sent-id"},
        ) as mock_send:
            ok = EmailService.send_verification_email(
                to="user@example.com",
                token="integration-token",
                name="Dora",
            )
        assert ok is True
        mock_send.assert_called_once()
        payload = mock_send.call_args[0][0]
        assert payload["to"] == ["user@example.com"]
        assert "integration-token" in payload["html"]
    finally:
        object.__setattr__(settings, "resend_api_key", original)
