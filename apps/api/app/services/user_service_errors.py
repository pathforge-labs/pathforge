"""
PathForge — User Service Exceptions
=====================================
Structured exception hierarchy for authentication failures.

Raising semantic exceptions (rather than a generic ``ValueError`` with
a human-readable ``str(exc)``) lets the API layer map errors to HTTP
status codes without string matching. That keeps service-layer
messages editable for UX without risking a silent status-code drift
in the route handler.

Hierarchy
---------
``AuthenticationError``  (base)
├── ``InvalidCredentialsError``    → 401
├── ``InactiveAccountError``       → 403
├── ``UnverifiedAccountError``     → 403
└── ``OAuthOnlyAccountError``      → 403

``PasswordResetError``  (base)
├── ``InvalidResetTokenError``     → 400
├── ``ExpiredResetTokenError``     → 400
└── ``ResetTokenAlreadyUsedError`` → 400

All subclasses carry a ``message`` attribute that is safe to render
to the user; callers should *not* inspect private attributes or the
stringified exception when making control-flow decisions — use
``isinstance`` checks instead.
"""

from __future__ import annotations


class AuthenticationError(Exception):
    """Base class for all authentication failures.

    Subclasses represent distinct failure modes that the API layer
    maps to specific HTTP status codes. The ``message`` attribute is
    a user-facing string; the route handler surfaces it verbatim in
    the response body.
    """

    default_message: str = "Authentication failed"

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)


class InvalidCredentialsError(AuthenticationError):
    """Email not found or password did not verify.

    Always surfaced with a generic message to avoid account-enumeration
    attacks. Maps to HTTP 401.
    """

    default_message = "Incorrect email or password"


class InactiveAccountError(AuthenticationError):
    """Account exists but its ``is_active`` flag is False.

    Usually set by an admin during suspension or by the GDPR delete
    flow. Maps to HTTP 403.
    """

    default_message = "User account is inactive"


class UnverifiedAccountError(AuthenticationError):
    """Email-based account has never confirmed its email address.

    The caller is expected to render a recovery message pointing the
    user at /check-email or a "resend verification" flow. Maps to
    HTTP 403.
    """

    default_message = (
        "Please verify your email address before signing in. "
        "Check your inbox for the verification link "
        "or request a new one from the sign-in page."
    )


class OAuthOnlyAccountError(AuthenticationError):
    """Account has no password — a Google/Microsoft sign-in is required.

    Raised when an OAuth-provisioned user attempts password login
    (F23). The ``provider`` attribute lets the UI render the correct
    brand button in the error state. Maps to HTTP 403.
    """

    def __init__(self, provider: str) -> None:
        self.provider: str = provider
        message = (
            f"This account uses {provider} sign-in. "
            f"Please use the {provider} button to log in."
        )
        super().__init__(message)


# ── Password-reset failures ───────────────────────────────────────


class PasswordResetError(Exception):
    """Base class for password-reset failures (F30)."""

    default_message: str = "Password reset failed"

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)


class InvalidResetTokenError(PasswordResetError):
    """Reset token doesn't match any user, or timestamp missing."""

    default_message = "Invalid or expired reset token"


class ExpiredResetTokenError(PasswordResetError):
    """Reset token was valid at some point but has aged out."""

    default_message = "Reset token has expired. Please request a new one."


class ResetTokenAlreadyUsedError(PasswordResetError):
    """Reset token was consumed by a previous request (race or replay).

    Raised by the atomic consume-and-update path — if the UPDATE
    affects zero rows after the pre-check passed, another caller
    completed the reset first. Surfaced to users as a distinct
    message so the UI can route them to /forgot-password.
    """

    default_message = (
        "Reset token has already been used. Please request a new one."
    )
