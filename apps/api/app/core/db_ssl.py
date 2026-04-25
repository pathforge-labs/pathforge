"""
PathForge API — Database TLS context builder
==============================================
Hardened asyncpg `connect_args` for TLS negotiation. Kept as a
side-effect-free module so `alembic/env.py` can import it without
spinning up the runtime engine defined in `app.core.database`.

See ADR-0001 for the decision rationale.
"""
from __future__ import annotations

import ssl
from typing import Any


def build_connect_args(enabled: bool) -> dict[str, Any]:
    """Return asyncpg connect_args for the requested TLS posture.

    Pure function — takes the resolved boolean rather than reading module
    state, so tests and migration bootstrapping can exercise it without the
    `settings` singleton.

    When `enabled` is True the context enforces:
    - `CERT_REQUIRED` — reject connections to any host presenting no cert.
    - `check_hostname=True` — validate SAN matches the DB hostname.
    - `minimum_version=TLSv1_2` — no legacy TLS/SSL.

    The CA bundle is the system default (loaded by
    `ssl.create_default_context`). We do not pin; see ADR-0001 alternative E.
    """
    if not enabled:
        return {}

    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return {"ssl": ctx}
