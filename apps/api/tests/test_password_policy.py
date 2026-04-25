"""
Unit tests for ``app.core.password_policy``.

These tests pin down the precise complexity rules so that any drift
between this module and its frontend mirror
(``apps/web/src/lib/auth/password-policy.ts``) is visible in CI.
"""

from __future__ import annotations

import pytest

from app.core.password_policy import (
    PASSWORD_SPECIAL_CHARS_PATTERN,
    validate_password_complexity,
)

# ── Happy path ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    [
        "Abcdef1!",          # minimal 8 chars with all three classes
        "StrongP@ss123",     # typical production-grade password
        "MyP@ssw0rd",        # already used in tests
        "ValidPass1!",
        "Complex#2026",
        "Secure`Pw1",        # backtick special char
        "Secure~Pw1",        # tilde special char
        "Secure;Pw1",        # semicolon special char
    ],
)
def test_valid_passwords_pass(value: str) -> None:
    assert validate_password_complexity(value) == value


# ── Missing uppercase ─────────────────────────────────────────────


def test_missing_uppercase_rejected() -> None:
    with pytest.raises(ValueError, match="one uppercase letter"):
        validate_password_complexity("abcdef1!")


def test_single_uppercase_accepted() -> None:
    # Exactly one uppercase letter is sufficient.
    assert validate_password_complexity("Abcdef1!") == "Abcdef1!"


# ── Missing digit ─────────────────────────────────────────────────


def test_missing_digit_rejected() -> None:
    with pytest.raises(ValueError, match="one digit"):
        validate_password_complexity("Abcdefg!")


def test_single_digit_accepted() -> None:
    assert validate_password_complexity("Abcdef1!") == "Abcdef1!"


# ── Missing special ───────────────────────────────────────────────


def test_missing_special_rejected() -> None:
    with pytest.raises(ValueError, match="one special character"):
        validate_password_complexity("Abcdef12")


@pytest.mark.parametrize(
    "special",
    [
        "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
        ",", ".", "?", '"', ":", "{", "}", "|", "<", ">",
        "-", "_", "=", "+", "[", "]", "\\", "/", "'", "`", "~", ";",
    ],
)
def test_each_special_char_accepted(special: str) -> None:
    """Every character in the documented set satisfies the special-char rule."""
    value = f"Abcd1234{special}"
    assert validate_password_complexity(value) == value


# ── Combined / multi-missing messages ─────────────────────────────


def test_multiple_missing_classes_listed_in_order() -> None:
    """Error message mentions every missing class so users can fix in one pass."""
    with pytest.raises(ValueError) as exc:
        validate_password_complexity("abcdefgh")  # missing upper, digit, special

    message = str(exc.value)
    assert "one uppercase letter" in message
    assert "one digit" in message
    assert "one special character" in message


def test_uppercase_digit_missing_special_only() -> None:
    with pytest.raises(ValueError) as exc:
        validate_password_complexity("Abcdef12")

    message = str(exc.value)
    assert "one uppercase letter" not in message
    assert "one digit" not in message
    assert "one special character" in message


# ── Drift guard ───────────────────────────────────────────────────


def test_special_chars_pattern_is_public_and_nonempty() -> None:
    """The frontend mirror references this pattern — it must exist."""
    assert isinstance(PASSWORD_SPECIAL_CHARS_PATTERN, str)
    assert PASSWORD_SPECIAL_CHARS_PATTERN.startswith("[")
    assert PASSWORD_SPECIAL_CHARS_PATTERN.endswith("]")
    # Basic sanity: the character class contains the common punctuation
    # landmarks. If anyone removes these, the frontend will drift.
    for marker in ("!", "@", "#", "$", "%"):
        assert marker in PASSWORD_SPECIAL_CHARS_PATTERN
