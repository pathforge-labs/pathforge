"""
PathForge — Shared Password Policy
====================================
Single source of truth for password complexity validation.

Used by both the register schema and the password-reset schema so that
the same rules apply everywhere. The frontend mirrors this regex in
``apps/web/src/lib/auth/password-policy.ts`` — keep the two in sync
whenever the ruleset changes.

OWASP-aligned requirements (ASVS V2.1 — Password Security):
- Minimum 8 characters (enforced at Field level via min_length)
- At least one uppercase letter
- At least one digit
- At least one special character from a wide, printable set

Why extract:
- Sprint 39 audit finding: frontend and backend regexes had drifted
  (subtle escaping differences). Users saw "valid on frontend, 422 from
  backend" errors. Extracting this constant fixes the drift.
"""

from __future__ import annotations

import re

# ── Special character class ────────────────────────────────────────────
# Keep this pattern in sync with
# ``apps/web/src/lib/auth/password-policy.ts``.
#
# Character class: !@#$%^&*(),.?":{}|<>-_=+[]\/'`~;
# Rationale: mirrors the "punctuation" set common to US-ASCII keyboards;
# excludes whitespace and control characters. `-` is placed after an
# escape (`\-`) for portability across regex dialects.
PASSWORD_SPECIAL_CHARS_PATTERN: str = r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\/'`~;]"

_UPPERCASE_PATTERN: re.Pattern[str] = re.compile(r"[A-Z]")
_DIGIT_PATTERN: re.Pattern[str] = re.compile(r"\d")
_SPECIAL_PATTERN: re.Pattern[str] = re.compile(PASSWORD_SPECIAL_CHARS_PATTERN)


def validate_password_complexity(value: str) -> str:
    """Raise ``ValueError`` if ``value`` does not satisfy complexity rules.

    Returns the input unchanged on success so callers can use this as a
    Pydantic ``@field_validator`` body or a pre-save hook.

    The message format matches the frontend validator verbatim so that
    error messages are identical regardless of which layer catches them.
    """
    missing: list[str] = []
    if not _UPPERCASE_PATTERN.search(value):
        missing.append("one uppercase letter")
    if not _DIGIT_PATTERN.search(value):
        missing.append("one digit")
    if not _SPECIAL_PATTERN.search(value):
        missing.append("one special character")

    if missing:
        raise ValueError(
            f"Password must contain at least {', '.join(missing)}"
        )
    return value
