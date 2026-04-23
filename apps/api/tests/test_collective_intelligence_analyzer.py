"""
Unit tests for CollectiveIntelligenceAnalyzer.

Covers:
  - 3 static helpers (compute_pulse_score, compute_pulse_category,
    compute_demand_intensity)
  - 4 async LLM methods (analyze_industry_snapshot, analyze_salary_benchmark,
    analyze_peer_cohort, analyze_career_pulse)
  - 4 private clamping validators (_clamp_industry_snapshot,
    _clamp_salary_benchmark, _clamp_peer_cohort, _clamp_career_pulse)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.collective_intelligence_analyzer import (
    MAX_CI_CONFIDENCE,
    MIN_COHORT_SIZE,
    VALID_DEMAND_INTENSITIES,
    VALID_TREND_DIRECTIONS,
    CollectiveIntelligenceAnalyzer,
    _clamp_career_pulse,
    _clamp_industry_snapshot,
    _clamp_peer_cohort,
    _clamp_salary_benchmark,
)

# ── Helpers ────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str) -> tuple[str, dict]:
    return text[:max_length], {}


def _patch_sanitize():
    return patch(
        "app.ai.collective_intelligence_analyzer.sanitize_user_text",
        side_effect=_sanitize_passthrough,
    )


def _patch_complete_json(return_value):
    return patch(
        "app.ai.collective_intelligence_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── compute_pulse_score ────────────────────────────────────────


class TestComputePulseScore:
    def test_basic_weighted_formula(self) -> None:
        # 0.30*80 + 0.25*70 + 0.25*60 + 0.20*50 = 24 + 17.5 + 15 + 10 = 66.5
        result = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=80.0, salary=70.0, skill_relevance=60.0, trend=50.0,
        )
        assert abs(result - 66.5) < 0.01

    def test_all_100_returns_100(self) -> None:
        result = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=100.0, salary=100.0, skill_relevance=100.0, trend=100.0,
        )
        assert result == 100.0

    def test_all_zero_returns_zero(self) -> None:
        result = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=0.0, salary=0.0, skill_relevance=0.0, trend=0.0,
        )
        assert result == 0.0

    def test_negative_inputs_clamped_to_zero(self) -> None:
        result = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=-50.0, salary=-10.0, skill_relevance=-5.0, trend=-30.0,
        )
        assert result == 0.0

    def test_over_100_inputs_clamped(self) -> None:
        result = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=200.0, salary=150.0, skill_relevance=999.0, trend=500.0,
        )
        assert result == 100.0

    def test_result_rounded_to_one_decimal(self) -> None:
        result = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=33.3, salary=33.3, skill_relevance=33.3, trend=33.3,
        )
        assert result == round(result, 1)


# ── compute_pulse_category ─────────────────────────────────────


class TestComputePulseCategory:
    def test_score_0_is_critical(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=0.0) == "critical"

    def test_score_20_is_critical(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=20.0) == "critical"

    def test_score_21_is_low(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=21.0) == "low"

    def test_score_40_is_low(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=40.0) == "low"

    def test_score_41_is_moderate(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=41.0) == "moderate"

    def test_score_60_is_moderate(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=60.0) == "moderate"

    def test_score_61_is_healthy(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=61.0) == "healthy"

    def test_score_80_is_healthy(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=80.0) == "healthy"

    def test_score_81_is_thriving(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=81.0) == "thriving"

    def test_score_100_is_thriving(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=100.0) == "thriving"


# ── compute_demand_intensity ───────────────────────────────────


class TestComputeDemandIntensity:
    def test_score_0_is_low(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=0.0) == "low"

    def test_score_20_is_low(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=20.0) == "low"

    def test_score_21_is_moderate(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=21.0) == "moderate"

    def test_score_40_is_moderate(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=40.0) == "moderate"

    def test_score_41_is_high(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=41.0) == "high"

    def test_score_60_is_high(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=60.0) == "high"

    def test_score_61_is_very_high(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=61.0) == "very_high"

    def test_score_80_is_very_high(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=80.0) == "very_high"

    def test_score_81_is_critical(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=81.0) == "critical"

    def test_score_100_is_critical(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=100.0) == "critical"


# ── _clamp_industry_snapshot ───────────────────────────────────


class TestClampIndustrySnapshot:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 9.0}
        _clamp_industry_snapshot(data)
        assert data["confidence"] == MAX_CI_CONFIDENCE

    def test_confidence_negative_becomes_zero(self) -> None:
        data = {"confidence": -1.0}
        _clamp_industry_snapshot(data)
        assert data["confidence"] == 0.0

    def test_invalid_confidence_type_becomes_zero(self) -> None:
        data = {"confidence": "high"}
        _clamp_industry_snapshot(data)
        assert data["confidence"] == 0.0

    def test_invalid_trend_direction_becomes_stable(self) -> None:
        data = {"trend_direction": "unknown"}
        _clamp_industry_snapshot(data)
        assert data["trend_direction"] == "stable"

    def test_valid_trend_directions_preserved(self) -> None:
        for trend in VALID_TREND_DIRECTIONS:
            data = {"trend_direction": trend}
            _clamp_industry_snapshot(data)
            assert data["trend_direction"] == trend

    def test_invalid_demand_intensity_becomes_moderate(self) -> None:
        data = {"demand_intensity": "extreme"}
        _clamp_industry_snapshot(data)
        assert data["demand_intensity"] == "moderate"

    def test_valid_demand_intensities_preserved(self) -> None:
        for level in VALID_DEMAND_INTENSITIES:
            data = {"demand_intensity": level}
            _clamp_industry_snapshot(data)
            assert data["demand_intensity"] == level

    def test_negative_salary_range_becomes_none(self) -> None:
        data = {"avg_salary_range_min": -5000.0}
        _clamp_industry_snapshot(data)
        assert data["avg_salary_range_min"] is None

    def test_positive_salary_range_preserved(self) -> None:
        data = {"avg_salary_range_max": 90000.0}
        _clamp_industry_snapshot(data)
        assert data["avg_salary_range_max"] == 90000.0

    def test_non_numeric_growth_becomes_none(self) -> None:
        data = {"growth_rate_pct": "fast"}
        _clamp_industry_snapshot(data)
        assert data["growth_rate_pct"] is None

    def test_numeric_growth_preserved(self) -> None:
        data = {"growth_rate_pct": 12.5}
        _clamp_industry_snapshot(data)
        assert data["growth_rate_pct"] == 12.5


# ── _clamp_salary_benchmark ────────────────────────────────────


class TestClampSalaryBenchmark:
    def test_benchmark_min_negative_becomes_zero(self) -> None:
        data = {"benchmark_min": -1000.0}
        _clamp_salary_benchmark(data)
        assert data["benchmark_min"] == 0.0

    def test_benchmark_fields_non_numeric_become_zero(self) -> None:
        data = {"benchmark_min": "low", "benchmark_median": None}
        _clamp_salary_benchmark(data)
        assert data["benchmark_min"] == 0.0
        assert data["benchmark_median"] == 0.0

    def test_user_percentile_clamped_0_to_100(self) -> None:
        data = {"user_percentile": 150.0}
        _clamp_salary_benchmark(data)
        assert data["user_percentile"] == 100.0

    def test_user_percentile_non_numeric_becomes_none(self) -> None:
        data = {"user_percentile": "top"}
        _clamp_salary_benchmark(data)
        assert data["user_percentile"] is None

    def test_experience_factor_clamped_0_to_2(self) -> None:
        data = {"experience_factor": 5.0}
        _clamp_salary_benchmark(data)
        assert data["experience_factor"] == 2.0

    def test_experience_factor_non_numeric_becomes_none(self) -> None:
        data = {"experience_factor": "high"}
        _clamp_salary_benchmark(data)
        assert data["experience_factor"] is None

    def test_skill_premium_numeric_preserved(self) -> None:
        data = {"skill_premium_pct": 15.5}
        _clamp_salary_benchmark(data)
        assert data["skill_premium_pct"] == 15.5

    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 10.0}
        _clamp_salary_benchmark(data)
        assert data["confidence"] == MAX_CI_CONFIDENCE


# ── _clamp_peer_cohort ─────────────────────────────────────────


class TestClampPeerCohort:
    def test_cohort_size_below_min_becomes_min(self) -> None:
        data = {"cohort_size": 2}
        _clamp_peer_cohort(data)
        assert data["cohort_size"] == MIN_COHORT_SIZE

    def test_cohort_size_non_numeric_becomes_min(self) -> None:
        data = {"cohort_size": "many"}
        _clamp_peer_cohort(data)
        assert data["cohort_size"] == MIN_COHORT_SIZE

    def test_user_rank_percentile_clamped_0_to_100(self) -> None:
        data = {"user_rank_percentile": 120.0}
        _clamp_peer_cohort(data)
        assert data["user_rank_percentile"] == 100.0

    def test_user_rank_percentile_non_numeric_becomes_50(self) -> None:
        data = {"user_rank_percentile": "top"}
        _clamp_peer_cohort(data)
        assert data["user_rank_percentile"] == 50.0

    def test_avg_skills_count_non_numeric_becomes_zero(self) -> None:
        data = {"avg_skills_count": "many"}
        _clamp_peer_cohort(data)
        assert data["avg_skills_count"] == 0.0

    def test_avg_experience_years_non_numeric_becomes_zero(self) -> None:
        data = {"avg_experience_years": "lots"}
        _clamp_peer_cohort(data)
        assert data["avg_experience_years"] == 0.0

    def test_negative_avg_skills_becomes_zero(self) -> None:
        data = {"avg_skills_count": -5.0}
        _clamp_peer_cohort(data)
        assert data["avg_skills_count"] == 0.0

    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 100.0}
        _clamp_peer_cohort(data)
        assert data["confidence"] == MAX_CI_CONFIDENCE


# ── _clamp_career_pulse ────────────────────────────────────────


class TestClampCareerPulse:
    def test_components_clamped_to_0_100(self) -> None:
        data = {
            "demand_component": 200.0,
            "salary_component": -50.0,
            "skill_relevance_component": 100.0,
            "trend_component": 50.0,
        }
        _clamp_career_pulse(data)
        assert data["demand_component"] == 100.0
        assert data["salary_component"] == 0.0

    def test_pulse_score_recomputed_from_components(self) -> None:
        data = {
            "demand_component": 80.0,
            "salary_component": 70.0,
            "skill_relevance_component": 60.0,
            "trend_component": 50.0,
            "pulse_score": 99.0,  # should be overwritten
        }
        _clamp_career_pulse(data)
        expected = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=80.0, salary=70.0, skill_relevance=60.0, trend=50.0,
        )
        assert data["pulse_score"] == expected

    def test_pulse_category_set_from_score(self) -> None:
        data = {
            "demand_component": 90.0,
            "salary_component": 90.0,
            "skill_relevance_component": 90.0,
            "trend_component": 90.0,
        }
        _clamp_career_pulse(data)
        assert data["pulse_category"] == "thriving"

    def test_invalid_trend_direction_becomes_stable(self) -> None:
        data = {
            "demand_component": 50.0,
            "salary_component": 50.0,
            "skill_relevance_component": 50.0,
            "trend_component": 50.0,
            "trend_direction": "chaotic",
        }
        _clamp_career_pulse(data)
        assert data["trend_direction"] == "stable"

    def test_valid_trend_direction_preserved(self) -> None:
        for trend in VALID_TREND_DIRECTIONS:
            data = {
                "demand_component": 50.0,
                "salary_component": 50.0,
                "skill_relevance_component": 50.0,
                "trend_component": 50.0,
                "trend_direction": trend,
            }
            _clamp_career_pulse(data)
            assert data["trend_direction"] == trend

    def test_confidence_capped_at_max(self) -> None:
        data = {
            "demand_component": 50.0,
            "salary_component": 50.0,
            "skill_relevance_component": 50.0,
            "trend_component": 50.0,
            "confidence": 99.0,
        }
        _clamp_career_pulse(data)
        assert data["confidence"] == MAX_CI_CONFIDENCE

    def test_non_numeric_components_become_50(self) -> None:
        data = {
            "demand_component": "high",
            "salary_component": 50.0,
            "skill_relevance_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_pulse(data)
        assert data["demand_component"] == 50.0


# ── analyze_industry_snapshot (LLM) ───────────────────────────


class TestAnalyzeIndustrySnapshot:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "trend_direction": "rising",
            "demand_intensity": "high",
            "confidence": 0.75,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_industry_snapshot(
                industry="Technology",
                region="Europe",
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python",
                years_experience=7,
            )
        assert isinstance(result, dict)
        assert result["trend_direction"] == "rising"

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.collective_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_industry_snapshot(
                industry="Finance",
                region="Global",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Finance",
                skills="Python",
                years_experience=5,
            )
        assert result["confidence"] == 0.0
        assert result["trend_direction"] == "stable"

    @pytest.mark.asyncio
    async def test_invalid_trend_clamped(self) -> None:
        response = {"trend_direction": "exploding"}
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_industry_snapshot(
                industry="Tech",
                region="Europe",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                skills="Python",
                years_experience=4,
            )
        assert result["trend_direction"] == "stable"


# ── analyze_salary_benchmark (LLM) ────────────────────────────


class TestAnalyzeSalaryBenchmark:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "benchmark_min": 70000.0,
            "benchmark_median": 85000.0,
            "benchmark_max": 100000.0,
            "confidence": 0.8,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_salary_benchmark(
                role="Senior Engineer",
                location="Amsterdam",
                experience_years=7,
                currency="EUR",
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, Kubernetes",
            )
        assert isinstance(result, dict)
        assert result["benchmark_median"] == 85000.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.collective_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_salary_benchmark(
                role="Dev",
                location="Berlin",
                experience_years=5,
                currency="EUR",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                skills="Python",
            )
        assert result["confidence"] == 0.0
        assert result["benchmark_median"] == 0.0


# ── analyze_peer_cohort (LLM) ──────────────────────────────────


class TestAnalyzePeerCohort:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "cohort_size": 500,
            "user_rank_percentile": 75.0,
            "avg_skills_count": 12.5,
            "confidence": 0.7,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_peer_cohort(
                role="Engineer",
                experience_min=5,
                experience_max=10,
                region="Europe",
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                user_skills_count=15,
                skills="Python, FastAPI",
                years_experience=7,
            )
        assert isinstance(result, dict)
        assert result["cohort_size"] == 500

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.collective_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_peer_cohort(
                role="Dev",
                experience_min=2,
                experience_max=5,
                region="Global",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                user_skills_count=8,
                skills="Python",
                years_experience=4,
            )
        assert result["cohort_size"] == MIN_COHORT_SIZE
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_cohort_size_enforces_minimum(self) -> None:
        response = {"cohort_size": 2, "user_rank_percentile": 50.0}
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_peer_cohort(
                role="Dev",
                experience_min=0,
                experience_max=2,
                region="Global",
                primary_role="Dev",
                seniority_level="junior",
                primary_industry="Tech",
                user_skills_count=5,
                skills="Python",
                years_experience=1,
            )
        assert result["cohort_size"] == MIN_COHORT_SIZE


# ── analyze_career_pulse (LLM) ────────────────────────────────


class TestAnalyzeCareerPulse:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "demand_component": 80.0,
            "salary_component": 70.0,
            "skill_relevance_component": 75.0,
            "trend_component": 65.0,
            "trend_direction": "rising",
            "confidence": 0.8,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_career_pulse(
                industry="Technology",
                region="Europe",
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python",
                years_experience=7,
                location="Amsterdam",
            )
        assert isinstance(result, dict)
        assert 0.0 <= result["pulse_score"] <= 100.0

    @pytest.mark.asyncio
    async def test_pulse_category_matches_computed_score(self) -> None:
        response = {
            "demand_component": 90.0,
            "salary_component": 90.0,
            "skill_relevance_component": 90.0,
            "trend_component": 90.0,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CollectiveIntelligenceAnalyzer.analyze_career_pulse(
                industry="Tech",
                region="Europe",
                primary_role="Dev",
                seniority_level="senior",
                primary_industry="Tech",
                skills="Python",
                years_experience=8,
                location="Berlin",
            )
        assert result["pulse_category"] == "thriving"

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.collective_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_career_pulse(
                industry="Finance",
                region="Global",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Finance",
                skills="Python",
                years_experience=5,
                location="London",
            )
        assert result["pulse_score"] == 50.0
        assert result["confidence"] == 0.0
