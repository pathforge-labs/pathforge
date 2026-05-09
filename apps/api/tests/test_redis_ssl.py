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


# ── ADR-0002 corrigendum (2026-05-09): trusted internal networks ─────
# Railway's platform-internal Redis service (`*.railway.internal`) is
# private to the project, plaintext-only at the daemon, and reachable
# only via the project's internal network. Forcing `rediss://` on this
# endpoint produces a TLS handshake failure at runtime. The corrigendum
# carves out trusted private hostnames from the scheme upgrade.

@pytest.mark.parametrize(
    "internal_url",
    [
        "redis://default:secret@redis.railway.internal:6379",
        "redis://default:secret@redis.railway.internal:6379/0",
        "redis://default:secret@cache.railway.internal:6379",
        "redis://default:secret@svc-name.internal:6379",
    ],
)
def test_redis_internal_url_keeps_plaintext_scheme_in_production(
    internal_url: str,
) -> None:
    """`*.railway.internal` / `*.internal` URLs must NOT be upgraded to
    `rediss://` even when `redis_ssl=True` and `environment=production`.

    Otherwise asyncpg-redis attempts a TLS handshake against a daemon
    that does not speak TLS and the connection fails — see the
    2026-05-09 production deploy chain (issue #49 follow-up).
    """
    out = resolve_redis_url(internal_url, ssl_enabled=True, environment="production")
    assert out == internal_url, (
        f"internal-network URL was rewritten to {out!r}; expected unchanged"
    )
    assert out.startswith("redis://"), "scheme must remain plaintext"


@pytest.mark.parametrize(
    "external_url",
    [
        "redis://default:secret@redis.example.com:6379",
        "redis://default:secret@my-redis.upstash.io:6379",
    ],
)
def test_redis_external_url_still_upgrades_in_production(
    external_url: str,
) -> None:
    """The internal-network exemption must NOT broaden — public/external
    hostnames still get the standard `rediss://` upgrade in production.
    """
    out = resolve_redis_url(external_url, ssl_enabled=True, environment="production")
    assert out.startswith("rediss://"), (
        f"external URL not upgraded to TLS: got {out!r}"
    )


def test_redis_internal_url_logs_info_not_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The internal-network bypass is an INFO event (auditable, not a
    warning). Using WARNING would create false alarms in normal
    operation against a Railway-internal Redis service."""
    import logging

    with caplog.at_level(logging.INFO, logger="app.core.redis_ssl"):
        resolve_redis_url(
            "redis://default:secret@redis.railway.internal:6379",
            ssl_enabled=True,
            environment="production",
        )
    msgs = [
        (rec.levelno, rec.getMessage())
        for rec in caplog.records
        if rec.name == "app.core.redis_ssl"
    ]
    assert any(
        lv == logging.INFO and "trusted internal network" in m for lv, m in msgs
    ), f"expected INFO log for internal-network bypass; got {msgs!r}"
    # And: no credentials should appear (defense-in-depth — same as
    # other tests in this file).
    for _, m in msgs:
        assert "secret" not in m
