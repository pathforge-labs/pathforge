"""
PathForge AI Engine — Salary Intelligence Engine™ Analyzer
============================================================
AI pipeline for the Salary Intelligence Engine system.

4 LLM methods:
    1. analyze_salary_range — Personalized salary range estimation
    2. analyze_skill_impacts — Per-skill salary impact quantification
    3. project_trajectory — Salary trajectory with projections
    4. simulate_scenario — What-if salary scenario simulation

4 Static helpers:
    1. compute_market_percentile — Position in salary distribution
    2. compute_confidence_interval — Statistical confidence from data
    3. compute_salary_delta — Delta between two salary estimates
    4. normalize_currency — Currency conversion with fallback rates

All methods follow the established analyzer pattern:
    - Static async methods for LLM calls
    - complete_json for structured LLM output
    - sanitize_user_text before all LLM calls
    - Timing + structured logging
    - Safe fallbacks on error
"""

import logging
import time
from typing import Any

from app.ai.salary_intelligence_prompts import (
    SALARY_INTELLIGENCE_SYSTEM_PROMPT,
    SALARY_RANGE_USER_PROMPT,
    SALARY_SCENARIO_USER_PROMPT,
    SALARY_TRAJECTORY_USER_PROMPT,
    SKILL_IMPACTS_USER_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text
from app.schemas.salary_intelligence import MAX_LLM_CONFIDENCE

logger = logging.getLogger(__name__)

# ── Currency Conversion Fallback Rates ─────────────────────────
# Conservative rates for offline/fallback scenarios.
# Production would use a real-time API; these are safety nets.

FALLBACK_RATES_TO_EUR: dict[str, float] = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.17,
    "CHF": 1.05,
}

FALLBACK_RATES_FROM_EUR: dict[str, float] = {
    "EUR": 1.0,
    "USD": 1.09,
    "GBP": 0.86,
    "CHF": 0.95,
}


