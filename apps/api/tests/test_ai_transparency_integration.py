"""
PathForge — AI Trust Layer™ Integration Tests
================================================
Cross-domain integration verifying that transparency metadata
flows from the observability layer through the API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.llm_observability import (
    TransparencyRecord,
    compute_confidence_score,
    confidence_label,
    get_transparency_log,
)

# ── Cross-Domain: Observability → API Integration ─────────────


@pytest.mark.asyncio
async def test_full_transparency_pipeline(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """End-to-end: record analysis → query via API → verify transparency data.

    This test validates that data flows correctly from the in-memory
    transparency log through the API endpoints to the user.
    """
    log = get_transparency_log()
    log.reset()

    user_id = str(authenticated_user.id)

    # Step 1: Simulate a completed AI analysis with transparency metadata
    score = compute_confidence_score(
        tier="primary",
        retries=0,
        latency_seconds=1.5,
        completion_tokens=800,
        max_tokens=4096,
    )
    label = confidence_label(score)

    record = TransparencyRecord(
        analysis_type="career_dna.hidden_skills",
        model="anthropic/claude-sonnet-4-20250514",
        tier="primary",
        confidence_score=score,
        confidence_label=label,
        data_sources=["experience_text", "skills_list"],
        prompt_tokens=250,
        completion_tokens=800,
        latency_ms=1500,
        success=True,
        retries=0,
    )

    log.record(user_id=user_id, entry=record)

    # Step 2: Query the analyses list API
    list_response = await auth_client.get(
        "/api/v1/ai-transparency/analyses",
    )
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total_count"] == 1
    assert list_data["user_id"] == user_id

    analysis = list_data["analyses"][0]
    assert analysis["analysis_type"] == "career_dna.hidden_skills"
    assert analysis["confidence_score"] == round(score, 3)
    assert analysis["confidence_label"] == "High"
    assert analysis["model_tier"] == "primary"

    # Step 3: Query the specific analysis detail
    detail_response = await auth_client.get(
        f"/api/v1/ai-transparency/analyses/{record.analysis_id}",
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["tokens_used"] == 1050  # 250 + 800
    assert detail["latency_ms"] == 1500
    assert "experience_text" in detail["data_sources"]

    # Step 4: Verify health endpoint reflects the recorded analysis
    health_response = await auth_client.get(
        "/api/v1/ai-transparency/health",
    )
    assert health_response.status_code == 200
    health = health_response.json()
    assert health["system_status"] == "operational"
    assert health["total_analyses"] >= 1
    assert health["active_users"] >= 1

    # Cleanup
    log.reset()


@pytest.mark.asyncio
async def test_confidence_score_reflects_in_api(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """Confidence scoring algorithm results are accurately served by the API."""
    log = get_transparency_log()
    log.reset()

    user_id = str(authenticated_user.id)

    # Create records with different confidence characteristics
    high_confidence_score = compute_confidence_score(
        tier="primary", retries=0, latency_seconds=0.5,
        completion_tokens=500, max_tokens=4096,
    )
    low_confidence_score = compute_confidence_score(
        tier="fast", retries=2, latency_seconds=12.0,
        completion_tokens=3900, max_tokens=4096,
    )

    log.record(
        user_id=user_id,
        entry=TransparencyRecord(
            analysis_type="high.confidence",
            confidence_score=high_confidence_score,
            confidence_label=confidence_label(high_confidence_score),
        ),
    )
    log.record(
        user_id=user_id,
        entry=TransparencyRecord(
            analysis_type="low.confidence",
            confidence_score=low_confidence_score,
            confidence_label=confidence_label(low_confidence_score),
        ),
    )

    response = await auth_client.get(
        "/api/v1/ai-transparency/analyses?limit=10",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2

    # Newest first — low confidence should be first
    analyses = data["analyses"]
    assert analyses[0]["analysis_type"] == "low.confidence"
    assert analyses[0]["confidence_label"] == "Low"
    assert analyses[1]["analysis_type"] == "high.confidence"
    assert analyses[1]["confidence_label"] == "High"

    # Verify high > low confidence
    assert analyses[1]["confidence_score"] > analyses[0]["confidence_score"]

    log.reset()


@pytest.mark.asyncio
async def test_user_isolation_across_domains(
    auth_client: AsyncClient,
    authenticated_user: User,
) -> None:
    """Multiple users' data stays isolated across all API endpoints."""
    log = get_transparency_log()
    log.reset()

    user_id = str(authenticated_user.id)
    other_user = "other-user-uuid-12345"

    # Seed both users
    our_record = TransparencyRecord(analysis_type="our.analysis")
    log.record(user_id=user_id, entry=our_record)

    their_record = TransparencyRecord(analysis_type="their.analysis")
    log.record(user_id=other_user, entry=their_record)

    # List: only our records
    list_resp = await auth_client.get("/api/v1/ai-transparency/analyses")
    assert list_resp.json()["total_count"] == 1
    assert list_resp.json()["analyses"][0]["analysis_type"] == "our.analysis"

    # Detail: can access our record
    our_detail = await auth_client.get(
        f"/api/v1/ai-transparency/analyses/{our_record.analysis_id}",
    )
    assert our_detail.status_code == 200

    # Detail: cannot access their record (404, not 403)
    their_detail = await auth_client.get(
        f"/api/v1/ai-transparency/analyses/{their_record.analysis_id}",
    )
    assert their_detail.status_code == 404

    # Health: shows aggregated data (both users contribute)
    health_resp = await auth_client.get("/api/v1/ai-transparency/health")
    health = health_resp.json()
    assert health["active_users"] == 2  # Both users counted
    assert health["analyses_in_memory"] == 2  # Both analyses counted

    log.reset()
