"""End-to-end tests for the AI Usage Summary route (T4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_transparency import AITransparencyRecord
from app.models.user import User


def _seed_record(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    analysis_type: str,
    model: str = "claude-sonnet-4-5",
    prompt_tokens: int = 1_000,
    completion_tokens: int = 500,
) -> None:
    session.add(
        AITransparencyRecord(
            user_id=user_id,
            analysis_id=str(uuid.uuid4()),
            analysis_type=analysis_type,
            model=model,
            tier="primary",
            confidence_score=0.9,
            confidence_label="High",
            data_sources=[],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=1500,
            success=True,
            retries=0,
            created_at=datetime.now(UTC),
        )
    )


@pytest.mark.asyncio
async def test_summary_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/ai-usage/summary")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_summary_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    resp = await auth_client.get("/api/v1/ai-usage/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_calls"] == 0
    assert body["total_cost_eur_cents"] == 0
    assert body["engines"] == []
    assert body["period_label"] == "current_month"
    assert body["has_unpriced_models"] is False


@pytest.mark.asyncio
async def test_summary_aggregates_seeded_records(
    auth_client: AsyncClient,
    authenticated_user: User,
    db_session: AsyncSession,
) -> None:
    _seed_record(
        db_session,
        user_id=authenticated_user.id,
        analysis_type="career_dna",
        prompt_tokens=10_000,
        completion_tokens=5_000,
    )
    _seed_record(
        db_session,
        user_id=authenticated_user.id,
        analysis_type="threat_radar",
        prompt_tokens=2_000,
        completion_tokens=1_000,
    )
    await db_session.commit()

    resp = await auth_client.get("/api/v1/ai-usage/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_calls"] == 2
    assert body["total_prompt_tokens"] == 12_000
    assert body["total_completion_tokens"] == 6_000
    # Both calls priced (claude-sonnet-4-5 is in the table) → no
    # unpriced flag.
    assert body["has_unpriced_models"] is False
    # EUR cost is positive but we don't pin a specific value here —
    # the unit test in test_ai_usage_service.py already pins the
    # arithmetic; this test just asserts it round-trips through the
    # API surface.
    assert body["total_cost_eur_cents"] > 0

    engines = {row["engine"]: row for row in body["engines"]}
    assert engines["career_dna"]["calls"] == 1
    assert engines["threat_radar"]["calls"] == 1
    # Sorted alphabetically by engine name.
    assert [row["engine"] for row in body["engines"]] == [
        "career_dna",
        "threat_radar",
    ]


@pytest.mark.asyncio
async def test_summary_flags_unpriced_models(
    auth_client: AsyncClient,
    authenticated_user: User,
    db_session: AsyncSession,
) -> None:
    _seed_record(
        db_session,
        user_id=authenticated_user.id,
        analysis_type="career_dna",
        model="future-unknown-model-2027",
        prompt_tokens=10_000,
        completion_tokens=5_000,
    )
    await db_session.commit()

    resp = await auth_client.get("/api/v1/ai-usage/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_calls"] == 1
    assert body["total_cost_eur_cents"] == 0
    assert body["has_unpriced_models"] is True


@pytest.mark.asyncio
async def test_summary_rejects_unknown_period(
    auth_client: AsyncClient,
) -> None:
    resp = await auth_client.get(
        "/api/v1/ai-usage/summary",
        params={"period": "all_time"},
    )
    # FastAPI's Literal validation rejects with 422.
    assert resp.status_code == 422
