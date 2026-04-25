"""
PathForge — PII Redactor
=========================
Regex-based PII scrubber for Langfuse trace sanitization.

Scoped to HIGH-CONFIDENCE patterns only (audit C5):
- Emails (~99% precision)
- Phone numbers (~95%)
- SSN/BSN patterns (~98%)
- Credit card numbers (~97%)
- IP addresses (~99%)
- URLs with auth tokens (~90%)

Name detection is deliberately EXCLUDED — regex-based name detection
has ~40% precision and creates false positives. This is a policy
decision documented in the Sprint 29 audit.

Usage:
    from app.core.pii_redactor import redact_pii

    clean_text = redact_pii("Contact me at john@example.com")
    # → "Contact me at [EMAIL]"
"""

from __future__ import annotations

import re

# ── Compiled Regex Patterns ───────────────────────────────────

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Email addresses: user@domain.tld (most specific — must run first)
    (
        re.compile(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        ),
        "[EMAIL]",
    ),
    # US SSN: 123-45-6789 or 123 45 6789 (before phone — more specific)
    (
        re.compile(r"\b\d{3}[\-\s]\d{2}[\-\s]\d{4}\b"),
        "[SSN]",
    ),
    # Dutch BSN: 9 digits (before phone — more specific)
    (
        re.compile(r"\b\d{9}\b"),
        "[BSN]",
    ),
    # Credit card numbers: 13-19 digits with optional separators (before phone)
    (
        re.compile(
            r"\b(?:\d[\s\-]?){13,19}\b",
        ),
        "[CC]",
    ),
    # IPv4 addresses: 192.168.1.1 (before phone — dots distinguish from digits)
    (
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
        ),
        "[IP]",
    ),
    # URLs with auth tokens: ...?token=xxx, ...?key=xxx, ...&api_key=xxx
    (
        re.compile(
            r"(?:token|key|api_key|secret|password|auth)"
            r"[=:]\s*['\"]?[a-zA-Z0-9\-_.~+/]{8,}['\"]?",
            re.IGNORECASE,
        ),
        "[URL_TOKEN]",
    ),
    # Phone numbers: international and local formats (most general — runs last)
    # Matches: +31 6 1234 5678, (555) 123-4567, 06-12345678, +1-800-555-0199
    (
        re.compile(
            r"(?:\+?\d{1,3}[\s\-.]?)?"  # Optional country code
            r"(?:\(?\d{1,4}\)?[\s\-.]?)"  # Area code
            r"(?:\d[\s\-.]?){6,12}",  # Subscriber number
        ),
        "[PHONE]",
    ),
]


def redact_pii(text: str) -> str:
    """Redact PII from text using high-confidence regex patterns.

    Args:
        text: Input text that may contain PII.

    Returns:
        Text with PII replaced by category placeholders.
    """
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
