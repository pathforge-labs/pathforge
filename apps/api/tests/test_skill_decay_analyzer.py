"""
Unit tests for SkillDecayAnalyzer and its pure helper methods.

Covers: exponential decay math, half-life lookups, decay classification,
urgency computation, and all four async LLM methods.
"""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm import LLMError

# ── Helpers ───────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str):
    return text[:max_length], {}


# ── compute_base_freshness ────────────────────────────────────────


class TestComputeBaseFreshness:
    def test_zero_days_returns_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        assert SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=0, half_life_days=1095
        ) == 100.0

    def test_negative_days_returns_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        assert SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=-10, half_life_days=1095
        ) == 100.0

    def test_half_life_days_gives_50_percent(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        result = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=1095, half_life_days=1095
        )
        assert abs(result - 50.0) < 0.1

    def test_double_half_life_gives_25_percent(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        result = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=2190, half_life_days=1095
        )
        assert abs(result - 25.0) < 0.1

    def test_invalid_half_life_uses_default(self) -> None:
        from app.ai.skill_decay_analyzer import DEFAULT_HALF_LIFE_DAYS, SkillDecayAnalyzer

        result_default = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=1000, half_life_days=0
        )
        result_explicit = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=1000, half_life_days=DEFAULT_HALF_LIFE_DAYS
        )
        assert result_default == result_explicit

    def test_very_large_days_approaches_zero(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        result = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=100_000, half_life_days=1095
        )
        assert result == 0.0

    def test_score_is_clamped_to_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        result = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=1, half_life_days=1095
        )
        assert result <= 100.0


# ── get_half_life_for_category ────────────────────────────────────


