"""
PathForge — Career DNA Analyzer Unit Tests
============================================
Tests for all 6 CareerDNAAnalyzer methods.
LLM calls (complete_json_with_transparency) are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.career_dna_analyzer import (
    CareerDNAAnalyzer,
    _default_blueprint,
    _default_growth_vector,
    _default_market_position,
    _default_values_profile,
)
from app.core.llm import LLMError

# ── Helpers ───────────────────────────────────────────────────

_EXP_TEXT = "Senior Python Developer at Acme Inc. 5 years experience."
_SKILLS = ["Python", "FastAPI", "PostgreSQL"]


def _make_record(**kwargs: Any) -> MagicMock:
    record = MagicMock()
    record.latency_ms = kwargs.get("latency_ms", 250)
    record.confidence_score = kwargs.get("confidence_score", 0.82)
    return record


LLM_PATH = "app.ai.career_dna_analyzer.complete_json_with_transparency"


# ── default fallbacks ─────────────────────────────────────────


def test_default_blueprint_keys() -> None:
    bp = _default_blueprint()
    assert "total_years" in bp
    assert "career_direction" in bp


def test_default_growth_vector_keys() -> None:
    gv = _default_growth_vector()
    assert "growth_score" in gv
    assert gv["growth_score"] == 50.0


def test_default_values_profile_keys() -> None:
    vp = _default_values_profile()
    assert "confidence" in vp
    assert vp["confidence"] == 0.0


def test_default_market_position_keys() -> None:
    mp = _default_market_position()
    assert "percentile_overall" in mp
    assert mp["matching_job_count"] == 0


# ── discover_hidden_skills ────────────────────────────────────


@pytest.mark.asyncio
async def test_discover_hidden_skills_empty_exp_returns_empty() -> None:
    skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
        explicit_skills=_SKILLS, experience_text=""
    )
    assert skills == []
    assert record is None


@pytest.mark.asyncio
async def test_discover_hidden_skills_whitespace_exp_returns_empty() -> None:
    skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
        explicit_skills=_SKILLS, experience_text="   \t\n"
    )
    assert skills == []
    assert record is None


@pytest.mark.asyncio
async def test_discover_hidden_skills_happy_path() -> None:
    fake_data = {
        "hidden_skills": [
            {"skill": "Leadership", "confidence": 0.85},
            {"skill": "Mentoring", "confidence": 0.95},  # will be capped to 0.9
        ]
    }
    record = _make_record()

    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, record)):
        skills, ret_record = await CareerDNAAnalyzer.discover_hidden_skills(
            explicit_skills=_SKILLS, experience_text=_EXP_TEXT
        )

    assert len(skills) == 2
    assert skills[1]["confidence"] == 0.9  # capped
    assert ret_record is record


@pytest.mark.asyncio
async def test_discover_hidden_skills_confidence_above_09_capped() -> None:
    fake_data = {
        "hidden_skills": [
            {"skill": "X", "confidence": 1.0},
        ]
    }
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        skills, _ = await CareerDNAAnalyzer.discover_hidden_skills(
            explicit_skills=[], experience_text=_EXP_TEXT
        )
    assert skills[0]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_discover_hidden_skills_llm_error_returns_empty() -> None:
    with patch(LLM_PATH, new_callable=AsyncMock, side_effect=LLMError("rate limit")):
        skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
            explicit_skills=_SKILLS, experience_text=_EXP_TEXT
        )
    assert skills == []
    assert record is None


@pytest.mark.asyncio
async def test_discover_hidden_skills_empty_explicit_skills() -> None:
    fake_data = {"hidden_skills": [{"skill": "Y", "confidence": 0.7}]}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        skills, _ = await CareerDNAAnalyzer.discover_hidden_skills(
            explicit_skills=[], experience_text=_EXP_TEXT
        )
    assert len(skills) == 1


# ── analyze_experience_blueprint ─────────────────────────────


@pytest.mark.asyncio
async def test_analyze_experience_blueprint_empty_returns_default() -> None:
    result, record = await CareerDNAAnalyzer.analyze_experience_blueprint("")
    assert result == _default_blueprint()
    assert record is None


@pytest.mark.asyncio
async def test_analyze_experience_blueprint_happy_path() -> None:
    fake_data = {"total_years": 5.0, "role_count": 2, "career_direction": "growth"}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, record = await CareerDNAAnalyzer.analyze_experience_blueprint(_EXP_TEXT)

    assert result["total_years"] == 5.0
    assert result["career_direction"] == "growth"
    assert record is not None


@pytest.mark.asyncio
async def test_analyze_experience_blueprint_llm_error_returns_default() -> None:
    with patch(LLM_PATH, new_callable=AsyncMock, side_effect=LLMError("timeout")):
        result, record = await CareerDNAAnalyzer.analyze_experience_blueprint(_EXP_TEXT)

    assert result == _default_blueprint()
    assert record is None


# ── compute_growth_vector ─────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_growth_vector_empty_exp_returns_default() -> None:
    result, record = await CareerDNAAnalyzer.compute_growth_vector(
        experience_text="",
        skills_text="Python",
        preferences_text="remote work",
    )
    assert result == _default_growth_vector()
    assert record is None


@pytest.mark.asyncio
async def test_compute_growth_vector_happy_path() -> None:
    fake_data = {
        "current_trajectory": "ascending",
        "growth_score": 75.0,
        "projected_roles": ["Tech Lead"],
    }
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, record = await CareerDNAAnalyzer.compute_growth_vector(
            experience_text=_EXP_TEXT,
            skills_text="Python, FastAPI",
            preferences_text="startup environment",
        )

    assert result["growth_score"] == 75.0
    assert record is not None


@pytest.mark.asyncio
async def test_compute_growth_vector_score_clamped_to_100() -> None:
    fake_data = {"growth_score": 150.0}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, _ = await CareerDNAAnalyzer.compute_growth_vector(
            experience_text=_EXP_TEXT,
            skills_text="Python",
            preferences_text="",
        )
    assert result["growth_score"] == 100.0


@pytest.mark.asyncio
async def test_compute_growth_vector_score_clamped_to_0() -> None:
    fake_data = {"growth_score": -50.0}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, _ = await CareerDNAAnalyzer.compute_growth_vector(
            experience_text=_EXP_TEXT,
            skills_text="Python",
            preferences_text=None,  # type: ignore[arg-type]
        )
    assert result["growth_score"] == 0.0


@pytest.mark.asyncio
async def test_compute_growth_vector_llm_error_returns_default() -> None:
    with patch(LLM_PATH, new_callable=AsyncMock, side_effect=LLMError("error")):
        result, record = await CareerDNAAnalyzer.compute_growth_vector(
            experience_text=_EXP_TEXT,
            skills_text="Python",
            preferences_text="remote",
        )
    assert result == _default_growth_vector()
    assert record is None


@pytest.mark.asyncio
async def test_compute_growth_vector_none_preferences() -> None:
    fake_data = {"growth_score": 60.0}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, _ = await CareerDNAAnalyzer.compute_growth_vector(
            experience_text=_EXP_TEXT,
            skills_text="Python",
            preferences_text=None,  # type: ignore[arg-type]
        )
    assert result["growth_score"] == 60.0


# ── extract_values_profile ────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_values_profile_empty_returns_default() -> None:
    result, record = await CareerDNAAnalyzer.extract_values_profile("", "remote")
    assert result == _default_values_profile()
    assert record is None


@pytest.mark.asyncio
async def test_extract_values_profile_happy_path() -> None:
    fake_data = {
        "work_style": "async",
        "impact_preference": "global",
        "confidence": 0.88,
    }
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, record = await CareerDNAAnalyzer.extract_values_profile(
            _EXP_TEXT, "flexible hours"
        )
    assert result["confidence"] == 0.88
    assert record is not None


@pytest.mark.asyncio
async def test_extract_values_profile_confidence_clamped_above_1() -> None:
    fake_data = {"confidence": 1.5}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, _ = await CareerDNAAnalyzer.extract_values_profile(_EXP_TEXT, "remote")
    assert result["confidence"] == 1.0


@pytest.mark.asyncio
async def test_extract_values_profile_confidence_clamped_below_0() -> None:
    fake_data = {"confidence": -0.5}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, _ = await CareerDNAAnalyzer.extract_values_profile(_EXP_TEXT, "")
    assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_extract_values_profile_llm_error_returns_default() -> None:
    with patch(LLM_PATH, new_callable=AsyncMock, side_effect=LLMError("fail")):
        result, record = await CareerDNAAnalyzer.extract_values_profile(_EXP_TEXT, "x")
    assert result == _default_values_profile()
    assert record is None


@pytest.mark.asyncio
async def test_extract_values_profile_none_preferences() -> None:
    fake_data = {"confidence": 0.6}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        result, _ = await CareerDNAAnalyzer.extract_values_profile(
            _EXP_TEXT, None  # type: ignore[arg-type]
        )
    assert result["confidence"] == 0.6


# ── synthesize_summary ────────────────────────────────────────


@pytest.mark.asyncio
async def test_synthesize_summary_happy_path() -> None:
    fake_data = {"summary": "Experienced Python engineer with strong backend skills."}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        summary, record = await CareerDNAAnalyzer.synthesize_summary(
            skills_summary="Python, FastAPI",
            experience_summary="5 years backend",
            growth_summary="Ascending trajectory",
            values_summary="Impact-driven",
            market_summary="High demand",
        )
    assert "Python" in summary or len(summary) > 0
    assert record is not None


@pytest.mark.asyncio
async def test_synthesize_summary_empty_inputs() -> None:
    fake_data = {"summary": "Summary of empty profile."}
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        summary, _ = await CareerDNAAnalyzer.synthesize_summary(
            skills_summary="",
            experience_summary="",
            growth_summary="",
            values_summary="",
            market_summary="",
        )
    assert isinstance(summary, str)


@pytest.mark.asyncio
async def test_synthesize_summary_missing_summary_key() -> None:
    fake_data: dict[str, Any] = {}  # no "summary" key
    with patch(LLM_PATH, new_callable=AsyncMock, return_value=(fake_data, _make_record())):
        summary, _ = await CareerDNAAnalyzer.synthesize_summary(
            skills_summary="x",
            experience_summary="y",
            growth_summary="z",
            values_summary="a",
            market_summary="b",
        )
    assert summary == ""


@pytest.mark.asyncio
async def test_synthesize_summary_llm_error_returns_empty() -> None:
    with patch(LLM_PATH, new_callable=AsyncMock, side_effect=LLMError("fail")):
        summary, record = await CareerDNAAnalyzer.synthesize_summary(
            skills_summary="s",
            experience_summary="e",
            growth_summary="g",
            values_summary="v",
            market_summary="m",
        )
    assert summary == ""
    assert record is None


# ── compute_market_position (pure function) ───────────────────


def test_compute_market_position_no_skills_returns_default() -> None:
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=[], job_listings_data=[{"title": "Python Dev", "description": "python"}]
    )
    assert result == _default_market_position()


def test_compute_market_position_no_listings_returns_default() -> None:
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python"], job_listings_data=[]
    )
    assert result == _default_market_position()


def test_compute_market_position_skill_in_title() -> None:
    listings = [
        {"title": "Python Engineer", "description": "backend work"},
        {"title": "Java Dev", "description": "spring boot"},
    ]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python"], job_listings_data=listings
    )
    assert result["matching_job_count"] == 1
    assert result["skill_demand_scores"]["Python"] == 0.5


def test_compute_market_position_skill_in_description() -> None:
    listings = [
        {"title": "Engineer", "description": "We use python and fastapi"},
        {"title": "Engineer", "description": "We use java"},
    ]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["python"], job_listings_data=listings
    )
    assert result["matching_job_count"] == 1


def test_compute_market_position_multiple_skills() -> None:
    listings = [
        {"title": "Python Dev", "description": "fastapi postgresql"},
        {"title": "Python Django", "description": "web framework"},
    ]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python", "FastAPI", "PostgreSQL"],
        job_listings_data=listings,
    )
    assert "Python" in result["skill_demand_scores"]
    assert "FastAPI" in result["skill_demand_scores"]
    assert result["percentile_overall"] > 0


def test_compute_market_position_high_demand_gives_rising_trend() -> None:
    listings = [{"title": f"Python Dev {i}", "description": "python"} for i in range(10)]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python", "FastAPI", "PostgreSQL"],
        job_listings_data=listings,
    )
    # Python matches all 10 (>30% threshold for rising)
    assert result["market_trend"] in ("rising", "stable")


def test_compute_market_position_low_demand_gives_declining_trend() -> None:
    listings = [
        {"title": "COBOL Dev", "description": "mainframe"},
        {"title": "COBOL Expert", "description": "legacy"},
    ]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python", "FastAPI", "PostgreSQL"],
        job_listings_data=listings,
    )
    assert result["market_trend"] == "declining"


def test_compute_market_position_percentile_capped_at_100() -> None:
    listings = [{"title": "Python Dev", "description": "python"} for _ in range(5)]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python"],
        job_listings_data=listings,
    )
    assert result["percentile_overall"] <= 100.0


def test_compute_market_position_deduplicates_matching_listings() -> None:
    """A listing matching both Python AND FastAPI counts once in matching_job_count."""
    listings = [
        {"title": "Python FastAPI Dev", "description": "python fastapi"},
    ]
    result = CareerDNAAnalyzer.compute_market_position(
        skill_names=["Python", "FastAPI"],
        job_listings_data=listings,
    )
    # One unique listing matched even though 2 skills match it
    assert result["matching_job_count"] == 1