class SalaryIntelligenceAnalyzer:
    """
    AI pipeline for Salary Intelligence Engine™ analysis.

    Each method performs a focused LLM call and returns
    validated structured data. All salary estimates include
    transparent factor breakdowns for explainability.
    """

    # ── Static Helpers ─────────────────────────────────────────

    @staticmethod
    def compute_market_percentile(
        *,
        estimated_median: float,
        market_min: float,
        market_max: float,
    ) -> float:
        """
        Compute where a salary sits in the market distribution.

        Uses linear interpolation between market min/max.
        Clamped to 0-100 range.

        Args:
            estimated_median: The user's estimated median salary.
            market_min: Bottom of market range for similar roles.
            market_max: Top of market range for similar roles.

        Returns:
            Percentile from 0.0 to 100.0.
        """
        if market_max <= market_min:
            return 50.0
        percentile = (
            (estimated_median - market_min) / (market_max - market_min)
        ) * 100.0
        return max(0.0, min(100.0, round(percentile, 1)))

    @staticmethod
    def compute_confidence_interval(
        *,
        data_points_count: int,
        base_confidence: float = 0.5,
    ) -> float:
        """
        Adjust confidence based on number of data points.

        More data points → higher confidence, capped at 0.85.

        Args:
            data_points_count: Number of supporting data points.
            base_confidence: Starting confidence from LLM.

        Returns:
            Adjusted confidence from 0.0 to 0.85.
        """
        if data_points_count <= 0:
            return max(0.1, base_confidence * 0.5)

        # Logarithmic scaling: more data → diminishing confidence boost
        data_boost = min(0.3, 0.05 * (data_points_count ** 0.5))
        adjusted = base_confidence + data_boost
        return float(max(0.1, min(MAX_LLM_CONFIDENCE, round(adjusted, 3))))

    @staticmethod
    def compute_salary_delta(
        *,
        current_median: float,
        projected_median: float,
    ) -> tuple[float, float]:
        """
        Calculate absolute and percentage delta between salaries.

        Args:
            current_median: Current salary estimate.
            projected_median: Projected salary after change.

        Returns:
            Tuple of (delta_amount, delta_percent).
        """
        delta_amount = round(projected_median - current_median, 2)
        if current_median > 0:
            delta_percent = round(
                (delta_amount / current_median) * 100.0, 2
            )
        else:
            delta_percent = 0.0
        return delta_amount, delta_percent

    @staticmethod
    def normalize_currency(
        *,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> float:
        """
        Convert between supported currencies using fallback rates.

        In production, this would call a real-time FX API.
        Fallback rates ensure the system never fails on currency.

        Args:
            amount: Amount to convert.
            from_currency: Source currency code.
            to_currency: Target currency code.

        Returns:
            Converted amount.
        """
        if from_currency == to_currency:
            return amount

        # Convert to EUR first, then to target
        to_eur_rate = FALLBACK_RATES_TO_EUR.get(
            from_currency.upper(), 1.0
        )
        from_eur_rate = FALLBACK_RATES_FROM_EUR.get(
            to_currency.upper(), 1.0
        )
        converted = amount * to_eur_rate * from_eur_rate
        return round(converted, 2)

    # ── LLM: Salary Range Estimation ──────────────────────────

    @staticmethod
    async def analyze_salary_range(
        *,
        role_title: str,
        location: str,
        seniority_level: str,
        industry: str,
        years_of_experience: int,
        skills_data: str,
        experience_summary: str,
        currency: str = "EUR",
    ) -> dict[str, Any]:
        """
        Estimate personalized salary range via LLM intelligence.

        Multi-factor model:
            Salary = Base(role, location, seniority)
                   × SkillPremium(skills)
                   × ExperienceMultiplier(years)
                   × MarketCondition(supply/demand)

        Args:
            role_title: Target/current role title.
            location: Geographic location.
            seniority_level: Career seniority level.
            industry: Primary industry.
            years_of_experience: Total professional years.
            skills_data: Formatted skills portfolio.
            experience_summary: Career experience narrative.
            currency: Target currency for estimates.

        Returns:
            Dict with estimate details or empty dict on error.
        """
        clean_role, _ = sanitize_user_text(
            role_title, max_length=255, context="salary_role",
        )
        clean_location, _ = sanitize_user_text(
            location, max_length=255, context="salary_location",
        )
        clean_industry, _ = sanitize_user_text(
            industry, max_length=255, context="salary_industry",
        )
        clean_skills, _ = sanitize_user_text(
            skills_data, max_length=3000, context="salary_skills",
        )
        clean_exp, _ = sanitize_user_text(
            experience_summary, max_length=2000, context="salary_experience",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SALARY_RANGE_USER_PROMPT.format(
                    role_title=clean_role,
                    location=clean_location,
                    seniority_level=seniority_level,
                    industry=clean_industry,
                    years_of_experience=years_of_experience,
                    skills_data=clean_skills,
                    experience_summary=clean_exp,
                    currency=currency,
                ),
                system_prompt=SALARY_INTELLIGENCE_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=2048,
            )

            # Validate and clamp essential fields
            _clamp_salary_estimate(data)

            elapsed = time.monotonic() - start
            logger.info(
                "Salary range estimated: %s in %s — "
                "%.0f-%.0f %s (conf=%.2f, %.2fs)",
                clean_role,
                clean_location,
                data.get("estimated_min", 0),
                data.get("estimated_max", 0),
                currency,
                data.get("confidence", 0),
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Salary range estimation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}

    # ── LLM: Skill Impact Analysis ────────────────────────────

    @staticmethod
    async def analyze_skill_impacts(
        *,
        skills_data: str,
        role_title: str,
        location: str,
        seniority_level: str,
        industry: str,
        estimated_median: float,
        market_percentile: float,
        currency: str = "EUR",
    ) -> list[dict[str, Any]]:
        """
        Quantify per-skill salary contribution via LLM.

        Args:
            skills_data: Formatted skills portfolio.
            role_title: Current or target role.
            location: Geographic location.
            seniority_level: Career seniority.
            industry: Primary industry.
            estimated_median: Current median salary estimate.
            market_percentile: Current market percentile.
            currency: Currency for impact amounts.

        Returns:
            List of skill impact dicts or empty list on error.
        """
        clean_skills, _ = sanitize_user_text(
            skills_data, max_length=3000, context="impact_skills",
        )
        clean_role, _ = sanitize_user_text(
            role_title, max_length=255, context="impact_role",
        )
        clean_location, _ = sanitize_user_text(
            location, max_length=255, context="impact_location",
        )
        clean_industry, _ = sanitize_user_text(
            industry, max_length=255, context="impact_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SKILL_IMPACTS_USER_PROMPT.format(
                    skills_data=clean_skills,
                    role_title=clean_role,
                    location=clean_location,
                    seniority_level=seniority_level,
                    industry=clean_industry,
                    estimated_median=estimated_median,
                    market_percentile=market_percentile,
                    currency=currency,
                ),
                system_prompt=SALARY_INTELLIGENCE_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=3072,
            )

            impacts: list[dict[str, Any]] = data.get("impacts", [])

            # Clamp scarcity and demand values
            for impact in impacts:
                scarcity = impact.get("scarcity_factor", 0.5)
                impact["scarcity_factor"] = max(
                    0.0, min(1.0, float(scarcity))
                )
                demand = impact.get("demand_premium", 50.0)
                impact["demand_premium"] = max(
                    0.0, min(100.0, float(demand))
                )

            elapsed = time.monotonic() - start
            positive = sum(
                1 for impact in impacts
                if impact.get("impact_direction") == "positive"
            )
            logger.info(
                "Skill impacts analyzed: %d skills, %d positive (%.2fs)",
                len(impacts),
                positive,
                elapsed,
            )
            return impacts

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Skill impact analysis failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: Trajectory Projection ────────────────────────────

    @staticmethod
    async def project_trajectory(
        *,
        current_median: float,
        market_percentile: float,
        confidence: float,
        role_title: str,
        location: str,
        seniority_level: str,
        industry: str,
        skill_momentum_data: str,
        historical_data: str,
        currency: str = "EUR",
    ) -> dict[str, Any]:
        """
        Project salary trajectory for 6/12 months via LLM.

        Args:
            current_median: Current salary estimate median.
            market_percentile: Current market positioning.
            confidence: Current estimate confidence.
            role_title: Current or target role.
            location: Geographic location.
            seniority_level: Career seniority.
            industry: Primary industry.
            skill_momentum_data: Skill velocity/freshness data.
            historical_data: Previous salary history entries.
            currency: Currency for projections.

        Returns:
            Dict with projection details or empty dict on error.
        """
        clean_momentum, _ = sanitize_user_text(
            skill_momentum_data, max_length=2000, context="traj_momentum",
        )
        clean_history, _ = sanitize_user_text(
            historical_data, max_length=2000, context="traj_history",
        )
        clean_role, _ = sanitize_user_text(
            role_title, max_length=255, context="traj_role",
        )
        clean_location, _ = sanitize_user_text(
            location, max_length=255, context="traj_location",
        )
        clean_industry, _ = sanitize_user_text(
            industry, max_length=255, context="traj_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SALARY_TRAJECTORY_USER_PROMPT.format(
                    current_median=current_median,
                    market_percentile=market_percentile,
                    confidence=confidence,
                    role_title=clean_role,
                    location=clean_location,
                    seniority_level=seniority_level,
                    industry=clean_industry,
                    skill_momentum_data=clean_momentum,
                    historical_data=clean_history,
                    currency=currency,
                ),
                system_prompt=SALARY_INTELLIGENCE_SYSTEM_PROMPT,
                tier=LLMTier.FAST,
                temperature=0.1,
                max_tokens=1536,
            )

            # Validate projections
            _clamp_trajectory_projection(data, current_median)

            elapsed = time.monotonic() - start
            logger.info(
                "Salary trajectory projected: %s — 6m=%.0f, 12m=%.0f %s "
                "(conf=%.2f, %.2fs)",
                data.get("trend_direction", "unknown"),
                data.get("projected_6m_median", 0),
                data.get("projected_12m_median", 0),
                currency,
                data.get("trend_confidence", 0),
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Salary trajectory projection failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}

    # ── LLM: What-If Scenario Simulation ──────────────────────

    @staticmethod
    async def simulate_scenario(
        *,
        current_median: float,
        current_min: float,
        current_max: float,
        role_title: str,
        location: str,
        current_skills: str,
        scenario_type: str,
        scenario_label: str,
        scenario_input: str,
        currency: str = "EUR",
    ) -> dict[str, Any]:
        """
        Simulate salary impact of a career scenario via LLM.

        Args:
            current_median: Current salary median.
            current_min: Current salary lower bound.
            current_max: Current salary upper bound.
            role_title: Current role.
            location: Current location.
            current_skills: Formatted current skills.
            scenario_type: Type of scenario.
            scenario_label: Human-readable scenario description.
            scenario_input: Serialized scenario parameters.
            currency: Currency for projections.

        Returns:
            Dict with scenario results or empty dict on error.
        """
        clean_skills, _ = sanitize_user_text(
            current_skills, max_length=2000, context="scenario_skills",
        )
        clean_label, _ = sanitize_user_text(
            scenario_label, max_length=255, context="scenario_label",
        )
        clean_input, _ = sanitize_user_text(
            scenario_input, max_length=500, context="scenario_input",
        )
        clean_role, _ = sanitize_user_text(
            role_title, max_length=255, context="scenario_role",
        )
        clean_location, _ = sanitize_user_text(
            location, max_length=255, context="scenario_location",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SALARY_SCENARIO_USER_PROMPT.format(
                    current_median=current_median,
                    current_min=current_min,
                    current_max=current_max,
                    role_title=clean_role,
                    location=clean_location,
                    current_skills=clean_skills,
                    scenario_type=scenario_type,
                    scenario_label=clean_label,
                    scenario_input=clean_input,
                    currency=currency,
                ),
                system_prompt=SALARY_INTELLIGENCE_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.2,
                max_tokens=2048,
            )

            # Validate scenario results
            _clamp_scenario_result(data)

            elapsed = time.monotonic() - start
            logger.info(
                "Salary scenario simulated: %s — delta=%+.1f%% "
                "(conf=%.2f, %.2fs)",
                scenario_type,
                data.get("delta_percent", 0),
                data.get("confidence", 0),
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Salary scenario simulation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}


