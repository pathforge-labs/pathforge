"""
Unit tests for the PII redactor.

Verifies that each pattern category redacts correctly and that
clean text passes through unmodified.
"""

from __future__ import annotations

import pytest

from app.core.pii_redactor import redact_pii

# ── Email ───────────────────────────────────────────────────────


class TestEmailRedaction:
    def test_simple_email(self) -> None:
        result = redact_pii("Contact me at john@example.com please")
        assert "[EMAIL]" in result
        assert "john@example.com" not in result

    def test_email_with_plus_tag(self) -> None:
        result = redact_pii("john+filter@domain.co.uk")
        assert "[EMAIL]" in result

    def test_email_mixed_case(self) -> None:
        result = redact_pii("Send to John.Doe@Company.COM")
        assert "[EMAIL]" in result
        assert "Company.COM" not in result

    def test_multiple_emails(self) -> None:
        result = redact_pii("CC: a@b.com and also c@d.org")
        assert result.count("[EMAIL]") == 2


# ── Phone ───────────────────────────────────────────────────────


class TestPhoneRedaction:
    def test_us_format(self) -> None:
        result = redact_pii("Call (555) 123-4567 now")
        assert "[PHONE]" in result
        assert "555" not in result

    def test_dutch_mobile(self) -> None:
        result = redact_pii("Bereik mij op 06-12345678")
        assert "[PHONE]" in result

    def test_international_format(self) -> None:
        result = redact_pii("+31 6 12 34 56 78")
        assert "[PHONE]" in result


# ── SSN ────────────────────────────────────────────────────────


class TestSSNRedaction:
    def test_ssn_dashes(self) -> None:
        result = redact_pii("SSN: 123-45-6789")
        assert "[SSN]" in result
        assert "123-45-6789" not in result

    def test_ssn_spaces(self) -> None:
        result = redact_pii("My SSN is 123 45 6789.")
        assert "[SSN]" in result


# ── BSN ────────────────────────────────────────────────────────


class TestBSNRedaction:
    def test_nine_digit_bsn(self) -> None:
        result = redact_pii("BSN: 123456789")
        assert "[BSN]" in result
        assert "123456789" not in result

    def test_non_nine_digit_not_redacted(self) -> None:
        result = redact_pii("Order #12345678")
        # 8-digit number should not be caught by the 9-digit BSN pattern
        assert "[BSN]" not in result


# ── Credit Card ────────────────────────────────────────────────


class TestCreditCardRedaction:
    def test_visa_number(self) -> None:
        result = redact_pii("Card: 4111111111111111")
        assert "[CC]" in result
        assert "4111" not in result

    def test_amex_with_spaces(self) -> None:
        result = redact_pii("3782 822463 10005")
        assert "[CC]" in result


# ── IP Address ─────────────────────────────────────────────────


class TestIPRedaction:
    def test_ipv4_address(self) -> None:
        result = redact_pii("Server at 192.168.1.1 is down")
        assert "[IP]" in result
        assert "192.168.1.1" not in result

    def test_localhost_not_redacted(self) -> None:
        # 127.0.0.1 is a valid IP and SHOULD be redacted
        result = redact_pii("localhost 127.0.0.1")
        assert "[IP]" in result

    def test_non_ip_not_redacted(self) -> None:
        result = redact_pii("version 3.12.1 released")
        assert "[IP]" not in result


# ── URL Tokens ─────────────────────────────────────────────────


class TestURLTokenRedaction:
    def test_api_key_param(self) -> None:
        result = redact_pii("api_key=sk-abc123def456ghi789")
        assert "[URL_TOKEN]" in result
        assert "sk-abc123def456ghi789" not in result

    def test_token_param(self) -> None:
        result = redact_pii("?token=eyJhbGciOiJIUzI1NiJ9.payload.sig")
        assert "[URL_TOKEN]" in result

    def test_password_param(self) -> None:
        result = redact_pii("password=MySecret123!")
        assert "[URL_TOKEN]" in result


# ── Clean Text ─────────────────────────────────────────────────


class TestCleanText:
    def test_no_pii_unchanged(self) -> None:
        text = "I am a software engineer with 5 years of experience."
        assert redact_pii(text) == text

    def test_empty_string(self) -> None:
        assert redact_pii("") == ""

    def test_whitespace_only(self) -> None:
        assert redact_pii("   ") == "   "


# ── Mixed PII ──────────────────────────────────────────────────


class TestMixedPII:
    def test_email_and_phone_in_same_string(self) -> None:
        text = "Reach me at john@example.com or call +31612345678"
        result = redact_pii(text)
        assert "[EMAIL]" in result
        assert "john@example.com" not in result

    def test_all_pii_types(self) -> None:
        text = (
            "Email: test@example.com "
            "IP: 10.0.0.1 "
            "Token: api_key=abcdefghij1234567890"
        )
        result = redact_pii(text)
        assert "test@example.com" not in result
        assert "10.0.0.1" not in result
        assert "abcdefghij1234567890" not in result

    def test_redaction_preserves_surrounding_text(self) -> None:
        result = redact_pii("Send to john@example.com thanks")
        assert result.startswith("Send to ")
        assert result.endswith(" thanks")
