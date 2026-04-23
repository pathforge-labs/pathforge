"""
Regression tests for ConfigurationError's DSN-leak safety
(ADR-0001 + ADR-0002 supplement, post-security-review).

Pydantic v2 wraps `ValueError` / `AssertionError` raised inside
`@model_validator` into `ValidationError`, whose `.errors()[*]['input']`
dict carries the full validated input — including the `database_url`
and `redis_url` which embed `user:password@host` credentials. Any future
handler that serialises `.errors()` (Sentry's Pydantic integration,
custom error middleware, log-formatter regressions) would leak
the DSN.

`ConfigurationError` inherits from `RuntimeError` — Pydantic does NOT
wrap it — so the exception propagates as-is with only the static message
we author. These tests pin that behaviour and prove no DSN-shaped
sentinel reaches any accessible attribute of the exception.
"""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.errors import ConfigurationError
from app.core.redis_ssl import resolve_redis_url

pytestmark = pytest.mark.usefixtures("hermetic_settings_env")

_SECRET_A = "a" * 40
_SECRET_B = "b" * 40


def _make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "jwt_secret": _SECRET_A,
        "jwt_refresh_secret": _SECRET_B,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _assert_no_dsn_fragments(exc: BaseException, sentinels: list[str]) -> None:
    """Assert that `str(exc)`, `repr(exc)`, and — critically — any
    `ValidationError.errors()[*]['input']` dict is free of credential
    fragments. The `errors()` path is where the DSN could leak if the
    exception were a ValueError/AssertionError.
    """
    rendered_forms: list[str] = [str(exc), repr(exc)]

    errors_method = getattr(exc, "errors", None)
    if callable(errors_method):
        try:
            errors_payload = errors_method()
        except Exception:
            errors_payload = None
        if errors_payload is not None:
            rendered_forms.append(repr(errors_payload))

    for rendered in rendered_forms:
        for fragment in sentinels:
            assert fragment not in rendered, (
                f"DSN-leak regression: fragment {fragment!r} appeared in "
                f"exception representation: {rendered!r}"
            )


# ── Exception type pinning ──────────────────────────────────────────

def test_config_error_is_runtime_error_not_value_error() -> None:
    """Critical invariant: `ConfigurationError` must NOT inherit from
    `ValueError`. Pydantic v2's `@model_validator` wraps ValueError
    into `ValidationError` with the full input dict, which is the
    exact leak path we are closing.
    """
    assert issubclass(ConfigurationError, RuntimeError)
    assert not issubclass(ConfigurationError, ValueError)


# ── DB downgrade guard ─────────────────────────────────────────────

def test_db_downgrade_guard_raises_configuration_error_not_validation_error() -> None:
    leaky_url = "postgresql+asyncpg://leakuser:leakpass@leakhost:5432/db"
    with pytest.raises(ConfigurationError) as exc_info:
        _make_settings(
            environment="production",
            database_ssl=False,
            database_url=leaky_url,
        )
    _assert_no_dsn_fragments(
        exc_info.value,
        ["leakuser", "leakpass", "leakhost", leaky_url],
    )


# ── Redis downgrade guard ──────────────────────────────────────────

def test_redis_downgrade_guard_raises_configuration_error_not_validation_error() -> None:
    leaky_url = "redis://leakuser:leakpass@leakhost:6379/0"
    with pytest.raises(ConfigurationError) as exc_info:
        _make_settings(
            environment="production",
            redis_ssl=False,
            redis_url=leaky_url,
        )
    _assert_no_dsn_fragments(
        exc_info.value,
        ["leakuser", "leakpass", "leakhost", leaky_url],
    )


def test_redis_scheme_conflict_in_prod_raises_configuration_error() -> None:
    """`rediss://` + `redis_ssl=False` + production raises from inside
    `resolve_redis_url`. Must be a ConfigurationError, no DSN leak.
    """
    leaky_url = "rediss://leakuser:leakpass@leakhost:6379/0"
    with pytest.raises(ConfigurationError) as exc_info:
        resolve_redis_url(leaky_url, False, "production")
    _assert_no_dsn_fragments(
        exc_info.value,
        ["leakuser", "leakpass", "leakhost", leaky_url],
    )


# ── JWT insecure-default guard ─────────────────────────────────────

def test_jwt_insecure_default_in_prod_raises_configuration_error() -> None:
    """The JWT guard is the third validator that could have leaked —
    pin its exception type here too.
    """
    with pytest.raises(ConfigurationError):
        _make_settings(
            environment="production",
            jwt_secret="change-me-in-production-use-a-real-secret",
            jwt_refresh_secret=_SECRET_B,
        )


# ── Meta-regression: ValidationError must not surface at all ───────

def test_no_validation_error_surface_on_fatal_config_paths() -> None:
    """Ensures the class hierarchy: any fatal config path raises
    ConfigurationError, and `pytest.raises(Exception)` captures exactly
    that — never a `ValidationError`. Future contributors who
    accidentally re-introduce `raise ValueError(...)` inside a
    `@model_validator` will fail this test.
    """
    from pydantic import ValidationError

    leaky_url = "postgresql+asyncpg://leakuser:leakpass@leakhost:5432/db"
    try:
        _make_settings(
            environment="production",
            database_ssl=False,
            database_url=leaky_url,
        )
    except ValidationError as exc:  # pragma: no cover
        pytest.fail(
            f"Fatal config guard surfaced as ValidationError (DSN-leak "
            f"risk): {exc!r}"
        )
    except ConfigurationError:
        pass  # expected
