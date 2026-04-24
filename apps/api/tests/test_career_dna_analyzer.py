"""
Unit tests for CareerDNAAnalyzer.

Covers all 6 async/static methods:
  - discover_hidden_skills (LLM, confidence cap 0.85)
  - analyze_experience_blueprint (LLM)
  - compute_growth_vector (LLM, growth_score clamping)
  - extract_values_profile (LLM, confidence clamping)
  - synthesize_summary (LLM)
  - compute_market_position (pure data analysis)

Plus default fallback helpers:
  - _default_blueprint
  - _default_growth_vector
  - _default_values_profile
  - _default_market_position
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.career_dna_analyzer import (
    CareerDNAAnalyzer,
    _default_blueprint,
    _default_growth_vector,
    _default_market_position,
    _default_values_profile,
)
from app.core.llm import LLMError
from app.core.llm_observability import TransparencyRecord

PATCH_TARGET = "app.ai.career_dna_analyzer.complete_json_with_transparency"


# ── Helpers ────────────────────────────────────────────────────


def _make_record(
    analysis_type: str = "career_dna.test",
    confidence: float = 0.85,
    latency_ms: int = 120,
) -> TransparencyRecord:
    return TransparencyRecord(
        analysis_type=analysis_type,
        model="test-model",
        tier="PRIMARY",
        confidence_score=confidence,
        confidence_label="high",
        data_sources=["experience_text"],
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=latency_ms,
        success=True,
    )


def _patch_complete(return_value=None, side_effect=None):
    if side_effect is not None:
        return patch(PATCH_TARGET, new_callable=AsyncMock, side_effect=side_effect)
    return patch(PATCH_TARGET, new_callable=AsyncMock, return_value=return_value)


# ─────────────────────────────────────────────────────────────────
# discover_hidden_skills
# ─────────────────────────────────────────────────────────────────


class TestDiscoverHiddenSkills:
    @pytest.mark.asyncio
    async def test_happy_path_returns_skills_and_record(self) -> None:
        fake_record = _make_record("career_dna.hidden_skills")
        fake_data = {
            "hidden_skills": [
                {"name": "Project Management", "confidence": 0.75},
                {"name": "Cross-cultural Communication", "confidence": 0.8},
            ],
        }
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher as mock_llm:
            skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=["Python", "SQL"],
                experience_text="Led a team of 5 engineers across 3 countries...",
            )

        assert len(skills) == 2
        assert skills[0]["name"] == "Project Management"
        assert record is fake_record
        mock_llm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_experience_returns_empty_and_none(self) -> None:
        patcher = _patch_complete(return_value=({"hidden_skills": []}, _make_record()))
        with patcher as mock_llm:
            skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=["Python"],
                experience_text="",
            )

        assert skills == []
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_experience_returns_empty(self) -> None:
        patcher = _patch_complete(return_value=({"hidden_skills": []}, _make_record()))
        with patcher as mock_llm:
            skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=[],
                experience_text="   \n\t  ",
            )

        assert skills == []
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_confidence_cap_at_0_85(self) -> None:
        fake_record = _make_record()
        fake_data = {
            "hidden_skills": [
                {"name": "Leadership", "confidence": 0.99},
                {"name": "Strategy", "confidence": 0.95},
                {"name": "Empathy", "confidence": 0.7},
            ],
        }
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            skills, _ = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=[],
                experience_text="Some meaningful experience text.",
            )

        assert skills[0]["confidence"] == 0.85
        assert skills[1]["confidence"] == 0.85
        assert skills[2]["confidence"] == 0.7

    @pytest.mark.asyncio
    async def test_confidence_exactly_0_85_unchanged(self) -> None:
        fake_record = _make_record()
        fake_data = {
            "hidden_skills": [{"name": "Skill A", "confidence": 0.85}],
        }
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            skills, _ = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=[],
                experience_text="Experience text.",
            )

        assert skills[0]["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_missing_confidence_key_preserved(self) -> None:
        fake_record = _make_record()
        fake_data = {"hidden_skills": [{"name": "Skill X"}]}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            skills, _ = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=[],
                experience_text="Experience text.",
            )

        assert skills[0]["name"] == "Skill X"
        assert "confidence" not in skills[0] or skills[0].get("confidence", 0) == 0

    @pytest.mark.asyncio
    async def test_missing_hidden_skills_key_returns_empty(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({}, fake_record))
        with patcher:
            skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=[],
                experience_text="Experience text.",
            )

        assert skills == []
        assert record is fake_record

    @pytest.mark.asyncio
    async def test_empty_explicit_skills_uses_none_listed(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({"hidden_skills": []}, fake_record))
        with patcher as mock_llm:
            await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=[],
                experience_text="Experience text.",
            )

        _args, kwargs = mock_llm.call_args
        assert "None listed" in kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_and_none(self) -> None:
        patcher = _patch_complete(side_effect=LLMError("LLM failed"))
        with patcher:
            skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
                explicit_skills=["Python"],
                experience_text="Experience text.",
            )

        assert skills == []
        assert record is None


# ─────────────────────────────────────────────────────────────────
# analyze_experience_blueprint
# ─────────────────────────────────────────────────────────────────


class TestAnalyzeExperienceBlueprint:
    @pytest.mark.asyncio
    async def test_happy_path_returns_blueprint_and_record(self) -> None:
        fake_record = _make_record("career_dna.experience_blueprint")
        fake_data = {
            "total_years": 7.5,
            "role_count": 3,
            "avg_tenure_months": 30.0,
            "career_direction": "ascending",
            "industry_diversity": 0.4,
            "seniority_trajectory": "senior",
            "pattern_analysis": "Steady growth",
        }
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, record = await CareerDNAAnalyzer.analyze_experience_blueprint(
                experience_text="Worked as SWE for 7.5 years across 3 roles...",
            )

        assert data["total_years"] == 7.5
        assert data["career_direction"] == "ascending"
        assert record is fake_record

    @pytest.mark.asyncio
    async def test_empty_experience_returns_default(self) -> None:
        patcher = _patch_complete(return_value=({}, _make_record()))
        with patcher as mock_llm:
            data, record = await CareerDNAAnalyzer.analyze_experience_blueprint("")

        assert data == _default_blueprint()
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_experience_returns_default(self) -> None:
        patcher = _patch_complete(return_value=({}, _make_record()))
        with patcher as mock_llm:
            data, record = await CareerDNAAnalyzer.analyze_experience_blueprint(
                "  \t\n ",
            )

        assert data == _default_blueprint()
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_llm_error_returns_default_and_none(self) -> None:
        patcher = _patch_complete(side_effect=LLMError("Timeout"))
        with patcher:
            data, record = await CareerDNAAnalyzer.analyze_experience_blueprint(
                "Meaningful experience.",
            )

        assert data == _default_blueprint()
        assert record is None

    @pytest.mark.asyncio
    async def test_returns_raw_llm_data_unvalidated(self) -> None:
        fake_record = _make_record()
        fake_data = {"custom_field": "custom_value", "role_count": 99}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.analyze_experience_blueprint(
                "Experience text.",
            )

        assert data["custom_field"] == "custom_value"
        assert data["role_count"] == 99


# ─────────────────────────────────────────────────────────────────
# compute_growth_vector
# ─────────────────────────────────────────────────────────────────


class TestComputeGrowthVector:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        fake_record = _make_record("career_dna.growth_vector")
        fake_data = {
            "current_trajectory": "accelerating",
            "projected_roles": ["Senior Engineer", "Tech Lead"],
            "skill_velocity": "high",
            "growth_score": 82.0,
            "analysis_reasoning": "Strong trajectory.",
        }
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, record = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="5 years of SWE experience.",
                skills_text="Python, SQL, React",
                preferences_text="Looking for leadership",
            )

        assert data["growth_score"] == 82.0
        assert data["current_trajectory"] == "accelerating"
        assert record is fake_record

    @pytest.mark.asyncio
    async def test_empty_experience_returns_default(self) -> None:
        patcher = _patch_complete(return_value=({}, _make_record()))
        with patcher as mock_llm:
            data, record = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="",
                skills_text="Python",
                preferences_text="growth",
            )

        assert data == _default_growth_vector()
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_experience_returns_default(self) -> None:
        patcher = _patch_complete(return_value=({}, _make_record()))
        with patcher as mock_llm:
            data, record = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="   ",
                skills_text="Python",
                preferences_text="growth",
            )

        assert data == _default_growth_vector()
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_growth_score_clamped_above_100(self) -> None:
        fake_record = _make_record()
        fake_data = {"current_trajectory": "steady", "growth_score": 150.0}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Meaningful text.",
                skills_text="Python",
                preferences_text="growth",
            )

        assert data["growth_score"] == 100.0

    @pytest.mark.asyncio
    async def test_growth_score_clamped_below_0(self) -> None:
        fake_record = _make_record()
        fake_data = {"current_trajectory": "steady", "growth_score": -25.5}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Meaningful text.",
                skills_text="Python",
                preferences_text="growth",
            )

        assert data["growth_score"] == 0.0

    @pytest.mark.asyncio
    async def test_growth_score_boundary_0(self) -> None:
        fake_record = _make_record()
        fake_data = {"growth_score": 0.0}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Exp.",
                skills_text="s",
                preferences_text="p",
            )

        assert data["growth_score"] == 0.0

    @pytest.mark.asyncio
    async def test_growth_score_boundary_100(self) -> None:
        fake_record = _make_record()
        fake_data = {"growth_score": 100.0}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Exp.",
                skills_text="s",
                preferences_text="p",
            )

        assert data["growth_score"] == 100.0

    @pytest.mark.asyncio
    async def test_growth_score_missing_defaults_to_50(self) -> None:
        fake_record = _make_record()
        fake_data = {"current_trajectory": "steady"}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Exp.",
                skills_text="s",
                preferences_text="p",
            )

        assert data["growth_score"] == 50.0

    @pytest.mark.asyncio
    async def test_growth_score_coerced_from_int(self) -> None:
        fake_record = _make_record()
        fake_data = {"growth_score": 75}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Exp.",
                skills_text="s",
                preferences_text="p",
            )

        assert data["growth_score"] == 75.0
        assert isinstance(data["growth_score"], float)

    @pytest.mark.asyncio
    async def test_empty_preferences_uses_not_specified(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({"growth_score": 50.0}, fake_record))
        with patcher as mock_llm:
            await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Exp.",
                skills_text="s",
                preferences_text="",
            )

        _args, kwargs = mock_llm.call_args
        assert "Not specified" in kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_llm_error_returns_default(self) -> None:
        patcher = _patch_complete(side_effect=LLMError("Rate limit"))
        with patcher:
            data, record = await CareerDNAAnalyzer.compute_growth_vector(
                experience_text="Exp.",
                skills_text="s",
                preferences_text="p",
            )

        assert data == _default_growth_vector()
        assert record is None


# ─────────────────────────────────────────────────────────────────
# extract_values_profile
# ─────────────────────────────────────────────────────────────────


class TestExtractValuesProfile:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        fake_record = _make_record("career_dna.values_profile")
        fake_data = {
            "work_style": "collaborative",
            "impact_preference": "team",
            "environment_fit": "startup",
            "derived_values": ["autonomy", "growth"],
            "confidence": 0.78,
        }
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, record = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Led cross-functional teams.",
                preferences_text="Prefer startups.",
            )

        assert data["work_style"] == "collaborative"
        assert data["confidence"] == 0.78
        assert record is fake_record

    @pytest.mark.asyncio
    async def test_empty_experience_returns_default(self) -> None:
        patcher = _patch_complete(return_value=({}, _make_record()))
        with patcher as mock_llm:
            data, record = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="",
                preferences_text="prefs",
            )

        assert data == _default_values_profile()
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_experience_returns_default(self) -> None:
        patcher = _patch_complete(return_value=({}, _make_record()))
        with patcher as mock_llm:
            data, record = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="  \n  ",
                preferences_text="prefs",
            )

        assert data == _default_values_profile()
        assert record is None
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_confidence_clamped_above_1(self) -> None:
        fake_record = _make_record()
        fake_data = {"work_style": "flexible", "confidence": 1.5}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="prefs",
            )

        assert data["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_confidence_clamped_below_0(self) -> None:
        fake_record = _make_record()
        fake_data = {"work_style": "flexible", "confidence": -0.3}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="prefs",
            )

        assert data["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_confidence_boundary_0(self) -> None:
        fake_record = _make_record()
        fake_data = {"confidence": 0.0}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="prefs",
            )

        assert data["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_confidence_boundary_1(self) -> None:
        fake_record = _make_record()
        fake_data = {"confidence": 1.0}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="prefs",
            )

        assert data["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_confidence_missing_defaults_to_0_5(self) -> None:
        fake_record = _make_record()
        fake_data = {"work_style": "flexible"}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            data, _ = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="prefs",
            )

        assert data["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_empty_preferences_uses_not_specified(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({"confidence": 0.5}, fake_record))
        with patcher as mock_llm:
            await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="",
            )

        _args, kwargs = mock_llm.call_args
        assert "Not specified" in kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_llm_error_returns_default(self) -> None:
        patcher = _patch_complete(side_effect=LLMError("Network"))
        with patcher:
            data, record = await CareerDNAAnalyzer.extract_values_profile(
                experience_text="Exp.",
                preferences_text="prefs",
            )

        assert data == _default_values_profile()
        assert record is None


# ─────────────────────────────────────────────────────────────────
# synthesize_summary
# ─────────────────────────────────────────────────────────────────


class TestSynthesizeSummary:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        fake_record = _make_record("career_dna.summary")
        fake_data = {"summary": "A senior engineer with growth trajectory."}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            summary, record = await CareerDNAAnalyzer.synthesize_summary(
                skills_summary="Python, SQL",
                experience_summary="5 years SWE",
                growth_summary="Accelerating",
                values_summary="Autonomy",
                market_summary="High demand",
            )

        assert summary == "A senior engineer with growth trajectory."
        assert record is fake_record

    @pytest.mark.asyncio
    async def test_missing_summary_key_returns_empty_string(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({}, fake_record))
        with patcher:
            summary, record = await CareerDNAAnalyzer.synthesize_summary(
                skills_summary="s",
                experience_summary="e",
                growth_summary="g",
                values_summary="v",
                market_summary="m",
            )

        assert summary == ""
        assert record is fake_record

    @pytest.mark.asyncio
    async def test_none_summary_value_returns_none_string(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({"summary": None}, fake_record))
        with patcher:
            summary, _ = await CareerDNAAnalyzer.synthesize_summary(
                skills_summary="s",
                experience_summary="e",
                growth_summary="g",
                values_summary="v",
                market_summary="m",
            )

        assert summary == "None"

    @pytest.mark.asyncio
    async def test_empty_summary_inputs_replaced_with_not_analyzed(self) -> None:
        fake_record = _make_record()
        patcher = _patch_complete(return_value=({"summary": "ok"}, fake_record))
        with patcher as mock_llm:
            await CareerDNAAnalyzer.synthesize_summary(
                skills_summary="",
                experience_summary="",
                growth_summary="",
                values_summary="",
                market_summary="",
            )

        _args, kwargs = mock_llm.call_args
        assert kwargs["prompt"].count("Not analyzed") == 5

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_string_and_none(self) -> None:
        patcher = _patch_complete(side_effect=LLMError("API error"))
        with patcher:
            summary, record = await CareerDNAAnalyzer.synthesize_summary(
                skills_summary="s",
                experience_summary="e",
                growth_summary="g",
                values_summary="v",
                market_summary="m",
            )

        assert summary == ""
        assert record is None

    @pytest.mark.asyncio
    async def test_summary_coerced_to_str(self) -> None:
        fake_record = _make_record()
        fake_data = {"summary": 12345}
        patcher = _patch_complete(return_value=(fake_data, fake_record))
        with patcher:
            summary, _ = await CareerDNAAnalyzer.synthesize_summary(
                skills_summary="s",
                experience_summary="e",
                growth_summary="g",
                values_summary="v",
                market_summary="m",
            )

        assert summary == "12345"
        assert isinstance(summary, str)


# ─────────────────────────────────────────────────────────────────
# compute_market_position (pure data, no LLM)
# ─────────────────────────────────────────────────────────────────


class TestComputeMarketPosition:
    def test_empty_skills_returns_default(self) -> None:
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=[],
            job_listings_data=[{"title": "SWE", "description": "Python"}],
        )
        assert result == _default_market_position()

    def test_empty_listings_returns_default(self) -> None:
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=[],
        )
        assert result == _default_market_position()

    def test_both_empty_returns_default(self) -> None:
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=[],
            job_listings_data=[],
        )
        assert result == _default_market_position()

    def test_single_skill_full_match(self) -> None:
        listings = [
            {"title": "Python Dev", "description": "Build with Python"},
            {"title": "Python Eng", "description": "Advanced Python role"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 1.0
        assert result["matching_job_count"] == 2
        assert result["percentile_overall"] == 100.0
        assert result["market_trend"] == "rising"

    def test_single_skill_no_match(self) -> None:
        listings = [
            {"title": "Marketing", "description": "Social media"},
            {"title": "Sales", "description": "Cold calling"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 0.0
        assert result["matching_job_count"] == 0
        assert result["percentile_overall"] == 0.0
        assert result["market_trend"] == "declining"

    def test_case_insensitive_matching(self) -> None:
        listings = [{"title": "PYTHON dev", "description": "PyThOn expert needed"}]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["python"] == 1.0

    def test_title_only_match(self) -> None:
        listings = [{"title": "Python Dev", "description": "Generic role"}]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 1.0

    def test_description_only_match(self) -> None:
        listings = [{"title": "Engineer", "description": "Uses Python daily"}]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 1.0

    def test_matching_job_count_deduplicates(self) -> None:
        # Both skills match the same listing — should count once.
        listings = [
            {"title": "Python/SQL Dev", "description": "Python and SQL work"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python", "SQL"],
            job_listings_data=listings,
        )
        assert result["matching_job_count"] == 1

    def test_multiple_skills_partial_match(self) -> None:
        listings = [
            {"title": "Python Dev", "description": "Python only"},
            {"title": "Rust Dev", "description": "Rust only"},
            {"title": "Go Dev", "description": "Go only"},
            {"title": "Python Lead", "description": "Python leadership"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python", "JavaScript"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 0.5
        assert result["skill_demand_scores"]["JavaScript"] == 0.0
        # avg = 0.25, percentile = 25.0
        assert result["percentile_overall"] == 25.0

    def test_market_trend_rising(self) -> None:
        # >60% of skills have demand > 0.3
        listings = [
            {"title": "Python Go Rust", "description": "Python Go Rust"},
            {"title": "Python Go Rust", "description": "Python Go Rust"},
            {"title": "Python Go Rust", "description": "Python Go Rust"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python", "Go", "Rust"],
            job_listings_data=listings,
        )
        assert result["market_trend"] == "rising"

    def test_market_trend_stable(self) -> None:
        # Exactly one of three skills has demand > 0.3 → 33% → stable
        listings = [
            {"title": "Python", "description": "Python"},
            {"title": "Python", "description": "Python"},
            {"title": "Marketing", "description": "Nothing"},
            {"title": "Sales", "description": "Nothing"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python", "Rust", "Haskell"],
            job_listings_data=listings,
        )
        assert result["market_trend"] == "stable"

    def test_market_trend_declining(self) -> None:
        listings = [
            {"title": "Marketing", "description": "Nothing tech"},
            {"title": "Sales", "description": "Nothing tech"},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python", "Rust"],
            job_listings_data=listings,
        )
        assert result["market_trend"] == "declining"

    def test_percentile_rounded_to_one_decimal(self) -> None:
        listings = [
            {"title": "Python", "description": ""},
            {"title": "Nothing", "description": ""},
            {"title": "Nothing", "description": ""},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        # 1/3 = 0.333 → percentile = 33.3
        assert result["percentile_overall"] == 33.3

    def test_demand_score_rounded_to_three_decimals(self) -> None:
        listings = [
            {"title": "Python", "description": ""},
            {"title": "Nothing", "description": ""},
            {"title": "Nothing", "description": ""},
        ]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 0.333

    def test_missing_title_and_description_keys(self) -> None:
        listings = [{}, {"title": "Python Dev"}]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 0.5
        assert result["matching_job_count"] == 1

    def test_non_string_title_description_coerced(self) -> None:
        listings = [{"title": 123, "description": None}]
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=listings,
        )
        assert result["skill_demand_scores"]["Python"] == 0.0

    def test_result_keys_present(self) -> None:
        result = CareerDNAAnalyzer.compute_market_position(
            skill_names=["Python"],
            job_listings_data=[{"title": "Python", "description": ""}],
        )
        assert set(result.keys()) == {
            "percentile_overall",
            "skill_demand_scores",
            "matching_job_count",
            "market_trend",
        }


# ─────────────────────────────────────────────────────────────────
# Default helpers
# ─────────────────────────────────────────────────────────────────


class TestDefaultHelpers:
    def test_default_blueprint_shape(self) -> None:
        result = _default_blueprint()
        assert result["total_years"] == 0.0
        assert result["role_count"] == 0
        assert result["avg_tenure_months"] == 0.0
        assert result["career_direction"] == "exploring"
        assert result["industry_diversity"] == 0.0
        assert result["seniority_trajectory"] is None
        assert result["pattern_analysis"] is None

    def test_default_growth_vector_shape(self) -> None:
        result = _default_growth_vector()
        assert result["current_trajectory"] == "steady"
        assert result["projected_roles"] is None
        assert result["skill_velocity"] is None
        assert result["growth_score"] == 50.0
        assert result["analysis_reasoning"] is None

    def test_default_values_profile_shape(self) -> None:
        result = _default_values_profile()
        assert result["work_style"] == "flexible"
        assert result["impact_preference"] == "team"
        assert result["environment_fit"] is None
        assert result["derived_values"] is None
        assert result["confidence"] == 0.0

    def test_default_market_position_shape(self) -> None:
        result = _default_market_position()
        assert result["percentile_overall"] == 0.0
        assert result["skill_demand_scores"] is None
        assert result["matching_job_count"] == 0
        assert result["market_trend"] == "stable"
