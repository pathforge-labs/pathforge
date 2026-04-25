"""
PathForge — Predictive Career & Skill Decay Route Tests
=========================================================
Happy-path and error-path coverage for predictive_career and skill_decay
route handlers. Service calls are mocked; route-handler bodies are exercised.
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


# ── ORM-shaped Mock Factories ─────────────────────────────────────────────────
# Build MagicMock instances with every attribute Pydantic's `model_validate`
# (with `from_attributes=True`) needs. This lets the real route-handler code
# call `Schema.model_validate(orm_obj)` end-to-end without us patching the
# class method or any private response builders.


def _orm_career_forecast() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.career_dna_id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.outlook_score = 78.5
    obj.outlook_category = "strong"
    obj.forecast_horizon_months = 12
    obj.role_component = 20.0
    obj.disruption_component = 18.0
    obj.opportunity_component = 22.0
    obj.trend_component = 18.5
    obj.top_actions = None
    obj.key_risks = None
    obj.key_opportunities = None
    obj.summary = None
    obj.confidence_score = 0.82
    obj.data_source = "AI"
    obj.disclaimer = "Disclaimer"
    obj.created_at = _now()
    return obj


def _orm_pc_preference() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.career_dna_id = uuid.uuid4()
    obj.forecast_horizon_months = 12
    obj.include_emerging_roles = True
    obj.include_disruption_alerts = True
    obj.include_opportunities = True
    obj.risk_tolerance = "medium"
    obj.focus_industries = None
    obj.focus_regions = None
    obj.created_at = _now()
    return obj


def _orm_skill_freshness() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.skill_name = "Python"
    obj.category = "Programming"
    obj.last_active_date = "2026-04-01"
    obj.freshness_score = 100.0
    obj.half_life_days = 180
    obj.decay_rate = "slow"
    obj.days_since_active = 0
    obj.refresh_urgency = 0.0
    obj.analysis_reasoning = None
    obj.computed_at = _now()
    return obj


def _orm_skill_decay_preference() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.tracking_enabled = True
    obj.notification_frequency = "weekly"
    obj.decay_alert_threshold = 40.0
    obj.focus_categories = None
    obj.excluded_skills = None
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# Predictive Career Engine
# ═══════════════════════════════════════════════════════════════════════════════


class TestPredictiveCareerRoutes:
    """Coverage for app/api/v1/predictive_career.py handler bodies."""

    @pytest.mark.asyncio
    async def test_emerging_roles_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-er@example.com")
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
            rate_limit_career_dna="100/minute",
        ):
            resp = await client.post(
                "/api/v1/predictive-career/emerging-roles",
                headers=_auth(user),
                json={},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_emerging_roles_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-er-err@example.com")
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.predictive_career.pc_service.scan_emerging_roles",
            new_callable=AsyncMock,
            side_effect=ValueError("Career DNA missing"),
        ), patch(
            "app.api.v1.predictive_career.settings",
            billing_enabled=False,
            rate_limit_career_dna="100/minute",
        ):
            resp = await client.post(
                "/api/v1/predictive-career/emerging-roles",
                headers=_auth(user),
                json={},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_disruption_forecasts_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-df@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_disruption_forecasts",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.post(
                "/api/v1/predictive-career/disruption-forecasts",
                headers=_auth(user),
                json={"forecast_horizon_months": 12},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_disruption_forecasts_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-df-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_disruption_forecasts",
            new_callable=AsyncMock,
            side_effect=ValueError("DNA missing"),
        ):
            resp = await client.post(
                "/api/v1/predictive-career/disruption-forecasts",
                headers=_auth(user),
                json={},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_opportunity_surfaces_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-os@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_opportunity_surfaces",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.post(
                "/api/v1/predictive-career/opportunity-surfaces",
                headers=_auth(user),
                json={"include_cross_border": True},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_opportunity_surfaces_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-os-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_opportunity_surfaces",
            new_callable=AsyncMock,
            side_effect=ValueError("DNA missing"),
        ):
            resp = await client.post(
                "/api/v1/predictive-career/opportunity-surfaces",
                headers=_auth(user),
                json={},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_career_forecast_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-cf@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_career_forecast",
            new_callable=AsyncMock,
            return_value=_orm_career_forecast(),
        ):
            resp = await client.post(
                "/api/v1/predictive-career/career-forecast",
                headers=_auth(user),
                json={"forecast_horizon_months": 12},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_career_forecast_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-cf-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_career_forecast",
            new_callable=AsyncMock,
            side_effect=ValueError("DNA missing"),
        ):
            resp = await client.post(
                "/api/v1/predictive-career/career-forecast",
                headers=_auth(user),
                json={},
            )
        assert resp.status_code == 400

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
    async def test_dashboard_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-dash-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_pc_dashboard",
            new_callable=AsyncMock,
            side_effect=ValueError("Bad state"),
        ):
            resp = await client.get(
                "/api/v1/predictive-career/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_run_scan_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-scan@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.run_predictive_scan",
            new_callable=AsyncMock,
            return_value={
                "career_forecast": None,
                "emerging_roles": [],
                "disruption_forecasts": [],
                "opportunity_surfaces": [],
            },
        ):
            resp = await client.post(
                "/api/v1/predictive-career/scan",
                headers=_auth(user),
                json={"forecast_horizon_months": 12},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_run_scan_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-scan-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.run_predictive_scan",
            new_callable=AsyncMock,
            side_effect=ValueError("Career DNA missing"),
        ):
            resp = await client.post(
                "/api/v1/predictive-career/scan",
                headers=_auth(user),
                json={},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-pref@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_or_update_preferences",
            new_callable=AsyncMock,
            return_value=_orm_pc_preference(),
        ):
            resp = await client.get(
                "/api/v1/predictive-career/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-pref-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_or_update_preferences",
            new_callable=AsyncMock,
            side_effect=ValueError("DNA missing"),
        ):
            resp = await client.get(
                "/api/v1/predictive-career/preferences", headers=_auth(user)
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-upref@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_or_update_preferences",
            new_callable=AsyncMock,
            return_value=_orm_pc_preference(),
        ):
            resp = await client.put(
                "/api/v1/predictive-career/preferences",
                headers=_auth(user),
                json={"forecast_horizon_months": 18, "risk_tolerance": "high"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "pc-upref-err@example.com")
        with patch(
            "app.api.v1.predictive_career.pc_service.get_or_update_preferences",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid update"),
        ):
            resp = await client.put(
                "/api/v1/predictive-career/preferences",
                headers=_auth(user),
                json={"risk_tolerance": "extreme"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_predictive_career_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/predictive-career/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Skill Decay & Growth Tracker
# ═══════════════════════════════════════════════════════════════════════════════


class TestSkillDecayRoutes:
    """Coverage for app/api/v1/skill_decay.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_empty_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-dash-empty@example.com")
        with patch(
            "app.api.v1.skill_decay.ic_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.skill_decay.ic_cache.set",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.skill_decay.SkillDecayService.get_dashboard",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/skill-decay", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_with_data_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-dash-data@example.com")
        with patch(
            "app.api.v1.skill_decay.ic_cache.get",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.skill_decay.ic_cache.set",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.skill_decay.SkillDecayService.get_dashboard",
            new_callable=AsyncMock,
            return_value={
                "freshness": [],
                "freshness_summary": {
                    "total_skills": 0,
                    "average_freshness": 0.0,
                    "skills_at_risk": 0,
                    "freshest_skill": None,
                    "stalest_skill": None,
                },
                "market_demand": [],
                "velocity": [],
                "reskilling_pathways": [],
                "preference": None,
                "last_scan_at": None,
            },
        ):
            resp = await client.get(
                "/api/v1/skill-decay", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_cached_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-dash-cached@example.com")
        cached_payload = {
            "freshness": [],
            "freshness_summary": {
                "total_skills": 0,
                "average_freshness": 0.0,
                "skills_at_risk": 0,
                "freshest_skill": None,
                "stalest_skill": None,
            },
            "market_demand": [],
            "velocity": [],
            "reskilling_pathways": [],
            "preference": None,
            "last_scan_at": None,
        }
        with patch(
            "app.api.v1.skill_decay.ic_cache.get",
            new_callable=AsyncMock,
            return_value=cached_payload,
        ):
            resp = await client.get(
                "/api/v1/skill-decay", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trigger_scan_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-scan@example.com")
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.skill_decay.SkillDecayService.run_full_scan",
            new_callable=AsyncMock,
            return_value={
                "status": "completed",
                "skills_analyzed": 0,
                "freshness": [],
                "market_demand": [],
                "velocity": [],
                "reskilling_pathways": [],
            },
        ), patch(
            "app.api.v1.skill_decay.ic_cache.invalidate_user",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.skill_decay.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.skill_decay.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.skill_decay.settings",
            billing_enabled=False,
            rate_limit_career_dna="100/minute",
        ):
            resp = await client.post(
                "/api/v1/skill-decay/scan", headers=_auth(user)
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_trigger_scan_404_when_dna_missing(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-scan-err@example.com")
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.skill_decay.SkillDecayService.run_full_scan",
            new_callable=AsyncMock,
            return_value={"status": "error", "detail": "Career DNA required"},
        ), patch(
            "app.api.v1.skill_decay.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.skill_decay.settings",
            billing_enabled=False,
            rate_limit_career_dna="100/minute",
        ):
            resp = await client.post(
                "/api/v1/skill-decay/scan", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_freshness_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-fresh@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.get_freshness_scores",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/api/v1/skill-decay/freshness", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_market_demand_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-md@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.get_market_demand",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/api/v1/skill-decay/market-demand", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_velocity_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-vel@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.get_velocity_map",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/api/v1/skill-decay/velocity", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_reskilling_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-resk@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.get_reskilling_paths",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/api/v1/skill-decay/reskilling", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_skill_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-ref@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.refresh_skill",
            new_callable=AsyncMock,
            return_value=_orm_skill_freshness(),
        ), patch(
            "app.api.v1.skill_decay.ic_cache.invalidate_user",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                "/api/v1/skill-decay/refresh",
                headers=_auth(user),
                json={"skill_name": "Python"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_skill_404_when_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-ref-404@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.refresh_skill",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/skill-decay/refresh",
                headers=_auth(user),
                json={"skill_name": "Unknown"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200_when_exists(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-pref@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.get_preferences",
            new_callable=AsyncMock,
            return_value=_orm_skill_decay_preference(),
        ):
            resp = await client.get(
                "/api/v1/skill-decay/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-pref-none@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.get_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/skill-decay/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-upref@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.update_preferences",
            new_callable=AsyncMock,
            return_value=_orm_skill_decay_preference(),
        ):
            resp = await client.put(
                "/api/v1/skill-decay/preferences",
                headers=_auth(user),
                json={"notification_frequency": "daily"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_404_when_dna_missing(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "sd-upref-404@example.com")
        with patch(
            "app.api.v1.skill_decay.SkillDecayService.update_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.put(
                "/api/v1/skill-decay/preferences",
                headers=_auth(user),
                json={"notification_frequency": "weekly"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_skill_decay_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/skill-decay")
        assert resp.status_code == 401
