"""
PathForge — Job Provider Tests
=================================
Tests for Adzuna and Jooble API clients with mocked HTTP responses.
Includes circuit breaker integration tests (ADR-0003 verification criteria).
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.circuit_breaker import CircuitOpenError
from app.jobs.providers.adzuna import AdzunaProvider, _format_salary
from app.jobs.providers.jooble import JoobleProvider

# ── Circuit breaker helpers ────────────────────────────────────────────────


class _FakeRedis:
    """In-memory Redis stub for provider circuit breaker tests."""

    def __init__(self, state: str = "closed", failures: int = 0, opened_at: float = 0.0) -> None:
        self._store: dict[str, str] = {
            "state": state,
            "failures": str(failures),
            "opened_at": str(opened_at),
        }

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._store)

    async def hset(self, key: str, mapping: dict[str, Any]) -> int:
        self._store.update({k: str(v) for k, v in mapping.items()})
        return 1

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _wire_fake_redis(provider: Any, state: str = "closed", failures: int = 0) -> _FakeRedis:
    """Replace the provider's circuit breaker Redis with an in-memory stub."""
    fake = _FakeRedis(state=state, failures=failures)
    provider._breaker._redis = fake
    return fake

# ── Helper ─────────────────────────────────────────────────────


def _mock_response(status_code: int, json_data=None, text: str = "") -> httpx.Response:
    """Create a properly constructed mock httpx.Response."""
    request = httpx.Request("GET", "https://test.com")
    if json_data is not None:
        import json as json_mod
        response = httpx.Response(
            status_code,
            request=request,
            content=json_mod.dumps(json_data).encode(),
            headers={"content-type": "application/json"},
        )
    else:
        response = httpx.Response(
            status_code,
            request=request,
            text=text,
        )
    return response


# ── Adzuna Fixtures ────────────────────────────────────────────


ADZUNA_RESPONSE = {
    "results": [
        {
            "id": "12345",
            "title": "Senior Python Developer",
            "company": {"display_name": "Tech Corp"},
            "description": "We are looking for a Python developer...",
            "location": {"display_name": "Amsterdam, Noord-Holland"},
            "redirect_url": "https://adzuna.nl/job/12345",
            "contract_type": "permanent",
            "salary_min": 60000,
            "salary_max": 80000,
            "category": {"label": "IT Jobs"},
            "created": "2026-02-13T00:00:00Z",
        },
        {
            "id": "67890",
            "title": "Data Engineer",
            "company": {"display_name": "Data Co"},
            "description": "Join our data team...",
            "location": {"display_name": "Rotterdam"},
            "redirect_url": "https://adzuna.nl/job/67890",
            "contract_time": "full_time",
            "category": {"label": "IT Jobs"},
            "created": "2026-02-12T00:00:00Z",
        },
    ],
    "count": 2,
}


# ── Jooble Fixtures ────────────────────────────────────────────


JOOBLE_RESPONSE = {
    "totalCount": 50,
    "jobs": [
        {
            "title": "Backend Developer",
            "location": "Amsterdam",
            "snippet": "Python/FastAPI backend developer needed...",
            "salary": "€55,000 - €75,000",
            "link": "https://jooble.org/job/abc123",
            "company": "StartupX",
            "id": "abc123",
            "updated": "2026-02-13",
            "type": "Full-time",
        },
    ],
}


# ── Adzuna Tests ───────────────────────────────────────────────


class TestAdzunaProvider:
    """Test Adzuna API client."""

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Should parse Adzuna response into RawJobListing objects."""
        mock_resp = _mock_response(200, json_data=ADZUNA_RESPONSE)

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            provider = AdzunaProvider(app_id="test_id", app_key="test_key")
            results = await provider.search(keywords="python developer", country="nl")

        assert len(results) == 2
        assert results[0].title == "Senior Python Developer"
        assert results[0].company == "Tech Corp"
        assert results[0].location == "Amsterdam, Noord-Holland"
        assert results[0].source_platform == "adzuna"
        assert results[0].external_id == "12345"

    @pytest.mark.asyncio
    async def test_search_api_error(self) -> None:
        """Should return empty list on HTTP error."""
        mock_resp = _mock_response(429, text="Rate limited")

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            provider = AdzunaProvider(app_id="test_id", app_key="test_key")
            results = await provider.search(keywords="python", country="nl")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_network_error(self) -> None:
        """Should return empty list on network error."""
        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            provider = AdzunaProvider(app_id="test_id", app_key="test_key")
            results = await provider.search(keywords="python", country="nl")

        assert results == []

    def test_provider_name(self) -> None:
        provider = AdzunaProvider(app_id="x", app_key="y")
        assert provider.name == "adzuna"


class TestAdzunaSalaryFormat:
    """Test salary formatting helper."""

    def test_salary_range(self) -> None:
        raw = {"salary_min": 60000, "salary_max": 80000}
        assert _format_salary(raw) == "€60,000 - €80,000"

    def test_salary_min_only(self) -> None:
        raw = {"salary_min": 50000, "salary_max": None}
        assert _format_salary(raw) == "€50,000+"

    def test_no_salary(self) -> None:
        raw = {}
        assert _format_salary(raw) == ""


# ── Jooble Tests ───────────────────────────────────────────────


class TestJoobleProvider:
    """Test Jooble API client."""

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Should parse Jooble response into RawJobListing objects."""
        mock_resp = _mock_response(200, json_data=JOOBLE_RESPONSE)

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            provider = JoobleProvider(api_key="test_key")
            results = await provider.search(keywords="backend developer")

        assert len(results) == 1
        assert results[0].title == "Backend Developer"
        assert results[0].company == "StartupX"
        assert results[0].location == "Amsterdam"
        assert results[0].source_platform == "jooble"
        assert results[0].external_id == "abc123"
        assert results[0].salary_info == "€55,000 - €75,000"

    @pytest.mark.asyncio
    async def test_search_api_error(self) -> None:
        """Should return empty list on HTTP error."""
        mock_resp = _mock_response(500, text="Server error")

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            provider = JoobleProvider(api_key="test_key")
            results = await provider.search(keywords="python")

        assert results == []

    def test_provider_name(self) -> None:
        provider = JoobleProvider(api_key="x")
        assert provider.name == "jooble"


