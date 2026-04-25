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


def resolve_redis_url(url: str, ssl_enabled: bool, environment: str) -> str:
    """Reconcile `REDIS_URL` scheme with `ssl_enabled` (ADR-0002).

    Reconciliation rules — upgrade-only; downgrade is never silent:

    - `redis://` + True  → upgrade scheme to `rediss://` (+ WARN log).
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

    if scheme == "redis" and ssl_enabled:
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
