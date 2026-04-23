"""
Unit tests for SalaryIntelligenceAnalyzer and its helpers.

Covers: 4 pure static methods, 4 async LLM methods, 3 clamping validators,
and currency fallback rate constants.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm import LLMError

# ── Helpers ───────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str):
    return text[:max_length], {}


# ── compute_market_percentile ─────────────────────────────────────


class TestComputeMarketPercentile:
    def test_at_minimum_gives_zero(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_market_percentile(
            estimated_median=50_000, market_min=50_000, market_max=100_000
        )
        assert result == 0.0

    def test_at_maximum_gives_100(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_market_percentile(
            estimated_median=100_000, market_min=50_000, market_max=100_000
        )
        assert result == 100.0

    def test_midpoint_gives_50(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_market_percentile(
            estimated_median=75_000, market_min=50_000, market_max=100_000
        )
        assert result == 50.0

    def test_equal_min_max_returns_50(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_market_percentile(
            estimated_median=80_000, market_min=80_000, market_max=80_000
        )
        assert result == 50.0

    def test_below_min_clamped_to_zero(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_market_percentile(
            estimated_median=30_000, market_min=50_000, market_max=100_000
        )
        assert result == 0.0

    def test_above_max_clamped_to_100(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_market_percentile(
            estimated_median=120_000, market_min=50_000, market_max=100_000
        )
        assert result == 100.0


# ── compute_confidence_interval ───────────────────────────────────


class TestComputeConfidenceInterval:
    def test_zero_data_points_reduces_confidence(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_confidence_interval(
            data_points_count=0, base_confidence=0.6
        )
        assert result < 0.6

    def test_more_data_points_increases_confidence(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        low = SalaryIntelligenceAnalyzer.compute_confidence_interval(
            data_points_count=1, base_confidence=0.5
        )
        high = SalaryIntelligenceAnalyzer.compute_confidence_interval(
            data_points_count=100, base_confidence=0.5
        )
        assert high > low

    def test_capped_at_085(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_confidence_interval(
            data_points_count=10000, base_confidence=0.99
        )
        assert result == 0.85

    def test_minimum_is_0_1(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_confidence_interval(
            data_points_count=0, base_confidence=0.0
        )
        assert result >= 0.1

    def test_default_base_confidence(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.compute_confidence_interval(
            data_points_count=5
        )
        assert 0.1 <= result <= 0.85


# ── compute_salary_delta ──────────────────────────────────────────


class TestComputeSalaryDelta:
    def test_positive_delta(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
            current_median=60_000, projected_median=72_000
        )
        assert amount == 12_000.0
        assert abs(percent - 20.0) < 0.01

    def test_negative_delta(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
            current_median=60_000, projected_median=54_000
        )
        assert amount == -6_000.0
        assert percent < 0

    def test_zero_current_median_gives_zero_percent(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
            current_median=0, projected_median=50_000
        )
        assert percent == 0.0
        assert amount == 50_000.0

    def test_identical_values_give_zero_delta(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
            current_median=70_000, projected_median=70_000
        )
        assert amount == 0.0
        assert percent == 0.0


# ── normalize_currency ─────────────────────────────────────────────


class TestNormalizeCurrency:
    def test_same_currency_returns_unchanged(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.normalize_currency(
            amount=50_000, from_currency="EUR", to_currency="EUR"
        )
        assert result == 50_000

    def test_eur_to_usd(self) -> None:
        from app.ai.salary_intelligence_analyzer import (
            FALLBACK_RATES_FROM_EUR,
            SalaryIntelligenceAnalyzer,
        )

        result = SalaryIntelligenceAnalyzer.normalize_currency(
            amount=50_000, from_currency="EUR", to_currency="USD"
        )
        expected = round(50_000 * 1.0 * FALLBACK_RATES_FROM_EUR["USD"], 2)
        assert result == expected

    def test_usd_to_eur(self) -> None:
        from app.ai.salary_intelligence_analyzer import (
            FALLBACK_RATES_TO_EUR,
            SalaryIntelligenceAnalyzer,
        )

        result = SalaryIntelligenceAnalyzer.normalize_currency(
            amount=60_000, from_currency="USD", to_currency="EUR"
        )
        expected = round(60_000 * FALLBACK_RATES_TO_EUR["USD"] * 1.0, 2)
        assert result == expected

    def test_unknown_currency_uses_1_0_rate(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        result = SalaryIntelligenceAnalyzer.normalize_currency(
            amount=10_000, from_currency="JPY", to_currency="EUR"
        )
        # JPY not in fallback rates → to_eur_rate = 1.0
        assert result == 10_000.0

    def test_case_insensitive_currency_code(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        upper = SalaryIntelligenceAnalyzer.normalize_currency(
            amount=50_000, from_currency="EUR", to_currency="USD"
        )
        lower = SalaryIntelligenceAnalyzer.normalize_currency(
            amount=50_000, from_currency="eur", to_currency="usd"
        )
        assert upper == lower


# ── analyze_salary_range ──────────────────────────────────────────


class TestAnalyzeSalaryRange:
    @pytest.mark.asyncio
    async def test_happy_path_returns_dict(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "estimated_min": 60_000, "estimated_median": 75_000,
                "estimated_max": 90_000, "confidence": 0.70, "data_points_count": 50,
                "market_percentile": 60.0,
            }
            result = await SalaryIntelligenceAnalyzer.analyze_salary_range(
                role_title="Backend Engineer",
                location="Amsterdam",
                seniority_level="Senior",
                industry="Software",
                years_of_experience=7,
                skills_data="Python, FastAPI",
                experience_summary="7 years backend",
            )

        assert result["estimated_median"] == 75_000
        assert result["confidence"] <= 0.85

    @pytest.mark.asyncio
    async def test_confidence_capped_at_085(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "estimated_min": 60_000, "estimated_median": 75_000,
                "estimated_max": 90_000, "confidence": 0.99,
                "data_points_count": 50, "market_percentile": 60.0,
            }
            result = await SalaryIntelligenceAnalyzer.analyze_salary_range(
                role_title="Dev", location="NL", seniority_level="Senior",
                industry="Tech", years_of_experience=5,
                skills_data="Python", experience_summary="5 years",
            )

        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota exceeded")
            result = await SalaryIntelligenceAnalyzer.analyze_salary_range(
                role_title="Dev", location="NL", seniority_level="Senior",
                industry="Tech", years_of_experience=5,
                skills_data="Python", experience_summary="5 years",
            )

        assert result == {}


# ── analyze_skill_impacts ─────────────────────────────────────────


class TestAnalyzeSkillImpacts:
    @pytest.mark.asyncio
    async def test_happy_path_returns_impacts(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "impacts": [
                    {"skill_name": "Python", "scarcity_factor": 0.8, "demand_premium": 70.0,
                     "impact_direction": "positive"}
                ]
            }
            result = await SalaryIntelligenceAnalyzer.analyze_skill_impacts(
                skills_data="Python",
                role_title="Dev",
                location="NL",
                seniority_level="Senior",
                industry="Tech",
                estimated_median=70_000,
                market_percentile=60.0,
            )

        assert len(result) == 1
        assert result[0]["skill_name"] == "Python"

    @pytest.mark.asyncio
    async def test_scarcity_factor_clamped_above_1(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "impacts": [{"skill_name": "Python", "scarcity_factor": 5.0, "demand_premium": 50.0}]
            }
            result = await SalaryIntelligenceAnalyzer.analyze_skill_impacts(
                skills_data="Python", role_title="Dev", location="NL",
                seniority_level="Senior", industry="Tech",
                estimated_median=70_000, market_percentile=60.0,
            )

        assert result[0]["scarcity_factor"] == 1.0

    @pytest.mark.asyncio
    async def test_demand_premium_clamped_above_100(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "impacts": [{"skill_name": "Python", "scarcity_factor": 0.5, "demand_premium": 200.0}]
            }
            result = await SalaryIntelligenceAnalyzer.analyze_skill_impacts(
                skills_data="Python", role_title="Dev", location="NL",
                seniority_level="Senior", industry="Tech",
                estimated_median=70_000, market_percentile=60.0,
            )

        assert result[0]["demand_premium"] == 100.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await SalaryIntelligenceAnalyzer.analyze_skill_impacts(
                skills_data="Python", role_title="Dev", location="NL",
                seniority_level="Senior", industry="Tech",
                estimated_median=70_000, market_percentile=60.0,
            )

        assert result == []


# ── project_trajectory ────────────────────────────────────────────


class TestProjectTrajectory:
    @pytest.mark.asyncio
    async def test_happy_path_returns_dict(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "trend_direction": "growing",
                "trend_confidence": 0.6,
                "projected_6m_median": 73_000.0,
                "projected_12m_median": 76_000.0,
            }
            result = await SalaryIntelligenceAnalyzer.project_trajectory(
                current_median=70_000,
                market_percentile=55.0,
                confidence=0.65,
                role_title="Dev",
                location="NL",
                seniority_level="Senior",
                industry="Tech",
                skill_momentum_data="Python: +5",
                historical_data="2023: 65k, 2024: 70k",
            )

        assert result["trend_direction"] == "growing"

    @pytest.mark.asyncio
    async def test_6m_projection_capped(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        current = 70_000.0
        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "trend_confidence": 0.5,
                "projected_6m_median": 999_999.0,  # way too high
                "projected_12m_median": 75_000.0,
            }
            result = await SalaryIntelligenceAnalyzer.project_trajectory(
                current_median=current,
                market_percentile=55.0, confidence=0.65,
                role_title="Dev", location="NL", seniority_level="Senior",
                industry="Tech", skill_momentum_data="", historical_data="",
            )

        max_6m = current * 1.075
        assert result["projected_6m_median"] <= max_6m

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota")
            result = await SalaryIntelligenceAnalyzer.project_trajectory(
                current_median=70_000, market_percentile=55.0, confidence=0.65,
                role_title="Dev", location="NL", seniority_level="Senior",
                industry="Tech", skill_momentum_data="", historical_data="",
            )

        assert result == {}


# ── simulate_scenario ─────────────────────────────────────────────


class TestSimulateScenario:
    @pytest.mark.asyncio
    async def test_happy_path_returns_dict(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "projected_min": 75_000.0,
                "projected_median": 85_000.0,
                "projected_max": 95_000.0,
                "confidence": 0.65,
                "delta_percent": 21.4,
            }
            result = await SalaryIntelligenceAnalyzer.simulate_scenario(
                current_median=70_000,
                current_min=60_000,
                current_max=80_000,
                role_title="Dev",
                location="NL",
                current_skills="Python",
                scenario_type="skill_addition",
                scenario_label="Learn Kubernetes",
                scenario_input='{"skill": "kubernetes"}',
            )

        assert result["projected_median"] == 85_000.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

        with patch("app.ai.salary_intelligence_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.salary_intelligence_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await SalaryIntelligenceAnalyzer.simulate_scenario(
                current_median=70_000, current_min=60_000, current_max=80_000,
                role_title="Dev", location="NL", current_skills="Python",
                scenario_type="skill_addition", scenario_label="Learn K8s",
                scenario_input="{}",
            )

        assert result == {}


# ── _clamp_salary_estimate ────────────────────────────────────────


class TestClampSalaryEstimate:
    def test_sorts_min_median_max(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_salary_estimate

        data: dict = {
            "estimated_min": 90_000, "estimated_median": 60_000,
            "estimated_max": 75_000, "confidence": 0.5,
            "data_points_count": 10, "market_percentile": 50.0,
        }
        _clamp_salary_estimate(data)
        assert data["estimated_min"] <= data["estimated_median"] <= data["estimated_max"]

    def test_confidence_capped_at_085(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_salary_estimate

        data: dict = {
            "estimated_min": 60_000, "estimated_median": 75_000,
            "estimated_max": 90_000, "confidence": 0.99,
            "data_points_count": 50, "market_percentile": 60.0,
        }
        _clamp_salary_estimate(data)
        assert data["confidence"] == 0.85

    def test_negative_data_points_corrected(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_salary_estimate

        data: dict = {
            "estimated_min": 60_000, "estimated_median": 75_000,
            "estimated_max": 90_000, "confidence": 0.5,
            "data_points_count": -5, "market_percentile": 50.0,
        }
        _clamp_salary_estimate(data)
        assert data["data_points_count"] == 0

    def test_percentile_clamped_to_100(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_salary_estimate

        data: dict = {
            "estimated_min": 60_000, "estimated_median": 75_000,
            "estimated_max": 90_000, "confidence": 0.5,
            "data_points_count": 10, "market_percentile": 150.0,
        }
        _clamp_salary_estimate(data)
        assert data["market_percentile"] == 100.0


# ── _clamp_trajectory_projection ─────────────────────────────────


class TestClampTrajectoryProjection:
    def test_confidence_capped_at_085(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_trajectory_projection

        data: dict = {"trend_confidence": 0.99, "projected_6m_median": 72_000, "projected_12m_median": 75_000}
        _clamp_trajectory_projection(data, current_median=70_000)
        assert data["trend_confidence"] == 0.85

    def test_6m_capped_at_7_5_percent_growth(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_trajectory_projection

        data: dict = {
            "trend_confidence": 0.5,
            "projected_6m_median": 999_999.0,
            "projected_12m_median": 80_000.0,
        }
        _clamp_trajectory_projection(data, current_median=70_000)
        assert data["projected_6m_median"] <= 70_000 * 1.075

    def test_12m_floored_at_minus_15_percent(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_trajectory_projection

        data: dict = {
            "trend_confidence": 0.5,
            "projected_6m_median": 65_000.0,
            "projected_12m_median": 0.0,  # way too low
        }
        _clamp_trajectory_projection(data, current_median=70_000)
        assert data["projected_12m_median"] >= 70_000 * 0.85


# ── _clamp_scenario_result ────────────────────────────────────────


class TestClampScenarioResult:
    def test_sorts_projected_values(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_scenario_result

        data: dict = {
            "projected_min": 90_000.0,
            "projected_median": 70_000.0,
            "projected_max": 80_000.0,
            "confidence": 0.6,
        }
        _clamp_scenario_result(data)
        assert data["projected_min"] <= data["projected_median"] <= data["projected_max"]

    def test_confidence_capped_at_085(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_scenario_result

        data: dict = {
            "projected_min": 60_000.0,
            "projected_median": 75_000.0,
            "projected_max": 90_000.0,
            "confidence": 0.99,
        }
        _clamp_scenario_result(data)
        assert data["confidence"] == 0.85

    def test_negative_projected_values_floored_at_zero(self) -> None:
        from app.ai.salary_intelligence_analyzer import _clamp_scenario_result

        data: dict = {
            "projected_min": -10_000.0,
            "projected_median": -5_000.0,
            "projected_max": 50_000.0,
            "confidence": 0.5,
        }
        _clamp_scenario_result(data)
        assert data["projected_min"] >= 0.0
        assert data["projected_median"] >= 0.0
