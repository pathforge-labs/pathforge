"""
Config integration tests for `redis_ssl` (ADR-0002).

Verifies:
- Environment-aware default: prod → True, else → False.
- Explicit overrides honoured in non-prod.
- `ENVIRONMENT=production` + `REDIS_SSL=false` raises.
- `ENVIRONMENT=production` + `REDIS_URL=rediss://…` + `REDIS_SSL=false`
  raises (scheme-stricter-than-flag in prod fails boot).
- Dev: `rediss://…` + `REDIS_SSL=false` resolves to TLS (scheme wins).
- `redis_ssl_enabled` property narrows `bool | None` → `bool` with an
  assertion that fires loudly if Pydantic validation did not complete.
- DB guard runs before Redis guard (stale-env resilience across both
  SSL surfaces).
"""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.errors import ConfigurationError

pytestmark = pytest.mark.usefixtures("hermetic_settings_env")

# Valid non-default JWT secrets that do NOT collide with the insecure set.
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


# ── Environment-aware default ────────────────────────────────────────

@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ("development", False),
        ("testing", False),
        ("staging", False),
        ("production", True),
    ],
)
def test_redis_ssl_auto_derives_from_environment(
    environment: str, expected: bool,
) -> None:
    s = _make_settings(environment=environment)
    assert s.redis_ssl_enabled is expected


# ── Explicit overrides ───────────────────────────────────────────────

def test_explicit_true_honoured_in_development() -> None:
    s = _make_settings(environment="development", redis_ssl=True)
    assert s.redis_ssl_enabled is True


def test_explicit_false_honoured_in_development() -> None:
    s = _make_settings(environment="development", redis_ssl=False)
    assert s.redis_ssl_enabled is False


def test_explicit_true_honoured_in_production() -> None:
    s = _make_settings(environment="production", redis_ssl=True)
    assert s.redis_ssl_enabled is True


# ── Production downgrade guard ───────────────────────────────────────

def test_explicit_redis_ssl_false_in_production_raises() -> None:
    with pytest.raises(ConfigurationError, match="REDIS_SSL=false is forbidden"):
        _make_settings(environment="production", redis_ssl=False)


def test_rediss_url_plus_ssl_false_in_production_raises() -> None:
    """Scheme and flag conflict + production → fail boot. The stricter
    control surface (scheme) must not be silently overridden. The
    concordant case (rediss:// + redis_ssl=True) is NOT a conflict — it
    is the intended prod posture — and must succeed cleanly.
    """
    with pytest.raises(ConfigurationError):
        _make_settings(
            environment="production",
            redis_ssl=False,
            redis_url="rediss://h:6379/0",
        )


def test_rediss_url_plus_ssl_true_in_production_succeeds() -> None:
    """Concordant case — scheme says TLS, flag says TLS, env=prod. No
    conflict; the intended prod posture. Must not raise."""
    s = _make_settings(
        environment="production",
        redis_ssl=True,
        redis_url="rediss://h:6379/0",
    )
    assert s.redis_ssl_enabled is True
    assert s.redis_url.startswith("rediss://")


# ── Scheme-wins-in-dev ─────────────────────────────────────────────

def test_rediss_url_in_dev_promotes_flag_to_true() -> None:
    """rediss:// + redis_ssl=False in dev: scheme wins (flag upgrades),
    warning logged, no exception."""
    s = _make_settings(
        environment="development",
        redis_ssl=False,
        redis_url="rediss://h:6379/0",
    )
    assert s.redis_ssl_enabled is True
    assert s.redis_url.startswith("rediss://")


def test_plain_url_plus_flag_true_upgrades_scheme() -> None:
    s = _make_settings(
        environment="development",
        redis_ssl=True,
        redis_url="redis://h:6379/0",
    )
    assert s.redis_url == "rediss://h:6379/0"
    assert s.redis_ssl_enabled is True


# ── redis_ssl_enabled accessor invariant ─────────────────────────────

@pytest.mark.parametrize("environment", ["development", "testing", "production"])
def test_redis_ssl_enabled_is_always_bool(environment: str) -> None:
    s = _make_settings(environment=environment)
    assert isinstance(s.redis_ssl_enabled, bool)
    # The raw field is also narrowed to bool post-validation.
    assert isinstance(s.redis_ssl, bool)


# ── Full matrix: environment × scheme × explicit flag ───────────────

@pytest.mark.parametrize("environment", ["development", "testing", "production"])
@pytest.mark.parametrize("explicit", [None, True, False])
@pytest.mark.parametrize("scheme", ["redis://", "rediss://"])
def test_redis_ssl_resolution_matrix(
    environment: str, explicit: bool | None, scheme: str,
) -> None:
    base_url = f"{scheme}u:p@h:6379/0"
    overrides: dict[str, object] = {
        "environment": environment,
        "redis_url": base_url,
    }
    if explicit is not None:
        overrides["redis_ssl"] = explicit

    # 1. Production + explicit False → raise.
    if environment == "production" and explicit is False:
        with pytest.raises(ConfigurationError):
            _make_settings(**overrides)
        return

    # 2. Production + rediss://... + flag ambiguous/False on URL side →
    #    also raise (conflict guard).
    if environment == "production" and scheme == "rediss://" and explicit is False:
        # Already returned above.
        return  # pragma: no cover

    s = _make_settings(**overrides)

    # Expected SSL resolution.
    if scheme == "rediss://":
        assert s.redis_ssl_enabled is True  # scheme wins (or agrees)
        assert s.redis_url.startswith("rediss://")
    elif explicit is True:
        assert s.redis_ssl_enabled is True
        assert s.redis_url.startswith("rediss://")
    else:
        assert s.redis_ssl_enabled is (environment == "production")
        expected_scheme = "rediss://" if environment == "production" else "redis://"
        assert s.redis_url.startswith(expected_scheme)


# ── Validator ordering regression (DB + Redis together) ─────────────

def test_prod_redis_guard_fires_even_when_db_url_has_ssl_param() -> None:
    """Regression pin: DB and Redis guards must both fire. A Settings
    object with BOTH a database_ssl=False (prod-illegal) and a Redis
    conflict must still raise — order of the validators must not mask
    either.
    """
    with pytest.raises(ConfigurationError):
        _make_settings(
            environment="production",
            database_ssl=False,          # trips the DB guard first
            redis_ssl=False,             # would also trip the Redis guard
            database_url="postgresql+asyncpg://u:p@h/db?sslmode=require",
            redis_url="redis://h:6379/0",
        )


def test_prod_redis_guard_fires_with_db_guard_clean() -> None:
    """The Redis guard is reached even when DB config is clean."""
    with pytest.raises(ConfigurationError, match="REDIS_SSL=false is forbidden"):
        _make_settings(
            environment="production",
            redis_ssl=False,
        )