class TestGetHalfLifeForCategory:
    def test_technical_category(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY, SkillDecayAnalyzer

        assert SkillDecayAnalyzer.get_half_life_for_category("technical") == HALF_LIFE_BY_CATEGORY["technical"]

    def test_soft_category(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY, SkillDecayAnalyzer

        assert SkillDecayAnalyzer.get_half_life_for_category("soft") == HALF_LIFE_BY_CATEGORY["soft"]

    def test_language_category(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY, SkillDecayAnalyzer

        assert SkillDecayAnalyzer.get_half_life_for_category("language") == HALF_LIFE_BY_CATEGORY["language"]

    def test_unknown_category_uses_default(self) -> None:
        from app.ai.skill_decay_analyzer import DEFAULT_HALF_LIFE_DAYS, SkillDecayAnalyzer

        assert SkillDecayAnalyzer.get_half_life_for_category("unknown_xyz") == DEFAULT_HALF_LIFE_DAYS

    def test_case_insensitive(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY, SkillDecayAnalyzer

        assert SkillDecayAnalyzer.get_half_life_for_category("TECHNICAL") == HALF_LIFE_BY_CATEGORY["technical"]

    def test_all_known_categories_return_nonzero(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY, SkillDecayAnalyzer

        for category in HALF_LIFE_BY_CATEGORY:
            assert SkillDecayAnalyzer.get_half_life_for_category(category) > 0


# ── classify_decay_rate ────────────────────────────────────────────


class TestClassifyDecayRate:
    def test_fast_for_short_half_life(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        assert SkillDecayAnalyzer.classify_decay_rate(500) == "fast"
        assert SkillDecayAnalyzer.classify_decay_rate(1000) == "fast"

    def test_moderate_for_mid_range(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        assert SkillDecayAnalyzer.classify_decay_rate(1001) == "moderate"
        assert SkillDecayAnalyzer.classify_decay_rate(1500) == "moderate"

    def test_slow_for_upper_range(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        assert SkillDecayAnalyzer.classify_decay_rate(1501) == "slow"
        assert SkillDecayAnalyzer.classify_decay_rate(3000) == "slow"

    def test_stable_for_long_half_life(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        assert SkillDecayAnalyzer.classify_decay_rate(3001) == "stable"
        assert SkillDecayAnalyzer.classify_decay_rate(10000) == "stable"


# ── compute_refresh_urgency ────────────────────────────────────────


class TestComputeRefreshUrgency:
    def test_high_freshness_low_demand_gives_low_urgency(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        urgency = SkillDecayAnalyzer.compute_refresh_urgency(
            freshness_score=100.0, demand_score=0.0
        )
        assert urgency == 0.0

    def test_zero_freshness_full_demand_gives_high_urgency(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        urgency = SkillDecayAnalyzer.compute_refresh_urgency(
            freshness_score=0.0, demand_score=100.0
        )
        assert urgency == 1.0

    def test_default_demand_is_50(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        result_explicit = SkillDecayAnalyzer.compute_refresh_urgency(
            freshness_score=50.0, demand_score=50.0
        )
        result_default = SkillDecayAnalyzer.compute_refresh_urgency(freshness_score=50.0)
        assert result_explicit == result_default

    def test_result_is_clamped_to_0_1(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        for f, d in [(-999.0, 200.0), (200.0, -100.0)]:
            urgency = SkillDecayAnalyzer.compute_refresh_urgency(
                freshness_score=f, demand_score=d
            )
            assert 0.0 <= urgency <= 1.0

    def test_formula_correctness(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        urgency = SkillDecayAnalyzer.compute_refresh_urgency(
            freshness_score=60.0, demand_score=80.0
        )
        expected = (0.4 * 0.6) + (0.8 * 0.4)  # freshness_factor=0.4, demand_factor=0.8
        assert abs(urgency - round(expected, 3)) < 0.001


# ── score_skill_freshness ──────────────────────────────────────────


class TestScoreSkillFreshness:
    @pytest.mark.asyncio
    async def test_happy_path_returns_assessments(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "assessments": [
                    {"skill_name": "Python", "freshness_adjustment": 5.0},
                    {"skill_name": "COBOL", "freshness_adjustment": -15.0},
                ]
            }
            result = await SkillDecayAnalyzer.score_skill_freshness(
                skills_data="Python: 30 days, COBOL: 3000 days",
                experience_summary="10 years backend",
                industry_context="Software",
            )

        assert len(result) == 2
        assert result[0]["skill_name"] == "Python"

    @pytest.mark.asyncio
    async def test_adjustment_clamped_at_plus_20(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "assessments": [{"skill_name": "Python", "freshness_adjustment": 99.0}]
            }
            result = await SkillDecayAnalyzer.score_skill_freshness(
                skills_data="Python",
                experience_summary="5 years",
                industry_context="Tech",
            )

        assert result[0]["freshness_adjustment"] == 20.0

    @pytest.mark.asyncio
    async def test_adjustment_clamped_at_minus_20(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "assessments": [{"skill_name": "COBOL", "freshness_adjustment": -99.0}]
            }
            result = await SkillDecayAnalyzer.score_skill_freshness(
                skills_data="COBOL",
                experience_summary="5 years",
                industry_context="Finance",
            )

        assert result[0]["freshness_adjustment"] == -20.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await SkillDecayAnalyzer.score_skill_freshness(
                skills_data="Python",
                experience_summary="5 years",
                industry_context="Tech",
            )

        assert result == []


# ── analyze_market_demand ──────────────────────────────────────────


class TestAnalyzeMarketDemand:
    @pytest.mark.asyncio
    async def test_happy_path_returns_demands(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "demands": [
                    {"skill_name": "Python", "demand_score": 90.0, "trend_confidence": 0.80},
                    {"skill_name": "COBOL", "demand_score": 20.0, "trend_confidence": 0.60},
                ]
            }
            result = await SkillDecayAnalyzer.analyze_market_demand(
                skills_list="Python, COBOL",
                industry_context="Software",
                experience_level="Senior",
            )

        assert len(result) == 2
        assert result[0]["demand_score"] == 90.0

    @pytest.mark.asyncio
    async def test_confidence_capped_at_0_85(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "demands": [{"skill_name": "Python", "demand_score": 90.0, "trend_confidence": 0.99}]
            }
            result = await SkillDecayAnalyzer.analyze_market_demand(
                skills_list="Python",
                industry_context="Tech",
                experience_level="Senior",
            )

        assert result[0]["trend_confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_demand_score_clamped_above_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "demands": [{"skill_name": "Python", "demand_score": 200.0, "trend_confidence": 0.5}]
            }
            result = await SkillDecayAnalyzer.analyze_market_demand(
                skills_list="Python",
                industry_context="Tech",
                experience_level="Senior",
            )

        assert result[0]["demand_score"] == 100.0

    @pytest.mark.asyncio
    async def test_demand_score_clamped_below_0(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "demands": [{"skill_name": "COBOL", "demand_score": -10.0, "trend_confidence": 0.5}]
            }
            result = await SkillDecayAnalyzer.analyze_market_demand(
                skills_list="COBOL",
                industry_context="Finance",
                experience_level="Senior",
            )

        assert result[0]["demand_score"] == 0.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota exceeded")
            result = await SkillDecayAnalyzer.analyze_market_demand(
                skills_list="Python",
                industry_context="Tech",
                experience_level="Senior",
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_default_region_is_global(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {"demands": []}

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", side_effect=_capture):
            await SkillDecayAnalyzer.analyze_market_demand(
                skills_list="Python",
                industry_context="Tech",
                experience_level="Senior",
            )

        assert "Global" in captured[0]


# ── compute_skill_velocity ────────────────────────────────────────


class TestComputeSkillVelocity:
    @pytest.mark.asyncio
    async def test_happy_path_returns_velocities(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "velocities": [
                    {"skill_name": "Python", "velocity_score": 60.0, "composite_health": 85.0}
                ]
            }
            result = await SkillDecayAnalyzer.compute_skill_velocity(
                freshness_data="Python: 90",
                demand_data="Python: high",
                professional_context="Senior backend engineer",
            )

        assert len(result) == 1
        assert result[0]["velocity_score"] == 60.0

    @pytest.mark.asyncio
    async def test_velocity_score_clamped_above_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "velocities": [{"skill_name": "Python", "velocity_score": 500.0, "composite_health": 50.0}]
            }
            result = await SkillDecayAnalyzer.compute_skill_velocity(
                freshness_data="Python: 90",
                demand_data="Python: high",
                professional_context="Senior engineer",
            )

        assert result[0]["velocity_score"] == 100.0

    @pytest.mark.asyncio
    async def test_velocity_score_clamped_below_minus_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "velocities": [{"skill_name": "COBOL", "velocity_score": -500.0, "composite_health": 10.0}]
            }
            result = await SkillDecayAnalyzer.compute_skill_velocity(
                freshness_data="COBOL: 5",
                demand_data="COBOL: low",
                professional_context="Developer",
            )

        assert result[0]["velocity_score"] == -100.0

    @pytest.mark.asyncio
    async def test_composite_health_clamped_above_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "velocities": [{"skill_name": "Python", "velocity_score": 50.0, "composite_health": 200.0}]
            }
            result = await SkillDecayAnalyzer.compute_skill_velocity(
                freshness_data="Python: 90",
                demand_data="Python: high",
                professional_context="Engineer",
            )

        assert result[0]["composite_health"] == 100.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("rate limit")
            result = await SkillDecayAnalyzer.compute_skill_velocity(
                freshness_data="Python",
                demand_data="high",
                professional_context="engineer",
            )

        assert result == []


# ── generate_reskilling_paths ──────────────────────────────────────


class TestGenerateReskillingPaths:
    @pytest.mark.asyncio
    async def test_happy_path_returns_pathways(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "pathways": [
                    {
                        "target_skill": "Kubernetes",
                        "priority": "critical",
                        "demand_alignment": 0.9,
                        "freshness_gain": 30.0,
                        "estimated_effort_hours": 40,
                    }
                ]
            }
            result = await SkillDecayAnalyzer.generate_reskilling_paths(
                velocity_data="velocity data",
                freshness_data="freshness data",
                demand_data="demand data",
                current_skills="Python, Docker",
                experience_level="Senior",
                industry_context="Cloud computing",
            )

        assert len(result) == 1
        assert result[0]["target_skill"] == "Kubernetes"

    @pytest.mark.asyncio
    async def test_demand_alignment_clamped_above_1(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "pathways": [{"target_skill": "K8s", "demand_alignment": 5.0,
                              "freshness_gain": 20.0, "estimated_effort_hours": 40}]
            }
            result = await SkillDecayAnalyzer.generate_reskilling_paths(
                velocity_data="v", freshness_data="f", demand_data="d",
                current_skills="Python", experience_level="Mid", industry_context="Tech",
            )

        assert result[0]["demand_alignment"] == 1.0

    @pytest.mark.asyncio
    async def test_freshness_gain_clamped_above_100(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "pathways": [{"target_skill": "K8s", "demand_alignment": 0.8,
                              "freshness_gain": 999.0, "estimated_effort_hours": 40}]
            }
            result = await SkillDecayAnalyzer.generate_reskilling_paths(
                velocity_data="v", freshness_data="f", demand_data="d",
                current_skills="Python", experience_level="Mid", industry_context="Tech",
            )

        assert result[0]["freshness_gain"] == 100.0

    @pytest.mark.asyncio
    async def test_effort_hours_clamped_above_500(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "pathways": [{"target_skill": "K8s", "demand_alignment": 0.8,
                              "freshness_gain": 20.0, "estimated_effort_hours": 9999}]
            }
            result = await SkillDecayAnalyzer.generate_reskilling_paths(
                velocity_data="v", freshness_data="f", demand_data="d",
                current_skills="Python", experience_level="Mid", industry_context="Tech",
            )

        assert result[0]["estimated_effort_hours"] == 500

    @pytest.mark.asyncio
    async def test_effort_hours_clamped_below_5(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "pathways": [{"target_skill": "K8s", "demand_alignment": 0.8,
                              "freshness_gain": 20.0, "estimated_effort_hours": 1}]
            }
            result = await SkillDecayAnalyzer.generate_reskilling_paths(
                velocity_data="v", freshness_data="f", demand_data="d",
                current_skills="Python", experience_level="Mid", industry_context="Tech",
            )

        assert result[0]["estimated_effort_hours"] == 5

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

        with patch("app.ai.skill_decay_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.skill_decay_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota exceeded")
            result = await SkillDecayAnalyzer.generate_reskilling_paths(
                velocity_data="v", freshness_data="f", demand_data="d",
                current_skills="Python", experience_level="Mid", industry_context="Tech",
            )

        assert result == []


# ── Constants ────────────────────────────────────────────────────


class TestHalfLifeConstants:
    def test_technical_half_life_is_shortest(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY

        assert HALF_LIFE_BY_CATEGORY["technical"] < HALF_LIFE_BY_CATEGORY["language"]

    def test_soft_skills_last_longer_than_tools(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY

        assert HALF_LIFE_BY_CATEGORY["soft"] > HALF_LIFE_BY_CATEGORY["tool"]

    def test_all_half_lives_are_positive(self) -> None:
        from app.ai.skill_decay_analyzer import HALF_LIFE_BY_CATEGORY

        assert all(v > 0 for v in HALF_LIFE_BY_CATEGORY.values())
