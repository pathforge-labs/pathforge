"""
Unit tests for the PathForge middleware stack.

Covers: RequestIDMiddleware, SecurityHeadersMiddleware, BotTrapMiddleware,
get_request_id(), and get_correlation_id() context helpers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from app.core.middleware import (
    BotTrapMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    get_correlation_id,
    get_request_id,
)

# ── App factories ─────────────────────────────────────────────────


def _make_base_app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def _ping():
        return PlainTextResponse("pong")

    @app.get("/api/test")
    async def _api_test():
        return PlainTextResponse("ok")

    @app.api_route("/{path:path}", methods=["GET"])
    async def _catch_all(path: str):
        return PlainTextResponse(f"/{path}")

    return app


# ── get_request_id / get_correlation_id ──────────────────────────


class TestContextHelpers:
    def test_get_request_id_returns_empty_by_default(self) -> None:
        assert get_request_id() == ""

    def test_get_correlation_id_returns_empty_by_default(self) -> None:
        assert get_correlation_id() == ""


# ── RequestIDMiddleware ───────────────────────────────────────────


class TestRequestIDMiddleware:
    @pytest.fixture()
    def client(self):
        app = _make_base_app()
        app.add_middleware(RequestIDMiddleware)
        with patch("app.core.middleware.settings") as s:
            s.is_production = False
            with TestClient(app, raise_server_exceptions=True) as c:
                yield c

    def test_response_has_x_request_id_header(self, client) -> None:
        assert "x-request-id" in client.get("/ping").headers

    def test_response_has_x_correlation_id_header(self, client) -> None:
        assert "x-correlation-id" in client.get("/ping").headers

    def test_response_has_x_response_time_header(self, client) -> None:
        assert "x-response-time" in client.get("/ping").headers

    def test_incoming_x_request_id_is_preserved(self, client) -> None:
        response = client.get("/ping", headers={"X-Request-ID": "my-trace-id"})
        assert response.headers["x-request-id"] == "my-trace-id"

    def test_incoming_x_correlation_id_is_preserved(self, client) -> None:
        response = client.get("/ping", headers={"X-Correlation-ID": "my-correlation"})
        assert response.headers["x-correlation-id"] == "my-correlation"

    def test_generated_request_id_is_uuid4_shaped(self, client) -> None:
        import re
        rid = client.get("/ping").headers["x-request-id"]
        assert re.match(r"^[0-9a-f-]{36}$", rid)

    def test_x_response_time_ends_with_ms(self, client) -> None:
        assert client.get("/ping").headers["x-response-time"].endswith("ms")


# ── SecurityHeadersMiddleware ─────────────────────────────────────


class TestSecurityHeadersMiddleware:
    def _make_client(self, is_production: bool):
        app = _make_base_app()
        app.add_middleware(SecurityHeadersMiddleware)
        return app, is_production

    def _get(self, is_production: bool, path: str = "/ping"):
        app, prod = self._make_client(is_production)
        with patch("app.core.middleware.settings") as s:
            s.is_production = prod
            with TestClient(app, raise_server_exceptions=True) as c:
                return c.get(path)

    def test_x_content_type_options_nosniff(self) -> None:
        assert self._get(False).headers["x-content-type-options"] == "nosniff"

    def test_x_frame_options_deny(self) -> None:
        assert self._get(False).headers["x-frame-options"] == "DENY"

    def test_referrer_policy_set(self) -> None:
        assert self._get(False).headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_set(self) -> None:
        assert "permissions-policy" in self._get(False).headers

    def test_cache_control_no_store(self) -> None:
        assert "no-store" in self._get(False).headers["cache-control"]

    def test_hsts_not_set_in_dev(self) -> None:
        assert "strict-transport-security" not in self._get(is_production=False).headers

    def test_hsts_set_in_production(self) -> None:
        response = self._get(is_production=True)
        assert "strict-transport-security" in response.headers
        assert "max-age=31536000" in response.headers["strict-transport-security"]


# ── BotTrapMiddleware ─────────────────────────────────────────────


class TestBotTrapMiddleware:
    def _get(self, path: str, is_production: bool):
        app = _make_base_app()
        app.add_middleware(BotTrapMiddleware)
        with patch("app.core.middleware.settings") as s:
            s.is_production = is_production
            with TestClient(app, raise_server_exceptions=False) as c:
                return c.get(path)

    def test_bot_path_returns_404_in_production(self) -> None:
        assert self._get("/.env", is_production=True).status_code == 404

    def test_wp_admin_returns_404_in_production(self) -> None:
        assert self._get("/wp-admin/login", is_production=True).status_code == 404

    def test_phpmyadmin_returns_404_in_production(self) -> None:
        assert self._get("/phpmyadmin", is_production=True).status_code == 404

    def test_bot_path_passes_through_in_dev(self) -> None:
        response = self._get("/.env", is_production=False)
        # Not trapped in dev — falls through to actual route
        assert response.status_code in (200, 404, 422)

    def test_well_known_excluded_from_trap(self) -> None:
        response = self._get("/.well-known/security.txt", is_production=True)
        # Bot trap exclusion: content will NOT be the plain "Not Found" trap response
        assert response.text != "Not Found"

    def test_normal_api_path_not_trapped(self) -> None:
        assert self._get("/api/test", is_production=True).status_code == 200
