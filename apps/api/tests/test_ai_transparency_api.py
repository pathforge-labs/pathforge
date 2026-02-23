"""
PathForge — AI Trust Layer™ API Tests
=======================================
Tests for AI transparency endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.llm_observability import (
    TransparencyRecord,
    get_transparency_log,
)


@pytest.mark.asyncio
async def test_health_endpoint_public_no_auth_required(
    client: AsyncClient,
) -> None:
    """GET /api/v1/ai-transparency/health requires no authentication."""
    response = await client.get("/api/v1/ai-transparency/health")
    assert response.status_code == 200

    data = response.json()
    assert "system_status" in data
    assert "success_rate" in data
    assert "uptime_seconds" in data
    assert data["system_status"] in ("operational", "degraded", "unavailable")


@pytest.mark.asyncio
async def test_health_endpoint_returns_operational_status(
    client: AsyncClient,
) -> None:
    """Health endpoint shows operational when no failures exist."""
    response = await client.get("/api/v1/ai-transparency/health")
    data = response.json()

    # Fresh system with no records → operational
    assert data["system_status"] == "operational"
    assert data["success_rate"] == 100.0


@pytest.mark.asyncio
async def test_analyses_endpoint_requires_auth(
    client: AsyncClient,
) -> None:
    """GET /api/v1/ai-transparency/analyses returns 401 without auth."""
    response = await client.get("/api/v1/ai-transparency/analyses")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_analyses_endpoint_returns_user_records_only(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """Authenticated user only sees their own analyses."""
    # Seed transparency log with records for the authenticated user
    log = get_transparency_log()
    log.reset()  # Clean state

    user_id = str(authenticated_user.id)
    other_user_id = "00000000-0000-0000-0000-000000000099"

    log.record(
        user_id=user_id,
        entry=TransparencyRecord(
            analysis_type="career_dna.hidden_skills",
            confidence_score=0.87,
            confidence_label="High",
            latency_ms=500,
        ),
    )
    log.record(
        user_id=other_user_id,
        entry=TransparencyRecord(
            analysis_type="threat_radar.scan",
            confidence_score=0.90,
            confidence_label="High",
            latency_ms=800,
        ),
    )

    response = await auth_client.get("/api/v1/ai-transparency/analyses")
    assert response.status_code == 200

    data = response.json()
    assert data["total_count"] == 1
    assert data["user_id"] == user_id
    assert data["analyses"][0]["analysis_type"] == "career_dna.hidden_skills"

    # Cleanup
    log.reset()


@pytest.mark.asyncio
async def test_analysis_detail_404_for_other_users(
    auth_client: AsyncClient,
) -> None:
    """Users cannot access other users' analysis records."""
    log = get_transparency_log()
    log.reset()

    # Create a record owned by a different user
    record = TransparencyRecord(analysis_type="other.analysis")
    log.record(
        user_id="00000000-0000-0000-0000-000000000099",
        entry=record,
    )

    response = await auth_client.get(
        f"/api/v1/ai-transparency/analyses/{record.analysis_id}",
    )
    assert response.status_code == 404

    log.reset()


@pytest.mark.asyncio
async def test_analysis_detail_returns_own_record(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """Authenticated user can access their own analysis detail."""
    log = get_transparency_log()
    log.reset()

    user_id = str(authenticated_user.id)
    record = TransparencyRecord(
        analysis_type="salary_intelligence.estimate",
        confidence_score=0.91,
        confidence_label="High",
        tier="primary",
        latency_ms=1200,
        prompt_tokens=150,
        completion_tokens=300,
        data_sources=["career_dna", "market_data"],
    )
    log.record(user_id=user_id, entry=record)

    response = await auth_client.get(
        f"/api/v1/ai-transparency/analyses/{record.analysis_id}",
    )
    assert response.status_code == 200

    data = response.json()
    assert data["analysis_type"] == "salary_intelligence.estimate"
    assert data["confidence_score"] == 0.91
    assert data["confidence_label"] == "High"
    assert data["model_tier"] == "primary"
    assert data["tokens_used"] == 450
    assert data["latency_ms"] == 1200
    assert "career_dna" in data["data_sources"]

    log.reset()


@pytest.mark.asyncio
async def test_analysis_detail_404_nonexistent(
    auth_client: AsyncClient,
) -> None:
    """Non-existent analysis ID returns 404."""
    response = await auth_client.get(
        "/api/v1/ai-transparency/analyses/nonexistent-id",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyses_limit_parameter(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """Limit parameter controls number of returned analyses."""
    log = get_transparency_log()
    log.reset()

    user_id = str(authenticated_user.id)
    for idx in range(10):
        log.record(
            user_id=user_id,
            entry=TransparencyRecord(analysis_type=f"test.{idx}"),
        )

    response = await auth_client.get(
        "/api/v1/ai-transparency/analyses?limit=3",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3

    log.reset()
