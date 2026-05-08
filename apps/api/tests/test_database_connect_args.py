"""
TLS context construction tests for `build_connect_args` (ADR-0001).

Verifies the asyncpg connect_args returned for both SSL-on and SSL-off
modes. Pure-function signature: `build_connect_args(enabled: bool)`.
"""
from __future__ import annotations

import ssl
from pathlib import Path

import certifi
import pytest

from app.core.db_ssl import build_connect_args

# ──────────────────────────────────────────────────────────────────────
# Identifiers used in trust-store assertions. The Subject CN match must
# stay in lock-step with the cert vendored at
# `apps/api/certs/supabase-prod-ca-2021.crt`. If Supabase rotates the
# root before its 2031-04-26 expiry, follow the corrigendum playbook in
# `docs/adr/0001-database-ssl-secure-by-default.md` and update both the
# bundle file and this constant.
# ──────────────────────────────────────────────────────────────────────
SUPABASE_ROOT_CN = "Supabase Root 2021 CA"
SUPABASE_CA_PATH = (
    Path(__file__).resolve().parent.parent / "certs" / "supabase-prod-ca-2021.crt"
)


def _trust_store_subject_cns(ctx: ssl.SSLContext) -> set[str]:
    """Extract every commonName subject from a context's trust store."""
    cns: set[str] = set()
    for cert in ctx.get_ca_certs():
        # `cert['subject']` is a tuple-of-tuples-of-tuples like
        # ((('countryName','US'),), (('commonName','Supabase Root 2021 CA'),))
        for rdn in cert.get("subject", ()):
            for attr, value in rdn:
                if attr == "commonName":
                    cns.add(value)
    return cns


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


def test_ssl_context_loads_certifi_mozilla_bundle() -> None:
    """certifi roots remain in the trust store — required for direct
    Supabase DB endpoints (`db.<ref>.supabase.co`, Let's Encrypt) and
    any non-Supabase Postgres provider."""
    ctx = build_connect_args(True)["ssl"]
    cafile = certifi.where()
    assert cafile.endswith("cacert.pem")
    # Mozilla bundle ships >100 roots; sanity-check the count is in the
    # right order of magnitude (loose bound — Mozilla can prune/add).
    assert len(ctx.get_ca_certs()) > 100


def test_ssl_context_loads_supabase_private_root() -> None:
    """Supabase Root 2021 CA must be in the trust store.

    This is the ROOT CAUSE assertion — without this root, the asyncpg
    connection to `*.pooler.supabase.com` fails with OpenSSL error 19
    (`X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN`) and the production
    deployment cannot complete `alembic upgrade head`.

    See ADR-0001 corrigendum (2026-05-08) for chain analysis.
    """
    ctx = build_connect_args(True)["ssl"]
    subjects = _trust_store_subject_cns(ctx)
    assert SUPABASE_ROOT_CN in subjects, (
        f"Supabase Root 2021 CA missing from trust store. "
        f"Loaded subjects (first 5): {sorted(subjects)[:5]}..."
    )


def test_supabase_ca_bundle_file_exists() -> None:
    """The vendored bundle must ship with the package."""
    assert SUPABASE_CA_PATH.is_file(), (
        f"Vendored Supabase CA missing at {SUPABASE_CA_PATH}. "
        f"Re-download from "
        f"https://raw.githubusercontent.com/supabase/cli/main/internal/gen/types/templates/prod-ca-2021.crt"
    )


def test_returns_fresh_context_each_call() -> None:
    """Defence-in-depth: do not share SSL context across callers.

    Sharing is safe in CPython today, but returning a fresh context
    isolates callers if one later wants to tweak verify options.
    """
    a = build_connect_args(True)["ssl"]
    b = build_connect_args(True)["ssl"]
    assert a is not b


def test_missing_supabase_bundle_raises_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the bundle file is missing, the function must raise immediately.

    Per ADR-0001 §"No break-glass knob": failure modes that compromise
    TLS posture (here: silently downgrading to a Supabase-incapable
    trust store) must be loud, not silent.

    The cache on `_validated_supabase_bundle` must be cleared both before
    (so the bad path is seen, not a cached good path from a prior test)
    and after (so subsequent tests don't see the bad path frozen in
    cache).
    """
    from app.core import db_ssl

    monkeypatch.setattr(
        db_ssl, "_SUPABASE_CA_BUNDLE", Path("/nonexistent/path/that-cannot-exist.crt")
    )
    db_ssl._validated_supabase_bundle.cache_clear()
    try:
        with pytest.raises(FileNotFoundError, match="Supabase CA bundle missing"):
            db_ssl.build_connect_args(True)
    finally:
        # Ensure the next test doesn't see the bad path cached.
        db_ssl._validated_supabase_bundle.cache_clear()
