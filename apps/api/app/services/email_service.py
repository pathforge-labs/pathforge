"""
PathForge — Email Service
============================
Typed Resend SDK wrapper for transactional emails.

Graceful degradation: when `resend_api_key` is empty (dev mode),
emails are logged but never sent. Production requires a valid key.

Sprint 39: Initial implementation for password reset and email verification.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Template Directory ─────────────────────────────────────────
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


def _load_template(template_name: str, **variables: str) -> str:
    """Load an HTML email template and substitute placeholders."""
    template_path = _TEMPLATE_DIR / template_name
    if not template_path.exists():
        logger.warning("Email template not found: %s", template_name)
        return f"<p>{variables.get('subject', 'PathForge Notification')}</p>"
    content = template_path.read_text(encoding="utf-8")
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def generate_token() -> tuple[str, str]:
    """Generate a secure token and its SHA-256 hash.

    Returns:
        Tuple of (raw_token, hashed_token). The raw token is sent via email;
        the hash is stored in the database. This prevents database leaks
        from being exploitable.
    """
    raw_token = secrets.token_urlsafe(32)
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, hashed_token


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    """Verify a raw token against its stored SHA-256 hash."""
    return hashlib.sha256(raw_token.encode()).hexdigest() == stored_hash


class EmailService:
    """Transactional email service using Resend SDK."""

    @staticmethod
    def _is_configured() -> bool:
        """Check if email delivery is properly configured."""
        return bool(settings.resend_api_key)

    @staticmethod
    def _send(
        *,
        to: str,
        subject: str,
        html: str,
    ) -> bool:
        """Send an email via Resend. Returns True on success, False on failure."""
        if not EmailService._is_configured():
            logger.info(
                "Email delivery disabled (no RESEND_API_KEY). "
                "Would send to=%s subject=%s",
                to,
                subject,
            )
            return False

        try:
            resend.api_key = settings.resend_api_key
            resend.Emails.send(
                {
                    "from": settings.digest_from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )
            logger.info("Email sent successfully to=%s subject=%s", to, subject)
            return True
        except Exception:
            logger.exception("Failed to send email to=%s subject=%s", to, subject)
            return False

    @staticmethod
    def send_verification_email(
        *,
        to: str,
        token: str,
        name: str,
    ) -> bool:
        """Send email verification link.

        The link carries both ``token`` and ``email`` as query
        parameters. ``email`` is appended so the verify-email page can
        offer one-click resend if the link has expired or fails — the
        recipient already owns this address, so we are not disclosing
        new information by including it. Both values are URL-encoded
        defensively in case the token contains URL-unsafe characters
        in a future format change.
        """
        from urllib.parse import urlencode

        query = urlencode({"token": token, "email": to})
        verify_url = f"{settings.frontend_url}/verify-email?{query}"
        html = _load_template(
            "verification.html",
            name=name,
            verify_url=verify_url,
            app_name=settings.app_name,
        )
        return EmailService._send(
            to=to,
            subject=f"Verify your {settings.app_name} email",
            html=html,
        )

    @staticmethod
    def send_password_reset_email(
        *,
        to: str,
        token: str,
        name: str,
    ) -> bool:
        """Send password reset link."""
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        expire_minutes = settings.password_reset_token_expire_minutes
        html = _load_template(
            "password_reset.html",
            name=name,
            reset_url=reset_url,
            expire_minutes=str(expire_minutes),
            app_name=settings.app_name,
        )
        return EmailService._send(
            to=to,
            subject=f"Reset your {settings.app_name} password",
            html=html,
        )

    @staticmethod
    def send_welcome_email(
        *,
        to: str,
        name: str,
    ) -> bool:
        """Send welcome email after successful registration + verification."""
        html = _load_template(
            "welcome.html",
            name=name,
            dashboard_url=f"{settings.frontend_url}/dashboard",
            app_name=settings.app_name,
        )
        return EmailService._send(
            to=to,
            subject=f"Welcome to {settings.app_name}!",
            html=html,
        )


def get_token_expiry_password_reset() -> datetime:
    """Get the expiry datetime for a password reset token."""
    return datetime.now(UTC) + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )


def get_token_expiry_email_verification() -> datetime:
    """Get the expiry datetime for an email verification token."""
    return datetime.now(UTC) + timedelta(
        hours=settings.email_verification_token_expire_hours
    )