# ── Private Validation Helpers ─────────────────────────────────


def _clamp_salary_estimate(data: dict[str, Any]) -> None:
    """Validate and clamp salary estimate fields in-place."""
    # Ensure min <= median <= max
    est_min = max(0.0, float(data.get("estimated_min", 0)))
    est_max = max(0.0, float(data.get("estimated_max", 0)))
    est_median = max(0.0, float(data.get("estimated_median", 0)))

    # Fix ordering if LLM got it wrong
    values = sorted([est_min, est_median, est_max])
    data["estimated_min"] = values[0]
    data["estimated_median"] = values[1]
    data["estimated_max"] = values[2]

    # Cap confidence at MAX_LLM_CONFIDENCE
    confidence = data.get("confidence", 0.5)
    data["confidence"] = max(0.0, min(MAX_LLM_CONFIDENCE, float(confidence)))

    # Ensure data points is non-negative
    data_points = data.get("data_points_count", 0)
    data["data_points_count"] = max(0, int(data_points))

    # Clamp market percentile
    percentile = data.get("market_percentile", 50.0)
    data["market_percentile"] = max(0.0, min(100.0, float(percentile)))


def _clamp_trajectory_projection(
    data: dict[str, Any],
    current_median: float,
) -> None:
    """Validate and clamp trajectory projection fields in-place."""
    # Cap confidence
    confidence = data.get("trend_confidence", 0.5)
    data["trend_confidence"] = max(0.0, min(0.85, float(confidence)))

    # Cap annual growth at 15% (conservative)
    max_6m = current_median * 1.075  # 7.5% in 6 months
    max_12m = current_median * 1.15  # 15% in 12 months
    min_6m = current_median * 0.90   # -10% floor
    min_12m = current_median * 0.85  # -15% floor

    proj_6m = float(data.get("projected_6m_median", current_median))
    proj_12m = float(data.get("projected_12m_median", current_median))

    data["projected_6m_median"] = max(min_6m, min(max_6m, proj_6m))
    data["projected_12m_median"] = max(min_12m, min(max_12m, proj_12m))


def _clamp_scenario_result(data: dict[str, Any]) -> None:
    """Validate and clamp scenario result fields in-place."""
    # Ensure projected values are non-negative
    for key in ("projected_min", "projected_max", "projected_median"):
        data[key] = max(0.0, float(data.get(key, 0)))

    # Fix ordering
    values = sorted([
        data["projected_min"],
        data["projected_median"],
        data["projected_max"],
    ])
    data["projected_min"] = values[0]
    data["projected_median"] = values[1]
    data["projected_max"] = values[2]

    # Cap confidence
    confidence = data.get("confidence", 0.5)
    data["confidence"] = max(0.0, min(0.85, float(confidence)))
