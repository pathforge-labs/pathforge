"""
Route-level cache integration tests for the intelligence response cache layer.

Verifies:
- GET dashboard endpoints serve cached data without calling the service
  layer (cache-hit path).
- GET dashboard endpoints call ic_cache.set on cache miss.
- POST scan / generate endpoints call ic_cache.invalidate_user after
  successful completion.
- PATCH / PUT mutating endpoints call ic_cache.invalidate_user.

The ic_cache singleton is patched per test so no Redis is required.
Service layer methods are patched on cache-hit tests to prove the
service is NOT called when a cache hit occurs.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Helpers ────────────────────────────────────────────────────────────────────


def _async_none() -> AsyncMock:
    """AsyncMock that returns None (cache miss)."""
    return AsyncMock(return_value=None)


def _async_noop() -> AsyncMock:
    """AsyncMock that returns None and records calls (for set / invalidate)."""
    return AsyncMock(return_value=None)


def _mock_career_dna() -> MagicMock:
    """Minimal CareerDNA ORM-like object accepted by _build_full_response."""
    m = MagicMock()
    m.id = uuid.uuid4()
    m.completeness_score = 80.0
    m.last_analysis_at = None
    m.version = 2
    m.summary = "Mock DNA"
    m.skill_genome = []
    m.hidden_skills = []
    m.experience_blueprint = None
    m.growth_vector = None
    m.values_profile = None
    m.market_position = None
    return m


# Minimal cached dicts that satisfy model_validate for each response schema.
_CAREER_DNA_CACHED: dict[str, Any] = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "completeness_score": 72.0,
    "version": 1,
    "summary": "from_cache",
    "hidden_skills": [],
}

_THREAT_RADAR_CACHED: dict[str, Any] = {
    "total_unread_alerts": 7,
    "industry_trends": [],
    "recent_alerts": [],
}

_SALARY_CACHED: dict[str, Any] = {
    "estimate": None,
    "skill_impacts": [],
    "recent_scenarios": [],
}

_SKILL_DECAY_CACHED: dict[str, Any] = {
    "freshness": [],
    "freshness_summary": {},
    "market_demand": [],
    "velocity": [],
    "reskilling_pathways": [],
}

_REC_CACHED: dict[str, Any] = {
    "total_pending": 5,
    "recent_recommendations": [],
    "latest_batch": None,
    "total_in_progress": 0,
    "total_completed": 0,
}


# ── Feature-gate bypass fixture ────────────────────────────────────────────────


@pytest.fixture
def bypass_feature_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow all feature-gated engines regardless of user tier.

    POST /scan endpoints for salary, skill_decay, and recommendation_intelligence
    require at least pro tier. This fixture bypasses the gate so cache
    invalidation can be tested without setting up a Stripe subscription.
    """
    from app.core import feature_gate

    monkeypatch.setattr(feature_gate, "check_engine_access", lambda tier, engine: True)


# ── Cache-hit: GET endpoints ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_career_dna_get_cache_hit_skips_service(
    auth_client: AsyncClient,
) -> None:
    """GET /career-dna must return cached payload without touching the service."""
    with (
        patch("app.api.v1.career_dna.ic_cache.get", new=AsyncMock(return_value=_CAREER_DNA_CACHED)),
        patch(
            "app.api.v1.career_dna.CareerDNAService.get_full_profile",
            side_effect=AssertionError("service must NOT be called on cache hit"),
        ),
    ):
        response = await auth_client.get("/api/v1/career-dna")

    assert response.status_code == 200
    assert response.json()["summary"] == "from_cache"


@pytest.mark.asyncio
async def test_threat_radar_get_cache_hit_skips_service(
    auth_client: AsyncClient,
) -> None:
    """GET /threat-radar must return cached payload without touching the service."""
    with (
        patch("app.api.v1.threat_radar.ic_cache.get", new=AsyncMock(return_value=_THREAT_RADAR_CACHED)),
        patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_overview",
            side_effect=AssertionError("service must NOT be called on cache hit"),
        ),
    ):
        response = await auth_client.get("/api/v1/threat-radar")

    assert response.status_code == 200
    assert response.json()["total_unread_alerts"] == 7


@pytest.mark.asyncio
async def test_salary_dashboard_cache_hit_skips_service(
    auth_client: AsyncClient,
) -> None:
    """GET /salary-intelligence must return cached payload without touching the service."""
    with (
        patch("app.api.v1.salary_intelligence.ic_cache.get", new=AsyncMock(return_value=_SALARY_CACHED)),
        patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_dashboard",
            side_effect=AssertionError("service must NOT be called on cache hit"),
        ),
    ):
        response = await auth_client.get("/api/v1/salary-intelligence")

    assert response.status_code == 200
    data = response.json()
    assert data["estimate"] is None
    assert data["skill_impacts"] == []


