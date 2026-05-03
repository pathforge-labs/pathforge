"""
PathForge API — Query Recorder (T2 / Sprint 55, ADR-0007)
==========================================================

Per-request DB query counter, plus the SQLAlchemy event listener that
populates it.  Engine-name derivation supports the Causality Ledger:
every counter is keyed by the route's principal engine (``career_dna``,
``threat_radar``, …) so :mod:`app.services.analytics_service` can later
correlate user-success events back to the engine chain that touched the
user.

Lifecycle
---------

1. :class:`app.core.middleware.QueryBudgetMiddleware` allocates a fresh
   :class:`QueryCounter` per request and stores it in
   :data:`query_counter_var`.
2. :func:`register_query_counter_listener` (called at app startup)
   subscribes to SQLAlchemy's ``after_cursor_execute`` event on the
   shared async engine.  Each cursor execution increments the active
   counter, if any.
3. The middleware reads the final count after the response body is
   built and compares it to the route's declared budget
   (:func:`app.core.query_budget.get_route_query_budget`).

Background tasks (ARQ workers, startup probes) run without an active
counter; the listener short-circuits in that case so non-request DB I/O
is uncounted by design.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

#: Sentinel returned from :func:`derive_engine_name` when no segment is
#: available (root path, health probe, etc.).  Kept as a label so
#: downstream telemetry doesn't have to carry an Optional.
DEFAULT_ENGINE_NAME = "unscoped"

# Path prefix the API mounts under. We strip this before deriving the
# principal engine so paths like ``/api/v1/career-dna/dashboard`` map
# to ``career_dna`` rather than ``api``.
_API_PREFIX_SEGMENTS = ("api", "v1")


@dataclass
class QueryCounter:
    """A per-request counter of SQL statements executed.

    Engine name is captured at allocation time and is treated as
    immutable — re-keying mid-request would corrupt the Causality
    Ledger's invariants.
    """

    engine_name: str
    count: int = field(default=0)

    def increment(self) -> None:
        self.count += 1


#: ContextVar carrying the active :class:`QueryCounter`.  ``None`` outside
#: a request scope (e.g. ARQ jobs, startup hooks) so the listener can
#: short-circuit cleanly.
query_counter_var: ContextVar[QueryCounter | None] = ContextVar(
    "query_counter", default=None
)

# Module-level guard ensures :func:`register_query_counter_listener` is
# idempotent across test-suite re-imports and uvicorn auto-reload.
_listener_registered = False


def derive_engine_name(path: str) -> str:
    """Return the principal engine label for a request path.

    The label is the **first non-prefix segment** with hyphens
    normalised to underscores.  ``/api/v1/career-dna/dashboard`` →
    ``career_dna``, ``/api/v1/auth/login`` → ``auth``.  Paths shorter
    than the prefix (e.g. ``/health/ready``) yield
    :data:`DEFAULT_ENGINE_NAME`.
    """
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return DEFAULT_ENGINE_NAME

    # Skip the API prefix if present.
    if (
        len(segments) >= len(_API_PREFIX_SEGMENTS)
        and tuple(segments[: len(_API_PREFIX_SEGMENTS)]) == _API_PREFIX_SEGMENTS
    ):
        segments = segments[len(_API_PREFIX_SEGMENTS) :]
    elif segments[0] == _API_PREFIX_SEGMENTS[0]:
        # Forward-compat: tolerate ``/api/<engine>`` without the version
        # segment, in case a future router mounts above v1.
        segments = segments[1:]

    if not segments:
        return DEFAULT_ENGINE_NAME

    return segments[0].replace("-", "_")


def _on_after_cursor_execute(
    _conn: Any,
    _cursor: Any,
    _statement: str,
    _parameters: Any,
    _context: Any,
    _executemany: bool,
) -> None:
    """SQLAlchemy event hook — increments the active counter, if any.

    Signature matches ``sqlalchemy.event.listen`` for
    ``after_cursor_execute`` on a Connection / Engine.  Argument names
    are prefixed with ``_`` because we don't read them; we count
    *executions*, not their detail.
    """
    counter = query_counter_var.get()
    if counter is None:
        return
    counter.increment()


def register_query_counter_listener() -> None:
    """Subscribe the counter listener to **every** SQLAlchemy engine.

    Listening on the :class:`sqlalchemy.engine.Engine` *class* (rather
    than a specific engine instance) means the production async engine,
    the conftest in-memory sqlite engine, and any future per-tenant
    engine all emit through the same handler.  The handler short-
    circuits when no :class:`QueryCounter` is installed in the current
    context, so non-request DB I/O (background ARQ jobs, Alembic
    migrations) is uncounted by design.

    Idempotent: safe to call from multiple startup paths (FastAPI
    lifespan, conftest, ARQ worker bootstrap) without risk of double
    counting.
    """
    global _listener_registered
    if _listener_registered:
        return

    event.listen(Engine, "after_cursor_execute", _on_after_cursor_execute)
    _listener_registered = True
    logger.debug("QueryCounter listener registered on Engine class")
