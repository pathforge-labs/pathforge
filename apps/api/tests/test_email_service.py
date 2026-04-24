"""
PathForge — Email Service Unit Tests
=========================================
Tests for template loading, token generation, and all send methods
in app/services/email_service.py.  Resend SDK is mocked throughout.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from app.services.email_service import (
    EmailService,
    generate_token,
    get_token_expiry_email_verification,
    get_token_expiry_password_reset,
    verify_token_hash,
)

# ── generate_token ────────────────────────────────────────────


def test_generate_token_returns_two_strings() -> None:
    raw, hashed = generate_token()
    assert isinstance(raw, str)
    assert isinstance(hashed, str)


def test_generate_token_raw_is_urlsafe() -> None:
    raw, _ = generate_token()
    import re
    assert re.match(r"^[A-Za-z0-9_-]+$", raw)


def test_generate_token_hash_is_sha256() -> None:
    raw, hashed = generate_token()
    expected = hashlib.sha256(raw.encode()).hexdigest()
    assert hashed == expected


def test_generate_token_unique_each_call() -> None:
    r1, h1 = generate_token()
    r2, h2 = generate_token()
    assert r1 != r2
    assert h1 != h2


# ── verify_token_hash ─────────────────────────────────────────


def test_verify_token_hash_valid() -> None:
    raw, hashed = generate_token()
    assert verify_token_hash(raw, hashed) is True


def test_verify_token_hash_invalid() -> None:
    raw, _ = generate_token()
    assert verify_token_hash(raw, "wronghash") is False


def test_verify_token_hash_tampered_raw() -> None:
    _, hashed = generate_token()
    assert verify_token_hash("tampered", hashed) is False


# ── _load_template ────────────────────────────────────────────


def test_load_template_substitutes_variables(tmp_path: Path) -> None:
    from app.services import email_service as em

    template_dir = tmp_path / "templates" / "email"
    template_dir.mkdir(parents=True)
    (template_dir / "test.html").write_text("<p>{{name}} {{app_name}}</p>")

    with patch.object(em, "_TEMPLATE_DIR", template_dir):
        from app.services.email_service import _load_template
        # Reload to pick up patched _TEMPLATE_DIR
        result = _load_template("test.html", name="Alice", app_name="PathForge")

    assert "Alice" in result
    assert "PathForge" in result
    assert "{{name}}" not in result


def test_load_template_missing_file_returns_fallback() -> None:
    with patch(
        "app.services.email_service._TEMPLATE_DIR",
        Path("/nonexistent/dir"),
    ):
        from app.services.email_service import _load_template
        result = _load_template("missing.html", subject="Hello")

    assert "Hello" in result


# ── EmailService._is_configured ──────────────────────────────


def test_is_configured_false_when_no_key() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "")
    try:
        assert EmailService._is_configured() is False
    finally:
        object.__setattr__(settings, "resend_api_key", original)


def test_is_configured_true_when_key_set() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "re_test_key")
    try:
        assert EmailService._is_configured() is True
    finally:
        object.__setattr__(settings, "resend_api_key", original)


# ── EmailService._send — dev mode (no key) ───────────────────


def test_send_dev_mode_returns_false() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "")
    try:
        result = EmailService._send(to="a@b.com", subject="Hi", html="<p>Hi</p>")
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is False


# ── EmailService._send — production mode ─────────────────────


def test_send_production_mode_calls_resend() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "re_prod_key")
    try:
        with patch("resend.Emails.send", return_value={"id": "em_123"}) as mock_send:
            result = EmailService._send(
                to="user@example.com", subject="Test", html="<p>test</p>"
            )
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is True
    mock_send.assert_called_once()


def test_send_production_mode_returns_false_on_error() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "re_prod_key")
    try:
        with patch("resend.Emails.send", side_effect=Exception("API error")):
            result = EmailService._send(
                to="user@example.com", subject="Test", html="<p>test</p>"
            )
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is False


# ── send_verification_email ───────────────────────────────────


def test_send_verification_email_dev_mode() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "")
    try:
        result = EmailService.send_verification_email(
            to="u@x.com", token="tok123", name="Bob"
        )
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is False


def test_send_verification_email_includes_token_in_url() -> None:
    from app.core.config import settings
    original_key = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "re_prod_key")
    try:
        with patch("resend.Emails.send"), \
             patch("app.services.email_service._load_template", return_value="<p>verify</p>") as mock_load:
            EmailService.send_verification_email(
                to="u@x.com", token="mytoken", name="Alice"
            )
        _, kw = mock_load.call_args
        assert "mytoken" in kw.get("verify_url", "")
    finally:
        object.__setattr__(settings, "resend_api_key", original_key)


# ── send_password_reset_email ─────────────────────────────────


def test_send_password_reset_email_dev_mode() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "")
    try:
        result = EmailService.send_password_reset_email(
            to="u@x.com", token="reset123", name="Alice"
        )
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is False


def test_send_password_reset_email_production() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "re_prod_key")
    try:
        with patch("resend.Emails.send", return_value={"id": "em_2"}), \
             patch("app.services.email_service._load_template", return_value="<p>reset</p>"):
            result = EmailService.send_password_reset_email(
                to="u@x.com", token="tok", name="Alice"
            )
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is True


# ── send_welcome_email ────────────────────────────────────────


def test_send_welcome_email_dev_mode() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "")
    try:
        result = EmailService.send_welcome_email(to="u@x.com", name="Carol")
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is False


def test_send_welcome_email_production() -> None:
    from app.core.config import settings
    original = settings.resend_api_key
    object.__setattr__(settings, "resend_api_key", "re_prod_key")
    try:
        with patch("resend.Emails.send", return_value={"id": "em_3"}), \
             patch("app.services.email_service._load_template", return_value="<p>welcome</p>"):
            result = EmailService.send_welcome_email(to="u@x.com", name="Carol")
    finally:
        object.__setattr__(settings, "resend_api_key", original)
    assert result is True


# ── token expiry helpers ──────────────────────────────────────


def test_get_token_expiry_password_reset_is_future() -> None:
    expiry = get_token_expiry_password_reset()
    assert expiry > datetime.now(UTC)


def test_get_token_expiry_email_verification_is_future() -> None:
    expiry = get_token_expiry_email_verification()
    assert expiry > datetime.now(UTC)


def test_token_expiry_email_verification_longer_than_reset() -> None:
    reset_expiry = get_token_expiry_password_reset()
    verify_expiry = get_token_expiry_email_verification()
    # Email verification is typically longer (hours) than reset (minutes)
    assert verify_expiry > reset_expiry
