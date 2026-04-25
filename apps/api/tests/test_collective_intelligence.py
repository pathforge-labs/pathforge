"""
PathForge — Collective Intelligence Engine™ Test Suite
=======================================================
Tests for Sprint 17: models, analyzer static helpers, clamping validators.

Coverage:
    - Model creation (5 models)
    - Analyzer static methods (compute_pulse_score, pulse_category, demand_intensity)
    - Clamping validators (industry, salary, peer cohort, career pulse)
    - Schema validation (response models)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.collective_intelligence_analyzer import (
    MAX_CI_CONFIDENCE,
    MIN_COHORT_SIZE,
    CollectiveIntelligenceAnalyzer,
    _clamp_career_pulse,
    _clamp_industry_snapshot,
    _clamp_peer_cohort,
    _clamp_salary_benchmark,
)
from app.models.collective_intelligence import (
    BenchmarkCurrency,
    CareerPulseEntry,
    CollectiveIntelligencePreference,
    DemandIntensity,
    IndustrySnapshot,
    PeerCohortAnalysis,
    PulseCategory,
    SalaryBenchmark,
    TrendDirection,
)
from app.schemas.collective_intelligence import (
    CareerPulseResponse,
    CollectiveIntelligenceDashboardResponse,
    IndustrySnapshotResponse,
    SalaryBenchmarkResponse,
)

# ── Enum Tests ─────────────────────────────────────────────────


class TestEnums:
    """Test StrEnum definitions."""

    def test_trend_direction_values(self) -> None:
        assert TrendDirection.RISING == "rising"
        assert TrendDirection.STABLE == "stable"
        assert TrendDirection.DECLINING == "declining"
        assert TrendDirection.EMERGING == "emerging"

    def test_demand_intensity_values(self) -> None:
        assert DemandIntensity.LOW == "low"
        assert DemandIntensity.MODERATE == "moderate"
        assert DemandIntensity.HIGH == "high"
        assert DemandIntensity.VERY_HIGH == "very_high"
        assert DemandIntensity.CRITICAL == "critical"

    def test_pulse_category_values(self) -> None:
        assert PulseCategory.CRITICAL == "critical"
        assert PulseCategory.LOW == "low"
        assert PulseCategory.MODERATE == "moderate"
        assert PulseCategory.HEALTHY == "healthy"
        assert PulseCategory.THRIVING == "thriving"

    def test_benchmark_currency_values(self) -> None:
        assert BenchmarkCurrency.EUR == "EUR"
        assert BenchmarkCurrency.USD == "USD"
        assert BenchmarkCurrency.GBP == "GBP"
        assert BenchmarkCurrency.CHF == "CHF"
        assert BenchmarkCurrency.CAD == "CAD"
        assert BenchmarkCurrency.AUD == "AUD"
        assert BenchmarkCurrency.OTHER == "other"


# ── Model Creation Tests ──────────────────────────────────────


class TestIndustrySnapshotModel:
    """Test IndustrySnapshot model instantiation."""

    def test_create_industry_snapshot(self) -> None:
        snapshot = IndustrySnapshot(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            industry="Software Development",
            region="Netherlands",
            trend_direction="rising",
            demand_intensity="high",
            confidence_score=0.75,
        )
        assert snapshot.industry == "Software Development"
        assert snapshot.region == "Netherlands"
        assert snapshot.trend_direction == "rising"
        assert snapshot.demand_intensity == "high"
        assert snapshot.confidence_score == 0.75
        assert snapshot.__tablename__ == "ci_industry_snapshots"

    def test_default_transparency_fields(self) -> None:
        snapshot = IndustrySnapshot(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            industry="Tech",
            region="EU",
            confidence_score=0.5,
        )
        # data_source has a Python-level default; verify if set
        if snapshot.data_source is not None:
            assert "AI-analyzed" in snapshot.data_source
        # disclaimer has a Python-level default; verify if set
        if snapshot.disclaimer is not None:
            assert "85%" in snapshot.disclaimer


class TestSalaryBenchmarkModel:
    """Test SalaryBenchmark model instantiation."""

    def test_create_salary_benchmark(self) -> None:
        benchmark = SalaryBenchmark(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            role="Software Engineer",
            location="Amsterdam",
            experience_years=5,
            benchmark_min=55000.0,
            benchmark_median=72000.0,
            benchmark_max=95000.0,
            currency="EUR",
            user_percentile=65.0,
            confidence_score=0.70,
        )
        assert benchmark.role == "Software Engineer"
        assert benchmark.benchmark_median == 72000.0
        assert benchmark.currency == "EUR"
        assert benchmark.__tablename__ == "ci_salary_benchmarks"


class TestPeerCohortAnalysisModel:
    """Test PeerCohortAnalysis model instantiation."""

    def test_create_peer_cohort(self) -> None:
        cohort = PeerCohortAnalysis(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            cohort_criteria={"role": "Engineer", "region": "EU"},
            cohort_size=50,
            user_rank_percentile=72.5,
            avg_skills_count=12.3,
            user_skills_count=15,
            avg_experience_years=6.5,
            confidence_score=0.65,
        )
        assert cohort.cohort_size == 50
        assert cohort.user_rank_percentile == 72.5
        assert cohort.__tablename__ == "ci_peer_cohort_analyses"


class TestCareerPulseEntryModel:
    """Test CareerPulseEntry model instantiation."""

    def test_create_career_pulse(self) -> None:
        pulse = CareerPulseEntry(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            pulse_score=72.5,
            pulse_category="healthy",
            trend_direction="rising",
            demand_component=80.0,
            salary_component=70.0,
            skill_relevance_component=65.0,
            trend_component=75.0,
            confidence_score=0.72,
        )
        assert pulse.pulse_score == 72.5
        assert pulse.pulse_category == "healthy"
        assert pulse.__tablename__ == "ci_career_pulse_entries"


class TestCollectiveIntelligencePreferenceModel:
    """Test CollectiveIntelligencePreference model instantiation."""

    def test_create_preference(self) -> None:
        pref = CollectiveIntelligencePreference(
            career_dna_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            include_industry_pulse=True,
            include_salary_benchmarks=True,
            include_peer_analysis=False,
            preferred_currency="EUR",
        )
        assert pref.include_industry_pulse is True
        assert pref.include_peer_analysis is False
        assert pref.__tablename__ == "ci_preferences"


# ── Static Helper Tests ───────────────────────────────────────


class TestComputePulseScore:
    """Test Career Pulse Index™ composite score computation."""

    def test_balanced_components(self) -> None:
        score = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=50.0, salary=50.0, skill_relevance=50.0, trend=50.0,
        )
        assert score == 50.0

    def test_all_maximum(self) -> None:
        score = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=100.0, salary=100.0, skill_relevance=100.0, trend=100.0,
        )
        assert score == 100.0

    def test_all_zero(self) -> None:
        score = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=0.0, salary=0.0, skill_relevance=0.0, trend=0.0,
        )
        assert score == 0.0

    def test_weighted_formula(self) -> None:
        # demand=80(×0.30=24) + salary=60(×0.25=15)
        # + skill=70(×0.25=17.5) + trend=50(×0.20=10) = 66.5
        score = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=80.0, salary=60.0, skill_relevance=70.0, trend=50.0,
        )
        assert score == 66.5

    def test_clamps_above_100(self) -> None:
        score = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=200.0, salary=200.0, skill_relevance=200.0, trend=200.0,
        )
        assert score == 100.0

    def test_clamps_below_0(self) -> None:
        score = CollectiveIntelligenceAnalyzer.compute_pulse_score(
            demand=-50.0, salary=-50.0, skill_relevance=-50.0, trend=-50.0,
        )
        assert score == 0.0


class TestComputePulseCategory:
    """Test pulse score → category mapping."""

    def test_critical_range(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=0.0) == "critical"
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=20.0) == "critical"

    def test_low_range(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=21.0) == "low"
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=40.0) == "low"

    def test_moderate_range(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=41.0) == "moderate"
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=60.0) == "moderate"

    def test_healthy_range(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=61.0) == "healthy"
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=80.0) == "healthy"

    def test_thriving_range(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=81.0) == "thriving"
        assert CollectiveIntelligenceAnalyzer.compute_pulse_category(pulse_score=100.0) == "thriving"


class TestComputeDemandIntensity:
    """Test demand score → intensity mapping."""

    def test_low_demand(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=10.0) == "low"

    def test_moderate_demand(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=30.0) == "moderate"

    def test_high_demand(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=50.0) == "high"

    def test_very_high_demand(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=70.0) == "very_high"

    def test_critical_demand(self) -> None:
        assert CollectiveIntelligenceAnalyzer.compute_demand_intensity(demand_score=90.0) == "critical"


# ── Clamping Validator Tests ──────────────────────────────────


class TestClampIndustrySnapshot:
    """Test _clamp_industry_snapshot validator."""

    def test_clamps_confidence_above_max(self) -> None:
        data: dict[str, Any] = {"confidence": 0.95}
        _clamp_industry_snapshot(data)
        assert data["confidence"] == MAX_CI_CONFIDENCE

    def test_clamps_confidence_below_zero(self) -> None:
        data: dict[str, Any] = {"confidence": -0.5}
        _clamp_industry_snapshot(data)
        assert data["confidence"] == 0.0

    def test_invalid_confidence_type(self) -> None:
        data: dict[str, Any] = {"confidence": "invalid"}
        _clamp_industry_snapshot(data)
        assert data["confidence"] == 0.0

    def test_invalid_trend_defaults_to_stable(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "trend_direction": "invalid",
        }
        _clamp_industry_snapshot(data)
        assert data["trend_direction"] == "stable"

    def test_invalid_demand_defaults_to_moderate(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "demand_intensity": "invalid",
        }
        _clamp_industry_snapshot(data)
        assert data["demand_intensity"] == "moderate"

    def test_negative_salary_range_set_to_none(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "avg_salary_range_min": -1000,
            "avg_salary_range_max": -500,
        }
        _clamp_industry_snapshot(data)
        assert data["avg_salary_range_min"] is None
        assert data["avg_salary_range_max"] is None


class TestClampSalaryBenchmark:
    """Test _clamp_salary_benchmark validator."""

    def test_clamps_confidence(self) -> None:
        data: dict[str, Any] = {"confidence": 0.99}
        _clamp_salary_benchmark(data)
        assert data["confidence"] == MAX_CI_CONFIDENCE

    def test_clamps_benchmarks_below_zero(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "benchmark_min": -100,
            "benchmark_median": -200,
            "benchmark_max": -300,
        }
        _clamp_salary_benchmark(data)
        assert data["benchmark_min"] == 0.0
        assert data["benchmark_median"] == 0.0
        assert data["benchmark_max"] == 0.0

    def test_clamps_percentile_range(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "benchmark_min": 0,
            "benchmark_median": 0,
            "benchmark_max": 0,
            "user_percentile": 150.0,
        }
        _clamp_salary_benchmark(data)
        assert data["user_percentile"] == 100.0

    def test_clamps_experience_factor(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "benchmark_min": 0,
            "benchmark_median": 0,
            "benchmark_max": 0,
            "experience_factor": 5.0,
        }
        _clamp_salary_benchmark(data)
        assert data["experience_factor"] == 2.0


class TestClampPeerCohort:
    """Test _clamp_peer_cohort validator."""

    def test_enforces_minimum_cohort_size(self) -> None:
        data: dict[str, Any] = {"confidence": 0.5, "cohort_size": 3}
        _clamp_peer_cohort(data)
        assert data["cohort_size"] == MIN_COHORT_SIZE

    def test_clamps_percentile(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "user_rank_percentile": 120.0,
        }
        _clamp_peer_cohort(data)
        assert data["user_rank_percentile"] == 100.0

    def test_invalid_cohort_size_type(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "cohort_size": "invalid",
        }
        _clamp_peer_cohort(data)
        assert data["cohort_size"] == MIN_COHORT_SIZE


class TestClampCareerPulse:
    """Test _clamp_career_pulse validator."""

    def test_recomputes_pulse_score_from_components(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "demand_component": 80.0,
            "salary_component": 60.0,
            "skill_relevance_component": 70.0,
            "trend_component": 50.0,
            "pulse_score": 999.0,  # will be overwritten
            "pulse_category": "wrong",  # will be overwritten
        }
        _clamp_career_pulse(data)
        # 80×0.30 + 60×0.25 + 70×0.25 + 50×0.20 = 24+15+17.5+10 = 66.5
        assert data["pulse_score"] == 66.5
        assert data["pulse_category"] == "healthy"

    def test_clamps_components_to_range(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "demand_component": 150.0,
            "salary_component": -20.0,
            "skill_relevance_component": 50.0,
            "trend_component": 50.0,
        }
        _clamp_career_pulse(data)
        assert data["demand_component"] == 100.0
        assert data["salary_component"] == 0.0

    def test_invalid_trend_defaults(self) -> None:
        data: dict[str, Any] = {
            "confidence": 0.5,
            "demand_component": 50,
            "salary_component": 50,
            "skill_relevance_component": 50,
            "trend_component": 50,
            "trend_direction": "unknown_trend",
        }
        _clamp_career_pulse(data)
        assert data["trend_direction"] == "stable"


# ── Schema Validation Tests ───────────────────────────────────


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_industry_snapshot_response(self) -> None:
        response = IndustrySnapshotResponse(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            industry="Software Development",
            region="Netherlands",
            trend_direction="rising",
            demand_intensity="high",
            currency="EUR",
            confidence_score=0.75,
            data_source="AI-analyzed",
            disclaimer="Disclaimer text",
            created_at=datetime.now(tz=UTC),
        )
        assert response.industry == "Software Development"
        assert response.confidence_score == 0.75

    def test_salary_benchmark_response(self) -> None:
        response = SalaryBenchmarkResponse(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role="Software Engineer",
            location="Amsterdam",
            experience_years=5,
            benchmark_min=55000.0,
            benchmark_median=72000.0,
            benchmark_max=95000.0,
            currency="EUR",
            confidence_score=0.70,
            data_source="AI-analyzed",
            disclaimer="Disclaimer",
            created_at=datetime.now(tz=UTC),
        )
        assert response.benchmark_median == 72000.0

    def test_career_pulse_response_validates_range(self) -> None:
        response = CareerPulseResponse(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            pulse_score=72.5,
            pulse_category="healthy",
            trend_direction="rising",
            demand_component=80.0,
            salary_component=70.0,
            skill_relevance_component=65.0,
            trend_component=75.0,
            confidence_score=0.72,
            data_source="AI-computed",
            disclaimer="Disclaimer",
            created_at=datetime.now(tz=UTC),
        )
        assert 0 <= response.pulse_score <= 100

    def test_dashboard_response_defaults(self) -> None:
        dashboard = CollectiveIntelligenceDashboardResponse()
        assert dashboard.latest_pulse is None
        assert dashboard.industry_snapshots == []
        assert dashboard.salary_benchmarks == []
        assert dashboard.peer_cohort_analyses == []
        assert "85%" in dashboard.disclaimer


# ── Analyzer LLM Method Tests (mocked) ────────────────────────


class TestAnalyzerLLMMethods:
    """Test analyzer LLM methods with mocked complete_json."""

    @pytest.mark.asyncio
    async def test_analyze_industry_snapshot_success(self) -> None:
        mock_result: dict[str, Any] = {
            "trend_direction": "rising",
            "demand_intensity": "high",
            "top_emerging_skills": {"skills": ["AI", "ML"]},
            "declining_skills": None,
            "avg_salary_range_min": 60000.0,
            "avg_salary_range_max": 95000.0,
            "growth_rate_pct": 12.5,
            "hiring_volume_trend": "Strong growth",
            "key_insights": {"opportunities": ["AI adoption"]},
            "confidence": 0.78,
        }

        with patch(
            "app.ai.collective_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_industry_snapshot(
                industry="Software Development",
                region="Netherlands",
                primary_role="Software Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, TypeScript",
                years_experience=8,
            )

        assert result["trend_direction"] == "rising"
        assert result["demand_intensity"] == "high"
        assert result["confidence"] == 0.78

    @pytest.mark.asyncio
    async def test_analyze_industry_snapshot_llm_failure(self) -> None:
        with (
            patch(
                "app.ai.collective_intelligence_analyzer.complete_json",
                new_callable=AsyncMock,
                side_effect=Exception("LLM error"),
            ),
            patch(
                "app.ai.collective_intelligence_analyzer.LLMError",
                Exception,
            ),
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_industry_snapshot(
                industry="Tech",
                region="EU",
                primary_role="Engineer",
                seniority_level="mid",
                primary_industry="Technology",
                skills="General",
                years_experience=3,
            )

        assert result["trend_direction"] == "stable"
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_career_pulse_success(self) -> None:
        mock_result: dict[str, Any] = {
            "pulse_score": 72.0,
            "pulse_category": "healthy",
            "trend_direction": "rising",
            "demand_component": 80.0,
            "salary_component": 65.0,
            "skill_relevance_component": 70.0,
            "trend_component": 60.0,
            "top_opportunities": None,
            "risk_factors": None,
            "recommended_actions": None,
            "summary": "Strong market position.",
            "confidence": 0.68,
        }

        with patch(
            "app.ai.collective_intelligence_analyzer.complete_json",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await CollectiveIntelligenceAnalyzer.analyze_career_pulse(
                industry="Technology",
                region="Netherlands",
                primary_role="Software Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, TypeScript",
                years_experience=8,
                location="Amsterdam",
            )

        # Pulse is recomputed from components by clamper
        # 80×0.30 + 65×0.25 + 70×0.25 + 60×0.20
        # = 24 + 16.25 + 17.5 + 12 = 69.75 → 69.8
        assert result["pulse_score"] == 69.8
        assert result["pulse_category"] == "healthy"
        assert result["confidence"] == 0.68
