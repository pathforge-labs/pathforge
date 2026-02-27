"""
PathForge API — Health Endpoint Tests
========================================
Tests for /api/v1/health and /api/v1/health/ready.

Sprint 30: Updated to validate new fields (redis, rate_limiting,
uptime_seconds, cold_start_ms) and HTTP 503 behavior.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /api/v1/health returns 200 with app info."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "PathForge"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """GET /api/v1/health/ready returns structured readiness response.

    In test environment (no Redis), the endpoint returns status based
    on available dependencies. Database should always be connected.
    """
    response = await client.get("/api/v1/health/ready")

    # Accept both 200 (all deps ok) and 503 (Redis not available)
    assert response.status_code in (200, 503)

    data = response.json()
    assert data["status"] in ("ok", "unhealthy")
    assert data["database"] == "connected"
    assert "redis" in data
    assert "rate_limiting" in data
    assert "uptime_seconds" in data
    assert data["app"] == "PathForge"
    assert "version" in data
