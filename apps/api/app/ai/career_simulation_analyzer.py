"""
PathForge AI Engine — Career Simulation Analyzer
====================================================
AI pipeline for the Career Simulation Engine™ — the industry's
first consumer-grade "what-if" career planning tool.

4 LLM methods:
    1. analyze_scenario — Confidence, feasibility, salary impact
    2. project_outcomes — Multi-dimension projections
    3. generate_recommendations — Prioritized action steps
    4. compare_scenarios — Multi-scenario ranking

4 Static helpers:
    1. compute_scenario_confidence — Composite capped at 0.85
    2. compute_roi_score — Return-on-investment calculation
    3. compute_feasibility_rating — Skill gap → feasibility %
    4. normalize_salary_delta — CoL-aware salary normalization

3 Clamping validators:
    1. _clamp_simulation_analysis — Cap confidence, validate enums
    2. _clamp_outcomes — Ensure delta consistency
    3. _clamp_recommendations — Validate priorities, cap weeks

All methods follow the established PathForge analyzer pattern:
    - Static async methods for LLM calls
    - complete_json for structured LLM output
    - sanitize_user_text before all LLM calls
    - Timing + structured logging
    - Safe fallbacks on error
"""

import logging
import time
from typing import Any

from app.ai.career_simulation_prompts import (
    OUTCOME_PROJECTION_PROMPT,
    PROMPT_VERSION,
    RECOMMENDATION_GENERATION_PROMPT,
    SCENARIO_ANALYSIS_PROMPT,
    SCENARIO_COMPARISON_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────

MAX_SIMULATION_CONFIDENCE = 0.85
"""Hard ceiling for LLM-generated simulation confidence scores."""

MAX_RECOMMENDATION_WEEKS = 104
"""Maximum estimated weeks for a single recommendation (2 years)."""


class CareerSimulationAnalyzer:
    """
    AI pipeline for Career Simulation Engine™ analysis.

    Each method performs a focused LLM call and returns
    validated structured data. All simulation projections
    include transparent factor breakdowns for explainability.
    """

    # ── Static Helpers ─────────────────────────────────────────

    @staticmethod
    def compute_scenario_confidence(
        *,
        skill_overlap_percent: float,
        llm_confidence: float,
        market_demand_score: float = 50.0,
        data_quality_factor: float = 0.5,
    ) -> float:
        """
        Compute composite scenario confidence, hard-capped at 0.85.

        Formula:
            weighted = 0.30 × skill_factor
                     + 0.30 × llm
                     + 0.20 × market_factor
                     + 0.20 × data_quality
            clamped to [0.0, MAX_SIMULATION_CONFIDENCE]

        Args:
            skill_overlap_percent: Skill overlap (0-100).
            llm_confidence: Raw LLM confidence (0-1).
            market_demand_score: Market demand (0-100, default 50).
            data_quality_factor: Available data quality (0-1, default 0.5).

        Returns:
            Capped confidence from 0.0 to 0.85.
        """
        skill_factor = min(1.0, max(0.0, skill_overlap_percent / 100.0))
        llm_factor = max(0.0, min(MAX_SIMULATION_CONFIDENCE, llm_confidence))
        market_factor = min(1.0, max(0.0, market_demand_score / 100.0))
        data_factor = min(1.0, max(0.0, data_quality_factor))

        weighted = (
            0.30 * skill_factor
            + 0.30 * llm_factor
            + 0.20 * market_factor
            + 0.20 * data_factor
        )

        return float(
            max(0.0, min(MAX_SIMULATION_CONFIDENCE, round(weighted, 3)))
        )

    @staticmethod
    def compute_roi_score(
        *,
        salary_delta_annual: float,
        investment_months: int,
        monthly_opportunity_cost: float = 0.0,
    ) -> float:
        """
        Calculate return-on-investment for a career simulation.

        Formula:
            total_cost = investment_months × monthly_opportunity_cost
            ROI = (salary_delta_annual / max(total_cost, 1)) × 100

        Positive ROI indicates the scenario pays off financially.
        Negative ROI indicates a financial cost (may still be
        worthwhile for non-financial reasons).

        Args:
            salary_delta_annual: Projected annual salary change (EUR).
            investment_months: Time investment required (months).
            monthly_opportunity_cost: Monthly cost during transition.

        Returns:
            ROI percentage. Can be negative.
        """
        if investment_months <= 0:
            return 0.0

        total_cost = investment_months * max(0.0, monthly_opportunity_cost)
        if total_cost <= 0:
            # No cost → use months as proxy denominator
            return round(salary_delta_annual / max(investment_months, 1), 2)

        return round((salary_delta_annual / total_cost) * 100.0, 2)

    @staticmethod
    def compute_feasibility_rating(
        *,
        skill_gap_count: int,
        estimated_months: int,
        confidence_score: float = 0.5,
    ) -> float:
        """
        Map skill gap count and timeline to feasibility (0-100).

        Lower skill gaps and shorter timelines increase feasibility.
        Confidence score provides an LLM-informed adjustment.

        Args:
            skill_gap_count: Number of skills to acquire.
            estimated_months: Estimated timeline in months.
            confidence_score: Simulation confidence (0-0.85).

        Returns:
            Feasibility rating from 0.0 to 100.0.
        """
        # Base feasibility inversely proportional to gap count
        if skill_gap_count == 0:
            gap_factor = 100.0
        elif skill_gap_count <= 2:
            gap_factor = 85.0
        elif skill_gap_count <= 5:
            gap_factor = 65.0
        elif skill_gap_count <= 10:
            gap_factor = 40.0
        else:
            gap_factor = 20.0

        # Timeline factor: shorter = more feasible
        if estimated_months <= 3:
            timeline_factor = 1.0
        elif estimated_months <= 6:
            timeline_factor = 0.9
        elif estimated_months <= 12:
            timeline_factor = 0.75
        elif estimated_months <= 24:
            timeline_factor = 0.6
        else:
            timeline_factor = 0.4

        # Confidence adjustment
        confidence_boost = (confidence_score / MAX_SIMULATION_CONFIDENCE) * 15.0

        feasibility = (gap_factor * timeline_factor) + confidence_boost
        return float(max(0.0, min(100.0, round(feasibility, 1))))

    @staticmethod
    def normalize_salary_delta(
        *,
        salary_delta: float,
        source_col_index: float = 100.0,
        target_col_index: float = 100.0,
    ) -> float:
        """
        Normalize salary delta accounting for cost-of-living differences.

        Uses a simple CoL index ratio to adjust raw salary deltas
        for geographic moves.

        Args:
            salary_delta: Raw salary difference (EUR).
            source_col_index: Source location CoL index (100 = baseline).
            target_col_index: Target location CoL index (100 = baseline).

        Returns:
            CoL-adjusted salary delta.
        """
        if source_col_index <= 0 or target_col_index <= 0:
            return salary_delta

        col_ratio = source_col_index / target_col_index
        return round(salary_delta * col_ratio, 2)

    # ── LLM: Scenario Analysis ─────────────────────────────────

    @staticmethod
    async def analyze_scenario(
        *,
        scenario_type: str,
        current_role: str,
        current_seniority: str,
        current_industry: str,
        current_location: str,
        skills: str,
        years_experience: int,
        scenario_parameters: str,
    ) -> dict[str, Any]:
        """
        Analyze a what-if career scenario via LLM intelligence.

        Produces confidence score, feasibility rating, salary impact,
        and timeline estimate with transparent factor breakdown.

        Args:
            scenario_type: Type of scenario (role_transition, etc.).
            current_role: User's current role title.
            current_seniority: User's current seniority level.
            current_industry: User's current industry.
            current_location: User's current location.
            skills: Formatted current skills string.
            years_experience: Total professional years.
            scenario_parameters: Formatted scenario-specific params.

        Returns:
            Dict with analysis details or empty dict on error.
        """
        clean_role, _ = sanitize_user_text(
            current_role, max_length=255, context="sim_current_role",
        )
        clean_seniority, _ = sanitize_user_text(
            current_seniority, max_length=100, context="sim_seniority",
        )
        clean_industry, _ = sanitize_user_text(
            current_industry, max_length=255, context="sim_industry",
        )
        clean_location, _ = sanitize_user_text(
            current_location, max_length=255, context="sim_location",
        )
        clean_skills, _ = sanitize_user_text(
            skills, max_length=3000, context="sim_skills",
        )
        clean_params, _ = sanitize_user_text(
            scenario_parameters, max_length=2000, context="sim_params",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SCENARIO_ANALYSIS_PROMPT.format(
                    version=PROMPT_VERSION,
                    scenario_type=scenario_type,
                    current_role=clean_role,
                    current_seniority=clean_seniority,
                    current_industry=clean_industry,
                    current_location=clean_location,
                    skills=clean_skills,
                    years_experience=years_experience,
                    scenario_parameters=clean_params,
                ),
                system_prompt="You are the PathForge Career Simulation Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=2048,
            )

            _clamp_simulation_analysis(data)

            elapsed = time.monotonic() - start
            logger.info(
                "Scenario analyzed: type=%s — "
                "confidence=%.2f, feasibility=%.1f (%.2fs)",
                scenario_type,
                data.get("confidence_score", 0),
                data.get("feasibility_rating", 0),
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Scenario analysis failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}

    # ── LLM: Outcome Projection ────────────────────────────────

    @staticmethod
    async def project_outcomes(
        *,
        scenario_type: str,
        current_role: str,
        scenario_parameters: str,
        confidence_score: float,
        reasoning: str,
    ) -> list[dict[str, Any]]:
        """
        Project dimensional outcomes for a career scenario.

        Produces projections across salary, demand, growth,
        skill gap, work-life balance, and job security.

        Args:
            scenario_type: Type of scenario.
            current_role: User's current role.
            scenario_parameters: Formatted scenario params.
            confidence_score: Analysis confidence score.
            reasoning: Analysis reasoning text.

        Returns:
            List of outcome dicts or empty list on error.
        """
        clean_role, _ = sanitize_user_text(
            current_role, max_length=255, context="outcome_role",
        )
        clean_params, _ = sanitize_user_text(
            scenario_parameters, max_length=2000, context="outcome_params",
        )
        clean_reasoning, _ = sanitize_user_text(
            reasoning or "No reasoning provided",
            max_length=2000,
            context="outcome_reasoning",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=OUTCOME_PROJECTION_PROMPT.format(
                    version=PROMPT_VERSION,
                    scenario_type=scenario_type,
                    current_role=clean_role,
                    scenario_parameters=clean_params,
                    confidence_score=confidence_score,
                    reasoning=clean_reasoning,
                ),
                system_prompt="You are the PathForge Career Simulation Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=2048,
            )

            outcomes: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("outcomes", [])
            )

            _clamp_outcomes(outcomes)

            elapsed = time.monotonic() - start
            logger.info(
                "Outcomes projected: %d dimensions (%.2fs)",
                len(outcomes),
                elapsed,
            )
            return outcomes

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Outcome projection failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: Recommendation Generation ─────────────────────────

    @staticmethod
    async def generate_recommendations(
        *,
        scenario_type: str,
        current_role: str,
        scenario_parameters: str,
        confidence_score: float,
        reasoning: str,
        outcomes_summary: str,
    ) -> list[dict[str, Any]]:
        """
        Generate prioritized action recommendations for a simulation.

        Produces 3-6 specific, actionable recommendations with
        priority levels and time estimates.

        Args:
            scenario_type: Type of scenario.
            current_role: User's current role.
            scenario_parameters: Formatted scenario params.
            confidence_score: Analysis confidence score.
            reasoning: Analysis reasoning text.
            outcomes_summary: Summary of projected outcomes.

        Returns:
            List of recommendation dicts or empty list on error.
        """
        clean_role, _ = sanitize_user_text(
            current_role, max_length=255, context="rec_role",
        )
        clean_params, _ = sanitize_user_text(
            scenario_parameters, max_length=2000, context="rec_params",
        )
        clean_reasoning, _ = sanitize_user_text(
            reasoning or "No reasoning provided",
            max_length=2000,
            context="rec_reasoning",
        )
        clean_outcomes, _ = sanitize_user_text(
            outcomes_summary or "No outcomes available",
            max_length=3000,
            context="rec_outcomes",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=RECOMMENDATION_GENERATION_PROMPT.format(
                    version=PROMPT_VERSION,
                    scenario_type=scenario_type,
                    current_role=clean_role,
                    scenario_parameters=clean_params,
                    confidence_score=confidence_score,
                    reasoning=clean_reasoning,
                    outcomes_summary=clean_outcomes,
                ),
                system_prompt="You are the PathForge Career Simulation Engine.",
                tier=LLMTier.FAST,
                temperature=0.2,
                max_tokens=2048,
            )

            recommendations: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("recommendations", [])
            )

            _clamp_recommendations(recommendations)

            elapsed = time.monotonic() - start
            logger.info(
                "Recommendations generated: %d items (%.2fs)",
                len(recommendations),
                elapsed,
            )
            return recommendations

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Recommendation generation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: Scenario Comparison ───────────────────────────────

    @staticmethod
    async def compare_scenarios(
        *,
        current_role: str,
        current_seniority: str,
        current_industry: str,
        scenarios_json: str,
    ) -> dict[str, Any]:
        """
        Compare multiple career scenarios and provide ranked analysis.

        Produces a ranked list of scenario IDs and trade-off analysis
        considering confidence, ROI, feasibility, and timeline.

        Args:
            current_role: User's current role.
            current_seniority: User's current seniority.
            current_industry: User's current industry.
            scenarios_json: JSON string of scenarios to compare.

        Returns:
            Dict with ranking and analysis or empty dict on error.
        """
        clean_role, _ = sanitize_user_text(
            current_role, max_length=255, context="compare_role",
        )
        clean_seniority, _ = sanitize_user_text(
            current_seniority, max_length=100, context="compare_seniority",
        )
        clean_industry, _ = sanitize_user_text(
            current_industry, max_length=255, context="compare_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SCENARIO_COMPARISON_PROMPT.format(
                    version=PROMPT_VERSION,
                    current_role=clean_role,
                    current_seniority=clean_seniority,
                    current_industry=clean_industry,
                    scenarios_json=scenarios_json,
                ),
                system_prompt="You are the PathForge Career Simulation Engine.",
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=2048,
            )

            elapsed = time.monotonic() - start
            logger.info(
                "Scenario comparison completed (%.2fs)",
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Scenario comparison failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}