@pytest.mark.asyncio
async def test_skill_decay_dashboard_cache_hit_skips_service(
    auth_client: AsyncClient,
) -> None:
    """GET /skill-decay must return cached payload without touching the service."""
    with (
        patch("app.api.v1.skill_decay.ic_cache.get", new=AsyncMock(return_value=_SKILL_DECAY_CACHED)),
        patch(
            "app.api.v1.skill_decay.SkillDecayService.get_dashboard",
            side_effect=AssertionError("service must NOT be called on cache hit"),
        ),
    ):
        response = await auth_client.get("/api/v1/skill-decay")

    assert response.status_code == 200
    assert response.json()["freshness"] == []


@pytest.mark.asyncio
async def test_recommendations_dashboard_cache_hit_skips_service(
    auth_client: AsyncClient,
) -> None:
    """GET /recommendations/dashboard must return cached payload without touching the service."""
    with (
        patch("app.api.v1.recommendation_intelligence.ic_cache.get", new=AsyncMock(return_value=_REC_CACHED)),
        patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_dashboard",
            side_effect=AssertionError("service must NOT be called on cache hit"),
        ),
    ):
        response = await auth_client.get("/api/v1/recommendations/dashboard")

    assert response.status_code == 200
    assert response.json()["total_pending"] == 5


# ── Cache-miss: ic_cache.set called on GET ─────────────────────────────────────


@pytest.mark.asyncio
async def test_threat_radar_cache_miss_calls_set(
    auth_client: AsyncClient,
) -> None:
    """GET /threat-radar on cache miss must call ic_cache.set with TTL_THREAT_RADAR."""
    from app.core.intelligence_cache import TTL_THREAT_RADAR

    mock_set = _async_noop()

    with (
        patch("app.api.v1.threat_radar.ic_cache.get", new=_async_none()),
        patch("app.api.v1.threat_radar.ic_cache.set", new=mock_set),
    ):
        response = await auth_client.get("/api/v1/threat-radar")

    assert response.status_code == 200
    mock_set.assert_called_once()
    _key, _data, _ttl = mock_set.call_args[0]  # positional args
    assert _ttl == TTL_THREAT_RADAR


@pytest.mark.asyncio
async def test_salary_cache_miss_calls_set(
    auth_client: AsyncClient,
) -> None:
    """GET /salary-intelligence on cache miss must call ic_cache.set with TTL_SALARY."""
    from app.core.intelligence_cache import TTL_SALARY

    mock_set = _async_noop()

    with (
        patch("app.api.v1.salary_intelligence.ic_cache.get", new=_async_none()),
        patch("app.api.v1.salary_intelligence.ic_cache.set", new=mock_set),
    ):
        response = await auth_client.get("/api/v1/salary-intelligence")

    assert response.status_code == 200
    mock_set.assert_called_once()
    _key, _data, _ttl = mock_set.call_args[0]
    assert _ttl == TTL_SALARY


# ── Invalidation: POST scan / generate endpoints ───────────────────────────────


@pytest.mark.asyncio
async def test_career_dna_generate_calls_invalidate(
    auth_client: AsyncClient,
    authenticated_user: Any,
) -> None:
    """POST /career-dna/generate must call invalidate_user after successful generation."""
    mock_invalidate = _async_noop()
    mock_dna = _mock_career_dna()

    with (
        patch("app.api.v1.career_dna.CareerDNAService.generate_full_profile", new=AsyncMock(return_value=mock_dna)),
        patch("app.api.v1.career_dna.ic_cache.invalidate_user", new=mock_invalidate),
    ):
        response = await auth_client.post("/api/v1/career-dna/generate")

    assert response.status_code == 201
    mock_invalidate.assert_called_once_with(authenticated_user.id)


@pytest.mark.asyncio
async def test_salary_scan_calls_invalidate(
    auth_client: AsyncClient,
    authenticated_user: Any,
    bypass_feature_gate: None,
) -> None:
    """POST /salary-intelligence/scan must call invalidate_user on success."""
    mock_invalidate = _async_noop()
    scan_result = {
        "status": "completed",
        "estimate": None,
        "skill_impacts": [],
        "history_entry_created": False,
    }

    with (
        patch("app.api.v1.salary_intelligence.SalaryIntelligenceService.run_full_scan", new=AsyncMock(return_value=scan_result)),
        patch("app.api.v1.salary_intelligence.ic_cache.invalidate_user", new=mock_invalidate),
    ):
        response = await auth_client.post("/api/v1/salary-intelligence/scan")

    assert response.status_code == 200
    mock_invalidate.assert_called_once_with(authenticated_user.id)


