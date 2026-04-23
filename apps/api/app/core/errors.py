"""
PathForge API — Shared exception types
========================================

Types that are re-used across `app.core.config`, `app.core.redis_ssl`,
`app.core.db_ssl`, and any other module that participates in the
secure-by-default posture established by ADR-0001 / ADR-0002.

Kept in a dedicated module so `redis_ssl.py` and `db_ssl.py` (both of
which raise on fatal posture violations) do NOT need to import from
`config.py` — avoiding the coupling / partial-import risk that would
arise during Settings() construction.
"""
from __future__ import annotations


class ConfigurationError(RuntimeError):
    """Raised when a production-critical configuration invariant fails.

    Inherits from `RuntimeError`, not `ValueError`: Pydantic v2 wraps
    `ValueError` and `AssertionError` raised inside `@model_validator`
    into `ValidationError`, whose `.errors()[*]['input']` dict carries
    the full validated input — including fields like `database_url` and
    `redis_url` that embed `user:password@host` credentials. Any future
    handler that serialises `.errors()` (Sentry's Pydantic integration,
    custom error middleware, log-formatter regressions) would leak
    DSN credentials.

    Raising a non-ValueError short-circuits Pydantic's wrapping: the
    exception propagates as-is with only the static message we author,
    no DSN surface.

    See ADR-0001 / ADR-0002 security reviews for the regression this
    closes.
    """