# ── Private Validation Helpers ─────────────────────────────────


def _clamp_simulation_analysis(data: dict[str, Any]) -> None:
    """Validate and clamp simulation analysis fields in-place."""
    # Cap confidence at MAX
    confidence = data.get("confidence_score", 0.5)
    data["confidence_score"] = max(
        0.0, min(MAX_SIMULATION_CONFIDENCE, float(confidence))
    )

    # Cap feasibility at 100
    feasibility = data.get("feasibility_rating", 50.0)
    data["feasibility_rating"] = max(0.0, min(100.0, float(feasibility)))

    # Ensure positive duration
    months = data.get("estimated_months", 6)
    data["estimated_months"] = max(1, min(120, int(months)))

    # Clamp salary impact to reasonable range (-100% to +200%)
    salary = data.get("salary_impact_percent", 0.0)
    data["salary_impact_percent"] = max(-100.0, min(200.0, float(salary)))

    # Ensure factors is a dict
    if not isinstance(data.get("factors"), dict):
        data["factors"] = {}


def _clamp_outcomes(outcomes: list[dict[str, Any]]) -> None:
    """Validate and clamp outcome projection fields in-place."""
    for outcome in outcomes:
        # Ensure dimension is a non-empty string
        if not outcome.get("dimension"):
            outcome["dimension"] = "unknown"

        # Ensure numeric fields are floats
        for field in ("current_value", "projected_value", "delta"):
            value = outcome.get(field, 0.0)
            try:
                outcome[field] = float(value)
            except (ValueError, TypeError):
                outcome[field] = 0.0

        # Recalculate delta for consistency
        outcome["delta"] = round(
            outcome["projected_value"] - outcome["current_value"], 2
        )


def _clamp_recommendations(recommendations: list[dict[str, Any]]) -> None:
    """Validate and clamp recommendation fields in-place."""
    valid_priorities = {"critical", "high", "medium", "nice_to_have"}

    for index, rec in enumerate(recommendations):
        # Validate priority
        if rec.get("priority", "").lower() not in valid_priorities:
            rec["priority"] = "medium"

        # Ensure title exists
        if not rec.get("title"):
            rec["title"] = "Untitled recommendation"

        # Clamp estimated weeks
        weeks = rec.get("estimated_weeks")
        if weeks is not None:
            rec["estimated_weeks"] = max(
                1, min(MAX_RECOMMENDATION_WEEKS, int(weeks))
            )

        # Ensure order index
        rec["order_index"] = rec.get("order_index", index)
