"""
Tests for the Content-Security-Policy header (Sprint 39 audit F33).

The middleware emits two distinct CSP profiles:

- **Production**: ``default-src 'none'`` — JSON API only, no browser
  context legitimately renders these responses.
- **Development**: relaxed enough for Swagger UI / ReDoc to load
  scripts and styles from ``cdn.jsdelivr.net``.

These tests pin both profiles so a future "let me just allow
unsafe-eval" patch fails CI loudly.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings

pytestmark = pytest.mark.asyncio


# ── Header presence ───────────────────────────────────────────────


async def test_csp_header_is_set_on_every_response(client: AsyncClient) -> None:
    """Even health-check responses carry a CSP."""
    response = await client.get("/api/v1/health")
    assert "content-security-policy" in {k.lower() for k in response.headers}


async def test_csp_header_set_on_4xx_responses(client: AsyncClient) -> None:
    """Error responses must also carry the CSP — they often render in browsers."""
    response = await client.get("/api/v1/this-route-does-not-exist")
    assert response.status_code == 404
    assert "content-security-policy" in {k.lower() for k in response.headers}


# ── Development profile ───────────────────────────────────────────


async def test_csp_dev_profile_allows_self_and_jsdelivr(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In dev/test, Swagger UI's CDN must be reachable."""
    monkeypatch.setattr(settings, "environment", "development")
    response = await client.get("/api/v1/health")
    csp = response.headers["content-security-policy"]

    # Default-src must be 'self', not 'none', so OpenAPI docs work.
    assert "default-src 'self'" in csp
    # Script + style sources must include the CDN that hosts the
    # Swagger UI bundle.
    assert "https://cdn.jsdelivr.net" in csp
    assert "script-src" in csp
    assert "style-src" in csp


# ── Production profile ────────────────────────────────────────────


async def test_csp_production_profile_is_strict(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production CSP forbids everything by default."""
    monkeypatch.setattr(settings, "environment", "production")
    response = await client.get("/api/v1/health")
    csp = response.headers["content-security-policy"]

    # Lock down the unscoped default — the most important directive.
    assert "default-src 'none'" in csp
    # No script source in production — JSON responses never execute JS.
    assert "script-src" not in csp
    # Inline event handlers and external CDNs are forbidden by the
    # absence of a permissive script/style allow-list.
    assert "cdn.jsdelivr.net" not in csp
    assert "'unsafe-inline'" not in csp


async def test_csp_blocks_iframe_embedding(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """frame-ancestors 'none' mirrors X-Frame-Options: DENY."""
    monkeypatch.setattr(settings, "environment", "production")
    response = await client.get("/api/v1/health")
    csp = response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp


async def test_csp_blocks_form_submissions(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """form-action 'none' prevents stray <form> targets in production responses."""
    monkeypatch.setattr(settings, "environment", "production")
    response = await client.get("/api/v1/health")
    csp = response.headers["content-security-policy"]
    assert "form-action 'none'" in csp


async def test_csp_blocks_base_uri_hijack(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """base-uri 'none' prevents <base href=...> attacks via injected HTML."""
    monkeypatch.setattr(settings, "environment", "production")
    response = await client.get("/api/v1/health")
    csp = response.headers["content-security-policy"]
    assert "base-uri 'none'" in csp


# ── Companion headers ─────────────────────────────────────────────


async def test_x_frame_options_still_set(client: AsyncClient) -> None:
    """Belt-and-suspenders: legacy X-Frame-Options remains in place.

    Older browsers ignore CSP frame-ancestors but honour the legacy
    header. Both live until X-Frame-Options is fully obsoleted.
    """
    response = await client.get("/api/v1/health")
    assert response.headers.get("x-frame-options") == "DENY"
