"""
PathForge — Predictive Career Engine™ Test Suite
===================================================
Tests for Sprint 19: models, analyzer static helpers, clamping validators.

Coverage:
    - Model creation (5 models)
    - Analyzer static methods (compute_outlook_score, outlook_category)
    - Clamping validators (emerging role, disruption, opportunity, forecast)
    - Schema validation (response models)
    - LLM methods (mocked)
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.predictive_career_analyzer import (
    MAX_PC_CONFIDENCE,
    PredictiveCareerAnalyzer,
    _clamp_career_forecast,
    _clamp_disruption_forecast,
    _clamp_emerging_role,
    _clamp_opportunity_surface,
)
from app.models.predictive_career import (
    CareerForecast,
    DisruptionForecast,
    DisruptionType,
    EmergenceStage,
    EmergingRole,
    OpportunitySurface,
    OpportunityType,
    PredictiveCareerPreference,
    RiskTolerance,
)
from app.schemas.predictive_career import (
    CareerForecastResponse,
    DisruptionForecastResponse,
    EmergingRoleResponse,
    OpportunitySurfaceResponse,
    PredictiveCareerDashboardResponse,
)

# ── Enum Tests ─────────────────────────────────────────────────


class TestEnums:
    """Test StrEnum definitions."""

    def test_emergence_stage_values(self) -> None:
        assert EmergenceStage.NASCENT == "nascent"
        assert EmergenceStage.GROWING == "growing"
        assert EmergenceStage.MAINSTREAM == "mainstream"
        assert EmergenceStage.DECLINING == "declining"

    def test_disruption_type_values(self) -> None:
        assert DisruptionType.TECHNOLOGY == "technology"
        assert DisruptionType.REGULATION == "regulation"
        assert DisruptionType.MARKET_SHIFT == "market_shift"
        assert DisruptionType.AUTOMATION == "automation"
        assert DisruptionType.CONSOLIDATION == "consolidation"

    def test_opportunity_type_values(self) -> None:
        assert OpportunityType.EMERGING_ROLE == "emerging_role"
        assert OpportunityType.SKILL_DEMAND == "skill_demand"
        assert OpportunityType.INDUSTRY_GROWTH == "industry_growth"
        assert OpportunityType.GEOGRAPHIC_EXPANSION == "geographic_expansion"

    def test_risk_tolerance_values(self) -> None:
        assert RiskTolerance.CONSERVATIVE == "conservative"
        assert RiskTolerance.MODERATE == "moderate"
        assert RiskTolerance.AGGRESSIVE == "aggressive"


# ── Model Creation Tests ──────────────────────────────────────


class TestEmergingRoleModel:
    """Test EmergingRole model instantiation."""

    def test_create_emerging_role(self) -> None:
        role = EmergingRole(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            role_title="AI Integration Engineer",
            industry="Technology",
            emergence_stage="nascent",
            growth_rate_pct=42.5,
            skill_overlap_pct=87.3,
            confidence_score=0.78,
        )
        assert role.role_title == "AI Integration Engineer"
        assert role.industry == "Technology"
        assert role.emergence_stage == "nascent"
        assert role.growth_rate_pct == 42.5
        assert role.skill_overlap_pct == 87.3
        assert role.confidence_score == 0.78
        assert role.__tablename__ == "pc_emerging_roles"

    def test_default_transparency_fields(self) -> None:
        role = EmergingRole(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            role_title="Test Role",
            industry="Tech",
            confidence_score=0.5,
        )
        if role.data_source is not None:
            assert "AI-analyzed" in role.data_source
        if role.disclaimer is not None:
            assert "85%" in role.disclaimer


class TestDisruptionForecastModel:
    """Test DisruptionForecast model instantiation."""

    def test_create_disruption_forecast(self) -> None:
        forecast = DisruptionForecast(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            disruption_title="EU AI Act Compliance",
            disruption_type="regulation",
            industry="Technology",
            severity_score=72.0,
            timeline_months=18,
            confidence_score=0.65,
        )
        assert forecast.disruption_title == "EU AI Act Compliance"
        assert forecast.disruption_type == "regulation"
        assert forecast.severity_score == 72.0
        assert forecast.timeline_months == 18
        assert forecast.__tablename__ == "pc_disruption_forecasts"


class TestOpportunitySurfaceModel:
    """Test OpportunitySurface model instantiation."""

    def test_create_opportunity_surface(self) -> None:
        opportunity = OpportunitySurface(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            opportunity_title="Fractional CTO Demand",
            opportunity_type="emerging_role",
            source_signal="market_analysis",
            relevance_score=85.0,
            confidence_score=0.72,
        )
        assert opportunity.opportunity_title == "Fractional CTO Demand"
        assert opportunity.opportunity_type == "emerging_role"
        assert opportunity.relevance_score == 85.0
        assert opportunity.__tablename__ == "pc_opportunity_surfaces"


class TestCareerForecastModel:
    """Test CareerForecast model instantiation."""

    def test_create_career_forecast(self) -> None:
        forecast = CareerForecast(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            outlook_score=73.0,
            outlook_category="favorable",
            forecast_horizon_months=12,
            role_component=80.0,
            disruption_component=65.0,
            opportunity_component=70.0,
            trend_component=75.0,
            confidence_score=0.68,
        )
        assert forecast.outlook_score == 73.0
        assert forecast.outlook_category == "favorable"
        assert forecast.forecast_horizon_months == 12
        assert forecast.__tablename__ == "pc_career_forecasts"


class TestPredictiveCareerPreferenceModel:
    """Test PredictiveCareerPreference model instantiation."""

    def test_create_preference(self) -> None:
        pref = PredictiveCareerPreference(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            forecast_horizon_months=24,
            include_emerging_roles=True,
            include_disruption_alerts=True,
            include_opportunities=True,
            risk_tolerance="aggressive",
        )
        assert pref.forecast_horizon_months == 24
        assert pref.include_emerging_roles is True
        assert pref.risk_tolerance == "aggressive"
        assert pref.__tablename__ == "pc_preferences"


# ── Static Helper Tests ───────────────────────────────────────


class TestComputeOutlookScore:
    """Test Career Forecast Index™ composite score computation."""

    def test_balanced_components(self) -> None:
        score = PredictiveCareerAnalyzer.compute_outlook_score(
            role=50.0, disruption=50.0, opportunity=50.0, trend=50.0,
        )
        assert score == 50.0

    def test_all_maximum(self) -> None:
        score = PredictiveCareerAnalyzer.compute_outlook_score(
            role=100.0, disruption=100.0, opportunity=100.0, trend=100.0,
        )
        assert score == 100.0

    def test_all_zero(self) -> None:
        score = PredictiveCareerAnalyzer.compute_outlook_score(
            role=0.0, disruption=0.0, opportunity=0.0, trend=0.0,
        )
        assert score == 0.0

    def test_weighted_formula(self) -> None:
        # 0.30*80 + 0.25*60 + 0.25*70 + 0.20*90
        # = 24 + 15 + 17.5 + 18 = 74.5
        score = PredictiveCareerAnalyzer.compute_outlook_score(
            role=80.0, disruption=60.0, opportunity=70.0, trend=90.0,
        )
        assert score == 74.5

    def test_clamps_above_100(self) -> None:
        score = PredictiveCareerAnalyzer.compute_outlook_score(
            role=200.0, disruption=200.0, opportunity=200.0, trend=200.0,
        )
        assert score == 100.0

    def test_clamps_below_0(self) -> None:
        score = PredictiveCareerAnalyzer.compute_outlook_score(
            role=-50.0, disruption=-50.0, opportunity=-50.0, trend=-50.0,
        )
        assert score == 0.0


class TestComputeOutlookCategory:
    """Test outlook score → category mapping."""

    def test_critical_range(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=15.0,
        ) == "critical"

    def test_at_risk_range(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=35.0,
        ) == "at_risk"

    def test_moderate_range(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=50.0,
        ) == "moderate"

    def test_favorable_range(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=70.0,
        ) == "favorable"

    def test_exceptional_range(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=90.0,
        ) == "exceptional"

    def test_boundary_20_is_critical(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=20.0,
        ) == "critical"

    def test_boundary_40_is_at_risk(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=40.0,
        ) == "at_risk"

    def test_boundary_60_is_moderate(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=60.0,
        ) == "moderate"

    def test_boundary_80_is_favorable(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(
            outlook_score=80.0,
        ) == "favorable"


# ── Clamping Validator Tests ──────────────────────────────────


class TestClampEmergingRole:
    """Test _clamp_emerging_role validator."""

    def test_clamps_confidence_above_max(self) -> None:
        data: dict[str, Any] = {"confidence": 0.95}
        _clamp_emerging_role(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_clamps_confidence_below_zero(self) -> None:
        data: dict[str, Any] = {"confidence": -0.5}
        _clamp_emerging_role(data)
        assert data["confidence"] == 0.0

    def test_invalid_confidence_type(self) -> None:
        data: dict[str, Any] = {"confidence": "invalid"}
        _clamp_emerging_role(data)
        assert data["confidence"] == 0.0

    def test_invalid_stage_defaults_to_nascent(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "emergence_stage": "unknown",
        }
        _clamp_emerging_role(data)
        assert data["emergence_stage"] == "nascent"

    def test_valid_stage_preserved(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "emergence_stage": "growing",
        }
        _clamp_emerging_role(data)
        assert data["emergence_stage"] == "growing"

    def test_skill_overlap_clamped_below_zero(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "skill_overlap_pct": -10.0,
        }
        _clamp_emerging_role(data)
        assert data["skill_overlap_pct"] == 0.0

    def test_skill_overlap_clamped_above_100(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "skill_overlap_pct": 150.0,
        }
        _clamp_emerging_role(data)
        assert data["skill_overlap_pct"] == 100.0

    def test_negative_months_set_to_none(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "time_to_mainstream_months": -3,
        }
        _clamp_emerging_role(data)
        assert data["time_to_mainstream_months"] is None

    def test_valid_months_preserved(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "time_to_mainstream_months": 18,
        }
        _clamp_emerging_role(data)
        assert data["time_to_mainstream_months"] == 18

    def test_negative_salary_range_cleared(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "avg_salary_range_min": -1000,
            "avg_salary_range_max": -500,
        }
        _clamp_emerging_role(data)
        assert data["avg_salary_range_min"] is None
        assert data["avg_salary_range_max"] is None


class TestClampDisruptionForecast:
    """Test _clamp_disruption_forecast validator."""

    def test_clamps_confidence(self) -> None:
        data: dict[str, Any] = {"confidence": 0.99}
        _clamp_disruption_forecast(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_invalid_disruption_type_defaults(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "disruption_type": "unknown",
        }
        _clamp_disruption_forecast(data)
        assert data["disruption_type"] == "technology"

    def test_valid_disruption_type_preserved(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "disruption_type": "regulation",
        }
        _clamp_disruption_forecast(data)
        assert data["disruption_type"] == "regulation"

    def test_severity_clamped_above_100(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "severity_score": 150.0,
        }
        _clamp_disruption_forecast(data)
        assert data["severity_score"] == 100.0

    def test_severity_clamped_below_zero(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "severity_score": -20.0,
        }
        _clamp_disruption_forecast(data)
        assert data["severity_score"] == 0.0

    def test_timeline_months_minimum(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "timeline_months": 0,
        }
        _clamp_disruption_forecast(data)
        assert data["timeline_months"] == 1

    def test_invalid_timeline_type(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "timeline_months": "invalid",
        }
        _clamp_disruption_forecast(data)
        assert data["timeline_months"] == 12


class TestClampOpportunitySurface:
    """Test _clamp_opportunity_surface validator."""

    def test_clamps_confidence(self) -> None:
        data: dict[str, Any] = {"confidence": 1.0}
        _clamp_opportunity_surface(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_invalid_type_defaults(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "opportunity_type": "invalid",
        }
        _clamp_opportunity_surface(data)
        assert data["opportunity_type"] == "emerging_role"

    def test_valid_type_preserved(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "opportunity_type": "skill_demand",
        }
        _clamp_opportunity_surface(data)
        assert data["opportunity_type"] == "skill_demand"

    def test_relevance_clamped_above_100(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "relevance_score": 120.0,
        }
        _clamp_opportunity_surface(data)
        assert data["relevance_score"] == 100.0

    def test_relevance_clamped_below_zero(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "relevance_score": -10.0,
        }
        _clamp_opportunity_surface(data)
        assert data["relevance_score"] == 0.0


class TestClampCareerForecast:
    """Test _clamp_career_forecast validator."""

    def test_clamps_confidence(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.99,
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_recomputes_outlook_from_components(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.70,
            "role_component": 80.0,
            "disruption_component": 60.0,
            "opportunity_component": 70.0,
            "trend_component": 90.0,
            "outlook_score": 0.0,  # Will be recomputed
        }
        _clamp_career_forecast(data)
        # 0.30*80 + 0.25*60 + 0.25*70 + 0.20*90 = 74.5
        assert data["outlook_score"] == 74.5
        assert data["outlook_category"] == "favorable"

    def test_clamps_components_above_100(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "role_component": 150.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["role_component"] == 100.0

    def test_clamps_components_below_zero(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "role_component": -20.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["role_component"] == 0.0

    def test_invalid_component_type_defaults_to_50(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "role_component": "invalid",
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["role_component"] == 50.0

    def test_forecast_horizon_clamped_minimum(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
            "forecast_horizon_months": 1,
        }
        _clamp_career_forecast(data)
        assert data["forecast_horizon_months"] == 3

    def test_forecast_horizon_clamped_maximum(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
            "forecast_horizon_months": 72,
        }
        _clamp_career_forecast(data)
        assert data["forecast_horizon_months"] == 36

    def test_zero_components_produce_critical(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "role_component": 0.0,
            "disruption_component": 0.0,
            "opportunity_component": 0.0,
            "trend_component": 0.0,
        }
        _clamp_career_forecast(data)
        assert data["outlook_score"] == 0.0
        assert data["outlook_category"] == "critical"


# ── LLM Method Tests (Mocked) ────────────────────────────────


class TestAnalyzeEmergingRolesMocked:
    """Test analyze_emerging_roles with mocked LLM."""

    @pytest.mark.asyncio
    async def test_returns_clamped_roles(self) -> None:
        mock_response = {
            "emerging_roles": [
                {
                    "role_title": "AI Safety Engineer",
                    "emergence_stage": "nascent",
                    "growth_rate_pct": 45.0,
                    "skill_overlap_pct": 78.0,
                    "confidence": 0.90,
                    "time_to_mainstream_months": 24,
                    "avg_salary_range_min": 80000,
                    "avg_salary_range_max": 120000,
                },
            ],
        }
        with patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            roles = await PredictiveCareerAnalyzer.analyze_emerging_roles(
                industry="Technology",
                region="Netherlands",
                min_skill_overlap_pct=50.0,
                primary_role="Software Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, FastAPI, PostgreSQL",
                years_experience=8,
                location="Amsterdam",
            )

        assert len(roles) == 1
        assert roles[0]["role_title"] == "AI Safety Engineer"
        assert roles[0]["confidence"] == MAX_PC_CONFIDENCE  # Clamped
        assert roles[0]["skill_overlap_pct"] == 78.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty(self) -> None:
        from app.core.llm import LLMError

        with patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("Service unavailable"),
        ):
            roles = await PredictiveCareerAnalyzer.analyze_emerging_roles(
                industry="Technology",
                region="Netherlands",
                min_skill_overlap_pct=50.0,
                primary_role="Software Engineer",
                seniority_level="mid",
                primary_industry="Technology",
                skills="Python",
                years_experience=5,
                location="Amsterdam",
            )

        assert roles == []


class TestForecastDisruptionsMocked:
    """Test forecast_disruptions with mocked LLM."""

    @pytest.mark.asyncio
    async def test_returns_clamped_disruptions(self) -> None:
        mock_response = {
            "disruptions": [
                {
                    "disruption_title": "EU AI Act Compliance",
                    "disruption_type": "regulation",
                    "severity_score": 72.0,
                    "timeline_months": 18,
                    "confidence": 0.70,
                    "impact_on_user": "Moderate impact on AI development roles",
                },
            ],
        }
        with patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            disruptions = await PredictiveCareerAnalyzer.forecast_disruptions(
                industry="Technology",
                forecast_horizon_months=12,
                primary_role="Software Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, ML, FastAPI",
                years_experience=8,
                location="Amsterdam",
            )

        assert len(disruptions) == 1
        assert disruptions[0]["disruption_type"] == "regulation"
        assert disruptions[0]["confidence"] == 0.70


class TestSurfaceOpportunitiesMocked:
    """Test surface_opportunities with mocked LLM."""

    @pytest.mark.asyncio
    async def test_returns_clamped_opportunities(self) -> None:
        mock_response = {
            "opportunities": [
                {
                    "opportunity_title": "Fractional CTO Demand",
                    "opportunity_type": "emerging_role",
                    "relevance_score": 85.0,
                    "confidence": 0.75,
                    "reasoning": "Growing demand in EU market",
                },
            ],
        }
        with patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            opportunities = await PredictiveCareerAnalyzer.surface_opportunities(
                industry="Technology",
                region="Europe",
                include_cross_border=True,
                primary_role="CTO",
                seniority_level="lead",
                primary_industry="Technology",
                skills="Architecture, Python, AWS",
                years_experience=15,
                location="Amsterdam",
            )

        assert len(opportunities) == 1
        assert opportunities[0]["opportunity_type"] == "emerging_role"
        assert opportunities[0]["relevance_score"] == 85.0


class TestComputeCareerForecastMocked:
    """Test compute_career_forecast with mocked LLM."""

    @pytest.mark.asyncio
    async def test_returns_clamped_forecast(self) -> None:
        mock_response = {
            "role_component": 80.0,
            "disruption_component": 60.0,
            "opportunity_component": 70.0,
            "trend_component": 90.0,
            "confidence": 0.70,
            "forecast_horizon_months": 12,
            "top_actions": ["Upskill in AI/ML"],
            "key_risks": ["Industry consolidation"],
            "summary": "Favorable outlook with action recommended.",
        }
        with patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            forecast = await PredictiveCareerAnalyzer.compute_career_forecast(
                industry="Technology",
                region="Netherlands",
                forecast_horizon_months=12,
                emerging_roles_count=3,
                disruptions_count=2,
                opportunities_count=4,
                primary_role="Software Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, FastAPI",
                years_experience=8,
                location="Amsterdam",
            )

        assert forecast["outlook_score"] == 74.5
        assert forecast["outlook_category"] == "favorable"
        assert forecast["confidence"] == 0.70

    @pytest.mark.asyncio
    async def test_llm_error_returns_safe_default(self) -> None:
        from app.core.llm import LLMError

        with patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("Timeout"),
        ):
            forecast = await PredictiveCareerAnalyzer.compute_career_forecast(
                industry="Technology",
                region="Netherlands",
                forecast_horizon_months=12,
                emerging_roles_count=0,
                disruptions_count=0,
                opportunities_count=0,
                primary_role="Software Engineer",
                seniority_level="mid",
                primary_industry="Technology",
                skills="Python",
                years_experience=5,
                location="Amsterdam",
            )

        assert forecast["outlook_score"] == 50.0
        assert forecast["outlook_category"] == "moderate"
        assert forecast["confidence"] == 0.0


# ── Schema Validation Tests ──────────────────────────────────


class TestSchemaValidation:
    """Test Pydantic response schemas accept model-like data."""

    def test_emerging_role_response(self) -> None:
        data = {
            "id": str(uuid.uuid4()),
            "career_dna_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "role_title": "AI Engineer",
            "industry": "Technology",
            "emergence_stage": "nascent",
            "growth_rate_pct": 42.0,
            "skill_overlap_pct": 78.0,
            "confidence_score": 0.72,
            "data_source": "AI-analyzed signals",
            "disclaimer": "AI-generated predictions",
            "created_at": "2026-02-23T01:00:00",
            "updated_at": "2026-02-23T01:00:00",
        }
        response = EmergingRoleResponse.model_validate(data)
        assert response.role_title == "AI Engineer"
        assert response.confidence_score == 0.72

    def test_disruption_forecast_response(self) -> None:
        data = {
            "id": str(uuid.uuid4()),
            "career_dna_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "disruption_title": "AI Automation Wave",
            "disruption_type": "automation",
            "industry": "Technology",
            "severity_score": 65.0,
            "timeline_months": 12,
            "confidence_score": 0.60,
            "data_source": "AI-analyzed signals",
            "disclaimer": "AI-generated predictions",
            "created_at": "2026-02-23T01:00:00",
            "updated_at": "2026-02-23T01:00:00",
        }
        response = DisruptionForecastResponse.model_validate(data)
        assert response.disruption_type == "automation"

    def test_opportunity_surface_response(self) -> None:
        data = {
            "id": str(uuid.uuid4()),
            "career_dna_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "opportunity_title": "Growth Analyst",
            "opportunity_type": "skill_demand",
            "source_signal": "market_analysis",
            "relevance_score": 80.0,
            "confidence_score": 0.68,
            "data_source": "AI-analyzed signals",
            "disclaimer": "AI-generated predictions",
            "created_at": "2026-02-23T01:00:00",
            "updated_at": "2026-02-23T01:00:00",
        }
        response = OpportunitySurfaceResponse.model_validate(data)
        assert response.relevance_score == 80.0

    def test_career_forecast_response(self) -> None:
        data = {
            "id": str(uuid.uuid4()),
            "career_dna_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "outlook_score": 72.0,
            "outlook_category": "favorable",
            "forecast_horizon_months": 12,
            "role_component": 80.0,
            "disruption_component": 65.0,
            "opportunity_component": 70.0,
            "trend_component": 75.0,
            "confidence_score": 0.65,
            "data_source": "AI-computed signals",
            "disclaimer": "AI-generated predictions",
            "created_at": "2026-02-23T01:00:00",
            "updated_at": "2026-02-23T01:00:00",
        }
        response = CareerForecastResponse.model_validate(data)
        assert response.outlook_category == "favorable"

    def test_dashboard_response(self) -> None:
        data = {
            "emerging_roles": [],
            "disruption_forecasts": [],
            "opportunity_surfaces": [],
            "latest_forecast": None,
        }
        response = PredictiveCareerDashboardResponse.model_validate(data)
        assert response.emerging_roles == []
        assert response.latest_forecast is None
        assert "Predictive Career Engine" in response.data_source


# ── Confidence Cap Tests ──────────────────────────────────────


class TestConfidenceCap:
    """Verify the 0.85 confidence cap across all clampers."""

    def test_max_confidence_constant(self) -> None:
        assert MAX_PC_CONFIDENCE == 0.85

    def test_emerging_role_cap(self) -> None:
        data: dict[str, Any] = {"confidence": 1.0}
        _clamp_emerging_role(data)
        assert data["confidence"] == 0.85

    def test_disruption_forecast_cap(self) -> None:
        data: dict[str, Any] = {"confidence": 1.0}
        _clamp_disruption_forecast(data)
        assert data["confidence"] == 0.85

    def test_opportunity_surface_cap(self) -> None:
        data: dict[str, Any] = {"confidence": 1.0}
        _clamp_opportunity_surface(data)
        assert data["confidence"] == 0.85

    def test_career_forecast_cap(self) -> None:
        data: dict[str, Any] = {
            "confidence": 1.0,
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["confidence"] == 0.85
