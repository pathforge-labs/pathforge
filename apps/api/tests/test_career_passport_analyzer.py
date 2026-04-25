"""
Unit tests for CareerPassportAnalyzer.

Covers:
  - 4 static helpers (compute_passport_score, compute_credential_confidence,
    compute_financial_score, compute_demand_score)
  - 4 async LLM methods (analyze_credential_mapping, analyze_country_comparison,
    analyze_visa_feasibility, analyze_market_demand)
  - 4 private clamping validators (_clamp_credential_mapping,
    _clamp_country_comparison, _clamp_visa_assessment, _clamp_market_demand)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.career_passport_analyzer import (
    MAX_PASSPORT_CONFIDENCE,
    VALID_DEMAND_LEVELS,
    VALID_EQF_LEVELS,
    VALID_VISA_CATEGORIES,
    CareerPassportAnalyzer,
    _clamp_country_comparison,
    _clamp_credential_mapping,
    _clamp_market_demand,
    _clamp_visa_assessment,
)

# ── Helpers ────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str) -> tuple[str, dict]:
    return text[:max_length], {}


def _patch_sanitize():
    return patch(
        "app.ai.career_passport_analyzer.sanitize_user_text",
        side_effect=_sanitize_passthrough,
    )


def _patch_complete_json(return_value):
    return patch(
        "app.ai.career_passport_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── compute_financial_score ────────────────────────────────────


class TestComputeFinancialScore:
    def test_positive_delta_above_30_returns_one(self) -> None:
        assert CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=50.0) == 1.0

    def test_negative_delta_below_minus_30_returns_zero(self) -> None:
        assert CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=-50.0) == 0.0

    def test_zero_delta_returns_half(self) -> None:
        result = CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=0.0)
        assert abs(result - 0.5) < 0.001

    def test_positive_30_returns_one(self) -> None:
        assert CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=30.0) == 1.0

    def test_negative_30_returns_zero(self) -> None:
        assert CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=-30.0) == 0.0

    def test_positive_15_returns_three_quarters(self) -> None:
        # (15 + 30) / 60 = 0.75
        result = CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=15.0)
        assert abs(result - 0.75) < 0.001

    def test_negative_15_returns_one_quarter(self) -> None:
        # (-15 + 30) / 60 = 0.25
        result = CareerPassportAnalyzer.compute_financial_score(purchasing_power_delta=-15.0)
        assert abs(result - 0.25) < 0.001


# ── compute_demand_score ───────────────────────────────────────


class TestComputeDemandScore:
    def test_low_returns_0_2(self) -> None:
        assert CareerPassportAnalyzer.compute_demand_score(demand_level="low") == 0.2

    def test_moderate_returns_0_5(self) -> None:
        assert CareerPassportAnalyzer.compute_demand_score(demand_level="moderate") == 0.5

    def test_high_returns_0_75(self) -> None:
        assert CareerPassportAnalyzer.compute_demand_score(demand_level="high") == 0.75

    def test_very_high_returns_1_0(self) -> None:
        assert CareerPassportAnalyzer.compute_demand_score(demand_level="very_high") == 1.0

    def test_unknown_level_returns_0_5(self) -> None:
        assert CareerPassportAnalyzer.compute_demand_score(demand_level="extreme") == 0.5


# ── compute_credential_confidence ─────────────────────────────


class TestComputeCredentialConfidence:
    def test_capped_at_max_passport_confidence(self) -> None:
        result = CareerPassportAnalyzer.compute_credential_confidence(
            llm_confidence=1.0,
            eqf_level_known=True,
            career_dna_completeness=1.0,
        )
        assert result == MAX_PASSPORT_CONFIDENCE

    def test_zero_inputs_returns_eqf_unknown_minimum(self) -> None:
        # 0.50*0 + 0.30*0.3 + 0.20*0 = 0.09
        result = CareerPassportAnalyzer.compute_credential_confidence(
            llm_confidence=0.0,
            eqf_level_known=False,
            career_dna_completeness=0.0,
        )
        assert abs(result - 0.09) < 0.001

    def test_eqf_known_bonus_is_higher(self) -> None:
        known = CareerPassportAnalyzer.compute_credential_confidence(
            llm_confidence=0.5, eqf_level_known=True
        )
        unknown = CareerPassportAnalyzer.compute_credential_confidence(
            llm_confidence=0.5, eqf_level_known=False
        )
        assert known > unknown

    def test_negative_llm_confidence_clamped(self) -> None:
        result = CareerPassportAnalyzer.compute_credential_confidence(
            llm_confidence=-5.0
        )
        assert result >= 0.0

    def test_default_career_dna_is_half(self) -> None:
        # 0.50*0.5 + 0.30*0.8 + 0.20*0.5 = 0.25 + 0.24 + 0.10 = 0.59
        result = CareerPassportAnalyzer.compute_credential_confidence(
            llm_confidence=0.5,
            eqf_level_known=True,
        )
        assert abs(result - 0.590) < 0.001


# ── compute_passport_score ─────────────────────────────────────


class TestComputePassportScore:
    def test_returns_all_score_keys(self) -> None:
        result = CareerPassportAnalyzer.compute_passport_score(
            credential_confidence=0.7,
            visa_eligibility=0.6,
            demand_level="high",
            purchasing_power_delta=10.0,
        )
        for key in ("credential_score", "visa_score", "demand_score", "financial_score", "overall_score"):
            assert key in result

    def test_overall_score_capped_at_one(self) -> None:
        result = CareerPassportAnalyzer.compute_passport_score(
            credential_confidence=MAX_PASSPORT_CONFIDENCE,
            visa_eligibility=MAX_PASSPORT_CONFIDENCE,
            demand_level="very_high",
            purchasing_power_delta=30.0,
        )
        assert result["overall_score"] <= 1.0

    def test_demand_score_maps_correctly(self) -> None:
        result = CareerPassportAnalyzer.compute_passport_score(
            credential_confidence=0.0,
            visa_eligibility=0.0,
            demand_level="very_high",
            purchasing_power_delta=0.0,
        )
        assert result["demand_score"] == 1.0

    def test_financial_score_for_neutral_delta(self) -> None:
        result = CareerPassportAnalyzer.compute_passport_score(
            credential_confidence=0.0,
            visa_eligibility=0.0,
            demand_level="low",
            purchasing_power_delta=0.0,
        )
        assert abs(result["financial_score"] - 0.5) < 0.001

    def test_low_inputs_low_overall(self) -> None:
        result = CareerPassportAnalyzer.compute_passport_score(
            credential_confidence=0.0,
            visa_eligibility=0.0,
            demand_level="low",
            purchasing_power_delta=-30.0,
        )
        assert result["overall_score"] < 0.2


# ── _clamp_credential_mapping ──────────────────────────────────


class TestClampCredentialMapping:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 5.0}
        _clamp_credential_mapping(data)
        assert data["confidence"] == MAX_PASSPORT_CONFIDENCE

    def test_confidence_negative_clamped_to_zero(self) -> None:
        data = {"confidence": -1.0}
        _clamp_credential_mapping(data)
        assert data["confidence"] == 0.0

    def test_invalid_confidence_type_becomes_zero(self) -> None:
        data = {"confidence": "high"}
        _clamp_credential_mapping(data)
        assert data["confidence"] == 0.0

    def test_invalid_eqf_level_becomes_level_6(self) -> None:
        data = {"eqf_level": "level_99"}
        _clamp_credential_mapping(data)
        assert data["eqf_level"] == "level_6"

    def test_valid_eqf_levels_preserved(self) -> None:
        for level in VALID_EQF_LEVELS:
            data = {"eqf_level": level}
            _clamp_credential_mapping(data)
            assert data["eqf_level"] == level

    def test_missing_equivalent_level_gets_default(self) -> None:
        data: dict = {}
        _clamp_credential_mapping(data)
        assert "Unknown equivalent" in data["equivalent_level"]

    def test_missing_recognition_notes_gets_default(self) -> None:
        data: dict = {}
        _clamp_credential_mapping(data)
        assert "ENIC-NARIC" in data["recognition_notes"]


# ── _clamp_country_comparison ──────────────────────────────────


class TestClampCountryComparison:
    def test_delta_fields_converted_to_float(self) -> None:
        data = {"col_delta_pct": "15", "salary_delta_pct": 10, "purchasing_power_delta": None}
        _clamp_country_comparison(data)
        assert isinstance(data["col_delta_pct"], float)
        assert isinstance(data["salary_delta_pct"], float)

    def test_non_numeric_delta_becomes_zero(self) -> None:
        data = {"col_delta_pct": "unavailable"}
        _clamp_country_comparison(data)
        assert data["col_delta_pct"] == 0.0

    def test_invalid_demand_level_becomes_moderate(self) -> None:
        data = {"market_demand_level": "extreme"}
        _clamp_country_comparison(data)
        assert data["market_demand_level"] == "moderate"

    def test_valid_demand_levels_preserved(self) -> None:
        for level in VALID_DEMAND_LEVELS:
            data = {"market_demand_level": level}
            _clamp_country_comparison(data)
            assert data["market_demand_level"] == level


# ── _clamp_visa_assessment ─────────────────────────────────────


class TestClampVisaAssessment:
    def test_eligibility_score_capped_at_max(self) -> None:
        data = {"eligibility_score": 99.0}
        _clamp_visa_assessment(data)
        assert data["eligibility_score"] == MAX_PASSPORT_CONFIDENCE

    def test_eligibility_negative_clamped_to_zero(self) -> None:
        data = {"eligibility_score": -5.0}
        _clamp_visa_assessment(data)
        assert data["eligibility_score"] == 0.0

    def test_invalid_eligibility_type_becomes_zero(self) -> None:
        data = {"eligibility_score": "high"}
        _clamp_visa_assessment(data)
        assert data["eligibility_score"] == 0.0

    def test_invalid_visa_type_becomes_other(self) -> None:
        data = {"visa_type": "tourist"}
        _clamp_visa_assessment(data)
        assert data["visa_type"] == "other"

    def test_valid_visa_categories_preserved(self) -> None:
        for cat in VALID_VISA_CATEGORIES:
            data = {"visa_type": cat}
            _clamp_visa_assessment(data)
            assert data["visa_type"] == cat

    def test_processing_weeks_clamped_1_to_52(self) -> None:
        data = {"processing_time_weeks": 200}
        _clamp_visa_assessment(data)
        assert data["processing_time_weeks"] == 52

    def test_processing_weeks_below_1_becomes_1(self) -> None:
        data = {"processing_time_weeks": 0}
        _clamp_visa_assessment(data)
        assert data["processing_time_weeks"] == 1

    def test_non_numeric_processing_weeks_becomes_none(self) -> None:
        data = {"processing_time_weeks": "four weeks"}
        _clamp_visa_assessment(data)
        assert data["processing_time_weeks"] is None


# ── _clamp_market_demand ───────────────────────────────────────


class TestClampMarketDemand:
    def test_invalid_demand_level_becomes_moderate(self) -> None:
        data = {"demand_level": "unknown"}
        _clamp_market_demand(data)
        assert data["demand_level"] == "moderate"

    def test_valid_demand_levels_preserved(self) -> None:
        for level in VALID_DEMAND_LEVELS:
            data = {"demand_level": level}
            _clamp_market_demand(data)
            assert data["demand_level"] == level

    def test_negative_positions_becomes_zero(self) -> None:
        data = {"open_positions_estimate": -100}
        _clamp_market_demand(data)
        assert data["open_positions_estimate"] == 0

    def test_non_numeric_positions_becomes_none(self) -> None:
        data = {"open_positions_estimate": "many"}
        _clamp_market_demand(data)
        assert data["open_positions_estimate"] is None

    def test_negative_salary_range_becomes_none(self) -> None:
        data = {"salary_range_min": -1000.0, "salary_range_max": 80000.0}
        _clamp_market_demand(data)
        assert data["salary_range_min"] is None
        assert data["salary_range_max"] == 80000.0

    def test_non_numeric_growth_becomes_none(self) -> None:
        data = {"yoy_growth_pct": "fast"}
        _clamp_market_demand(data)
        assert data["yoy_growth_pct"] is None

    def test_numeric_growth_preserved(self) -> None:
        data = {"yoy_growth_pct": 12.5}
        _clamp_market_demand(data)
        assert data["yoy_growth_pct"] == 12.5


# ── analyze_credential_mapping (LLM) ──────────────────────────


class TestAnalyzeCredentialMapping:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "equivalent_level": "Bachelor",
            "eqf_level": "level_6",
            "confidence": 0.75,
            "recognition_notes": "Well-recognized",
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CareerPassportAnalyzer.analyze_credential_mapping(
                source_qualification="BSc Computer Science",
                source_country="Turkey",
                target_country="Germany",
                primary_role="Software Engineer",
                primary_industry="Technology",
                years_experience=5,
            )
        assert isinstance(result, dict)
        assert result["confidence"] <= MAX_PASSPORT_CONFIDENCE

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.career_passport_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CareerPassportAnalyzer.analyze_credential_mapping(
                source_qualification="MSc",
                source_country="Turkey",
                target_country="Netherlands",
                primary_role="Engineer",
                primary_industry="Tech",
                years_experience=3,
            )
        assert result["confidence"] == 0.0
        assert "ENIC-NARIC" in result["recognition_notes"]

    @pytest.mark.asyncio
    async def test_confidence_clamped_in_output(self) -> None:
        response = {"confidence": 10.0, "eqf_level": "level_6"}
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CareerPassportAnalyzer.analyze_credential_mapping(
                source_qualification="PhD",
                source_country="Turkey",
                target_country="Germany",
                primary_role="Researcher",
                primary_industry="Academia",
                years_experience=8,
            )
        assert result["confidence"] == MAX_PASSPORT_CONFIDENCE


# ── analyze_country_comparison (LLM) ──────────────────────────


class TestAnalyzeCountryComparison:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "col_delta_pct": 20.0,
            "salary_delta_pct": 35.0,
            "purchasing_power_delta": 15.0,
            "market_demand_level": "high",
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CareerPassportAnalyzer.analyze_country_comparison(
                source_country="Turkey",
                target_country="Germany",
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                years_experience=7,
                salary_context="60000 EUR",
            )
        assert isinstance(result, dict)
        assert result["market_demand_level"] == "high"

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.career_passport_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CareerPassportAnalyzer.analyze_country_comparison(
                source_country="Turkey",
                target_country="Netherlands",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                years_experience=4,
                salary_context="",
            )
        assert result["purchasing_power_delta"] == 0.0
        assert result["market_demand_level"] == "moderate"


# ── analyze_visa_feasibility (LLM) ────────────────────────────


class TestAnalyzeVisaFeasibility:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "visa_type": "blue_card",
            "eligibility_score": 0.8,
            "processing_time_weeks": 8,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CareerPassportAnalyzer.analyze_visa_feasibility(
                nationality="Turkish",
                target_country="Germany",
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                years_experience=6,
                education_level="master",
            )
        assert isinstance(result, dict)
        assert result["eligibility_score"] <= MAX_PASSPORT_CONFIDENCE
        assert result["visa_type"] == "blue_card"

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.career_passport_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CareerPassportAnalyzer.analyze_visa_feasibility(
                nationality="Turkish",
                target_country="Switzerland",
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                years_experience=3,
                education_level="bachelor",
            )
        assert result["visa_type"] == "other"
        assert result["eligibility_score"] == 0.0


# ── analyze_market_demand (LLM) ───────────────────────────────


class TestAnalyzeMarketDemand:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "demand_level": "very_high",
            "open_positions_estimate": 5000,
            "yoy_growth_pct": 8.5,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CareerPassportAnalyzer.analyze_market_demand(
                country="Germany",
                role="Senior Engineer",
                industry="Technology",
                primary_role="Engineer",
                seniority_level="senior",
                skills="Python, Kubernetes",
            )
        assert isinstance(result, dict)
        assert result["demand_level"] == "very_high"

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.career_passport_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await CareerPassportAnalyzer.analyze_market_demand(
                country="Netherlands",
                role="Dev",
                industry="Finance",
                primary_role="Dev",
                seniority_level="mid",
                skills="Python",
            )
        assert result["demand_level"] == "moderate"
        assert result["open_positions_estimate"] is None

    @pytest.mark.asyncio
    async def test_invalid_demand_clamped(self) -> None:
        response = {"demand_level": "extreme"}
        with _patch_sanitize(), _patch_complete_json(response):
            result = await CareerPassportAnalyzer.analyze_market_demand(
                country="Germany",
                role="Dev",
                industry="Tech",
                primary_role="Dev",
                seniority_level="junior",
                skills="Python",
            )
        assert result["demand_level"] == "moderate"