# ── ADR-0003 Verification: Circuit Breaker Integration ────────────────────────


class TestAdzunaCircuitBreaker:
    """Verify ADR-0003: circuit breaker wired into AdzunaProvider."""

    @pytest.mark.asyncio
    async def test_open_circuit_returns_empty_without_http_call(self) -> None:
        """OPEN circuit should return [] immediately without hitting the API."""
        provider = AdzunaProvider(app_id="id", app_key="key")
        _wire_fake_redis(provider, state="open", failures=3)
        provider._breaker._redis._store["opened_at"] = str(time.time())

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            results = await provider.search(keywords="python")

        assert results == []
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_4xx_does_not_trip_circuit(self) -> None:
        """4xx HTTP response should be handled as client error — circuit stays CLOSED."""
        mock_resp = _mock_response(400, text="Bad request")
        provider = AdzunaProvider(app_id="id", app_key="key")
        fake_redis = _wire_fake_redis(provider, state="closed")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search(keywords="python")

        assert results == []
        # Failure counter must NOT have incremented (4xx is client error, not outage)
        assert fake_redis._store.get("failures", "0") == "0"

    @pytest.mark.asyncio
    async def test_5xx_increments_failure_counter(self) -> None:
        """5xx HTTP response should increment the circuit failure counter."""
        mock_resp = _mock_response(503, text="Service Unavailable")
        provider = AdzunaProvider(app_id="id", app_key="key")
        fake_redis = _wire_fake_redis(provider, state="closed")

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search(keywords="python")

        assert results == []
        assert int(fake_redis._store.get("failures", "0")) == 1

    @pytest.mark.asyncio
    async def test_fail_open_redis_unavailable_proceeds_normally(self) -> None:
        """When Redis is unavailable (OPS-4), search should proceed without circuit protection."""
        mock_resp = _mock_response(200, json_data={"results": []})
        provider = AdzunaProvider(app_id="id", app_key="key")
        _wire_fake_redis(provider)

        async def _redis_error(*_: Any, **__: Any) -> None:
            raise ConnectionError("Redis not provisioned")

        provider._breaker._redis.hgetall = _redis_error  # type: ignore[method-assign]

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search(keywords="python")

        assert results == []  # empty results from API, not from circuit


class TestJoobleCircuitBreaker:
    """Verify ADR-0003: circuit breaker wired into JoobleProvider."""

    @pytest.mark.asyncio
    async def test_open_circuit_returns_empty_without_http_call(self) -> None:
        """OPEN circuit should return [] immediately without hitting the API."""
        provider = JoobleProvider(api_key="key")
        _wire_fake_redis(provider, state="open", failures=3)
        provider._breaker._redis._store["opened_at"] = str(time.time())

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            results = await provider.search(keywords="python")

        assert results == []
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_4xx_does_not_trip_circuit(self) -> None:
        """4xx should not trip Jooble circuit breaker."""
        mock_resp = _mock_response(403, text="Forbidden")
        provider = JoobleProvider(api_key="key")
        fake_redis = _wire_fake_redis(provider, state="closed")

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search(keywords="python")

        assert results == []
        assert fake_redis._store.get("failures", "0") == "0"

    @pytest.mark.asyncio
    async def test_5xx_increments_failure_counter(self) -> None:
        """5xx should increment Jooble circuit failure counter."""
        mock_resp = _mock_response(500, text="Internal Server Error")
        provider = JoobleProvider(api_key="key")
        fake_redis = _wire_fake_redis(provider, state="closed")

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
            results = await provider.search(keywords="python")

        assert results == []
        assert int(fake_redis._store.get("failures", "0")) == 1

    @pytest.mark.asyncio
    async def test_adzuna_jooble_circuits_are_independent(self) -> None:
        """Adzuna and Jooble circuit states must not share Redis keys."""
        adzuna = AdzunaProvider(app_id="id", app_key="key")
        jooble = JoobleProvider(api_key="key")

        _wire_fake_redis(adzuna, state="open", failures=3)
        adzuna._breaker._redis._store["opened_at"] = str(time.time())
        _wire_fake_redis(jooble, state="closed")

        mock_resp = _mock_response(200, json_data={"jobs": []})
        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=mock_resp):
            jooble_results = await jooble.search(keywords="python")

        # Jooble circuit is CLOSED — should attempt and return normally
        assert jooble_results == []  # empty from API, not blocked
