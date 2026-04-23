"""
Unit tests for the Cloudflare Turnstile CAPTCHA verifier.

Covers: dev-mode skip, missing token, success, failure,
and httpx errors in both production and dev environments.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ──────────────────────────────────────────────────────


def _make_httpx_response(success: bool, error_codes: list[str] | None = None) -> MagicMock:
    resp = MagicMock()
    payload = {"success": success}
    if error_codes is not None:
        payload["error-codes"] = error_codes
    resp.json.return_value = payload
    return resp


# ── Dev mode (no secret key) ──────────────────────────────────────


@pytest.mark.asyncio
class TestTurnstileDevMode:
    async def test_returns_true_when_no_secret_key(self) -> None:
        with patch("app.core.turnstile.settings") as mock_settings:
            mock_settings.turnstile_secret_key = ""
            from app.core.turnstile import verify_turnstile_token

            result = await verify_turnstile_token("any-token")
        assert result is True

    async def test_returns_true_even_with_none_token_in_dev(self) -> None:
        with patch("app.core.turnstile.settings") as mock_settings:
            mock_settings.turnstile_secret_key = ""
            from app.core.turnstile import verify_turnstile_token

            result = await verify_turnstile_token(None)
        assert result is True


# ── Production mode ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestTurnstileProductionMode:
    async def test_raises_400_when_no_token(self) -> None:
        with patch("app.core.turnstile.settings") as mock_settings:
            mock_settings.turnstile_secret_key = "secret-key"
            mock_settings.is_production = True

            from app.core.turnstile import verify_turnstile_token

            with pytest.raises(HTTPException) as exc_info:
                await verify_turnstile_token(None)

        assert exc_info.value.status_code == 400
        assert "CAPTCHA" in exc_info.value.detail

    async def test_returns_true_on_successful_verification(self) -> None:
        fake_response = _make_httpx_response(success=True)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=fake_response)

        with patch("app.core.turnstile.settings") as mock_settings, \
             patch("app.core.turnstile.httpx.AsyncClient", return_value=mock_client):
            mock_settings.turnstile_secret_key = "test-secret"
            mock_settings.is_production = True

            from app.core.turnstile import verify_turnstile_token

            result = await verify_turnstile_token("valid-token")

        assert result is True

    async def test_raises_400_on_failed_verification(self) -> None:
        fake_response = _make_httpx_response(
            success=False, error_codes=["invalid-input-response"]
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=fake_response)

        with patch("app.core.turnstile.settings") as mock_settings, \
             patch("app.core.turnstile.httpx.AsyncClient", return_value=mock_client):
            mock_settings.turnstile_secret_key = "test-secret"
            mock_settings.is_production = True

            from app.core.turnstile import verify_turnstile_token

            with pytest.raises(HTTPException) as exc_info:
                await verify_turnstile_token("bad-token")

        assert exc_info.value.status_code == 400
        assert "CAPTCHA verification failed" in exc_info.value.detail

    async def test_raises_503_on_httpx_error_in_production(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with patch("app.core.turnstile.settings") as mock_settings, \
             patch("app.core.turnstile.httpx.AsyncClient", return_value=mock_client):
            mock_settings.turnstile_secret_key = "test-secret"
            mock_settings.is_production = True

            from app.core.turnstile import verify_turnstile_token

            with pytest.raises(HTTPException) as exc_info:
                await verify_turnstile_token("any-token")

        assert exc_info.value.status_code == 503

    async def test_returns_true_on_httpx_error_in_dev(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with patch("app.core.turnstile.settings") as mock_settings, \
             patch("app.core.turnstile.httpx.AsyncClient", return_value=mock_client):
            mock_settings.turnstile_secret_key = "test-secret"
            mock_settings.is_production = False

            from app.core.turnstile import verify_turnstile_token

            result = await verify_turnstile_token("any-token")

        assert result is True

    async def test_posts_secret_and_token_to_cloudflare(self) -> None:
        fake_response = _make_httpx_response(success=True)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=fake_response)

        with patch("app.core.turnstile.settings") as mock_settings, \
             patch("app.core.turnstile.httpx.AsyncClient", return_value=mock_client):
            mock_settings.turnstile_secret_key = "my-secret"
            mock_settings.is_production = True

            from app.core.turnstile import verify_turnstile_token

            await verify_turnstile_token("user-token")

        call_kwargs = mock_client.post.call_args
        posted_data = call_kwargs[1]["data"] if "data" in call_kwargs[1] else call_kwargs[0][1]
        assert posted_data["secret"] == "my-secret"
        assert posted_data["response"] == "user-token"
