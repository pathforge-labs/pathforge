"""
PathForge API — Database TLS context builder
==============================================
Hardened asyncpg `connect_args` for TLS negotiation. Kept as a
side-effect-free module so `alembic/env.py` can import it without
spinning up the runtime engine defined in `app.core.database`.

See ADR-0001 (and its 2026-05-08 corrigendum) for the decision rationale.
"""
from __future__ import annotations

import ssl
from pathlib import Path
from typing import Any

import certifi

# ──────────────────────────────────────────────────────────────────────
# Trust store composition
# ──────────────────────────────────────────────────────────────────────
# Supabase's Supavisor pooler endpoints (`*.pooler.supabase.com`) present
# a chain rooted at `Supabase Root 2021 CA` — a Supabase-private root
# that is NOT in any public WebPKI bundle (Mozilla/certifi, distro
# bundles, AWS RDS bundle). OpenSSL rejects the chain with
# `X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN` against any standard trust
# store.
#
# Empirically verified 2026-05-08 by direct probe of
# `aws-0-eu-west-1.pooler.supabase.com:5432`:
#   depth=0  CN=*.pooler.supabase.com               (Supabase-issued leaf)
#   depth=1  CN=Supabase Intermediate 2021 CA
#   depth=2  CN=Supabase Root 2021 CA               (self-signed, private)
#
# The cert file in `certs/supabase-prod-ca-2021.crt` is the canonical
# Supabase root distributed via `supabase/cli` (Go embed). SHA-256 of
# the X.509 cert (not the file bytes):
#   80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:
#   5A:FE:F6:07:D0:7B:72:E6:CA:FA
# Validity: 2021-04-28 → 2031-04-26 (rotation playbook in ADR-0001).
#
# We UNION the Supabase root onto the Mozilla bundle (`certifi.where()`)
# rather than replacing it, so the trust store still validates:
#   - Direct Supabase DB endpoints (`db.<ref>.supabase.co`, Let's Encrypt)
#   - Any non-Supabase Postgres provider (RDS, Neon, etc.)
#   - Future migration off Supabase pooler
# in addition to the pooler itself.
# ──────────────────────────────────────────────────────────────────────

# Path resolves correctly in both layouts:
#   - Local dev: <repo>/apps/api/app/core/db_ssl.py → <repo>/apps/api/certs/
#   - Container: /app/app/core/db_ssl.py            → /app/certs/
_SUPABASE_CA_BUNDLE = (
    Path(__file__).resolve().parent.parent.parent / "certs" / "supabase-prod-ca-2021.crt"
)


def build_connect_args(enabled: bool) -> dict[str, Any]:
    """Return asyncpg connect_args for the requested TLS posture.

    Pure function — takes the resolved boolean rather than reading module
    state, so tests and migration bootstrapping can exercise it without
    the `settings` singleton.

    When `enabled` is True the context enforces:
    - `CERT_REQUIRED` — reject connections to any host presenting no cert.
    - `check_hostname=True` — validate SAN matches the DB hostname.
    - `minimum_version=TLSv1_2` — no legacy TLS/SSL.

    Trust anchors (UNION):
    - Mozilla CA bundle from `certifi` — covers public WebPKI roots
      (Let's Encrypt, AWS, Google Trust Services, etc.) used by direct
      Supabase DB endpoints and most other Postgres providers.
    - `Supabase Root 2021 CA` — required for the Supabase Supavisor
      pooler endpoints (`*.pooler.supabase.com`), which chain to a
      Supabase-private root not present in any public bundle.

    The Supabase root is vendored at `apps/api/certs/supabase-prod-ca-
    2021.crt`. If that file is missing the function raises `FileNotFoundError`
    at startup rather than silently downgrading to a Supabase-incapable
    trust store — failure must be loud, not silent (ADR-0001 §"No break-
    glass knob").
    """
    if not enabled:
        return {}

    if not _SUPABASE_CA_BUNDLE.is_file():
        raise FileNotFoundError(
            f"Supabase CA bundle missing at {_SUPABASE_CA_BUNDLE}. "
            "The Docker image must include `apps/api/certs/` (see "
            "docker/Dockerfile.api). Refusing to build SSL context "
            "with public-only trust — would fail against pooler at "
            "runtime."
        )

    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.load_verify_locations(cafile=str(_SUPABASE_CA_BUNDLE))
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return {"ssl": ctx}
