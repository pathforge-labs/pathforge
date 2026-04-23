"""
Alembic migration TLS wiring regression test (ADR-0001).

Guards against the class of silent bug where the runtime engine uses TLS
but `alembic upgrade head` connects plaintext because `env.py` was
refactored and dropped the shared `build_connect_args` helper.

Source-level assertions only — `alembic/env.py` runs migrations at import
time and needs a live Alembic context, so behavioural coverage belongs in
a migration integration test (not a unit test). The text-level guards
catch the most plausible regression path: a refactor that preserves
runtime behaviour but accidentally removes the connect_args kwarg.
"""
from __future__ import annotations

import pathlib

_ENV_PY = (
    pathlib.Path(__file__).parent.parent / "alembic" / "env.py"
).read_text(encoding="utf-8")


def test_env_py_imports_build_connect_args() -> None:
    """The shared TLS builder must remain imported."""
    assert "from app.core.db_ssl import build_connect_args" in _ENV_PY


def test_env_py_passes_connect_args_to_engine() -> None:
    """`connect_args=build_connect_args(...)` must be passed to the engine
    factory. Catches a refactor that swaps to a different engine constructor
    without preserving the TLS path.
    """
    assert "connect_args=build_connect_args(" in _ENV_PY


def test_env_py_uses_settings_database_ssl() -> None:
    """The boolean sent to the builder must come from the validated
    `settings.database_ssl_enabled` property — which asserts on a
    future `None` leak and narrows to `bool`. A refactor that calls the
    raw `settings.database_ssl` field (type `bool | None`) would regress
    the invariant established by ADR-0001.
    """
    assert "build_connect_args(settings.database_ssl_enabled)" in _ENV_PY
