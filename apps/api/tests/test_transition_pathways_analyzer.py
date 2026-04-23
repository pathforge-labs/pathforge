"""
Unit tests for TransitionPathwaysAnalyzer.

Covers:
  - 4 static helpers (compute_skill_overlap, compute_transition_difficulty,
    estimate_timeline_range, compute_transition_confidence)
  - 4 async LLM methods (analyze_transition, generate_skill_bridge,
    create_milestones, compare_roles)
  - 3 private clamping validators (_clamp_transition_analysis,
    _clamp_skill_bridge_entries, _clamp_milestones)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.transition_pathways_analyzer import (
    MAX_TRANSITION_CONFIDENCE,
    TransitionPathwaysAnalyzer,
    _clamp_milestones,
    _clamp_skill_bridge_entries,
    _clamp_transition_analysis,
)

# ── Helpers ────────────────────────────────────────────────────


def _sanitize_passthrough(text: str, *, max_length: int, context: str) -> tuple[str, dict]:
    return text[:max_length], {}


def _patch_sanitize():
    return patch(
        "app.ai.transition_pathways_analyzer.sanitize_user_text",
        side_effect=_sanitize_passthrough,
    )


def _patch_complete_json(return_value):
    return patch(
        "app.ai.transition_pathways_analyzer.complete_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── compute_skill_overlap ──────────────────────────────────────


class TestComputeSkillOverlap:
    def test_full_overlap_returns_100(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_skill_overlap(
            current_skills=["Python", "FastAPI"],
            target_skills=["Python", "FastAPI"],
        )
        assert result == 100.0

    def test_no_overlap_returns_zero(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_skill_overlap(
            current_skills=["Java", "Spring"],
            target_skills=["Python", "FastAPI"],
        )
        assert result == 0.0

    def test_partial_overlap_is_correct(self) -> None:
        # 1 of 2 target skills → 50%
        result = TransitionPathwaysAnalyzer.compute_skill_overlap(
            current_skills=["Python", "Java"],
            target_skills=["Python", "FastAPI"],
        )
        assert abs(result - 50.0) < 0.01

    def test_empty_target_skills_returns_zero(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_skill_overlap(
            current_skills=["Python"],
            target_skills=[],
        )
        assert result == 0.0

    def test_empty_current_skills_returns_zero(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_skill_overlap(
            current_skills=[],
            target_skills=["Python"],
        )
        assert result == 0.0

    def test_case_insensitive_matching(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_skill_overlap(
            current_skills=["PYTHON", "FastAPI"],
            target_skills=["python", "fastapi"],
        )
        assert result == 100.0


# ── compute_transition_difficulty ─────────────────────────────


class TestComputeTransitionDifficulty:
    def test_high_overlap_no_gap_is_easy(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=80.0, seniority_gap=1,
        )
        assert result == "easy"

    def test_medium_overlap_small_gap_is_moderate(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=50.0, seniority_gap=2,
        )
        assert result == "moderate"

    def test_low_overlap_medium_gap_is_challenging(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=25.0, seniority_gap=2,
        )
        assert result == "challenging"

    def test_very_low_overlap_large_gap_is_extreme(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=10.0, seniority_gap=5,
        )
        assert result == "extreme"

    def test_70_overlap_at_boundary(self) -> None:
        assert TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=70.0, seniority_gap=1,
        ) == "easy"

    def test_45_overlap_with_gap_2(self) -> None:
        assert TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=45.0, seniority_gap=2,
        ) == "moderate"

    def test_gap_3_or_less_with_low_overlap_is_challenging(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_difficulty(
            skill_overlap_percent=15.0, seniority_gap=3,
        )
        assert result == "challenging"


# ── estimate_timeline_range ────────────────────────────────────


class TestEstimateTimelineRange:
    def test_easy_with_no_extra_skills(self) -> None:
        opt, real, cons = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="easy", skills_to_acquire=2,
        )
        assert opt == 2 and real == 4 and cons == 6

    def test_moderate_base_range(self) -> None:
        opt, real, cons = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="moderate", skills_to_acquire=2,
        )
        assert opt == 4 and real == 8 and cons == 12

    def test_challenging_base_range(self) -> None:
        opt, real, cons = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="challenging", skills_to_acquire=2,
        )
        assert opt == 8 and real == 14 and cons == 20

    def test_extreme_base_range(self) -> None:
        opt, real, cons = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="extreme", skills_to_acquire=2,
        )
        assert opt == 14 and real == 22 and cons == 30

    def test_extra_skills_increase_timeline(self) -> None:
        _opt_base, real_base, _cons_base = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="moderate", skills_to_acquire=3,
        )
        _opt_extra, real_extra, _cons_extra = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="moderate", skills_to_acquire=5,
        )
        assert real_extra > real_base

    def test_unknown_difficulty_uses_default(self) -> None:
        opt, real, cons = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="unknown", skills_to_acquire=0,
        )
        assert opt == 6 and real == 12 and cons == 18

    def test_optimistic_lte_realistic_lte_conservative(self) -> None:
        opt, real, cons = TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="challenging", skills_to_acquire=8,
        )
        assert opt <= real <= cons


# ── compute_transition_confidence ─────────────────────────────


class TestComputeTransitionConfidence:
    def test_basic_formula(self) -> None:
        # skill_factor = 0.6, llm = 0.7 (capped at 0.85), market = 0.5
        # 0.4*0.6 + 0.4*0.7 + 0.2*0.5 = 0.24 + 0.28 + 0.10 = 0.62
        result = TransitionPathwaysAnalyzer.compute_transition_confidence(
            skill_overlap_percent=60.0,
            llm_confidence=0.7,
            market_demand_score=50.0,
        )
        assert abs(result - 0.620) < 0.001

    def test_capped_at_max_confidence(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_confidence(
            skill_overlap_percent=100.0,
            llm_confidence=1.0,
            market_demand_score=100.0,
        )
        assert result == MAX_TRANSITION_CONFIDENCE

    def test_zero_inputs_returns_zero(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_confidence(
            skill_overlap_percent=0.0,
            llm_confidence=0.0,
            market_demand_score=0.0,
        )
        assert result == 0.0

    def test_default_market_demand_is_50(self) -> None:
        result = TransitionPathwaysAnalyzer.compute_transition_confidence(
            skill_overlap_percent=60.0,
            llm_confidence=0.7,
        )
        # same as test_basic_formula
        assert abs(result - 0.620) < 0.001


# ── _clamp_transition_analysis ─────────────────────────────────


class TestClampTransitionAnalysis:
    def test_confidence_capped_at_max(self) -> None:
        data = {"confidence_score": 9.9}
        _clamp_transition_analysis(data)
        assert data["confidence_score"] == MAX_TRANSITION_CONFIDENCE

    def test_success_probability_capped_at_max(self) -> None:
        data = {"success_probability": 5.0}
        _clamp_transition_analysis(data)
        assert data["success_probability"] == MAX_TRANSITION_CONFIDENCE

    def test_skill_overlap_clamped_0_to_100(self) -> None:
        data = {"skill_overlap_percent": 150.0}
        _clamp_transition_analysis(data)
        assert data["skill_overlap_percent"] == 100.0

    def test_estimated_duration_enforces_minimum_1(self) -> None:
        data = {"estimated_duration_months": 0}
        _clamp_transition_analysis(data)
        assert data["estimated_duration_months"] == 1

    def test_timeline_ordering_enforced(self) -> None:
        # If conservative < realistic (reversed), should be sorted
        data = {
            "optimistic_months": 12,
            "realistic_months": 6,
            "conservative_months": 3,
        }
        _clamp_transition_analysis(data)
        assert data["optimistic_months"] <= data["realistic_months"] <= data["conservative_months"]

    def test_invalid_difficulty_becomes_moderate(self) -> None:
        data = {"difficulty": "impossible"}
        _clamp_transition_analysis(data)
        assert data["difficulty"] == "moderate"

    def test_valid_difficulty_preserved(self) -> None:
        for diff in ("easy", "moderate", "challenging", "extreme"):
            data = {"difficulty": diff}
            _clamp_transition_analysis(data)
            assert data["difficulty"] == diff

    def test_negative_skills_to_acquire_becomes_zero(self) -> None:
        data = {"skills_to_acquire_count": -5}
        _clamp_transition_analysis(data)
        assert data["skills_to_acquire_count"] == 0


# ── _clamp_skill_bridge_entries ────────────────────────────────


class TestClampSkillBridgeEntries:
    def test_invalid_priority_becomes_medium(self) -> None:
        skills = [{"priority": "urgent"}]
        _clamp_skill_bridge_entries(skills)
        assert skills[0]["priority"] == "medium"

    def test_valid_priorities_preserved(self) -> None:
        for priority in ("critical", "high", "medium", "nice_to_have"):
            s = [{"priority": priority}]
            _clamp_skill_bridge_entries(s)
            assert s[0]["priority"] == priority

    def test_invalid_category_becomes_technical(self) -> None:
        skills = [{"category": "unknown_category"}]
        _clamp_skill_bridge_entries(skills)
        assert skills[0]["category"] == "technical"

    def test_estimated_weeks_clamped_1_to_104(self) -> None:
        skills = [{"estimated_weeks": 200}]
        _clamp_skill_bridge_entries(skills)
        assert skills[0]["estimated_weeks"] == 104

    def test_estimated_weeks_below_1_becomes_1(self) -> None:
        skills = [{"estimated_weeks": 0}]
        _clamp_skill_bridge_entries(skills)
        assert skills[0]["estimated_weeks"] == 1

    def test_impact_clamped_0_to_0_15(self) -> None:
        skills = [{"impact_on_confidence": 0.5}]
        _clamp_skill_bridge_entries(skills)
        assert skills[0]["impact_on_confidence"] == 0.15

    def test_none_weeks_stays_none(self) -> None:
        skills = [{"estimated_weeks": None}]
        _clamp_skill_bridge_entries(skills)
        assert skills[0]["estimated_weeks"] is None


# ── _clamp_milestones ──────────────────────────────────────────


class TestClampMilestones:
    def test_invalid_phase_becomes_preparation(self) -> None:
        milestones = [{"phase": "unknown_phase"}]
        _clamp_milestones(milestones)
        assert milestones[0]["phase"] == "preparation"

    def test_valid_phases_preserved(self) -> None:
        for phase in ("preparation", "skill_building", "transition", "establishment"):
            m = [{"phase": phase}]
            _clamp_milestones(m)
            assert m[0]["phase"] == phase

    def test_target_week_clamped_1_to_156(self) -> None:
        milestones = [{"target_week": 500}]
        _clamp_milestones(milestones)
        assert milestones[0]["target_week"] == 156

    def test_target_week_below_1_becomes_1(self) -> None:
        milestones = [{"target_week": 0}]
        _clamp_milestones(milestones)
        assert milestones[0]["target_week"] == 1

    def test_order_index_assigned_from_position(self) -> None:
        milestones = [{"phase": "preparation"}, {"phase": "transition"}]
        _clamp_milestones(milestones)
        assert milestones[0]["order_index"] == 0
        assert milestones[1]["order_index"] == 1

    def test_existing_order_index_preserved(self) -> None:
        milestones = [{"phase": "preparation", "order_index": 42}]
        _clamp_milestones(milestones)
        assert milestones[0]["order_index"] == 42


# ── analyze_transition (LLM) ──────────────────────────────────


class TestAnalyzeTransition:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        response = {
            "confidence_score": 0.7,
            "success_probability": 0.65,
            "skill_overlap_percent": 60.0,
            "estimated_duration_months": 9,
            "difficulty": "moderate",
        }
        with _patch_sanitize(), _patch_complete_json(response):
            result = await TransitionPathwaysAnalyzer.analyze_transition(
                from_role="Backend Engineer",
                to_role="Data Scientist",
                seniority_level="senior",
                location="Amsterdam",
                industry="Technology",
                years_experience=7,
                current_skills="Python, FastAPI",
            )
        assert isinstance(result, dict)
        assert result["confidence_score"] <= MAX_TRANSITION_CONFIDENCE

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_dict(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.transition_pathways_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await TransitionPathwaysAnalyzer.analyze_transition(
                from_role="Dev",
                to_role="Manager",
                seniority_level="mid",
                location="Berlin",
                industry="Tech",
                years_experience=5,
                current_skills="Python",
            )
        assert result == {}


# ── generate_skill_bridge (LLM) ───────────────────────────────


class TestGenerateSkillBridge:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        skills = [{"priority": "critical", "category": "technical", "skill_name": "ML"}]
        with _patch_sanitize(), _patch_complete_json(skills):
            result = await TransitionPathwaysAnalyzer.generate_skill_bridge(
                current_skills="Python, FastAPI",
                from_role="Backend Engineer",
                to_role="Data Scientist",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.transition_pathways_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await TransitionPathwaysAnalyzer.generate_skill_bridge(
                current_skills="Python",
                from_role="Dev",
                to_role="Manager",
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_priority_clamped(self) -> None:
        skills = [{"priority": "urgent", "category": "technical"}]
        with _patch_sanitize(), _patch_complete_json(skills):
            result = await TransitionPathwaysAnalyzer.generate_skill_bridge(
                current_skills="Python",
                from_role="Dev",
                to_role="Lead",
            )
        assert result[0]["priority"] == "medium"


# ── create_milestones (LLM) ───────────────────────────────────


class TestCreateMilestones:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        milestones = [{"phase": "preparation", "target_week": 4, "title": "Start"}]
        with _patch_sanitize(), _patch_complete_json(milestones):
            result = await TransitionPathwaysAnalyzer.create_milestones(
                from_role="Backend Engineer",
                to_role="Data Scientist",
                skills_to_acquire="ML, Statistics",
                estimated_months=9,
                difficulty="moderate",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.transition_pathways_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await TransitionPathwaysAnalyzer.create_milestones(
                from_role="Dev",
                to_role="Lead",
                skills_to_acquire="Management",
                estimated_months=6,
                difficulty="easy",
            )
        assert result == []


# ── compare_roles (LLM) ───────────────────────────────────────


class TestCompareRoles:
    @pytest.mark.asyncio
    async def test_returns_list_on_success(self) -> None:
        comparisons = [{"dimension": "salary", "current_value": 80000, "target_value": 95000}]
        with _patch_sanitize(), _patch_complete_json(comparisons):
            result = await TransitionPathwaysAnalyzer.compare_roles(
                from_role="Backend Engineer",
                to_role="Data Scientist",
                location="Amsterdam",
                seniority_level="senior",
                industry="Technology",
            )
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.core.llm import LLMError

        with _patch_sanitize(), patch(
            "app.ai.transition_pathways_analyzer.complete_json",
            new_callable=AsyncMock,
            side_effect=LLMError("fail"),
        ):
            result = await TransitionPathwaysAnalyzer.compare_roles(
                from_role="Dev",
                to_role="Manager",
                location="Berlin",
                seniority_level="mid",
                industry="Tech",
            )
        assert result == []
