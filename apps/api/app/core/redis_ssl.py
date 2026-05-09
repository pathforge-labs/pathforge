"""
PathForge API — Redis TLS reconciliation helper
=================================================
Shared scheme/flag reconciliation for every Redis consumer (token
blacklist, rate limiter, LLM budget guard, ARQ worker, and any future
caller). Replaces the three previously-duplicated inline rewrites in
`token_blacklist.py`, `rate_limit.py`, and `worker.py`.

See ADR-0002 for the decision rationale.
"""
from __future__ import annotations

import logging
from urllib.parse import urlsplit, urlunsplit

from app.core.errors import ConfigurationError

_logger = logging.getLogger(__name__)

# ADR-0002 corrigendum (2026-05-09): private internal networks are
# trusted endpoints where TLS is neither possible nor required. The
# Railway platform's internal Redis service is reachable only via
# `*.railway.internal` hostnames, the network is private to the
# project, and the Redis daemon listens plaintext on TCP — there is
# no TLS endpoint to negotiate against, and forcing `rediss://`
# produces a `redis.exceptions.ConnectionError` at TLS handshake
# time. The scheme upgrade and the production-downgrade guard both
# skip these hostnames; the connection still does not traverse the
# public internet, so the security posture is preserved.
_INTERNAL_NETWORK_SUFFIXES: tuple[str, ...] = (
    ".railway.internal",
    ".internal",  # generic catch-all for analogous platforms
)


def _is_internal_network(hostname: str | None) -> bool:
    """True if `hostname` is on a trusted private platform network."""
    if not hostname:
        return False
    return any(hostname.endswith(s) for s in _INTERNAL_NETWORK_SUFFIXES)


def resolve_redis_url(url: str, ssl_enabled: bool, environment: str) -> str:
    """Reconcile `REDIS_URL` scheme with `ssl_enabled` (ADR-0002).

    Reconciliation rules — upgrade-only; downgrade is never silent:

    - `redis://` + True  → upgrade scheme to `rediss://` (+ WARN log).
      EXCEPT when the hostname is a trusted internal network (e.g.
      `*.railway.internal`): the scheme is left as `redis://` and the
      caller is expected to skip TLS for that single connection. See
      the corrigendum in `docs/adr/0002-redis-ssl-secure-by-default.md`.
    - `rediss://` + False:
        - `environment == "production"` → raise `ConfigurationError`.
          Scheme is the stricter control surface; a production downgrade
          is treated as a configuration bug, not a preference. A
          `ConfigurationError` (RuntimeError subclass) is used rather
          than `ValueError` so Pydantic v2 does NOT wrap the exception
          into `ValidationError` whose `.errors()` payload would leak the
          full DSN — see `app/core/errors.py` for rationale.
        - Otherwise → scheme wins (WARN log). Flag should be considered
          upgraded by the caller; `Settings` handles this automatically.
    - Concordant cases return `url` unchanged.

    Never interpolates `url` (or any substring of it) into log messages
    — the DSN carries `user:password@host` credentials.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    internal = _is_internal_network(parts.hostname)

    if scheme == "redis" and ssl_enabled:
        if internal:
            # Private platform network — TLS is unavailable at the Redis
            # daemon and the traffic does not leave the project's
            # internal network. Leave the scheme plaintext and emit an
            # INFO log so the choice is auditable.
            _logger.info(
                "REDIS_URL points at a trusted internal network; "
                "leaving scheme 'redis' plaintext despite redis_ssl=True "
                "(ADR-0002 corrigendum 2026-05-09).",
            )
            return url
        upgraded = urlunsplit(("rediss", *parts[1:]))
        _logger.warning(
            "REDIS_URL scheme 'redis' upgraded to 'rediss' to match "
            "redis_ssl=True (ADR-0002).",
        )
        return upgraded

    if scheme == "rediss" and not ssl_enabled:
        if environment == "production":
            msg = (
                "FATAL: REDIS_URL uses the 'rediss://' scheme but "
                "REDIS_SSL=false — these are conflicting TLS directives "
                "and a production downgrade is forbidden (ADR-0002). "
                "Remove the override or set REDIS_SSL=true."
            )
            raise ConfigurationError(msg)
        _logger.warning(
            "REDIS_URL scheme 'rediss' conflicts with redis_ssl=False; "
            "scheme wins (flag upgraded). TLS remains on (ADR-0002).",
        )
        return url  # scheme already carries TLS

    return url


def arq_ssl_flag(ssl_enabled: bool) -> bool:
    """Return the boolean ARQ's `RedisSettings(ssl=...)` takes.

    A one-line wrapper exists for naming clarity: `arq_ssl_flag(...)`
    at a call site reads as "the Redis SSL decision for the ARQ path",
    making the intent explicit and greppable. No transformation today;
    the wrapper is a seam for future evolution (e.g., if ARQ introduces
    an `ssl_context` kwarg).
    """
    return ssl_enabled
