"""
Unit tests for the shared Redis TLS helper (ADR-0002).

Covers the reconciliation matrix (`REDIS_URL` scheme × `REDIS_SSL` flag ×
environment), non-scheme URL component preservation, and idempotency.
"""
from __future__ import annotations

import logging

import pytest

from app.core.errors import ConfigurationError
from app.core.redis_ssl import arq_ssl_flag, resolve_redis_url

# ── Core reconciliation cells ─────────────────────────────────────────

@pytest.mark.parametrize(
    ("url_in", "ssl_enabled", "environment", "expected"),
    [
        # Concordant cases — no-op.
        ("redis://h:6379/0", False, "development", "redis://h:6379/0"),
        ("rediss://h:6379/0", True, "development", "rediss://h:6379/0"),
        ("redis://h:6379/0", False, "production", "redis://h:6379/0"),
        ("rediss://h:6379/0", True, "production", "rediss://h:6379/0"),
        # Upgrade — flag wins, scheme promoted.
        ("redis://h:6379/0", True, "development", "rediss://h:6379/0"),
        ("redis://h:6379/0", True, "production", "rediss://h:6379/0"),
        # Scheme-strict, non-prod: rediss:// scheme wins silently (flag
        # auto-upgrades); no downgrade.
        ("rediss://h:6379/0", False, "development", "rediss://h:6379/0"),
        ("rediss://h:6379/0", False, "testing", "rediss://h:6379/0"),
    ],
)
def test_reconciliation_matrix(
    url_in: str, ssl_enabled: bool, environment: str, expected: str,
) -> None:
    assert resolve_redis_url(url_in, ssl_enabled, environment) == expected


def test_rediss_plus_ssl_false_in_production_raises() -> None:
    """Scheme says TLS, flag says plaintext, env=production → fail boot.

    Confidentiality-preserving: accepting the stricter setting would be
    correct but the operator's intent is ambiguous, so we refuse to boot
    in production (matches ADR-0001 downgrade-guard posture).
    """
    with pytest.raises(ConfigurationError, match="conflicting"):
        resolve_redis_url("rediss://h:6379/0", False, "production")


# ── Non-scheme URL component preservation ────────────────────────────

@pytest.mark.parametrize(
    "url_in",
    [
        "redis://h:6379/0",
        "redis://user@h:6379/0",
        "redis://user:pass@h:6379/0",
        "redis://user:pass@h:6379/3",
        "redis://h:6379/0?socket_timeout=5",
        "redis://h:6379/0?socket_timeout=5&socket_keepalive=true",
        # IPv6 bracket syntax
        "redis://[::1]:6379/0",
        "redis://user:pass@[2001:db8::1]:6379/2",
    ],
)
def test_non_scheme_components_preserved_on_upgrade(url_in: str) -> None:
    """Every byte past the scheme must be preserved on upgrade."""
    upgraded = resolve_redis_url(url_in, True, "development")
    assert upgraded.startswith("rediss://")
    # The suffix after `://` is identical between input and output.
    assert upgraded.split("://", 1)[1] == url_in.split("://", 1)[1]


# ── Idempotency ──────────────────────────────────────────────────────

@pytest.mark.parametrize("ssl_enabled", [True, False])
@pytest.mark.parametrize("environment", ["development", "testing"])
def test_idempotent(ssl_enabled: bool, environment: str) -> None:
    url = "redis://u:p@h:6379/3?socket_timeout=5"
    once = resolve_redis_url(url, ssl_enabled, environment)
    twice = resolve_redis_url(once, ssl_enabled, environment)
    assert once == twice


# ── DSN-leak regression ─────────────────────────────────────────────

def test_upgrade_warning_log_never_includes_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When the helper rewrites the scheme, the WARNING message must
    never interpolate the URL (which carries user:password@host).
    """
    leaky = "redis://leakuser:leakpass@leakhost:6379/0"
    with caplog.at_level(logging.WARNING, logger="app.core.redis_ssl"):
        resolve_redis_url(leaky, True, "development")
    assert caplog.records, "Expected a WARNING when scheme is upgraded"
    for record in caplog.records:
        rendered = record.getMessage()
        for sentinel in ("leakuser", "leakpass", "leakhost", leaky):
            assert sentinel not in rendered, (
                f"Credential-leak regression: {sentinel!r} appeared in "
                f"helper log: {rendered!r}"
            )


def test_conflict_warning_in_dev_never_includes_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Same discipline for the dev-mode conflict warning (rediss:// +
    flag False → scheme wins, log a warning).
    """
    leaky = "rediss://leakuser:leakpass@leakhost:6379/0"
    with caplog.at_level(logging.WARNING, logger="app.core.redis_ssl"):
        resolve_redis_url(leaky, False, "development")
    for record in caplog.records:
        rendered = record.getMessage()
        for sentinel in ("leakuser", "leakpass", "leakhost", leaky):
            assert sentinel not in rendered


# ── arq_ssl_flag — trivial but pinned ──────────────────────────────

@pytest.mark.parametrize(("flag", "expected"), [(True, True), (False, False)])
def test_arq_ssl_flag(flag: bool, expected: bool) -> None:
    assert arq_ssl_flag(flag) is expected
