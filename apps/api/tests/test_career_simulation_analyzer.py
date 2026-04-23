"""
Unit tests for CareerSimulationAnalyzer and its helper functions.

Covers: all 4 static helpers, all 4 async LLM methods, and all
3 private clamping validators.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm import LLMError

# ── Helpers ───────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str):
    return text[:max_length], {}


# ── compute_scenario_confidence ────────────────────────────────────


class TestComputeScenarioConfidence:
    def test_perfect_inputs_capped_at_085(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_scenario_confidence(
            skill_overlap_percent=100.0,
            llm_confidence=1.0,
            market_demand_score=100.0,
            data_quality_factor=1.0,
        )
        assert result == 0.85

    def test_zero_inputs_give_zero(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_scenario_confidence(
            skill_overlap_percent=0.0,
            llm_confidence=0.0,
            market_demand_score=0.0,
            data_quality_factor=0.0,
        )
        assert result == 0.0

    def test_default_market_and_quality_defaults(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result_default = CareerSimulationAnalyzer.compute_scenario_confidence(
            skill_overlap_percent=50.0,
            llm_confidence=0.5,
        )
        result_explicit = CareerSimulationAnalyzer.compute_scenario_confidence(
            skill_overlap_percent=50.0,
            llm_confidence=0.5,
            market_demand_score=50.0,
            data_quality_factor=0.5,
        )
        assert result_default == result_explicit

    def test_formula_weights_are_correct(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        # Skill=50%, LLM=0.4, market=60, quality=0.8
        result = CareerSimulationAnalyzer.compute_scenario_confidence(
            skill_overlap_percent=50.0,
            llm_confidence=0.4,
            market_demand_score=60.0,
            data_quality_factor=0.8,
        )
        expected = 0.30 * 0.5 + 0.30 * 0.4 + 0.20 * 0.6 + 0.20 * 0.8
        assert abs(result - round(expected, 3)) < 0.001

    def test_overclamped_inputs_are_normalized(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_scenario_confidence(
            skill_overlap_percent=200.0,  # > 100
            llm_confidence=2.0,           # > 0.85 → capped
            market_demand_score=200.0,    # > 100
            data_quality_factor=2.0,      # > 1.0
        )
        assert result == 0.85


# ── compute_roi_score ─────────────────────────────────────────────


class TestComputeROIScore:
    def test_zero_investment_months_returns_zero(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        assert CareerSimulationAnalyzer.compute_roi_score(
            salary_delta_annual=50000.0,
            investment_months=0,
        ) == 0.0

    def test_no_opportunity_cost_uses_months_denominator(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_roi_score(
            salary_delta_annual=12000.0,
            investment_months=6,
            monthly_opportunity_cost=0.0,
        )
        assert result == round(12000.0 / 6, 2)

    def test_with_opportunity_cost(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_roi_score(
            salary_delta_annual=24000.0,
            investment_months=6,
            monthly_opportunity_cost=2000.0,
        )
        assert result == round((24000.0 / 12000.0) * 100.0, 2)

    def test_negative_salary_delta_gives_negative_roi(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_roi_score(
            salary_delta_annual=-10000.0,
            investment_months=3,
        )
        assert result < 0


# ── compute_feasibility_rating ────────────────────────────────────


class TestComputeFeasibilityRating:
    def test_zero_gaps_gives_high_feasibility(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=0,
            estimated_months=3,
            confidence_score=0.85,
        )
        assert result > 80.0

    def test_two_gaps_gives_moderate_feasibility(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=2,
            estimated_months=6,
            confidence_score=0.5,
        )
        assert 50.0 < result < 100.0

    def test_five_gaps_gives_mid_feasibility(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=5,
            estimated_months=12,
            confidence_score=0.5,
        )
        assert result > 0.0

    def test_ten_gaps_gives_low_feasibility(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=10,
            estimated_months=24,
            confidence_score=0.3,
        )
        assert result < 50.0

    def test_many_gaps_gives_lowest_base(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=20,
            estimated_months=36,
            confidence_score=0.1,
        )
        assert result < 30.0

    def test_short_timeline_higher_than_long(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        short = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=2, estimated_months=2, confidence_score=0.5
        )
        long = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=2, estimated_months=30, confidence_score=0.5
        )
        assert short > long

    def test_six_month_timeline_factor(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=0,
            estimated_months=6,
            confidence_score=0.5,
        )
        assert 0.0 <= result <= 100.0

    def test_twelve_month_timeline_factor(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=0,
            estimated_months=12,
            confidence_score=0.5,
        )
        assert 0.0 <= result <= 100.0

    def test_twenty_four_month_timeline_factor(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=0,
            estimated_months=24,
            confidence_score=0.5,
        )
        assert 0.0 <= result <= 100.0

    def test_result_clamped_to_100(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.compute_feasibility_rating(
            skill_gap_count=0,
            estimated_months=1,
            confidence_score=0.85,
        )
        assert result <= 100.0


# ── normalize_salary_delta ─────────────────────────────────────────


class TestNormalizeSalaryDelta:
    def test_equal_col_indexes_no_change(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.normalize_salary_delta(
            salary_delta=10000.0,
            source_col_index=100.0,
            target_col_index=100.0,
        )
        assert result == 10000.0

    def test_higher_target_col_reduces_effective_delta(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.normalize_salary_delta(
            salary_delta=10000.0,
            source_col_index=100.0,
            target_col_index=150.0,
        )
        assert result < 10000.0

    def test_lower_target_col_increases_effective_delta(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.normalize_salary_delta(
            salary_delta=10000.0,
            source_col_index=150.0,
            target_col_index=100.0,
        )
        assert result > 10000.0

    def test_zero_source_col_returns_delta_unchanged(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.normalize_salary_delta(
            salary_delta=5000.0,
            source_col_index=0.0,
            target_col_index=100.0,
        )
        assert result == 5000.0

    def test_negative_col_index_returns_delta_unchanged(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        result = CareerSimulationAnalyzer.normalize_salary_delta(
            salary_delta=5000.0,
            source_col_index=-10.0,
            target_col_index=100.0,
        )
        assert result == 5000.0


# ── analyze_scenario ──────────────────────────────────────────────


class TestAnalyzeScenario:
    @pytest.mark.asyncio
    async def test_happy_path_returns_dict(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        llm_data = {
            "confidence_score": 0.7,
            "feasibility_rating": 75.0,
            "estimated_months": 6,
            "salary_impact_percent": 20.0,
            "factors": {"key_factor": "strong skill overlap"},
        }
        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_data
            result = await CareerSimulationAnalyzer.analyze_scenario(
                scenario_type="role_transition",
                current_role="Backend Engineer",
                current_seniority="Mid",
                current_industry="Software",
                current_location="Amsterdam",
                skills="Python, FastAPI",
                years_experience=5,
                scenario_parameters="Target: Staff Engineer",
            )

        assert result["confidence_score"] <= 0.85
        assert "feasibility_rating" in result

    @pytest.mark.asyncio
    async def test_confidence_clamped_by_clamp_helper(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"confidence_score": 0.99, "feasibility_rating": 50.0,
                                     "estimated_months": 6, "salary_impact_percent": 10.0}
            result = await CareerSimulationAnalyzer.analyze_scenario(
                scenario_type="role_transition",
                current_role="Dev", current_seniority="Mid",
                current_industry="Tech", current_location="NL",
                skills="Python", years_experience=5,
                scenario_parameters="Target: Staff",
            )

        assert result["confidence_score"] == 0.85

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await CareerSimulationAnalyzer.analyze_scenario(
                scenario_type="role_transition",
                current_role="Dev", current_seniority="Mid",
                current_industry="Tech", current_location="NL",
                skills="Python", years_experience=5,
                scenario_parameters="Target: Staff",
            )

        assert result == {}


# ── project_outcomes ──────────────────────────────────────────────


class TestProjectOutcomes:
    @pytest.mark.asyncio
    async def test_happy_path_dict_with_outcomes_key(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "outcomes": [
                    {"dimension": "salary", "current_value": 70000.0, "projected_value": 90000.0, "delta": 20000.0}
                ]
            }
            result = await CareerSimulationAnalyzer.project_outcomes(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Strong overlap",
            )

        assert len(result) == 1
        assert result[0]["dimension"] == "salary"

    @pytest.mark.asyncio
    async def test_list_response_handled_directly(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        outcomes = [
            {"dimension": "demand", "current_value": 70.0, "projected_value": 90.0, "delta": 20.0}
        ]
        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = outcomes  # LLM returns list directly
            result = await CareerSimulationAnalyzer.project_outcomes(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Good fit",
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delta_recalculated(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "outcomes": [
                    {"dimension": "salary", "current_value": 70000.0, "projected_value": 90000.0, "delta": 999.0}
                ]
            }
            result = await CareerSimulationAnalyzer.project_outcomes(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Good fit",
            )

        assert result[0]["delta"] == 20000.0  # recalculated

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota")
            result = await CareerSimulationAnalyzer.project_outcomes(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Good fit",
            )

        assert result == []


# ── generate_recommendations ──────────────────────────────────────


class TestGenerateRecommendations:
    @pytest.mark.asyncio
    async def test_happy_path_dict_with_recommendations_key(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "recommendations": [
                    {"title": "Get Kubernetes cert", "priority": "high", "estimated_weeks": 8}
                ]
            }
            result = await CareerSimulationAnalyzer.generate_recommendations(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Good fit",
                outcomes_summary="Salary +20%",
            )

        assert len(result) == 1
        assert result[0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_list_response_handled_directly(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        recs = [{"title": "Learn K8s", "priority": "critical", "estimated_weeks": 12}]
        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = recs
            result = await CareerSimulationAnalyzer.generate_recommendations(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Good fit",
                outcomes_summary="Salary +20%",
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota")
            result = await CareerSimulationAnalyzer.generate_recommendations(
                scenario_type="role_transition",
                current_role="Dev",
                scenario_parameters="Target: Staff",
                confidence_score=0.7,
                reasoning="Good fit",
                outcomes_summary="Salary +20%",
            )

        assert result == []


# ── compare_scenarios ─────────────────────────────────────────────


class TestCompareScenarios:
    @pytest.mark.asyncio
    async def test_happy_path_returns_dict(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"ranked_scenario_ids": ["s1", "s2"], "analysis": "s1 wins"}
            result = await CareerSimulationAnalyzer.compare_scenarios(
                current_role="Dev",
                current_seniority="Mid",
                current_industry="Tech",
                scenarios_json='[{"id": "s1"}, {"id": "s2"}]',
            )

        assert "ranked_scenario_ids" in result

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

        with patch("app.ai.career_simulation_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.career_simulation_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await CareerSimulationAnalyzer.compare_scenarios(
                current_role="Dev",
                current_seniority="Mid",
                current_industry="Tech",
                scenarios_json="[]",
            )

        assert result == {}


# ── _clamp_simulation_analysis ────────────────────────────────────


class TestClampSimulationAnalysis:
    def test_confidence_capped_at_085(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"confidence_score": 0.99}
        _clamp_simulation_analysis(data)
        assert data["confidence_score"] == 0.85

    def test_feasibility_capped_at_100(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"feasibility_rating": 150.0}
        _clamp_simulation_analysis(data)
        assert data["feasibility_rating"] == 100.0

    def test_months_clamped_to_max_120(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"estimated_months": 200}
        _clamp_simulation_analysis(data)
        assert data["estimated_months"] == 120

    def test_months_clamped_to_min_1(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"estimated_months": 0}
        _clamp_simulation_analysis(data)
        assert data["estimated_months"] == 1

    def test_salary_impact_clamped_max_200(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"salary_impact_percent": 999.0}
        _clamp_simulation_analysis(data)
        assert data["salary_impact_percent"] == 200.0

    def test_salary_impact_clamped_min_minus_100(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"salary_impact_percent": -999.0}
        _clamp_simulation_analysis(data)
        assert data["salary_impact_percent"] == -100.0

    def test_non_dict_factors_replaced_with_empty_dict(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"factors": "not a dict"}
        _clamp_simulation_analysis(data)
        assert data["factors"] == {}

    def test_dict_factors_preserved(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

        data: dict = {"factors": {"key": "value"}}
        _clamp_simulation_analysis(data)
        assert data["factors"] == {"key": "value"}


# ── _clamp_outcomes ───────────────────────────────────────────────


class TestClampOutcomes:
    def test_delta_recalculated_from_values(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_outcomes

        outcomes = [{"dimension": "salary", "current_value": 60000.0, "projected_value": 80000.0, "delta": 0.0}]
        _clamp_outcomes(outcomes)
        assert outcomes[0]["delta"] == 20000.0

    def test_empty_dimension_replaced_with_unknown(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_outcomes

        outcomes = [{"dimension": "", "current_value": 50.0, "projected_value": 70.0}]
        _clamp_outcomes(outcomes)
        assert outcomes[0]["dimension"] == "unknown"

    def test_string_numeric_fields_converted(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_outcomes

        outcomes = [{"dimension": "demand", "current_value": "60", "projected_value": "80", "delta": "20"}]
        _clamp_outcomes(outcomes)
        assert outcomes[0]["current_value"] == 60.0

    def test_invalid_numeric_field_defaults_to_zero(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_outcomes

        outcomes = [{"dimension": "demand", "current_value": "invalid", "projected_value": 80.0}]
        _clamp_outcomes(outcomes)
        assert outcomes[0]["current_value"] == 0.0


# ── _clamp_recommendations ────────────────────────────────────────


class TestClampRecommendations:
    def test_invalid_priority_replaced_with_medium(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_recommendations

        recs = [{"priority": "URGENT", "title": "Do something"}]
        _clamp_recommendations(recs)
        assert recs[0]["priority"] == "medium"

    def test_valid_priorities_preserved(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_recommendations

        for priority in ("critical", "high", "medium", "nice_to_have"):
            recs = [{"priority": priority, "title": "Test"}]
            _clamp_recommendations(recs)
            assert recs[0]["priority"] == priority

    def test_empty_title_replaced_with_default(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_recommendations

        recs = [{"priority": "high", "title": ""}]
        _clamp_recommendations(recs)
        assert recs[0]["title"] == "Untitled recommendation"

    def test_weeks_clamped_above_max(self) -> None:
        from app.ai.career_simulation_analyzer import (
            MAX_RECOMMENDATION_WEEKS,
            _clamp_recommendations,
        )

        recs = [{"priority": "high", "title": "Test", "estimated_weeks": 9999}]
        _clamp_recommendations(recs)
        assert recs[0]["estimated_weeks"] == MAX_RECOMMENDATION_WEEKS

    def test_weeks_clamped_below_1(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_recommendations

        recs = [{"priority": "high", "title": "Test", "estimated_weeks": 0}]
        _clamp_recommendations(recs)
        assert recs[0]["estimated_weeks"] == 1

    def test_order_index_defaults_to_position(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_recommendations

        recs = [
            {"priority": "high", "title": "A"},
            {"priority": "high", "title": "B"},
        ]
        _clamp_recommendations(recs)
        assert recs[0]["order_index"] == 0
        assert recs[1]["order_index"] == 1

    def test_existing_order_index_preserved(self) -> None:
        from app.ai.career_simulation_analyzer import _clamp_recommendations

        recs = [{"priority": "high", "title": "A", "order_index": 5}]
        _clamp_recommendations(recs)
        assert recs[0]["order_index"] == 5
