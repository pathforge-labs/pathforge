"""
Unit tests for HiddenJobMarketAnalyzer.

Covers:
  - 4 static helpers (compute_signal_confidence, calculate_match_strength,
    validate_signal_data, calculate_opportunity_probability)
  - 4 async LLM methods (analyze_company_signals, match_signal_to_career_dna,
    generate_outreach, surface_opportunities)
  - 4 private clamping validators (_clamp_signal_analysis, _clamp_match_result,
    _clamp_outreach, _clamp_opportunities)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.hidden_job_market_analyzer import (
    MAX_SIGNAL_CONFIDENCE,
    VALID_SIGNAL_TYPES,
    HiddenJobMarketAnalyzer,
    _clamp_match_result,
    _clamp_opportunities,
    _clamp_outreach,
    _clamp_signal_analysis,
)

# ── Helpers ────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str) -> tuple[str, dict]:
    return text[:max_length], {}


def _patch_sanitize():
    return patch(
        "app.ai.hidden_job_market_analyzer.sanitize_user_text",
        side_effect=_sanitize_passthrough,
    )


def _patch_complete_json(return_value):
    return patch(
        "app.ai.hidden_job_market_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── compute_signal_confidence ──────────────────────────────────


class TestComputeSignalConfidence:
    def test_basic_weighted_formula(self) -> None:
        # 0.40*0.8 + 0.35*0.6 + 0.25*0.7 = 0.32 + 0.21 + 0.175 = 0.705
        result = HiddenJobMarketAnalyzer.compute_signal_confidence(
            llm_confidence=0.8,
            signal_strength=0.6,
            career_dna_completeness=0.7,
        )
        assert abs(result - 0.705) < 0.001

    def test_capped_at_max_confidence(self) -> None:
        result = HiddenJobMarketAnalyzer.compute_signal_confidence(
            llm_confidence=1.0,
            signal_strength=1.0,
            career_dna_completeness=1.0,
        )
        assert result == MAX_SIGNAL_CONFIDENCE

    def test_zero_inputs_returns_zero(self) -> None:
        result = HiddenJobMarketAnalyzer.compute_signal_confidence(
            llm_confidence=0.0,
            signal_strength=0.0,
            career_dna_completeness=0.0,
        )
        assert result == 0.0

    def test_negative_inputs_clamped(self) -> None:
        result = HiddenJobMarketAnalyzer.compute_signal_confidence(
            llm_confidence=-5.0,
            signal_strength=-1.0,
            career_dna_completeness=-2.0,
        )
        assert result == 0.0

    def test_llm_confidence_capped_at_max_before_weighting(self) -> None:
        r1 = HiddenJobMarketAnalyzer.compute_signal_confidence(llm_confidence=99.0)
        r2 = HiddenJobMarketAnalyzer.compute_signal_confidence(llm_confidence=MAX_SIGNAL_CONFIDENCE)
        assert r1 == r2

    def test_default_factors_are_half(self) -> None:
        # 0.40*0.6 + 0.35*0.5 + 0.25*0.5 = 0.24 + 0.175 + 0.125 = 0.54
        result = HiddenJobMarketAnalyzer.compute_signal_confidence(llm_confidence=0.6)
        assert abs(result - 0.540) < 0.001


# ── calculate_match_strength ───────────────────────────────────


class TestCalculateMatchStrength:
    def test_basic_weighted_formula(self) -> None:
        # 0.45*0.8 + 0.35*0.7 + 0.20*0.5 = 0.36 + 0.245 + 0.10 = 0.705
        result = HiddenJobMarketAnalyzer.calculate_match_strength(
            skill_overlap=0.8,
            role_relevance=0.7,
            signal_strength=0.5,
        )
        assert abs(result - 0.705) < 0.001

    def test_all_ones_returns_one(self) -> None:
        result = HiddenJobMarketAnalyzer.calculate_match_strength(
            skill_overlap=1.0,
            role_relevance=1.0,
            signal_strength=1.0,
        )
        assert result == 1.0

    def test_all_zeros_returns_zero(self) -> None:
        result = HiddenJobMarketAnalyzer.calculate_match_strength(
            skill_overlap=0.0,
            role_relevance=0.0,
            signal_strength=0.0,
        )
        assert result == 0.0

    def test_negative_clamped_to_zero(self) -> None:
        result = HiddenJobMarketAnalyzer.calculate_match_strength(
            skill_overlap=-1.0,
            role_relevance=-1.0,
            signal_strength=0.0,
        )
        assert result == 0.0

    def test_default_signal_strength_is_half(self) -> None:
        # 0.45*0.5 + 0.35*0.5 + 0.20*0.5 = 0.225 + 0.175 + 0.10 = 0.50
        result = HiddenJobMarketAnalyzer.calculate_match_strength(
            skill_overlap=0.5,
            role_relevance=0.5,
        )
        assert abs(result - 0.50) < 0.001


# ── validate_signal_data ───────────────────────────────────────


class TestValidateSignalData:
    def test_valid_data_returns_true(self) -> None:
        data = {
            "signal_type": "funding",
            "title": "Series A Raise",
            "strength": 0.8,
            "confidence": 0.7,
        }
        valid, error = HiddenJobMarketAnalyzer.validate_signal_data(data)
        assert valid is True
        assert error == ""

    def test_missing_required_field_returns_false(self) -> None:
        data = {"signal_type": "funding", "title": "Title", "strength": 0.5}
        valid, error = HiddenJobMarketAnalyzer.validate_signal_data(data)
        assert valid is False
        assert "confidence" in error

    def test_invalid_signal_type_returns_false(self) -> None:
        data = {
            "signal_type": "invalid_type",
            "title": "Title",
            "strength": 0.5,
            "confidence": 0.6,
        }
        valid, error = HiddenJobMarketAnalyzer.validate_signal_data(data)
        assert valid is False
        assert "signal_type" in error

    def test_all_valid_signal_types_pass(self) -> None:
        for stype in VALID_SIGNAL_TYPES:
            data = {"signal_type": stype, "title": "T", "strength": 0.5, "confidence": 0.5}
            valid, _ = HiddenJobMarketAnalyzer.validate_signal_data(data)
            assert valid is True

    def test_zero_strength_is_valid(self) -> None:
        # strength=0 is falsy but valid
        data = {"signal_type": "funding", "title": "T", "strength": 0, "confidence": 0.5}
        valid, _error = HiddenJobMarketAnalyzer.validate_signal_data(data)
        assert valid is True


# ── calculate_opportunity_probability ─────────────────────────


class TestCalculateOpportunityProbability:
    def test_basic_formula(self) -> None:
        # count_factor = min(1.0, 3/5) = 0.6
        # 0.35*0.6 + 0.40*0.7 + 0.25*0.5 = 0.21 + 0.28 + 0.125 = 0.615
        result = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
            signal_count=3,
            avg_signal_strength=0.7,
            match_score=0.5,
        )
        assert abs(result - 0.615) < 0.001

    def test_capped_at_max_signal_confidence(self) -> None:
        result = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
            signal_count=100,
            avg_signal_strength=1.0,
            match_score=1.0,
        )
        assert result == MAX_SIGNAL_CONFIDENCE

    def test_zero_count_returns_minimum(self) -> None:
        result = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
            signal_count=0,
            avg_signal_strength=0.0,
            match_score=0.0,
        )
        assert result == 0.0

    def test_signal_count_5_gives_full_count_factor(self) -> None:
        # count_factor capped at 1 when count >= 5
        r5 = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
            signal_count=5, avg_signal_strength=0.5, match_score=0.5,
        )
        r10 = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
            signal_count=10, avg_signal_strength=0.5, match_score=0.5,
        )
        assert r5 == r10


# ── _clamp_signal_analysis ─────────────────────────────────────


class TestClampSignalAnalysis:
    def test_invalid_signal_type_becomes_funding(self) -> None:
        data = {
            "signals": [{"signal_type": "unknown", "confidence": 0.5, "strength": 0.5}]
        }
        _clamp_signal_analysis(data)
        assert data["signals"][0]["signal_type"] == "funding"

    def test_valid_signal_types_preserved(self) -> None:
        for stype in VALID_SIGNAL_TYPES:
            data = {"signals": [{"signal_type": stype, "confidence": 0.5, "strength": 0.5}]}
            _clamp_signal_analysis(data)
            assert data["signals"][0]["signal_type"] == stype

    def test_confidence_capped_at_max(self) -> None:
        data = {"signals": [{"signal_type": "funding", "confidence": 9.9, "strength": 0.5}]}
        _clamp_signal_analysis(data)
        assert data["signals"][0]["confidence"] == MAX_SIGNAL_CONFIDENCE

    def test_strength_clamped_to_one(self) -> None:
        data = {"signals": [{"signal_type": "funding", "confidence": 0.5, "strength": 5.0}]}
        _clamp_signal_analysis(data)
        assert data["signals"][0]["strength"] == 1.0

    def test_non_list_signals_becomes_empty_list(self) -> None:
        data = {"signals": "not a list"}
        _clamp_signal_analysis(data)
        assert data["signals"] == []

    def test_missing_title_gets_default(self) -> None:
        data = {"signals": [{"signal_type": "funding", "confidence": 0.5, "strength": 0.5}]}
        _clamp_signal_analysis(data)
        assert "Untitled signal" in data["signals"][0]["title"]

    def test_missing_description_gets_default(self) -> None:
        data = {"signals": [{"signal_type": "funding", "title": "T", "confidence": 0.5, "strength": 0.5}]}
        _clamp_signal_analysis(data)
        assert data["signals"][0]["description"]

    def test_missing_company_summary_gets_default(self) -> None:
        data: dict = {"signals": []}
        _clamp_signal_analysis(data)
        assert data["company_summary"]


# ── _clamp_match_result ────────────────────────────────────────


class TestClampMatchResult:
    def test_match_score_clamped_to_one(self) -> None:
        data = {"match_score": 5.0, "skill_overlap": 0.5, "role_relevance": 0.5}
        _clamp_match_result(data)
        assert data["match_score"] == 1.0

    def test_match_score_negative_clamped_to_zero(self) -> None:
        data = {"match_score": -1.0, "skill_overlap": 0.5, "role_relevance": 0.5}
        _clamp_match_result(data)
        assert data["match_score"] == 0.0

    def test_skill_overlap_clamped_to_one(self) -> None:
        data = {"match_score": 0.5, "skill_overlap": 10.0, "role_relevance": 0.5}
        _clamp_match_result(data)
        assert data["skill_overlap"] == 1.0

    def test_role_relevance_clamped(self) -> None:
        data = {"match_score": 0.5, "skill_overlap": 0.5, "role_relevance": 99.0}
        _clamp_match_result(data)
        assert data["role_relevance"] == 1.0

    def test_missing_explanation_gets_default(self) -> None:
        data: dict = {}
        _clamp_match_result(data)
        assert data["explanation"]

    def test_non_dict_matched_skills_gets_structure(self) -> None:
        data = {"matched_skills": ["Python"]}
        _clamp_match_result(data)
        assert isinstance(data["matched_skills"], dict)
        assert "highly_relevant" in data["matched_skills"]


# ── _clamp_outreach ────────────────────────────────────────────


class TestClampOutreach:
    def test_missing_subject_line_gets_default(self) -> None:
        data: dict = {}
        _clamp_outreach(data)
        assert data["subject_line"]

    def test_missing_body_gets_default(self) -> None:
        data: dict = {}
        _clamp_outreach(data)
        assert data["body"]

    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence": 9.9}
        _clamp_outreach(data)
        assert data["confidence"] == MAX_SIGNAL_CONFIDENCE

    def test_confidence_negative_clamped_to_zero(self) -> None:
        data = {"confidence": -5.0}
        _clamp_outreach(data)
        assert data["confidence"] == 0.0

    def test_non_dict_personalization_points_gets_structure(self) -> None:
        data = {"personalization_points": ["point1"]}
        _clamp_outreach(data)
        assert isinstance(data["personalization_points"], dict)
        assert "signal_reference" in data["personalization_points"]

    def test_existing_subject_line_preserved(self) -> None:
        data = {"subject_line": "My custom subject", "confidence": 0.7}
        _clamp_outreach(data)
        assert data["subject_line"] == "My custom subject"


# ── _clamp_opportunities ───────────────────────────────────────


class TestClampOpportunities:
    def test_missing_predicted_role_gets_default(self) -> None:
        data = {"opportunities": [{}]}
        _clamp_opportunities(data)
        assert "Unknown role" in data["opportunities"][0]["predicted_role"]

    def test_probability_capped_at_max(self) -> None:
        data = {"opportunities": [{"probability": 99.0}]}
        _clamp_opportunities(data)
        assert data["opportunities"][0]["probability"] == MAX_SIGNAL_CONFIDENCE

    def test_probability_negative_clamped_to_zero(self) -> None:
        data = {"opportunities": [{"probability": -1.0}]}
        _clamp_opportunities(data)
        assert data["opportunities"][0]["probability"] == 0.0

    def test_missing_reasoning_gets_default(self) -> None:
        data = {"opportunities": [{}]}
        _clamp_opportunities(data)
        assert data["opportunities"][0]["reasoning"]

    def test_non_dict_required_skills_gets_structure(self) -> None:
        data = {"opportunities": [{"required_skills": ["Python"]}]}
        _clamp_opportunities(data)
        assert isinstance(data["opportunities"][0]["required_skills"], dict)
        assert "must_have" in data["opportunities"][0]["required_skills"]

    def test_non_list_opportunities_becomes_empty_list(self) -> None:
        data = {"opportunities": "not a list"}
        _clamp_opportunities(data)
        assert data["opportunities"] == []


# ── analyze_company_signals (LLM) ─────────────────────────────


class TestAnalyzeCompanySignals:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "signals": [
                {"signal_type": "funding", "title": "Series B", "strength": 0.9, "confidence": 0.8},
            ],
            "company_summary": "Growing startup.",
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await HiddenJobMarketAnalyzer.analyze_company_signals(
                company_name="StartupXYZ",
                industry="Technology",
                current_role="Engineer",
                current_seniority="senior",
            )
        assert isinstance(result, dict)
        assert len(result["signals"]) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_signals(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.hidden_job_market_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await HiddenJobMarketAnalyzer.analyze_company_signals(
                company_name="Corp",
                industry="Finance",
                current_role="Dev",
                current_seniority="mid",
            )
        assert result["signals"] == []
        assert "Analysis unavailable" in result["company_summary"]

    @pytest.mark.asyncio
    async def test_invalid_signal_type_clamped(self) -> None:
        response = {
            "signals": [{"signal_type": "bad_type", "confidence": 0.5, "strength": 0.5}],
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await HiddenJobMarketAnalyzer.analyze_company_signals(
                company_name="Corp",
                industry="Tech",
                current_role="Dev",
                current_seniority="mid",
            )
        assert result["signals"][0]["signal_type"] == "funding"


# ── match_signal_to_career_dna (LLM) ──────────────────────────


class TestMatchSignalToCareerDNA:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "match_score": 0.82,
            "skill_overlap": 0.75,
            "role_relevance": 0.9,
            "explanation": "Strong fit for backend roles.",
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await HiddenJobMarketAnalyzer.match_signal_to_career_dna(
                company_name="Corp",
                signal_type="funding",
                signal_title="Series A",
                signal_description="Raised $10M",
                signal_strength=0.85,
                primary_role="Engineer",
                seniority_level="senior",
                primary_industry="Technology",
                skills="Python, FastAPI",
                years_experience=7,
            )
        assert isinstance(result, dict)
        assert 0.0 <= result["match_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.hidden_job_market_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await HiddenJobMarketAnalyzer.match_signal_to_career_dna(
                company_name="Corp",
                signal_type="funding",
                signal_title="Round",
                signal_description="Raised",
                signal_strength=0.5,
                primary_role="Dev",
                seniority_level="mid",
                primary_industry="Tech",
                skills="Python",
                years_experience=5,
            )
        assert result == {}


# ── generate_outreach (LLM) ────────────────────────────────────


class TestGenerateOutreach:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "subject_line": "Excited about your growth",
            "body": "Hello, I noticed your recent funding...",
            "confidence": 0.75,
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await HiddenJobMarketAnalyzer.generate_outreach(
                company_name="Corp",
                signal_type="funding",
                signal_title="Series A",
                signal_description="Raised $10M",
                primary_role="Engineer",
                skills="Python",
                years_experience=5,
                primary_industry="Tech",
            )
        assert isinstance(result, dict)
        assert "subject_line" in result

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.hidden_job_market_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await HiddenJobMarketAnalyzer.generate_outreach(
                company_name="Corp",
                signal_type="key_hire",
                signal_title="New CTO",
                signal_description="Hired new CTO",
                primary_role="Dev",
                skills="Python",
                years_experience=5,
                primary_industry="Tech",
            )
        assert result == {}


# ── surface_opportunities (LLM) ────────────────────────────────


class TestSurfaceOpportunities:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "opportunities": [
                {"predicted_role": "Backend Engineer", "probability": 0.7, "reasoning": "Good fit"},
            ],
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await HiddenJobMarketAnalyzer.surface_opportunities(
                signals=[{"signal_type": "funding", "title": "Series A", "strength": 0.8}],
                primary_role="Engineer",
                seniority_level="senior",
                skills="Python",
                primary_industry="Technology",
            )
        assert isinstance(result, dict)
        assert len(result["opportunities"]) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_opportunities(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.hidden_job_market_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await HiddenJobMarketAnalyzer.surface_opportunities(
                signals=[],
                primary_role="Dev",
                seniority_level="mid",
                skills="Python",
                primary_industry="Tech",
            )
        assert result["opportunities"] == []

    @pytest.mark.asyncio
    async def test_probability_clamped_in_output(self) -> None:
        response = {
            "opportunities": [{"probability": 99.9, "predicted_role": "Dev"}],
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await HiddenJobMarketAnalyzer.surface_opportunities(
                signals=[],
                primary_role="Dev",
                seniority_level="senior",
                skills="Python",
                primary_industry="Tech",
            )
        assert result["opportunities"][0]["probability"] == MAX_SIGNAL_CONFIDENCE
