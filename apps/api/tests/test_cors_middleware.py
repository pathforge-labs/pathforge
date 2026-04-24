"""
Tests for the CORS middleware allow-list (Sprint 39 audit F29).

Replaces the ``allow_methods=["*"]`` + ``allow_headers=["*"]``
wildcards with explicit lists. These tests pin the allow-list so a
future "let me just wildcard it" patch breaks visibly rather than
silently re-expanding the attack surface.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


_ALLOWED_ORIGIN = "http://localhost:3000"  # dev-mode CORS allow-list


async def _preflight(
    client: AsyncClient,
    *,
    origin: str = _ALLOWED_ORIGIN,
    method: str = "POST",
    request_headers: str = "Content-Type, Authorization",
) -> tuple[int, dict[str, str]]:
    """Fire an OPTIONS preflight and return (status, headers).

    Starlette's ``CORSMiddleware`` returns 400 with a plaintext body
    for disallowed origins/methods/headers rather than a 200 with an
    empty allow-list, so callers need both values to assert the full
    shape of the policy.
    """
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": request_headers,
        },
    )
    return response.status_code, dict(response.headers)


# ── Allow-list shape ──────────────────────────────────────────────


async def test_cors_allows_standard_rest_methods(client: AsyncClient) -> None:
    """GET/POST/PUT/PATCH/DELETE/OPTIONS are all reachable via CORS."""
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
        status, headers = await _preflight(client, method=method)
        assert status in (200, 204), f"{method} preflight returned {status}"
        allowed = headers.get("access-control-allow-methods", "")
        assert method in allowed, (
            f"method {method} missing from Allow-Methods={allowed!r}"
        )


async def test_cors_blocks_exotic_methods(client: AsyncClient) -> None:
    """TRACE/CONNECT/PROPFIND are actively rejected at preflight.

    These verbs have no legitimate use against a REST API; leaving
    them in ``allow_methods=["*"]`` gave attackers a reflection
    surface (TRACE) and a potential tunneling surface (CONNECT).
    Starlette's ``CORSMiddleware`` returns a 400 with a
    ``Disallowed CORS method`` body rather than an empty allow-list,
    so we assert on the status code.
    """
    for method in ("TRACE", "CONNECT", "PROPFIND"):
        status, headers = await _preflight(client, method=method)
        assert status == 400, (
            f"expected preflight rejection for {method}, got {status}"
        )
        # Defensive: if Starlette ever softens to 200 with empty
        # allow-list, the header check still fails closed.
        allowed = headers.get("access-control-allow-methods", "")
        assert method not in allowed


async def test_cors_allows_expected_request_headers(client: AsyncClient) -> None:
    status, headers = await _preflight(
        client,
        request_headers="Authorization, Content-Type, X-PathForge-Trace, X-Request-ID",
    )
    assert status in (200, 204)
    allowed = headers.get("access-control-allow-headers", "").lower()
    for expected in ("authorization", "content-type", "x-pathforge-trace", "x-request-id"):
        assert expected in allowed, (
            f"header {expected!r} missing from Allow-Headers={allowed!r}"
        )


async def test_cors_does_not_mirror_arbitrary_request_headers(
    client: AsyncClient,
) -> None:
    """A client asking for a header we did not allow-list is rejected.

    With ``allow_headers=["*"]`` Starlette echoed whatever the client
    put in ``Access-Control-Request-Headers``. That silently allowed
    any custom header to traverse the browser's CORS check, which
    undermines any future header-based auth gate (e.g. an internal
    admin header). With the explicit allow-list the preflight now
    rejects the request outright.
    """
    status, headers = await _preflight(
        client,
        request_headers="X-Injected-Debug-Flag",
    )
    assert status == 400
    allowed = headers.get("access-control-allow-headers", "").lower()
    assert "x-injected-debug-flag" not in allowed


# ── Credentials + origin echo ─────────────────────────────────────


async def test_cors_echoes_exact_origin_with_credentials(
    client: AsyncClient,
) -> None:
    """allow_credentials=True must be paired with an exact origin echo.

    A wildcard ``Access-Control-Allow-Origin: *`` combined with
    ``Allow-Credentials: true`` is rejected by every modern browser,
    so the middleware must echo the exact caller origin. If this
    regresses the frontend will silently lose cookies/auth.
    """
    status, headers = await _preflight(client)
    assert status in (200, 204)
    assert headers.get("access-control-allow-credentials") == "true"
    assert headers.get("access-control-allow-origin") == _ALLOWED_ORIGIN


async def test_cors_rejects_unknown_origin(client: AsyncClient) -> None:
    """Origins outside ``effective_cors_origins`` are not reflected."""
    status, headers = await _preflight(client, origin="https://evil.example.com")
    # Starlette rejects disallowed origins with 400. Defence-in-depth:
    # also confirm the attacker's origin is not echoed back.
    assert status == 400
    assert headers.get("access-control-allow-origin") != "https://evil.example.com"


# ── Preflight caching ─────────────────────────────────────────────


async def test_cors_preflight_cache_max_age_set(client: AsyncClient) -> None:
    """Browsers must be able to cache preflights to avoid 2× every request."""
    status, headers = await _preflight(client)
    assert status in (200, 204)
    max_age = headers.get("access-control-max-age")
    assert max_age is not None, "Access-Control-Max-Age missing — preflight won't cache"
    assert int(max_age) >= 60, f"Max-Age={max_age} is absurdly short"
