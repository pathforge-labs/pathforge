"""
TLS context construction tests for `build_connect_args` (ADR-0001).

Verifies the asyncpg connect_args returned for both SSL-on and SSL-off
modes. Pure-function signature: `build_connect_args(enabled: bool)`.
"""
from __future__ import annotations

import ssl

from app.core.db_ssl import build_connect_args


def test_empty_dict_when_ssl_disabled() -> None:
    assert build_connect_args(False) == {}


def test_ssl_context_when_ssl_enabled() -> None:
    args = build_connect_args(True)
    assert "ssl" in args
    assert isinstance(args["ssl"], ssl.SSLContext)


def test_ssl_context_requires_cert() -> None:
    ctx = build_connect_args(True)["ssl"]
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_ssl_context_checks_hostname() -> None:
    ctx = build_connect_args(True)["ssl"]
    assert ctx.check_hostname is True


def test_ssl_context_minimum_tls_1_2() -> None:
    ctx = build_connect_args(True)["ssl"]
    assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_ssl_context_uses_system_ca_bundle() -> None:
    """create_default_context loads the system CAs — we don't pin.

    Rationale: Supabase uses a public CA (Let's Encrypt chain); pinning would
    trade a rare risk (CA compromise) for a common risk (rotation breakage).
    ADR-0001 alternative E.
    """
    ctx = build_connect_args(True)["ssl"]
    # At least one trusted cert must be loaded from the system store.
    assert ctx.get_ca_certs() or ctx.get_ca_certs(binary_form=True)


def test_returns_fresh_context_each_call() -> None:
    """Defence-in-depth: do not share SSL context across callers.

    Sharing is safe in CPython today, but returning a fresh context isolates
    callers if one later wants to tweak verify options.
    """
    a = build_connect_args(True)["ssl"]
    b = build_connect_args(True)["ssl"]
    assert a is not b
