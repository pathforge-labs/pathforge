"""
PathForge — Career DNA Analyzer Transparency Tests
=====================================================
Per-method unit tests for AI Trust Layer™ transparency return values.

Sprint 20 Enhancement R3: Validates that every LLM-powered analyzer
method returns a well-formed TransparencyRecord alongside its results,
and that error/empty paths correctly return None.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.career_dna_analyzer import CareerDNAAnalyzer
from app.core.llm_observability import TransparencyRecord

# ── Fixture: Mock Transparency Record ──────────────────────────


def _make_transparency_record(
    analysis_type: str,
    data_sources: list[str],
) -> TransparencyRecord:
    """Build a realistic TransparencyRecord for test assertions."""
    return TransparencyRecord(
        analysis_type=analysis_type,
        model="anthropic/claude-sonnet-4-20250514",
        tier="primary",
        confidence_score=0.90,
        confidence_label="High",
        data_sources=data_sources,
        prompt_tokens=500,
        completion_tokens=200,
        latency_ms=1200,
        success=True,
        retries=0,
    )


# ── discover_hidden_skills ─────────────────────────────────────


@pytest.mark.asyncio
async def test_discover_hidden_skills_returns_transparency_record() -> None:
    """discover_hidden_skills returns (list, TransparencyRecord) on success."""
    mock_record = _make_transparency_record(
        analysis_type="career_dna.hidden_skills",
        data_sources=["experience_text", "skills_list"],
    )
    mock_data: dict[str, Any] = {
        "hidden_skills": [
            {"name": "Project Leadership", "confidence": 0.85, "evidence": "Led 3 teams"},
        ],
    }
    with patch(
        "app.ai.career_dna_analyzer.complete_json_with_transparency",
        new_callable=AsyncMock,
        return_value=(mock_data, mock_record),
    ):
        skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
            explicit_skills=["Python", "SQL"],
            experience_text="Led cross-functional teams across 3 projects.",
        )

    assert len(skills) == 1
    assert skills[0]["name"] == "Project Leadership"
    assert record is not None
    assert record.analysis_type == "career_dna.hidden_skills"
    assert record.confidence_score > 0.0
    assert record.latency_ms > 0
    assert "experience_text" in record.data_sources


@pytest.mark.asyncio
async def test_discover_hidden_skills_empty_input_returns_none() -> None:
    """discover_hidden_skills returns ([], None) for empty experience text."""
    skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
        explicit_skills=["Python"],
        experience_text="",
    )
    assert skills == []
    assert record is None


@pytest.mark.asyncio
async def test_discover_hidden_skills_llm_error_returns_none() -> None:
    """discover_hidden_skills returns ([], None) when LLM raises LLMError."""
    from app.core.llm import LLMError

    with patch(
        "app.ai.career_dna_analyzer.complete_json_with_transparency",
        new_callable=AsyncMock,
        side_effect=LLMError("Service unavailable"),
    ):
        skills, record = await CareerDNAAnalyzer.discover_hidden_skills(
            explicit_skills=["Python"],
            experience_text="Senior engineer at Acme Corp.",
        )

    assert skills == []
    assert record is None


# ── analyze_experience_blueprint ───────────────────────────────


@pytest.mark.asyncio
async def test_analyze_experience_blueprint_returns_transparency_record() -> None:
    """analyze_experience_blueprint returns (dict, TransparencyRecord) on success."""
    mock_record = _make_transparency_record(
        analysis_type="career_dna.experience_blueprint",
        data_sources=["experience_text"],
    )
    mock_data: dict[str, Any] = {
        "total_years": 8.5,
        "role_count": 4,
        "avg_tenure_months": 25.5,
        "career_direction": "ascending",
    }
    with patch(
        "app.ai.career_dna_analyzer.complete_json_with_transparency",
        new_callable=AsyncMock,
        return_value=(mock_data, mock_record),
    ):
        data, record = await CareerDNAAnalyzer.analyze_experience_blueprint(
            experience_text="8 years across 4 roles in fintech and SaaS.",
        )

    assert data["total_years"] == 8.5
    assert record is not None
    assert record.analysis_type == "career_dna.experience_blueprint"
    assert "experience_text" in record.data_sources


@pytest.mark.asyncio
async def test_analyze_experience_blueprint_empty_returns_none() -> None:
    """analyze_experience_blueprint returns (default_dict, None) for empty input."""
    data, record = await CareerDNAAnalyzer.analyze_experience_blueprint(
        experience_text="   ",
    )
    assert record is None
    assert data["total_years"] == 0.0
    assert data["career_direction"] == "exploring"


# ── compute_growth_vector ──────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_growth_vector_returns_transparency_record() -> None:
    """compute_growth_vector returns (dict, TransparencyRecord) on success."""
    mock_record = _make_transparency_record(
        analysis_type="career_dna.growth_vector",
        data_sources=["experience_text", "skills_list", "preferences"],
    )
    mock_data: dict[str, Any] = {
        "current_trajectory": "accelerating",
        "growth_score": 78.0,
        "projected_roles": ["Staff Engineer"],
    }
    with patch(
        "app.ai.career_dna_analyzer.complete_json_with_transparency",
        new_callable=AsyncMock,
        return_value=(mock_data, mock_record),
    ):
        data, record = await CareerDNAAnalyzer.compute_growth_vector(
            experience_text="Promoted twice in 4 years.",
            skills_text="Python, System Design, Team Leadership",
            preferences_text="Want to become a Staff Engineer",
        )

    assert data["growth_score"] == 78.0
    assert record is not None
    assert record.analysis_type == "career_dna.growth_vector"
    assert "preferences" in record.data_sources


@pytest.mark.asyncio
async def test_compute_growth_vector_empty_returns_none() -> None:
    """compute_growth_vector returns (default_dict, None) for empty experience."""
    data, record = await CareerDNAAnalyzer.compute_growth_vector(
        experience_text="",
        skills_text="Python",
        preferences_text="",
    )
    assert record is None
    assert data["current_trajectory"] == "steady"
    assert data["growth_score"] == 50.0


# ── extract_values_profile ─────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_values_profile_returns_transparency_record() -> None:
    """extract_values_profile returns (dict, TransparencyRecord) on success."""
    mock_record = _make_transparency_record(
        analysis_type="career_dna.values_profile",
        data_sources=["experience_text", "preferences"],
    )
    mock_data: dict[str, Any] = {
        "work_style": "collaborative",
        "impact_preference": "product",
        "confidence": 0.82,
    }
    with patch(
        "app.ai.career_dna_analyzer.complete_json_with_transparency",
        new_callable=AsyncMock,
        return_value=(mock_data, mock_record),
    ):
        data, record = await CareerDNAAnalyzer.extract_values_profile(
            experience_text="Focused on cross-team collaboration and product impact.",
            preferences_text="Prefer collaborative environments",
        )

    assert data["work_style"] == "collaborative"
    assert record is not None
    assert record.analysis_type == "career_dna.values_profile"
    assert "preferences" in record.data_sources


@pytest.mark.asyncio
async def test_extract_values_profile_empty_returns_none() -> None:
    """extract_values_profile returns (default_dict, None) for empty input."""
    data, record = await CareerDNAAnalyzer.extract_values_profile(
        experience_text="",
        preferences_text="",
    )
    assert record is None
    assert data["work_style"] == "flexible"
    assert data["confidence"] == 0.0


# ── synthesize_summary ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_synthesize_summary_returns_transparency_record() -> None:
    """synthesize_summary returns (str, TransparencyRecord) on success."""
    mock_record = _make_transparency_record(
        analysis_type="career_dna.summary",
        data_sources=[
            "skill_genome", "experience_blueprint",
            "growth_vector", "values_profile", "market_position",
        ],
    )
    mock_data: dict[str, Any] = {
        "summary": "A versatile senior engineer with strong growth trajectory.",
    }
    with patch(
        "app.ai.career_dna_analyzer.complete_json_with_transparency",
        new_callable=AsyncMock,
        return_value=(mock_data, mock_record),
    ):
        summary, record = await CareerDNAAnalyzer.synthesize_summary(
            skills_summary="Python, TypeScript, System Design",
            experience_summary="8 years across fintech and SaaS",
            growth_summary="Accelerating trajectory",
            values_summary="Collaborative, product-focused",
            market_summary="75th percentile demand",
        )

    assert "senior engineer" in summary.lower()
    assert record is not None
    assert record.analysis_type == "career_dna.summary"
    assert len(record.data_sources) == 5
    assert "skill_genome" in record.data_sources
