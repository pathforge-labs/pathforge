"""
PathForge — Career DNA, Career Action Planner, Salary Intelligence,
            Predictive Career & Notifications Route Tests
==================================================================
Happy-path and error-path coverage for 5 route modules.
Service calls are mocked; route-handler bodies are exercised.
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
from app.schemas.career_action_planner import (
    CareerActionPlannerPreferenceResponse,
    CareerActionPlanResponse,
    PlanStatsResponse,
)
from app.schemas.career_dna import CareerDNAResponse as _CareerDNAResponse
from app.schemas.notification import (
    NotificationDigestResponse,
    NotificationPreferenceResponse,
)
from app.schemas.predictive_career import PredictiveCareerPreferenceResponse
from app.schemas.salary_intelligence import (
    SalaryEstimateResponse,
    SalaryPreferenceResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str) -> User:
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


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _now() -> datetime:
    return datetime.now(UTC)


def _career_dna_response() -> _CareerDNAResponse:
    return _CareerDNAResponse(
        id=uuid.uuid4(),
        completeness_score=0.85,
        version=1,
    )


# ── Schema factories ───────────────────────────────────────────────────────────


def _cap_response() -> CareerActionPlanResponse:
    return CareerActionPlanResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        title="Become Staff Engineer",
        objective="Senior to Staff growth plan",
        plan_type="career_growth",
        status="active",
        priority_score=80.0,
        confidence=0.75,
        data_source="AI Analysis",
        disclaimer="For guidance only",
        created_at=_now(),
    )


def _cap_pref() -> CareerActionPlannerPreferenceResponse:
    return CareerActionPlannerPreferenceResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        preferred_sprint_length_weeks=4,
        max_milestones_per_plan=10,
        notification_frequency="weekly",
        auto_generate_recommendations=True,
        created_at=_now(),
    )


def _salary_estimate() -> SalaryEstimateResponse:
    return SalaryEstimateResponse(
        id=uuid.uuid4(),
        role_title="Software Engineer",
        location="Remote",
        seniority_level="senior",
        industry="Technology",
        estimated_min=80000.0,
        estimated_max=120000.0,
        estimated_median=100000.0,
        confidence=0.82,
        data_points_count=500,
        computed_at=_now(),
    )


def _salary_pref() -> SalaryPreferenceResponse:
    return SalaryPreferenceResponse(id=uuid.uuid4())


def _pc_pref() -> PredictiveCareerPreferenceResponse:
    return PredictiveCareerPreferenceResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        forecast_horizon_months=12,
        include_emerging_roles=True,
        include_disruption_alerts=True,
        include_opportunities=True,
        risk_tolerance="medium",
        created_at=_now(),
    )


def _notif_pref() -> NotificationPreferenceResponse:
    return NotificationPreferenceResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        min_severity="info",
        digest_enabled=True,
        digest_frequency="weekly",
        in_app_notifications=True,
        email_notifications=True,
        push_notifications=False,
        created_at=_now(),
        updated_at=_now(),
    )


def _notif_digest() -> NotificationDigestResponse:
    return NotificationDigestResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        digest_type="weekly",
        period_start=_now(),
        period_end=_now(),
        notification_count=5,
        created_at=_now(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Career DNA
# ═══════════════════════════════════════════════════════════════════════════════


class TestCareerDNARoutes:
    """Coverage for app/api/v1/career_dna.py handler bodies."""

    def _profile_mock(self) -> MagicMock:
        p = MagicMock()
        p.id = uuid.uuid4()
        p.user_id = uuid.uuid4()
        p.headline = "Software Engineer"
        p.career_stage = "mid"
        p.dominant_work_style = "analytical"
        p.core_identity_tags = []
        p.created_at = _now()
        p.updated_at = _now()
        p.skill_genome = []
        p.experience_blueprint = MagicMock()
        p.growth_vector = MagicMock()
        p.values_profile = MagicMock()
        p.market_position = MagicMock()
        p.hidden_skills = []
        return p

    @pytest.mark.asyncio
    async def test_get_full_profile_uses_cache_hit(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "dna-cache@example.com")
        dna = _career_dna_response()
        cached_data = {"id": str(uuid.uuid4()), "completeness_score": 0.9, "version": 1}
        with patch(
            "app.api.v1.career_dna.ic_cache.get",
            new_callable=AsyncMock,
            return_value=cached_data,
        ), patch(
            "app.api.v1.career_dna.CareerDNAResponse.model_validate",
            return_value=dna,
        ):
            resp = await client.get("/api/v1/career-dna", headers=_auth(user))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_full_profile_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "dna-404@example.com")
        with patch(
            "app.api.v1.career_dna.CareerDNAService.get_full_profile",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.career_dna.ic_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get("/api/v1/career-dna", headers=_auth(user))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_profile_returns_200_or_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "dna-del@example.com")
        with patch(
            "app.api.v1.career_dna.CareerDNAService.delete_profile",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_dna.ic_cache.invalidate_user",
            new_callable=AsyncMock,
        ):
            resp = await client.delete("/api/v1/career-dna", headers=_auth(user))
        assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_generate_profile_returns_success(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "dna-gen@example.com")
        dna = _career_dna_response()
        with patch(
            "app.api.v1.career_dna.CareerDNAService.generate_full_profile",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_dna._build_full_response",
            return_value=dna,
        ), patch(
            "app.api.v1.career_dna.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_dna.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_dna.ic_cache.invalidate_user",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_dna.ic_cache.set",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_dna.settings",
            billing_enabled=False,
        ):
            resp = await client.post(
                "/api/v1/career-dna/generate",
                headers=_auth(user),
                json={"dimensions": []},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_profile_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/career-dna")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Career Action Planner
# ═══════════════════════════════════════════════════════════════════════════════


class TestCareerActionPlannerRoutes:
    """Coverage for app/api/v1/career_action_planner.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-dash@example.com")
        result_mock = MagicMock()
        result_mock.active_plans = []
        result_mock.recent_recommendations = []
        result_mock.stats = MagicMock()
        result_mock.preferences = None
        with patch(
            "app.api.v1.career_action_planner.service.get_dashboard",
            new_callable=AsyncMock,
            return_value=result_mock,
        ), patch(
            "app.api.v1.career_action_planner.PlanStatsResponse.model_validate",
            return_value=PlanStatsResponse(),
        ):
            resp = await client.get(
                "/api/v1/career-action-planner/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_scan_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-scan@example.com")
        scan_result = MagicMock()
        scan_result.plan = MagicMock()
        scan_result.recommendations = []
        cap = _cap_response()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.career_action_planner.service.generate_plan",
            new_callable=AsyncMock,
            return_value=scan_result,
        ), patch(
            "app.api.v1.career_action_planner.CareerActionPlanResponse.model_validate",
            return_value=cap,
        ), patch(
            "app.api.v1.career_action_planner.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_action_planner.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_action_planner.settings",
            billing_enabled=False,
        ):
            resp = await client.post(
                "/api/v1/career-action-planner/scan",
                headers=_auth(user),
                json={"plan_type": "career_growth"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_plan_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-detail@example.com")
        plan_id = uuid.uuid4()
        cap = _cap_response()
        with patch(
            "app.api.v1.career_action_planner.service.get_plan",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_action_planner.CareerActionPlanResponse.model_validate",
            return_value=cap,
        ):
            resp = await client.get(
                f"/api/v1/career-action-planner/{plan_id}", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_plan_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-404@example.com")
        plan_id = uuid.uuid4()
        with patch(
            "app.api.v1.career_action_planner.service.get_plan",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/career-action-planner/{plan_id}", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_plan_status_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-status@example.com")
        plan_id = uuid.uuid4()
        cap = _cap_response()
        with patch(
            "app.api.v1.career_action_planner.service.update_plan_status",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_action_planner.CareerActionPlanResponse.model_validate",
            return_value=cap,
        ):
            resp = await client.put(
                f"/api/v1/career-action-planner/{plan_id}/status",
                headers=_auth(user),
                json={"status": "completed"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-pref@example.com")
        pref = _cap_pref()
        with patch(
            "app.api.v1.career_action_planner.service.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_action_planner.CareerActionPlannerPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/career-action-planner/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_returns_null_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-pref-none@example.com")
        with patch(
            "app.api.v1.career_action_planner.service.get_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/career-action-planner/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cap-upref@example.com")
        pref = _cap_pref()
        with patch(
            "app.api.v1.career_action_planner.service.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_action_planner.CareerActionPlannerPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/career-action-planner/preferences",
                headers=_auth(user),
                json={"preferred_sprint_length_weeks": 2},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/career-action-planner/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Salary Intelligence
# ═══════════════════════════════════════════════════════════════════════════════


class TestSalaryIntelligenceRoutes:
    """Coverage for app/api/v1/salary_intelligence.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-dash@example.com")
        dashboard = MagicMock()
        dashboard.estimate = None
        dashboard.skill_impacts = []
        dashboard.trajectory = None
        dashboard.recent_scenarios = []
        dashboard.preference = None
        dashboard.last_scan_at = None
        dashboard.data_source = "AI"
        dashboard.disclaimer = "Test"
        with patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_dashboard",
            new_callable=AsyncMock,
            return_value=dashboard,
        ), patch(
            "app.api.v1.salary_intelligence.SalaryDashboardResponse.model_validate",
            return_value=MagicMock(),
        ):
            resp = await client.get(
                "/api/v1/salary-intelligence", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_scan_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-scan@example.com")
        est = _salary_estimate()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.run_full_scan",
            new_callable=AsyncMock,
            return_value={
                "status": "completed",
                "estimate": None,
                "skill_impacts": [],
                "history_entry_created": False,
            },
        ), patch(
            "app.api.v1.salary_intelligence.ic_cache.invalidate_user",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.salary_intelligence.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.salary_intelligence.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.salary_intelligence.settings",
            billing_enabled=False,
        ):
            resp = await client.post(
                "/api/v1/salary-intelligence/scan", headers=_auth(user), json={}
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_estimate_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-est@example.com")
        est = _salary_estimate()
        with patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_salary_estimate",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.salary_intelligence.SalaryEstimateResponse.model_validate",
            return_value=est,
        ):
            resp = await client.get(
                "/api/v1/salary-intelligence/estimate", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_estimate_returns_null_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-est-404@example.com")
        with patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_salary_estimate",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/salary-intelligence/estimate", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_scenarios_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-scenarios@example.com")
        with patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_scenarios",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/api/v1/salary-intelligence/scenarios", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-pref@example.com")
        pref = _salary_pref()
        with patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.salary_intelligence.SalaryPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/salary-intelligence/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sal-upref@example.com")
        pref = _salary_pref()
        with patch(
            "app.api.v1.salary_intelligence.SalaryIntelligenceService.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.salary_intelligence.SalaryPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/salary-intelligence/preferences",
                headers=_auth(user),
                json={"preferred_currency": "EUR"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/salary-intelligence")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Predictive Career
# ═══════════════════════════════════════════════════════════════════════════════


class TestPredictiveCareerRoutes:
    """Coverage for app/api/v1/predictive_career.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-dash@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_pc_dashboard",
            new_callable=AsyncMock,
            return_value={
                "latest_forecast": None,
                "emerging_roles": [],
                "disruption_forecasts": [],
                "opportunity_surfaces": [],
                "preferences": None,
            },
        ):
            resp = await client.get(
                "/api/v1/predictive-career/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_emerging_roles_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-roles@example.com")
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.predictive_career.pc_service.scan_emerging_roles",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.api.v1.predictive_career.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.predictive_career.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.predictive_career.settings",
            billing_enabled=False,
        ):
            resp = await client.post(
                "/api/v1/predictive-career/emerging-roles",
                headers=_auth(user),
                json={"industry": "Technology"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-pref@example.com")
        pref = _pc_pref()
        with patch(
            "app.api.v1.predictive_career.pc_service.get_or_update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.predictive_career.PredictiveCareerPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/predictive-career/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-upref@example.com")
        pref = _pc_pref()
        with patch(
            "app.api.v1.predictive_career.pc_service.get_or_update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.predictive_career.PredictiveCareerPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/predictive-career/preferences",
                headers=_auth(user),
                json={"forecast_horizon_months": 24},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/predictive-career/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════════════════════════


class TestNotificationsRoutes:
    """Coverage for app/api/v1/notifications.py handler bodies."""

    @pytest.mark.asyncio
    async def test_list_notifications_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-list@example.com")
        with patch(
            "app.api.v1.notifications.NotificationService.list_notifications",
            new_callable=AsyncMock,
            return_value={
                "notifications": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "has_next": False,
            },
        ):
            resp = await client.get("/api/v1/notifications/", headers=_auth(user))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unread_count_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-count@example.com")
        with patch(
            "app.api.v1.notifications.NotificationService.get_unread_count",
            new_callable=AsyncMock,
            return_value={
                "total_unread": 3,
                "by_severity": {"info": 3, "warning": 0, "critical": 0},
                "by_engine": {},
            },
        ):
            resp = await client.get("/api/v1/notifications/count", headers=_auth(user))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_read_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-mark@example.com")
        nid = uuid.uuid4()
        with patch(
            "app.api.v1.notifications.NotificationService.mark_read",
            new_callable=AsyncMock,
            return_value=1,
        ):
            resp = await client.post(
                "/api/v1/notifications/mark-read",
                headers=_auth(user),
                json={"notification_ids": [str(nid)]},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_all_read_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-all@example.com")
        with patch(
            "app.api.v1.notifications.NotificationService.mark_all_read",
            new_callable=AsyncMock,
            return_value=5,
        ):
            resp = await client.post(
                "/api/v1/notifications/mark-all-read", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_digests_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-dig@example.com")
        with patch(
            "app.api.v1.notifications.NotificationService.list_digests",
            new_callable=AsyncMock,
            return_value={
                "digests": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
            },
        ):
            resp = await client.get(
                "/api/v1/notifications/digests", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_digest_returns_null(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-gendig-null@example.com")
        with patch(
            "app.api.v1.notifications.NotificationService.generate_digest",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/notifications/digests/generate?digest_type=weekly",
                headers=_auth(user),
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_generate_digest_returns_digest(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-gendig@example.com")
        digest = _notif_digest()
        with patch(
            "app.api.v1.notifications.NotificationService.generate_digest",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.notifications.NotificationDigestResponse.model_validate",
            return_value=digest,
        ):
            resp = await client.post(
                "/api/v1/notifications/digests/generate?digest_type=daily",
                headers=_auth(user),
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-pref@example.com")
        pref = _notif_pref()
        with patch(
            "app.api.v1.notifications.NotificationService.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.notifications.NotificationPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/notifications/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-pref-404@example.com")
        with patch(
            "app.api.v1.notifications.NotificationService.get_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/notifications/preferences", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-upref@example.com")
        pref = _notif_pref()
        with patch(
            "app.api.v1.notifications.NotificationService.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.notifications.NotificationPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/notifications/preferences",
                headers=_auth(user),
                json={"email_notifications": False},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_push_status_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-push@example.com")
        with patch(
            "app.api.v1.notifications.push_service.get_status",
            new_callable=AsyncMock,
            return_value={"registered": True, "token": "tok***", "platform": "ios"},
        ):
            resp = await client.get(
                "/api/v1/notifications/push-status", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_digest_400_bad_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "notif-400@example.com")
        resp = await client.post(
            "/api/v1/notifications/digests/generate?digest_type=monthly",
            headers=_auth(user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_notifications_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/notifications/")
        assert resp.status_code == 401
