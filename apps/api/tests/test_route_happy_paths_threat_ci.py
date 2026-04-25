"""
PathForge — Threat Radar & Collective Intelligence Route Tests
===============================================================
Happy-path and error-path coverage for:
    * app/api/v1/threat_radar.py        (prefix: /api/v1/threat-radar)
    * app/api/v1/collective_intelligence.py  (prefix: /api/v1/collective-intelligence)

All service/cache calls are mocked so the test suite exercises route-handler
bodies without touching the database-backed service layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    email: str = "route-threat@pathforge.eu",
) -> User:
    """Insert a minimal active/verified user for route-level tests."""
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


# ── Stubs for Threat Radar response objects ───────────────────


def _stub_risk() -> MagicMock:
    """Minimal object satisfying _risk_response() builder."""
    risk = MagicMock()
    risk.id = uuid.uuid4()
    risk.onet_soc_code = "15-1252.00"
    risk.onet_occupation_title = "Software Developer"
    risk.base_automation_probability = 0.25
    risk.contextual_risk_score = 30.0
    risk.risk_level = "low"
    risk.vulnerable_tasks = None
    risk.resilient_tasks = None
    risk.recommended_skills = None
    risk.analysis_reasoning = "Low risk"
    risk.opportunity_inversions = None
    risk.analyzed_at = datetime.now(UTC)
    return risk


def _stub_trend() -> MagicMock:
    trend = MagicMock()
    trend.id = uuid.uuid4()
    trend.industry_name = "Technology"
    trend.trend_direction = "up"
    trend.confidence = 0.8
    trend.key_signals = None
    trend.impact_on_user = None
    trend.recommended_actions = None
    trend.data_sources = None
    trend.analyzed_at = datetime.now(UTC)
    return trend


def _stub_snapshot() -> MagicMock:
    snap = MagicMock()
    snap.id = uuid.uuid4()
    snap.overall_score = 75.0
    snap.skill_diversity_index = 70.0
    snap.automation_resistance = 80.0
    snap.growth_velocity = 65.0
    snap.industry_stability = 72.0
    snap.adaptability_signal = 68.0
    snap.moat_score = 60.0
    snap.moat_strength = "moderate"
    snap.explanation = "Good resilience"
    snap.improvement_actions = None
    snap.computed_at = datetime.now(UTC)
    return snap


def _stub_alert() -> MagicMock:
    alert = MagicMock()
    alert.id = uuid.uuid4()
    alert.category = "automation"
    alert.severity = "medium"
    alert.title = "AI Risk Detected"
    alert.description = "Your role has medium automation risk"
    alert.opportunity = "Learn ML skills"
    alert.evidence = None
    alert.channel = "in_app"
    alert.status = "unread"
    alert.snoozed_until = None
    alert.read_at = None
    alert.created_at = datetime.now(UTC)
    return alert


def _stub_pref() -> MagicMock:
    pref = MagicMock()
    pref.id = uuid.uuid4()
    pref.enabled_categories = ["automation"]
    pref.min_severity = "low"
    pref.enabled_channels = ["in_app"]
    pref.quiet_hours_start = None
    pref.quiet_hours_end = None
    return pref


def _stub_overview_data() -> dict:
    return {
        "snapshot": _stub_snapshot(),
        "automation_risk": _stub_risk(),
        "shield_entries": [],
        "industry_trends": [_stub_trend()],
        "recent_alerts": [_stub_alert()],
        "total_unread_alerts": 1,
    }


# ── Stubs for Collective Intelligence response objects ────────


def _stub_ci_snapshot() -> dict:
    uid = uuid.uuid4()
    return {
        "id": uid,
        "career_dna_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "industry": "Technology",
        "region": "Netherlands",
        "trend_direction": "up",
        "demand_intensity": "high",
        "top_emerging_skills": None,
        "declining_skills": None,
        "avg_salary_range_min": 60000.0,
        "avg_salary_range_max": 90000.0,
        "currency": "EUR",
        "growth_rate_pct": 5.0,
        "hiring_volume_trend": "increasing",
        "key_insights": None,
        "confidence_score": 0.8,
        "data_source": "AI",
        "disclaimer": "AI generated",
        "created_at": datetime.now(UTC),
    }


def _stub_ci_salary() -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "role": "Software Engineer",
        "location": "Amsterdam",
        "experience_years": 5,
        "benchmark_min": 55000.0,
        "benchmark_median": 72000.0,
        "benchmark_max": 95000.0,
        "currency": "EUR",
        "user_percentile": 60.0,
        "skill_premium_pct": 10.0,
        "experience_factor": 1.1,
        "negotiation_insights": None,
        "premium_skills": None,
        "confidence_score": 0.75,
        "data_source": "AI",
        "disclaimer": "AI generated",
        "created_at": datetime.now(UTC),
    }


def _stub_ci_cohort() -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "cohort_criteria": {"role": "SWE"},
        "cohort_size": 50,
        "user_rank_percentile": 55.0,
        "avg_skills_count": 12.0,
        "user_skills_count": 14,
        "avg_experience_years": 5.5,
        "common_transitions": None,
        "top_differentiating_skills": None,
        "skill_gaps_vs_cohort": None,
        "confidence_score": 0.7,
        "data_source": "AI",
        "disclaimer": "AI generated",
        "created_at": datetime.now(UTC),
    }


def _stub_ci_pulse() -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "pulse_score": 72.0,
        "pulse_category": "healthy",
        "trend_direction": "up",
        "demand_component": 70.0,
        "salary_component": 75.0,
        "skill_relevance_component": 68.0,
        "trend_component": 74.0,
        "top_opportunities": None,
        "risk_factors": None,
        "recommended_actions": None,
        "summary": "Good market health",
        "confidence_score": 0.8,
        "data_source": "AI",
        "disclaimer": "AI generated",
        "created_at": datetime.now(UTC),
    }


def _stub_ci_prefs() -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": uuid.uuid4(),
        "include_industry_pulse": True,
        "include_salary_benchmarks": True,
        "include_peer_analysis": False,
        "preferred_industries": None,
        "preferred_locations": None,
        "preferred_currency": "EUR",
        "created_at": datetime.now(UTC),
    }


# ═══════════════════════════════════════════════════════════════
# THREAT RADAR TESTS
# ═══════════════════════════════════════════════════════════════


class TestThreatRadarOverview:
    """GET /api/v1/threat-radar — full dashboard."""

    async def test_overview_returns_200_with_no_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """When service returns falsy, responds with empty overview (200)."""
        user = await _make_user(db_session, "tr-overview-empty@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.threat_radar.ic_cache") as mock_cache,
            patch(
                "app.api.v1.threat_radar.ThreatRadarService.get_overview",
                new=AsyncMock(return_value={}),
            ),
        ):
            mock_cache.key.return_value = "k1"
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_cache.TTL_THREAT_RADAR = 300
            response = await client.get(
                "/api/v1/threat-radar", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total_unread_alerts"] == 0

    async def test_overview_returns_200_with_full_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """When service returns populated data, all fields are serialized."""
        user = await _make_user(db_session, "tr-overview-full@pathforge.eu")
        headers = _auth_headers(user)
        overview_data = _stub_overview_data()

        with (
            patch("app.api.v1.threat_radar.ic_cache") as mock_cache,
            patch(
                "app.api.v1.threat_radar.ThreatRadarService.get_overview",
                new=AsyncMock(return_value=overview_data),
            ),
        ):
            mock_cache.key.return_value = "k2"
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_cache.TTL_THREAT_RADAR = 300
            response = await client.get(
                "/api/v1/threat-radar", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total_unread_alerts"] == 1
        assert body["automation_risk"]["risk_level"] == "low"

    async def test_overview_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/threat-radar")
        assert response.status_code == 401

    async def test_overview_uses_cache_hit(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """When cache returns a valid JSON dict, skip service and return it."""
        user = await _make_user(db_session, "tr-overview-cache@pathforge.eu")
        headers = _auth_headers(user)
        cached_payload = {
            "resilience": None,
            "automation_risk": None,
            "skills_shield": None,
            "industry_trends": [],
            "recent_alerts": [],
            "total_unread_alerts": 0,
        }

        with patch("app.api.v1.threat_radar.ic_cache") as mock_cache:
            mock_cache.key.return_value = "k3"
            mock_cache.get = AsyncMock(return_value=cached_payload)
            response = await client.get(
                "/api/v1/threat-radar", headers=headers,
            )

        assert response.status_code == 200
        assert response.json()["total_unread_alerts"] == 0


class TestThreatRadarScan:
    """POST /api/v1/threat-radar/scan — full pipeline scan."""

    async def test_scan_returns_201_on_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-scan-ok@pathforge.eu")
        headers = _auth_headers(user)
        scan_result = {
            "status": "ok",
            "automation_risk": _stub_risk(),
            "industry_trend": _stub_trend(),
            "shield_entries": [],
            "snapshot": _stub_snapshot(),
            "alerts_generated": 2,
        }

        with (
            patch("app.api.v1.threat_radar.settings") as mock_settings,
            patch(
                "app.api.v1.threat_radar.ThreatRadarService.run_full_scan",
                new=AsyncMock(return_value=scan_result),
            ),
            patch("app.api.v1.threat_radar.ic_cache") as mock_cache,
        ):
            mock_settings.billing_enabled = False
            mock_settings.rate_limit_career_dna = "10/minute"
            mock_cache.invalidate_user = AsyncMock()
            response = await client.post(
                "/api/v1/threat-radar/scan",
                headers=headers,
                params={"soc_code": "15-1252.00", "industry_name": "Technology"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "completed"
        assert body["alerts_generated"] == 2

    async def test_scan_returns_404_on_error_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """result['status'] == 'error' → 404."""
        user = await _make_user(db_session, "tr-scan-err@pathforge.eu")
        headers = _auth_headers(user)
        error_result = {"status": "error", "detail": "Career DNA profile required"}

        with (
            patch("app.api.v1.threat_radar.settings") as mock_settings,
            patch(
                "app.api.v1.threat_radar.ThreatRadarService.run_full_scan",
                new=AsyncMock(return_value=error_result),
            ),
            patch("app.api.v1.threat_radar.ic_cache"),
        ):
            mock_settings.billing_enabled = False
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/threat-radar/scan",
                headers=headers,
                params={"soc_code": "15-1252.00", "industry_name": "Technology"},
            )

        assert response.status_code == 404
        assert "Career DNA" in response.json()["detail"]

    async def test_scan_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/threat-radar/scan",
            params={"soc_code": "15-1252.00", "industry_name": "Technology"},
        )
        assert response.status_code == 401


class TestThreatRadarAutomationRisk:
    """GET /api/v1/threat-radar/automation-risk."""

    async def test_automation_risk_returns_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-risk@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_overview",
            new=AsyncMock(return_value={"automation_risk": _stub_risk()}),
        ):
            response = await client.get(
                "/api/v1/threat-radar/automation-risk", headers=headers,
            )

        assert response.status_code == 200
        assert response.json()["onet_soc_code"] == "15-1252.00"

    async def test_automation_risk_returns_null_when_no_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-risk-null@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_overview",
            new=AsyncMock(return_value={}),
        ):
            response = await client.get(
                "/api/v1/threat-radar/automation-risk", headers=headers,
            )

        assert response.status_code == 200
        assert response.json() is None

    async def test_automation_risk_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.get("/api/v1/threat-radar/automation-risk")
        assert response.status_code == 401


class TestThreatRadarSkillsShield:
    """GET /api/v1/threat-radar/skills-shield."""

    async def test_skills_shield_returns_empty_matrix(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-shield@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_overview",
            new=AsyncMock(return_value={}),
        ):
            response = await client.get(
                "/api/v1/threat-radar/skills-shield", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total_skills"] == 0
        assert body["shields"] == []

    async def test_skills_shield_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.get("/api/v1/threat-radar/skills-shield")
        assert response.status_code == 401


class TestThreatRadarResilience:
    """GET /api/v1/threat-radar/resilience."""

    async def test_resilience_returns_score(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-resil@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_overview",
            new=AsyncMock(return_value={"snapshot": _stub_snapshot()}),
        ):
            response = await client.get(
                "/api/v1/threat-radar/resilience", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["overall_score"] == 75.0
        assert body["moat_strength"] == "moderate"

    async def test_resilience_returns_null_without_snapshot(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-resil-null@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_overview",
            new=AsyncMock(return_value={}),
        ):
            response = await client.get(
                "/api/v1/threat-radar/resilience", headers=headers,
            )

        assert response.status_code == 200
        assert response.json() is None

    async def test_resilience_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/threat-radar/resilience")
        assert response.status_code == 401


class TestThreatRadarResilienceHistory:
    """GET /api/v1/threat-radar/resilience/history."""

    async def test_history_returns_empty_when_no_career_dna(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """No CareerDNA row → returns minimal response with empty data."""
        user = await _make_user(db_session, "tr-hist@pathforge.eu")
        headers = _auth_headers(user)

        response = await client.get(
            "/api/v1/threat-radar/resilience/history", headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert "period_days" in body

    async def test_history_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/threat-radar/resilience/history",
        )
        assert response.status_code == 401


class TestThreatRadarAlerts:
    """GET /api/v1/threat-radar/alerts."""

    async def test_alerts_returns_paginated_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-alerts@pathforge.eu")
        headers = _auth_headers(user)
        alert = _stub_alert()
        service_result = {
            "alerts": [alert],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_alerts",
            new=AsyncMock(return_value=service_result),
        ):
            response = await client.get(
                "/api/v1/threat-radar/alerts", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["alerts"]) == 1
        assert body["alerts"][0]["category"] == "automation"

    async def test_alerts_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/threat-radar/alerts")
        assert response.status_code == 401


class TestThreatRadarUpdateAlert:
    """PATCH /api/v1/threat-radar/alerts/{alert_id}."""

    async def test_update_alert_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-upd-alert@pathforge.eu")
        headers = _auth_headers(user)
        alert = _stub_alert()
        alert_id = str(alert.id)

        with (
            patch(
                "app.api.v1.threat_radar.ThreatRadarService.update_alert_status",
                new=AsyncMock(return_value=alert),
            ),
            patch("app.api.v1.threat_radar.ic_cache") as mock_cache,
        ):
            mock_cache.invalidate_user = AsyncMock()
            response = await client.patch(
                f"/api/v1/threat-radar/alerts/{alert_id}",
                headers=headers,
                json={"status": "read"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "unread"  # from stub

    async def test_update_alert_returns_404_when_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-upd-alert-404@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.update_alert_status",
            new=AsyncMock(return_value=None),
        ):
            response = await client.patch(
                f"/api/v1/threat-radar/alerts/{uuid.uuid4()}",
                headers=headers,
                json={"status": "dismissed"},
            )

        assert response.status_code == 404
        assert "Alert not found" in response.json()["detail"]

    async def test_update_alert_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.patch(
            f"/api/v1/threat-radar/alerts/{uuid.uuid4()}",
            json={"status": "read"},
        )
        assert response.status_code == 401


class TestThreatRadarPreferences:
    """GET and PUT /api/v1/threat-radar/preferences."""

    async def test_get_preferences_returns_pref(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-pref-get@pathforge.eu")
        headers = _auth_headers(user)
        pref = _stub_pref()

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_preferences",
            new=AsyncMock(return_value=pref),
        ):
            response = await client.get(
                "/api/v1/threat-radar/preferences", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["min_severity"] == "low"

    async def test_get_preferences_returns_null_when_none(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-pref-null@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.get_preferences",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get(
                "/api/v1/threat-radar/preferences", headers=headers,
            )

        assert response.status_code == 200
        assert response.json() is None

    async def test_put_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-pref-put@pathforge.eu")
        headers = _auth_headers(user)
        pref = _stub_pref()

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.update_preferences",
            new=AsyncMock(return_value=pref),
        ):
            response = await client.put(
                "/api/v1/threat-radar/preferences",
                headers=headers,
                json={"min_severity": "medium", "enabled_categories": ["automation"]},
            )

        assert response.status_code == 200
        assert response.json()["min_severity"] == "low"

    async def test_put_preferences_returns_404_when_no_career_dna(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "tr-pref-put-404@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.threat_radar.ThreatRadarService.update_preferences",
            new=AsyncMock(return_value=None),
        ):
            response = await client.put(
                "/api/v1/threat-radar/preferences",
                headers=headers,
                json={"min_severity": "high"},
            )

        assert response.status_code == 404
        assert "Career DNA" in response.json()["detail"]

    async def test_get_preferences_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.get("/api/v1/threat-radar/preferences")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# COLLECTIVE INTELLIGENCE TESTS
# ═══════════════════════════════════════════════════════════════

# The /industry-snapshot endpoint uses require_feature("collective_intelligence"),
# which checks user tier. We bypass the gate by patching get_user_tier to return
# "pro" (which has collective_intelligence access) for CI tests.

_CI_FEATURE_GATE_PATCH = patch(
    "app.core.feature_gate.get_user_tier",
    return_value="pro",
)


class TestCIIndustrySnapshot:
    """POST /api/v1/collective-intelligence/industry-snapshot."""

    async def test_snapshot_returns_201(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-snapshot@pathforge.eu")
        headers = _auth_headers(user)
        snap = _stub_ci_snapshot()

        with (
            _CI_FEATURE_GATE_PATCH,
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_industry_snapshot",
                new=AsyncMock(return_value=snap),
            ),
        ):
            mock_settings.billing_enabled = False
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/industry-snapshot",
                headers=headers,
                json={"industry": "Technology", "region": "Netherlands"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["industry"] == "Technology"

    async def test_snapshot_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-snapshot-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            _CI_FEATURE_GATE_PATCH,
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_industry_snapshot",
                new=AsyncMock(side_effect=ValueError("Career DNA not found")),
            ),
        ):
            mock_settings.billing_enabled = False
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/industry-snapshot",
                headers=headers,
                json={"industry": "Technology", "region": "Netherlands"},
            )

        assert response.status_code == 400
        assert "Career DNA not found" in response.json()["detail"]

    async def test_snapshot_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/collective-intelligence/industry-snapshot",
            json={"industry": "Technology", "region": "Netherlands"},
        )
        assert response.status_code == 401


class TestCISalaryBenchmark:
    """POST /api/v1/collective-intelligence/salary-benchmark."""

    async def test_salary_benchmark_returns_201(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-salary@pathforge.eu")
        headers = _auth_headers(user)
        bench = _stub_ci_salary()

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_salary_benchmark",
                new=AsyncMock(return_value=bench),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/salary-benchmark",
                headers=headers,
                json={},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["currency"] == "EUR"
        assert body["benchmark_median"] == 72000.0

    async def test_salary_benchmark_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-salary-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_salary_benchmark",
                new=AsyncMock(side_effect=ValueError("no DNA")),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/salary-benchmark",
                headers=headers,
                json={},
            )

        assert response.status_code == 400

    async def test_salary_benchmark_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/collective-intelligence/salary-benchmark", json={},
        )
        assert response.status_code == 401


class TestCIPeerCohort:
    """POST /api/v1/collective-intelligence/peer-cohort."""

    async def test_peer_cohort_returns_201(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-cohort@pathforge.eu")
        headers = _auth_headers(user)
        cohort = _stub_ci_cohort()

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_peer_cohort_analysis",
                new=AsyncMock(return_value=cohort),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/peer-cohort",
                headers=headers,
                json={},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["cohort_size"] == 50

    async def test_peer_cohort_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-cohort-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_peer_cohort_analysis",
                new=AsyncMock(side_effect=ValueError("no DNA")),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/peer-cohort",
                headers=headers,
                json={},
            )

        assert response.status_code == 400

    async def test_peer_cohort_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/collective-intelligence/peer-cohort", json={},
        )
        assert response.status_code == 401


class TestCICareerPulse:
    """POST /api/v1/collective-intelligence/career-pulse."""

    async def test_career_pulse_returns_201(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-pulse@pathforge.eu")
        headers = _auth_headers(user)
        pulse = _stub_ci_pulse()

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_career_pulse",
                new=AsyncMock(return_value=pulse),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/career-pulse",
                headers=headers,
                json={},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["pulse_score"] == 72.0
        assert body["pulse_category"] == "healthy"

    async def test_career_pulse_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-pulse-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_career_pulse",
                new=AsyncMock(side_effect=ValueError("no DNA")),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/career-pulse",
                headers=headers,
                json={},
            )

        assert response.status_code == 400

    async def test_career_pulse_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/collective-intelligence/career-pulse", json={},
        )
        assert response.status_code == 401


class TestCIDashboard:
    """GET /api/v1/collective-intelligence/dashboard."""

    async def test_dashboard_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-dash@pathforge.eu")
        headers = _auth_headers(user)
        dashboard_data = {
            "latest_pulse": None,
            "industry_snapshots": [],
            "salary_benchmarks": [],
            "peer_cohort_analyses": [],
            "preferences": None,
        }

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_ci_dashboard",
                new=AsyncMock(return_value=dashboard_data),
            ),
        ):
            mock_settings.rate_limit_embed = "60/minute"
            response = await client.get(
                "/api/v1/collective-intelligence/dashboard", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["latest_pulse"] is None
        assert body["industry_snapshots"] == []

    async def test_dashboard_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/collective-intelligence/dashboard",
        )
        assert response.status_code == 401


class TestCIScan:
    """POST /api/v1/collective-intelligence/scan."""

    async def test_scan_returns_201(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-scan@pathforge.eu")
        headers = _auth_headers(user)
        scan_data = {
            "career_pulse": None,
            "industry_snapshot": None,
            "salary_benchmark": None,
            "peer_cohort": None,
        }

        with patch(
            "app.api.v1.collective_intelligence.ci_service.run_intelligence_scan",
            new=AsyncMock(return_value=scan_data),
        ):
            response = await client.post(
                "/api/v1/collective-intelligence/scan",
                headers=headers,
                json={},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["career_pulse"] is None

    async def test_scan_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-scan-err@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.collective_intelligence.ci_service.run_intelligence_scan",
            new=AsyncMock(side_effect=ValueError("no DNA")),
        ):
            response = await client.post(
                "/api/v1/collective-intelligence/scan",
                headers=headers,
                json={},
            )

        assert response.status_code == 400

    async def test_scan_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/collective-intelligence/scan", json={},
        )
        assert response.status_code == 401


class TestCICompareIndustries:
    """POST /api/v1/collective-intelligence/compare-industries."""

    async def test_compare_industries_returns_201(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-compare@pathforge.eu")
        headers = _auth_headers(user)
        compare_data = {
            "snapshots": [],
            "recommended_industry": "Technology",
            "recommendation_reasoning": "High growth",
        }

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.compare_industries",
                new=AsyncMock(return_value=compare_data),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/compare-industries",
                headers=headers,
                json={"industries": ["Technology", "Finance"], "region": "Netherlands"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["recommended_industry"] == "Technology"
        assert body["recommendation_reasoning"] == "High growth"

    async def test_compare_industries_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-compare-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.compare_industries",
                new=AsyncMock(side_effect=ValueError("too few industries")),
            ),
        ):
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/collective-intelligence/compare-industries",
                headers=headers,
                json={"industries": ["Technology", "Finance"], "region": "Netherlands"},
            )

        assert response.status_code == 400

    async def test_compare_industries_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            "/api/v1/collective-intelligence/compare-industries",
            json={"industries": ["A", "B"], "region": "EU"},
        )
        assert response.status_code == 401


class TestCIPreferences:
    """GET and PUT /api/v1/collective-intelligence/preferences."""

    async def test_get_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-pref-get@pathforge.eu")
        headers = _auth_headers(user)
        prefs = _stub_ci_prefs()

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_or_update_preferences",
                new=AsyncMock(return_value=prefs),
            ),
        ):
            mock_settings.rate_limit_parse = "30/minute"
            response = await client.get(
                "/api/v1/collective-intelligence/preferences", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["preferred_currency"] == "EUR"
        assert body["include_industry_pulse"] is True

    async def test_get_preferences_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-pref-get-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_or_update_preferences",
                new=AsyncMock(side_effect=ValueError("no DNA")),
            ),
        ):
            mock_settings.rate_limit_parse = "30/minute"
            response = await client.get(
                "/api/v1/collective-intelligence/preferences", headers=headers,
            )

        assert response.status_code == 400

    async def test_put_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-pref-put@pathforge.eu")
        headers = _auth_headers(user)
        prefs = _stub_ci_prefs()

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_or_update_preferences",
                new=AsyncMock(return_value=prefs),
            ),
        ):
            mock_settings.rate_limit_embed = "60/minute"
            response = await client.put(
                "/api/v1/collective-intelligence/preferences",
                headers=headers,
                json={"preferred_currency": "USD"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["preferred_currency"] == "EUR"

    async def test_put_preferences_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ci-pref-put-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch("app.api.v1.collective_intelligence.settings") as mock_settings,
            patch(
                "app.api.v1.collective_intelligence.ci_service.get_or_update_preferences",
                new=AsyncMock(side_effect=ValueError("no DNA")),
            ),
        ):
            mock_settings.rate_limit_embed = "60/minute"
            response = await client.put(
                "/api/v1/collective-intelligence/preferences",
                headers=headers,
                json={"preferred_currency": "USD"},
            )

        assert response.status_code == 400

    async def test_get_preferences_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.get(
            "/api/v1/collective-intelligence/preferences",
        )
        assert response.status_code == 401

    async def test_put_preferences_requires_auth(
        self, client: AsyncClient,
    ) -> None:
        response = await client.put(
            "/api/v1/collective-intelligence/preferences",
            json={},
        )
        assert response.status_code == 401
