"""
Unit tests for PredictiveCareerAnalyzer.

Covers:
  - 2 static helpers (compute_outlook_score, compute_outlook_category)
  - 4 async LLM methods (analyze_emerging_roles, forecast_disruptions,
    surface_opportunities, compute_career_forecast)
  - 4 private clamping validators (_clamp_emerging_role,
    _clamp_disruption_forecast, _clamp_opportunity_surface,
    _clamp_career_forecast)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.predictive_career_analyzer import (
    MAX_PC_CONFIDENCE,
    VALID_DISRUPTION_TYPES,
    VALID_EMERGENCE_STAGES,
    VALID_OPPORTUNITY_TYPES,
    PredictiveCareerAnalyzer,
    _clamp_career_forecast,
    _clamp_disruption_forecast,
    _clamp_emerging_role,
    _clamp_opportunity_surface,
)

# ── Helpers ────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str) -> tuple[str, dict]:
    return text[:max_length], {}


def _patch_sanitize():
    return patch(
        "app.ai.predictive_career_analyzer.sanitize_user_text",
        side_effect=_sanitize_passthrough,
    )


def _patch_complete_json(return_value):
    return patch(
        "app.ai.predictive_career_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── compute_outlook_score ──────────────────────────────────────


class TestComputeOutlookScore:
    def test_basic_weighted_formula(self) -> None:
        # 0.30*80 + 0.25*70 + 0.25*60 + 0.20*50 = 24+17.5+15+10 = 66.5
        result = PredictiveCareerAnalyzer.compute_outlook_score(
            role=80.0, disruption=70.0, opportunity=60.0, trend=50.0,
        )
        assert abs(result - 66.5) < 0.01

    def test_all_100_returns_100(self) -> None:
        result = PredictiveCareerAnalyzer.compute_outlook_score(
            role=100.0, disruption=100.0, opportunity=100.0, trend=100.0,
        )
        assert result == 100.0

    def test_all_zero_returns_zero(self) -> None:
        result = PredictiveCareerAnalyzer.compute_outlook_score(
            role=0.0, disruption=0.0, opportunity=0.0, trend=0.0,
        )
        assert result == 0.0

    def test_negative_clamped_to_zero(self) -> None:
        result = PredictiveCareerAnalyzer.compute_outlook_score(
            role=-50.0, disruption=-10.0, opportunity=-5.0, trend=-30.0,
        )
        assert result == 0.0

    def test_over_100_clamped(self) -> None:
        result = PredictiveCareerAnalyzer.compute_outlook_score(
            role=200.0, disruption=150.0, opportunity=999.0, trend=500.0,
        )
        assert result == 100.0

    def test_result_rounded_to_one_decimal(self) -> None:
        result = PredictiveCareerAnalyzer.compute_outlook_score(
            role=33.3, disruption=33.3, opportunity=33.3, trend=33.3,
        )
        assert result == round(result, 1)


# ── compute_outlook_category ───────────────────────────────────


class TestComputeOutlookCategory:
    def test_score_0_is_critical(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=0.0) == "critical"

    def test_score_20_is_critical(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=20.0) == "critical"

    def test_score_21_is_at_risk(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=21.0) == "at_risk"

    def test_score_40_is_at_risk(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=40.0) == "at_risk"

    def test_score_41_is_moderate(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=41.0) == "moderate"

    def test_score_60_is_moderate(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=60.0) == "moderate"

    def test_score_61_is_favorable(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=61.0) == "favorable"

    def test_score_80_is_favorable(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=80.0) == "favorable"

    def test_score_81_is_exceptional(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=81.0) == "exceptional"

    def test_score_100_is_exceptional(self) -> None:
        assert PredictiveCareerAnalyzer.compute_outlook_category(outlook_score=100.0) == "exceptional"


# ── _clamp_emerging_role ───────────────────────────────────────


class TestClampEmergingRole:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 9.0}
        _clamp_emerging_role(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_confidence_negative_becomes_zero(self) -> None:
        data = {"confidence": -1.0}
        _clamp_emerging_role(data)
        assert data["confidence"] == 0.0

    def test_invalid_confidence_type_becomes_zero(self) -> None:
        data = {"confidence": "high"}
        _clamp_emerging_role(data)
        assert data["confidence"] == 0.0

    def test_invalid_emergence_stage_becomes_nascent(self) -> None:
        data = {"emergence_stage": "unknown"}
        _clamp_emerging_role(data)
        assert data["emergence_stage"] == "nascent"

    def test_valid_emergence_stages_preserved(self) -> None:
        for stage in VALID_EMERGENCE_STAGES:
            data = {"emergence_stage": stage}
            _clamp_emerging_role(data)
            assert data["emergence_stage"] == stage

    def test_skill_overlap_pct_clamped_0_to_100(self) -> None:
        data = {"skill_overlap_pct": 200.0}
        _clamp_emerging_role(data)
        assert data["skill_overlap_pct"] == 100.0

    def test_skill_overlap_non_numeric_becomes_zero(self) -> None:
        data = {"skill_overlap_pct": "high"}
        _clamp_emerging_role(data)
        assert data["skill_overlap_pct"] == 0.0

    def test_negative_time_to_mainstream_becomes_none(self) -> None:
        data = {"time_to_mainstream_months": -5}
        _clamp_emerging_role(data)
        assert data["time_to_mainstream_months"] is None

    def test_positive_time_to_mainstream_preserved(self) -> None:
        data = {"time_to_mainstream_months": 24}
        _clamp_emerging_role(data)
        assert data["time_to_mainstream_months"] == 24

    def test_negative_salary_range_becomes_none(self) -> None:
        data = {"avg_salary_range_min": -1000.0, "avg_salary_range_max": 80000.0}
        _clamp_emerging_role(data)
        assert data["avg_salary_range_min"] is None
        assert data["avg_salary_range_max"] == 80000.0


# ── _clamp_disruption_forecast ─────────────────────────────────


class TestClampDisruptionForecast:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 10.0}
        _clamp_disruption_forecast(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_invalid_disruption_type_becomes_technology(self) -> None:
        data = {"disruption_type": "alien_invasion"}
        _clamp_disruption_forecast(data)
        assert data["disruption_type"] == "technology"

    def test_valid_disruption_types_preserved(self) -> None:
        for dtype in VALID_DISRUPTION_TYPES:
            data = {"disruption_type": dtype}
            _clamp_disruption_forecast(data)
            assert data["disruption_type"] == dtype

    def test_severity_clamped_0_to_100(self) -> None:
        data = {"severity_score": 200.0}
        _clamp_disruption_forecast(data)
        assert data["severity_score"] == 100.0

    def test_severity_non_numeric_becomes_50(self) -> None:
        data = {"severity_score": "extreme"}
        _clamp_disruption_forecast(data)
        assert data["severity_score"] == 50.0

    def test_timeline_months_enforces_minimum_1(self) -> None:
        data = {"timeline_months": 0}
        _clamp_disruption_forecast(data)
        assert data["timeline_months"] == 1

    def test_timeline_non_numeric_becomes_12(self) -> None:
        data = {"timeline_months": "soon"}
        _clamp_disruption_forecast(data)
        assert data["timeline_months"] == 12


# ── _clamp_opportunity_surface ─────────────────────────────────


class TestClampOpportunitySurface:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 9.9}
        _clamp_opportunity_surface(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE

    def test_invalid_opportunity_type_becomes_emerging_role(self) -> None:
        data = {"opportunity_type": "unknown"}
        _clamp_opportunity_surface(data)
        assert data["opportunity_type"] == "emerging_role"

    def test_valid_opportunity_types_preserved(self) -> None:
        for otype in VALID_OPPORTUNITY_TYPES:
            data = {"opportunity_type": otype}
            _clamp_opportunity_surface(data)
            assert data["opportunity_type"] == otype

    def test_relevance_score_clamped_0_to_100(self) -> None:
        data = {"relevance_score": 150.0}
        _clamp_opportunity_surface(data)
        assert data["relevance_score"] == 100.0

    def test_relevance_score_non_numeric_becomes_zero(self) -> None:
        data = {"relevance_score": "very high"}
        _clamp_opportunity_surface(data)
        assert data["relevance_score"] == 0.0


# ── _clamp_career_forecast ─────────────────────────────────────


class TestClampCareerForecast:
    def test_components_clamped_0_to_100(self) -> None:
        data = {
            "role_component": 200.0,
            "disruption_component": -10.0,
            "opportunity_component": 80.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["role_component"] == 100.0
        assert data["disruption_component"] == 0.0

    def test_outlook_score_recomputed_from_components(self) -> None:
        data = {
            "role_component": 80.0,
            "disruption_component": 70.0,
            "opportunity_component": 60.0,
            "trend_component": 50.0,
            "outlook_score": 99.0,  # should be overwritten
        }
        _clamp_career_forecast(data)
        expected = PredictiveCareerAnalyzer.compute_outlook_score(
            role=80.0, disruption=70.0, opportunity=60.0, trend=50.0,
        )
        assert data["outlook_score"] == expected

    def test_outlook_category_set_from_score(self) -> None:
        data = {
            "role_component": 90.0,
            "disruption_component": 90.0,
            "opportunity_component": 90.0,
            "trend_component": 90.0,
        }
        _clamp_career_forecast(data)
        assert data["outlook_category"] == "exceptional"

    def test_forecast_horizon_clamped_3_to_36(self) -> None:
        data = {
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
            "forecast_horizon_months": 100,
        }
        _clamp_career_forecast(data)
        assert data["forecast_horizon_months"] == 36

    def test_forecast_horizon_below_3_becomes_3(self) -> None:
        data = {
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
            "forecast_horizon_months": 1,
        }
        _clamp_career_forecast(data)
        assert data["forecast_horizon_months"] == 3

    def test_non_numeric_component_becomes_50(self) -> None:
        data = {
            "role_component": "high",
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_forecast(data)
        assert data["role_component"] == 50.0

    def test_confidence_capped_at_max(self) -> None:
        data = {
            "role_component": 50.0,
            "disruption_component": 50.0,
            "opportunity_component": 50.0,
            "trend_component": 50.0,
            "confidence": 99.0,
        }
        _clamp_career_forecast(data)
        assert data["confidence"] == MAX_PC_CONFIDENCE


# ── analyze_emerging_roles (LLM) ──────────────────────────────


class TestAnalyzeEmergingRoles:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        roles = [{"emergence_stage": "growing", "confidence": 0.7, "skill_overlap_pct": 75.0}]
        with _patch_sanitize(), _patch_complete_json({"emerging_roles": roles}):
            result = await PredictiveCareerAnalyzer.analyze_emerging_roles(
                industry="Technology",
                region="Europe",
                min_skill_overlap_pct=0.5,
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, FastAPI",
                years_experience=7,
                location="Amsterdam",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dict_response_extracts_roles_key(self) -> None:
        roles = [{"emergence_stage": "nascent", "confidence": 0.6}]
        with _patch_sanitize(), _patch_complete_json({"emerging_roles": roles}):
            result = await PredictiveCareerAnalyzer.analyze_emerging_roles(
                industry="Tech",
                region="Global",
                min_skill_overlap_pct=0.4,
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                skills="Python",
                years_experience=5,
                location="Berlin",
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await PredictiveCareerAnalyzer.analyze_emerging_roles(
                industry="Finance",
                region="EU",
                min_skill_overlap_pct=0.5,
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Finance",
                skills="Python",
                years_experience=5,
                location="London",
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_stage_clamped(self) -> None:
        with _patch_sanitize(), _patch_complete_json({"emerging_roles": [{"emergence_stage": "exploding", "confidence": 0.5}]}):
            result = await PredictiveCareerAnalyzer.analyze_emerging_roles(
                industry="Tech",
                region="EU",
                min_skill_overlap_pct=0.4,
                primary_role="Dev",
                seniority_level="senior",
                primary_industry="Tech",
                skills="Python",
                years_experience=6,
                location="Paris",
            )
        assert result[0]["emergence_stage"] == "nascent"


# ── forecast_disruptions (LLM) ────────────────────────────────


class TestForecastDisruptions:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        disruptions = [{"disruption_type": "automation", "severity_score": 70.0, "confidence": 0.8}]
        with _patch_sanitize(), _patch_complete_json({"disruptions": disruptions}):
            result = await PredictiveCareerAnalyzer.forecast_disruptions(
                industry="Technology",
                forecast_horizon_months=12,
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python",
                years_experience=7,
                location="Amsterdam",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dict_response_extracts_disruptions_key(self) -> None:
        disruptions = [{"disruption_type": "regulation", "severity_score": 50.0}]
        with _patch_sanitize(), _patch_complete_json({"disruptions": disruptions}):
            result = await PredictiveCareerAnalyzer.forecast_disruptions(
                industry="Finance",
                forecast_horizon_months=24,
                primary_role="Analyst",
                seniority_level="mid",
                primary_industry="Finance",
                skills="Python",
                years_experience=5,
                location="London",
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await PredictiveCareerAnalyzer.forecast_disruptions(
                industry="Healthcare",
                forecast_horizon_months=12,
                primary_role="Dev",
                seniority_level="junior",
                primary_industry="Healthcare",
                skills="Python",
                years_experience=2,
                location="Berlin",
            )
        assert result == []


# ── surface_opportunities (LLM) ───────────────────────────────


class TestSurfaceOpportunitiesPredictive:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        opps = [{"opportunity_type": "emerging_role", "relevance_score": 80.0, "confidence": 0.75}]
        with _patch_sanitize(), _patch_complete_json({"opportunities": opps}):
            result = await PredictiveCareerAnalyzer.surface_opportunities(
                industry="Technology",
                region="Europe",
                include_cross_border=False,
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python",
                years_experience=7,
                location="Amsterdam",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_dict_response_extracts_opportunities_key(self) -> None:
        opps = [{"opportunity_type": "skill_demand", "relevance_score": 60.0}]
        with _patch_sanitize(), _patch_complete_json({"opportunities": opps}):
            result = await PredictiveCareerAnalyzer.surface_opportunities(
                industry="Tech",
                region="Global",
                include_cross_border=True,
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                skills="Python",
                years_experience=4,
                location="Berlin",
            )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await PredictiveCareerAnalyzer.surface_opportunities(
                industry="Finance",
                region="EU",
                include_cross_border=False,
                primary_role="Dev",
                seniority_level="junior",
                primary_industry="Finance",
                skills="Python",
                years_experience=2,
                location="London",
            )
        assert result == []


# ── compute_career_forecast (LLM) ─────────────────────────────


class TestComputeCareerForecast:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "role_component": 80.0,
            "disruption_component": 70.0,
            "opportunity_component": 75.0,
            "trend_component": 65.0,
            "confidence": 0.8,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await PredictiveCareerAnalyzer.compute_career_forecast(
                industry="Technology",
                region="Europe",
                forecast_horizon_months=12,
                emerging_roles_count=3,
                disruptions_count=2,
                opportunities_count=5,
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python",
                years_experience=7,
                location="Amsterdam",
            )
        assert isinstance(result, dict)
        assert 0.0 <= result["outlook_score"] <= 100.0

    @pytest.mark.asyncio
    async def test_outlook_category_matches_score(self) -> None:
        response = {
            "role_component": 90.0,
            "disruption_component": 90.0,
            "opportunity_component": 90.0,
            "trend_component": 90.0,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await PredictiveCareerAnalyzer.compute_career_forecast(
                industry="Tech",
                region="EU",
                forecast_horizon_months=24,
                emerging_roles_count=4,
                disruptions_count=1,
                opportunities_count=6,
                primary_role="Dev",
                seniority_level="senior",
                primary_industry="Tech",
                skills="Python",
                years_experience=8,
                location="Berlin",
            )
        assert result["outlook_category"] == "exceptional"

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.predictive_career_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await PredictiveCareerAnalyzer.compute_career_forecast(
                industry="Finance",
                region="Global",
                forecast_horizon_months=12,
                emerging_roles_count=2,
                disruptions_count=3,
                opportunities_count=4,
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Finance",
                skills="Python",
                years_experience=5,
                location="London",
            )
        assert result["confidence"] == 0.0
        assert result["outlook_score"] == 50.0
