"""
Latent-bug regression tests for LLM budget guard Redis TLS (ADR-0002).

Prior to ADR-0002, `app.core.llm` passed `settings.redis_url` directly to
`aioredis.from_url()` without consulting `settings.redis_ssl`. With
`redis_ssl=True` configured, token blacklist + rate-limit traveled over
TLS while LLM budget tracking traveled plaintext — a partial rollout that
silently splits the TLS posture. These tests prevent regression.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.usefixtures("hermetic_settings_env")


@pytest.mark.asyncio
async def test_llm_budget_redis_uses_tls_scheme_when_ssl_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The budget-guard Redis connection must be opened with the
    reconciled URL (rediss:// when redis_ssl_enabled=True), not the raw
    `settings.redis_url` (which may be `redis://...`).
    """
    import app.core.llm as llm_module
    from app.core.config import settings

    # Reset module-level cached connection so the test triggers a fresh
    # from_url() call and sees fresh settings values.
    monkeypatch.setattr(llm_module, "_budget_redis", None, raising=False)

    captured: dict[str, Any] = {}

    def _spy(url: str, **kwargs: Any) -> MagicMock:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MagicMock()

    monkeypatch.setattr(llm_module.aioredis, "from_url", _spy)

    monkeypatch.setattr(settings, "redis_url", "redis://h:6379/0")
    monkeypatch.setattr(settings, "redis_ssl", True)

    # Invoke whatever accessor allocates the budget Redis client.
    await _invoke_budget_accessor(llm_module)

    url = captured.get("url")
    assert url is not None, "aioredis.from_url was not called"
    assert url.startswith("rediss://"), (
        f"LLM budget guard ignored redis_ssl_enabled — opened plaintext "
        f"connection: {url!r}"
    )


@pytest.mark.asyncio
async def test_llm_budget_redis_uses_plain_scheme_when_ssl_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Symmetric: with TLS off, no scheme promotion."""
    import app.core.llm as llm_module
    from app.core.config import settings

    monkeypatch.setattr(llm_module, "_budget_redis", None, raising=False)

    captured: dict[str, Any] = {}

    def _spy(url: str, **kwargs: Any) -> MagicMock:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MagicMock()

    monkeypatch.setattr(llm_module.aioredis, "from_url", _spy)
    monkeypatch.setattr(settings, "redis_url", "redis://h:6379/0")
    monkeypatch.setattr(settings, "redis_ssl", False)

    await _invoke_budget_accessor(llm_module)

    url = captured.get("url")
    assert url is not None
    assert url.startswith("redis://") and not url.startswith("rediss://")


async def _invoke_budget_accessor(llm_module: Any) -> None:
    """Call whichever public accessor instantiates the budget Redis
    client. The exact name is implementation-private; we probe the
    common candidates and fail loudly if none exists so a future rename
    is caught here rather than silently skipping the regression.
    """
    # Candidate names, in order of likelihood.
    for candidate in (
        "_get_budget_redis",
        "get_budget_redis",
        "_budget_redis_client",
    ):
        func = getattr(llm_module, candidate, None)
        if func is None:
            continue
        result = func()
        # Support both sync and async accessors.
        if hasattr(result, "__await__"):
            await result
        return

    # Fall back: if the module exposes a class-level accessor or only
    # connects lazily inside a budget-check call, call that instead.
    check = getattr(llm_module, "check_budget", None)
    if check is not None:
        # Budget checks typically take a provider + cost.
        res = check("anthropic", 0.0)
        if hasattr(res, "__await__"):
            await res
        return

    raise AssertionError(
        "Could not locate the budget Redis accessor on app.core.llm; "
        "add the current symbol to `_invoke_budget_accessor` candidates."
    )


# ── Consolidation regression ─────────────────────────────────────────

def test_no_direct_redis_from_url_outside_helper() -> None:
    """Every `Redis.from_url` / `aioredis.from_url` caller in app/ must
    route through the reconciliation helper. A new consumer that imports
    redis directly and bypasses the helper re-opens the exact drift this
    ADR closes.

    Uses `tokenize` to scan only real code tokens — docstrings and
    comments that legitimately *discuss* the anti-pattern (e.g. in a
    "Routes through … any direct `Redis.from_url(...)` call would …"
    sentence) are not flagged.

    Exemptions must be explicit: the helper module itself, plus any
    source line carrying a `# redis-ssl-exempt: <reason>` marker.
    """
    import pathlib
    import tokenize

    app_dir = pathlib.Path(__file__).parent.parent / "app"
    offenders: list[str] = []
    call_symbols = {"Redis", "aioredis", "redis"}

    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "redis_ssl.py":
            continue

        source_lines = py_file.read_text(encoding="utf-8").splitlines()

        with py_file.open("rb") as fh:
            tokens = list(tokenize.tokenize(fh.readline))

        # Walk tokens looking for: NAME(<symbol>) OP('.') NAME('from_url') OP('(')
        for i in range(len(tokens) - 3):
            t0, t1, t2, t3 = tokens[i : i + 4]
            if (
                t0.type == tokenize.NAME and t0.string in call_symbols
                and t1.type == tokenize.OP and t1.string == "."
                and t2.type == tokenize.NAME and t2.string == "from_url"
                and t3.type == tokenize.OP and t3.string == "("
            ):
                lineno = t0.start[0]
                line = source_lines[lineno - 1] if lineno <= len(source_lines) else ""
                if "redis-ssl-exempt" in line:
                    continue
                offenders.append(
                    f"{py_file.relative_to(app_dir)}:{lineno}: {line.strip()}"
                )

    assert not offenders, (
        "Direct `Redis.from_url(...)` calls that bypass `app.core.redis_ssl` "
        "were found. Route through `resolve_redis_url(...)` or add a "
        "`# redis-ssl-exempt: <reason>` comment to the same line:\n  "
        + "\n  ".join(offenders)
    )
