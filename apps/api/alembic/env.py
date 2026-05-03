"""
PathForge — Alembic env.py
============================
Async migration environment for Alembic with SQLAlchemy.
"""

import asyncio
import logging
import socket
import sys
import traceback
from logging.config import fileConfig
from urllib.parse import urlsplit

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.core.db_ssl import build_connect_args
from app.models import Base

# Alembic Config object
config = context.config

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


# ──────────────────────────────────────────────────────────────────
# Diagnostic prelude — emits structured signal BEFORE any connection
# is attempted, so an alembic failure during deploy leaves an
# unmistakable trail in Railway logs without exposing credentials.
# Remove this block once production migrations are stable.
# ──────────────────────────────────────────────────────────────────
def _emit_connection_diagnostics() -> None:
    log = logging.getLogger("alembic.diagnostics")
    # Idempotent — env.py can be imported multiple times in the same
    # process (test suites, multiple alembic CLI invocations); skip
    # re-adding the handler to avoid duplicate log lines.
    if not log.handlers:
        log.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "[ALEMBIC-DIAG] %(message)s",
        ))
        log.addHandler(handler)
        log.propagate = False

    parts = urlsplit(settings.database_url)
    # Redact password while still showing whether it is non-empty.
    has_password = bool(parts.password)
    user = parts.username or "(missing)"
    host = parts.hostname or "(missing)"
    port = parts.port or "(default)"
    db = (parts.path or "/").lstrip("/") or "(missing)"
    scheme = parts.scheme or "(missing)"
    log.info("scheme=%s host=%s port=%s user=%s db=%s password_set=%s ssl=%s",
             scheme, host, port, user, db, has_password,
             settings.database_ssl_enabled)

    # DNS pre-flight — separates hostname-resolution failures from
    # auth/TLS/network failures. asyncpg's own error message can be
    # ambiguous when the host doesn't resolve.
    if host and host != "(missing)":
        try:
            infos = socket.getaddrinfo(host, port if isinstance(port, int) else None,
                                       proto=socket.IPPROTO_TCP)
            addrs = sorted({i[4][0] for i in infos})
            log.info("dns_resolved %s → %s", host, addrs)
        except socket.gaierror as e:
            log.error("dns_failed %s → gaierror(%s, %s)", host, e.errno, e.strerror)
        except OSError as e:
            log.error("dns_failed %s → %s: %s", host, type(e).__name__, e)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL scripts)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with a live connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations.

    TLS is negotiated via the shared `build_connect_args` helper so the
    migration path matches the runtime engine (ADR-0001).
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=build_connect_args(settings.database_ssl_enabled),
    )

    # Emit pre-connect diagnostics only here, when an actual connection
    # is imminent — keeps non-migration alembic commands (history,
    # current, check) quiet.
    _emit_connection_diagnostics()
    diag_log = logging.getLogger("alembic.diagnostics")
    try:
        async with connectable.connect() as connection:
            diag_log.info("connect_ok — proceeding with migrations")
            await connection.run_sync(do_run_migrations)
    except Exception as exc:
        # Wide net intentional — surface the exception class + message
        # explicitly so Railway logs carry the actionable signal even
        # if the wrapped traceback is truncated by the log viewer.
        diag_log.error("connect_failed cls=%s msg=%s",
                       type(exc).__name__, exc)
        # Also dump the chained cause if any (asyncpg wraps OSError).
        if exc.__cause__ is not None:
            diag_log.error("caused_by cls=%s msg=%s",
                           type(exc.__cause__).__name__, exc.__cause__)
        diag_log.error("traceback_full:\n%s",
                       "".join(traceback.format_exception(exc)))
        raise
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (applies directly)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
