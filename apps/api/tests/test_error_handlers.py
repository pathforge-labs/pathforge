"""
Unit tests for the global error handlers.

Covers all three handlers (LLMError, ValueError, Exception)
and the response schema (_error_response).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from app.core.error_handlers import (
    generic_error_handler,
    llm_error_handler,
    register_error_handlers,
    value_error_handler,
)
from app.core.llm import LLMError


# ── Helpers ──────────────────────────────────────────────────────

_FAKE_REQUEST_ID = "test-request-id-123"


@pytest.fixture(autouse=True)
def _stub_request_id():
    with patch(
        "app.core.error_handlers.get_request_id",
        return_value=_FAKE_REQUEST_ID,
    ):
        yield


def _mock_request() -> MagicMock:
    return MagicMock()


# ── llm_error_handler ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestLLMErrorHandler:
    async def test_returns_503_status(self) -> None:
        exc = LLMError("All tiers exhausted")
        response = await llm_error_handler(_mock_request(), exc)
        assert response.status_code == 503

    async def test_error_type_is_ai_service_unavailable(self) -> None:
        import json

        exc = LLMError("timeout")
        response = await llm_error_handler(_mock_request(), exc)
        body = json.loads(response.body)
        assert body["error"] == "ai_service_unavailable"

    async def test_request_id_in_response(self) -> None:
        import json

        response = await llm_error_handler(_mock_request(), LLMError("err"))
        body = json.loads(response.body)
        assert body["request_id"] == _FAKE_REQUEST_ID

    async def test_detail_message_safe(self) -> None:
        import json

        response = await llm_error_handler(_mock_request(), LLMError("secret"))
        body = json.loads(response.body)
        # Detail should be the generic safe message, not the raw exception text
        assert "temporarily unavailable" in body["detail"]
        assert "secret" not in body["detail"]

    async def test_sentry_import_error_gracefully_handled(self) -> None:
        with patch("builtins.__import__", side_effect=ImportError):
            exc = LLMError("error")
            response = await llm_error_handler(_mock_request(), exc)
        assert response.status_code == 503


# ── value_error_handler ───────────────────────────────────────────


@pytest.mark.asyncio
class TestValueErrorHandler:
    async def test_returns_422_status(self) -> None:
        exc = ValueError("invalid input")
        response = await value_error_handler(_mock_request(), exc)
        assert response.status_code == 422

    async def test_error_type_is_validation_error(self) -> None:
        import json

        response = await value_error_handler(_mock_request(), ValueError("bad"))
        body = json.loads(response.body)
        assert body["error"] == "validation_error"

    async def test_detail_contains_exception_message(self) -> None:
        import json

        response = await value_error_handler(_mock_request(), ValueError("field X is required"))
        body = json.loads(response.body)
        assert "field X is required" in body["detail"]

    async def test_request_id_in_response(self) -> None:
        import json

        response = await value_error_handler(_mock_request(), ValueError("x"))
        body = json.loads(response.body)
        assert body["request_id"] == _FAKE_REQUEST_ID


# ── generic_error_handler ─────────────────────────────────────────


@pytest.mark.asyncio
class TestGenericErrorHandler:
    async def test_returns_500_status(self) -> None:
        exc = RuntimeError("something broke")
        response = await generic_error_handler(_mock_request(), exc)
        assert response.status_code == 500

    async def test_error_type_is_internal_error(self) -> None:
        import json

        response = await generic_error_handler(_mock_request(), RuntimeError("x"))
        body = json.loads(response.body)
        assert body["error"] == "internal_error"

    async def test_detail_does_not_leak_exception_message(self) -> None:
        import json

        response = await generic_error_handler(
            _mock_request(), RuntimeError("super secret db password")
        )
        body = json.loads(response.body)
        assert "super secret db password" not in body["detail"]

    async def test_request_id_in_response(self) -> None:
        import json

        response = await generic_error_handler(_mock_request(), Exception("err"))
        body = json.loads(response.body)
        assert body["request_id"] == _FAKE_REQUEST_ID

    async def test_sentry_import_error_gracefully_handled(self) -> None:
        with patch("builtins.__import__", side_effect=ImportError):
            response = await generic_error_handler(_mock_request(), Exception("err"))
        assert response.status_code == 500


# ── register_error_handlers ───────────────────────────────────────


class TestRegisterErrorHandlers:
    def test_registers_handlers_on_app(self) -> None:
        app = FastAPI()
        initial_count = len(app.exception_handlers)
        register_error_handlers(app)
        assert len(app.exception_handlers) > initial_count

    def test_llm_error_handler_registered(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        assert LLMError in app.exception_handlers

    def test_value_error_handler_registered(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        assert ValueError in app.exception_handlers

    def test_exception_handler_registered(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        assert Exception in app.exception_handlers