@pytest.mark.asyncio
async def test_skill_decay_scan_calls_invalidate(
    auth_client: AsyncClient,
    authenticated_user: Any,
    bypass_feature_gate: None,
) -> None:
    """POST /skill-decay/scan must call invalidate_user on success."""
    mock_invalidate = _async_noop()
    scan_result = {
        "status": "completed",
        "skills_analyzed": 0,
        "freshness": [],
        "market_demand": [],
        "velocity": [],
        "reskilling_pathways": [],
    }

    with (
        patch("app.api.v1.skill_decay.SkillDecayService.run_full_scan", new=AsyncMock(return_value=scan_result)),
        patch("app.api.v1.skill_decay.ic_cache.invalidate_user", new=mock_invalidate),
    ):
        response = await auth_client.post("/api/v1/skill-decay/scan")

    assert response.status_code == 201
    mock_invalidate.assert_called_once_with(authenticated_user.id)


# ── Invalidation: PATCH / PUT mutating endpoints ────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_hidden_skill_calls_invalidate(
    auth_client: AsyncClient,
    authenticated_user: Any,
    db_session: Any,
) -> None:
    """PATCH /career-dna/hidden-skills/{id} must call invalidate_user after confirm."""
    from app.models.career_dna import CareerDNA, HiddenSkill

    # Create a hidden skill in the DB for a career DNA
    career_dna = CareerDNA(user_id=authenticated_user.id)
    db_session.add(career_dna)
    await db_session.flush()

    skill = HiddenSkill(
        career_dna_id=career_dna.id,
        skill_name="Leadership",
        discovery_method="llm_inference",
        confidence=0.8,
    )
    db_session.add(skill)
    await db_session.flush()

    mock_invalidate = _async_noop()

    with patch("app.api.v1.career_dna.ic_cache.invalidate_user", new=mock_invalidate):
        response = await auth_client.patch(
            f"/api/v1/career-dna/hidden-skills/{skill.id}",
            json={"confirmed": True},
        )

    assert response.status_code == 200
    mock_invalidate.assert_called_once_with(authenticated_user.id)


@pytest.mark.asyncio
async def test_update_target_role_calls_invalidate(
    auth_client: AsyncClient,
    authenticated_user: Any,
    db_session: Any,
) -> None:
    """PUT /career-dna/growth/target-role must call invalidate_user after update."""
    from app.models.career_dna import CareerDNA, GrowthVector

    career_dna = CareerDNA(user_id=authenticated_user.id)
    db_session.add(career_dna)
    await db_session.flush()

    growth = GrowthVector(
        career_dna_id=career_dna.id,
        current_trajectory="steady",
        target_role="Software Engineer",
    )
    db_session.add(growth)
    await db_session.flush()

    mock_invalidate = _async_noop()

    with patch("app.api.v1.career_dna.ic_cache.invalidate_user", new=mock_invalidate):
        response = await auth_client.put(
            "/api/v1/career-dna/growth/target-role",
            json={"target_role": "Staff Engineer"},
        )

    assert response.status_code == 200
    mock_invalidate.assert_called_once_with(authenticated_user.id)


# ── Cache key contains user ID ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_cache_key_scoped_to_user(
    auth_client: AsyncClient,
    authenticated_user: Any,
) -> None:
    """The cache key passed to ic_cache.get must include the authenticated user's ID."""
    captured: list[str] = []

    async def _capture_get(key: str) -> None:
        captured.append(key)
        return None  # cache miss

    with (
        patch("app.api.v1.threat_radar.ic_cache.get", side_effect=_capture_get),
        patch("app.api.v1.threat_radar.ic_cache.set", new=_async_noop()),
    ):
        await auth_client.get("/api/v1/threat-radar")

    assert len(captured) == 1
    assert str(authenticated_user.id) in captured[0]


# ── Empty-dict cached value is NOT treated as miss ─────────────────────────────


@pytest.mark.asyncio
async def test_salary_empty_cache_hit_not_treated_as_miss(
    auth_client: AsyncClient,
) -> None:
    """An empty-dict cached salary response must be served (not re-fetched)."""
    empty_cached: dict[str, Any] = {
        "estimate": None,
        "skill_impacts": [],
        "trajectory": None,
        "recent_scenarios": [],
    }

    with (
        patch("app.api.v1.salary_intelligence.ic_cache.get", new=AsyncMock(return_value=empty_cached)),
        patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_dashboard",
            side_effect=AssertionError("service must NOT be called on cache hit"),
        ),
    ):
        response = await auth_client.get("/api/v1/salary-intelligence")

    assert response.status_code == 200
