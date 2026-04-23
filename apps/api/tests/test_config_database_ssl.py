"""
Config resolver + guard tests for `database_ssl` (ADR-0001).

Verifies:
- Environment-aware default: prod → True, else → False.
- Explicit overrides win in non-prod.
- `ENVIRONMENT=production` + explicit `database_ssl=False` raises.
- `DATABASE_URL` ssl/sslmode query params are stripped with a warning.

All tests instantiate `Settings` directly with `_env_file=None` to keep the
suite hermetic — no reliance on ambient env vars or the module-level
singleton.
"""
from __future__ import annotations

import logging

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def _scrub_ambient_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every env var this module exercises so ambient process state
    (developer shells with `DATABASE_URL=…?sslmode=require` exported, or
    CI running under `ENVIRONMENT=testing`) cannot silently shadow the
    kwargs each test passes. Without this, a matrix test that omits e.g.
    `database_url` would inherit whatever is in the environment.
    """
    for name in (
        "DATABASE_URL",
        "DATABASE_SSL",
        "ENVIRONMENT",
        "JWT_SECRET",
        "JWT_REFRESH_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

# Valid JWT secrets that do NOT collide with _INSECURE_JWT_DEFAULTS.
# Using two different values so the "secrets must differ" guard is satisfied.
_SECRET_A = "a" * 40
_SECRET_B = "b" * 40


def _make_settings(**overrides: object) -> Settings:
    """Build a hermetic Settings instance with safe JWT defaults."""
    base: dict[str, object] = {
        "_env_file": None,
        "jwt_secret": _SECRET_A,
        "jwt_refresh_secret": _SECRET_B,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# ── Environment-aware default resolution ─────────────────────────────

@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ("development", False),
        ("testing", False),
        ("staging", False),
        ("production", True),
    ],
)
def test_ssl_auto_derives_from_environment_when_unset(
    environment: str, expected: bool,
) -> None:
    s = _make_settings(environment=environment)
    assert s.database_ssl is expected


# ── Explicit overrides ───────────────────────────────────────────────

def test_explicit_true_honoured_in_development() -> None:
    s = _make_settings(environment="development", database_ssl=True)
    assert s.database_ssl is True


def test_explicit_false_honoured_in_development() -> None:
    s = _make_settings(environment="development", database_ssl=False)
    assert s.database_ssl is False


def test_explicit_true_honoured_in_production() -> None:
    s = _make_settings(environment="production", database_ssl=True)
    assert s.database_ssl is True


# ── Production downgrade guard ───────────────────────────────────────

def test_explicit_false_in_production_raises() -> None:
    with pytest.raises(ValueError, match="DATABASE_SSL=false is forbidden"):
        _make_settings(environment="production", database_ssl=False)


# ── DATABASE_URL SSL query-parameter sanitizer ───────────────────────

@pytest.mark.parametrize(
    ("url_in", "expected_url"),
    [
        # No ssl params — untouched
        (
            "postgresql+asyncpg://u:p@h:5432/db",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        # sslmode stripped, other params preserved
        (
            "postgresql+asyncpg://u:p@h:5432/db?sslmode=require",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgresql+asyncpg://u:p@h:5432/db?sslmode=require&application_name=pf",
            "postgresql+asyncpg://u:p@h:5432/db?application_name=pf",
        ),
        # ssl= stripped (asyncpg dialect flavour)
        (
            "postgresql+asyncpg://u:p@h:5432/db?ssl=true",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        # Case insensitive key match
        (
            "postgresql+asyncpg://u:p@h:5432/db?SSLMode=verify-full",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        # Preserve non-ssl params when stripping
        (
            "postgresql+asyncpg://u:p@h:5432/db?application_name=pf&sslmode=require&pool_size=5",
            "postgresql+asyncpg://u:p@h:5432/db?application_name=pf&pool_size=5",
        ),
        # Widened sanitiser: all libpq ssl* directives stripped
        # (sslcert, sslkey, sslrootcert, sslcrl, sslnegotiation, sslpassword)
        (
            "postgresql+asyncpg://u:p@h:5432/db?sslrootcert=/tmp/ca.pem&sslcert=/tmp/c.pem",
            "postgresql+asyncpg://u:p@h:5432/db",
        ),
        (
            "postgresql+asyncpg://u:p@h:5432/db?sslnegotiation=direct&application_name=pf",
            "postgresql+asyncpg://u:p@h:5432/db?application_name=pf",
        ),
    ],
)
def test_database_url_ssl_params_stripped(
    url_in: str, expected_url: str, caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        s = _make_settings(environment="development", database_url=url_in)
    assert s.database_url == expected_url
    if url_in != expected_url:
        assert any(
            "stripped" in record.message.lower() for record in caplog.records
        ), "Expected a WARNING log when stripping SSL params"


# ── Full 18-cell matrix (environment × explicit × url param) ─────────

@pytest.mark.parametrize("environment", ["development", "testing", "production"])
@pytest.mark.parametrize("explicit", [None, True, False])
@pytest.mark.parametrize(
    "url_suffix", ["", "?sslmode=require", "?ssl=true"],
)
def test_ssl_resolution_matrix(
    environment: str, explicit: bool | None, url_suffix: str,
) -> None:
    """Every combination behaves deterministically.

    - production + explicit False → ValueError.
    - production + (None | True) → database_ssl True.
    - non-prod + None → False.
    - non-prod + True → True.
    - non-prod + False → False.
    - URL ssl params stripped in every cell regardless of other outcomes.
    """
    base_url = "postgresql+asyncpg://u:p@h:5432/db"
    overrides: dict[str, object] = {
        "environment": environment,
        "database_url": base_url + url_suffix,
    }
    if explicit is not None:
        overrides["database_ssl"] = explicit

    if environment == "production" and explicit is False:
        with pytest.raises(ValueError, match="DATABASE_SSL=false is forbidden"):
            _make_settings(**overrides)
        return

    s = _make_settings(**overrides)

    # Expected SSL resolution
    if explicit is True:
        assert s.database_ssl is True
    elif explicit is False:
        assert s.database_ssl is False
    else:
        assert s.database_ssl is (environment == "production")

    # URL always ends up clean
    assert "sslmode" not in s.database_url.lower()
    assert "ssl=" not in s.database_url.lower()


# ── Regression guard: database_ssl is never None post-validation ────

@pytest.mark.parametrize("environment", ["development", "testing", "production"])
def test_database_ssl_is_bool_after_validation(environment: str) -> None:
    s = _make_settings(environment=environment)
    assert isinstance(s.database_ssl, bool)


# ── Credential-leak regression: DSN must NEVER appear in logs ───────

def test_url_sanitiser_never_logs_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If a DSN carrying credentials is stripped, the WARNING log line must
    not include username, password, host, or the full URL itself.

    Regression guard for a credential-leak-via-logs class of bugs: a future
    change that helpfully interpolates the URL into the warning would pipe
    the Supabase production password into Railway/Sentry logs.
    """
    leaky_dsn = (
        "postgresql+asyncpg://leakuser:leakpass@leakhost:5432/db"
        "?sslmode=require"
    )
    with caplog.at_level(logging.WARNING, logger="app.core.config"):
        _make_settings(environment="development", database_url=leaky_dsn)

    assert caplog.records, "Expected a WARNING log when stripping SSL params"
    for record in caplog.records:
        rendered = record.getMessage()
        for sentinel in ("leakuser", "leakpass", "leakhost", leaky_dsn):
            assert sentinel not in rendered, (
                f"Credential-leak regression: {sentinel!r} appeared in log: "
                f"{rendered!r}"
            )


# ── Validator ordering regression ───────────────────────────────────

def test_prod_downgrade_guard_fires_even_with_ssl_url_param() -> None:
    """Sanitiser runs before the guard, but the guard MUST still fire.

    Pins the invariant that the prod-downgrade guard inspects the resolved
    boolean (not URL state), so no reordering of the validators can
    short-circuit the fail-fast behaviour.
    """
    with pytest.raises(ValueError, match="DATABASE_SSL=false is forbidden"):
        _make_settings(
            environment="production",
            database_ssl=False,
            database_url="postgresql+asyncpg://u:p@h:5432/db?sslmode=require",
        )
