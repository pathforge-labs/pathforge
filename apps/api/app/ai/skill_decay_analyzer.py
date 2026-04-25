"""
PathForge AI Engine — Skill Decay & Growth Tracker Analyzer
=============================================================
AI pipeline for the Skill Decay & Growth Tracker system.

4 LLM methods:
    1. score_skill_freshness — Hybrid exponential decay + LLM contextual
    2. analyze_market_demand — Per-skill market demand intelligence
    3. compute_skill_velocity — Composite velocity from freshness + demand
    4. generate_reskilling_paths — Personalized pathway generation

All methods follow the same pattern as ThreatRadarAnalyzer:
    - Static async methods
    - complete_json for structured LLM output
    - sanitize_user_text before all LLM calls
    - Timing + structured logging
    - Safe fallbacks on error
"""

import logging
import math
import time
from typing import Any

from app.ai.skill_decay_prompts import (
    MARKET_DEMAND_USER_PROMPT,
    RESKILLING_PATHWAY_USER_PROMPT,
    SKILL_DECAY_SYSTEM_PROMPT,
    SKILL_FRESHNESS_USER_PROMPT,
    SKILL_VELOCITY_USER_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

# ── Half-Life Constants (WEF research-aligned) ─────────────────

HALF_LIFE_BY_CATEGORY: dict[str, int] = {
    "technical": 912,    # ~2.5 years
    "tool": 1095,        # ~3 years
    "domain": 1460,      # ~4 years
    "soft": 2555,        # ~7 years
    "language": 3650,    # ~10 years
}

DEFAULT_HALF_LIFE_DAYS = 1095  # ~3 years


class SkillDecayAnalyzer:
    """
    AI pipeline for Skill Decay & Growth Tracker analysis.

    Each method performs a focused LLM call and returns
    validated structured data. All results include reasoning
    and opportunity-oriented framing for empowering UX.
    """

    # ── Skill Freshness Scoring ────────────────────────────────

    @staticmethod
    def compute_base_freshness(
        *,
        days_since_active: int,
        half_life_days: int,
    ) -> float:
        """
        Compute base freshness score using exponential decay.

        Formula: freshness = 100 × exp(-λ × days)
        where λ = ln(2) / half_life_days

        Args:
            days_since_active: Days since the skill was last used.
            half_life_days: Category-calibrated half-life in days.

        Returns:
            Freshness score from 0.0 to 100.0.
        """
        if days_since_active <= 0:
            return 100.0
        if half_life_days <= 0:
            half_life_days = DEFAULT_HALF_LIFE_DAYS

        decay_constant = math.log(2) / half_life_days
        score = 100.0 * math.exp(-decay_constant * days_since_active)
        return max(0.0, min(100.0, round(score, 2)))

    @staticmethod
    def get_half_life_for_category(category: str) -> int:
        """Get WEF-aligned half-life in days for a skill category."""
        return HALF_LIFE_BY_CATEGORY.get(
            category.lower(), DEFAULT_HALF_LIFE_DAYS,
        )

    @staticmethod
    def classify_decay_rate(half_life_days: int) -> str:
        """Classify decay rate based on half-life duration."""
        if half_life_days <= 1000:
            return "fast"
        if half_life_days <= 1500:
            return "moderate"
        if half_life_days <= 3000:
            return "slow"
        return "stable"

    @staticmethod
    def compute_refresh_urgency(
        freshness_score: float,
        demand_score: float = 50.0,
    ) -> float:
        """
        Compute refresh urgency (0-1) combining freshness and demand.

        High urgency = low freshness + high demand (market needs it).
        Low urgency = high freshness OR low demand.
        """
        freshness_factor = max(0.0, (100.0 - freshness_score) / 100.0)
        demand_factor = demand_score / 100.0
        urgency = (freshness_factor * 0.6) + (demand_factor * 0.4)
        return max(0.0, min(1.0, round(urgency, 3)))

    @staticmethod
    async def score_skill_freshness(
        *,
        skills_data: str,
        experience_summary: str,
        industry_context: str,
    ) -> list[dict[str, Any]]:
        """
        Score freshness with LLM contextual adjustment.

        The LLM adjusts the base exponential decay score based on
        contextual factors (e.g., rapidly evolving skill ecosystems,
        adjacent skill maintenance, industry requirements).

        Args:
            skills_data: Formatted skills with last-used dates.
            experience_summary: Career experience narrative.
            industry_context: Primary industry context.

        Returns:
            List of dicts with: skill_name, category,
            freshness_adjustment, adjusted_reasoning, refresh_suggestion.
        """
        clean_skills, _ = sanitize_user_text(
            skills_data, max_length=3000, context="decay_skills",
        )
        clean_exp, _ = sanitize_user_text(
            experience_summary, max_length=2000, context="decay_exp",
        )
        clean_industry, _ = sanitize_user_text(
            industry_context, max_length=200, context="decay_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SKILL_FRESHNESS_USER_PROMPT.format(
                    skills_data=clean_skills,
                    experience_summary=clean_exp,
                    industry_context=clean_industry,
                ),
                system_prompt=SKILL_DECAY_SYSTEM_PROMPT,
                tier=LLMTier.FAST,
                temperature=0.1,
                max_tokens=2048,
            )

            assessments: list[dict[str, Any]] = data.get("assessments", [])

            # Clamp adjustments to ±20
            for entry in assessments:
                adj = entry.get("freshness_adjustment", 0.0)
                entry["freshness_adjustment"] = max(-20.0, min(20.0, float(adj)))

            elapsed = time.monotonic() - start
            logger.info(
                "Skill freshness assessed: %d skills (%.2fs)",
                len(assessments),
                elapsed,
            )
            return assessments

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Skill freshness scoring failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── Market Demand Analysis ─────────────────────────────────

    @staticmethod
    async def analyze_market_demand(
        *,
        skills_list: str,
        industry_context: str,
        experience_level: str,
        region: str = "Global",
    ) -> list[dict[str, Any]]:
        """
        Analyze market demand for each skill via LLM intelligence.

        Args:
            skills_list: Formatted list of skills to analyze.
            industry_context: Primary industry for demand context.
            experience_level: Professional experience level.
            region: Geographic region for regional demand.

        Returns:
            List of dicts with: skill_name, demand_score, demand_trend,
            trend_confidence, growth_projection_6m, growth_projection_12m,
            industry_relevance, reasoning.
        """
        clean_skills, _ = sanitize_user_text(
            skills_list, max_length=2000, context="demand_skills",
        )
        clean_industry, _ = sanitize_user_text(
            industry_context, max_length=200, context="demand_industry",
        )
        clean_level, _ = sanitize_user_text(
            experience_level, max_length=100, context="demand_level",
        )
        clean_region, _ = sanitize_user_text(
            region, max_length=100, context="demand_region",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=MARKET_DEMAND_USER_PROMPT.format(
                    skills_list=clean_skills,
                    industry_context=clean_industry,
                    experience_level=clean_level,
                    region=clean_region,
                ),
                system_prompt=SKILL_DECAY_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=3072,
            )

            demands: list[dict[str, Any]] = data.get("demands", [])

            # Cap confidence at 0.85 and clamp scores
            for entry in demands:
                if entry.get("trend_confidence", 0) > 0.85:
                    entry["trend_confidence"] = 0.85
                score = entry.get("demand_score", 50.0)
                entry["demand_score"] = max(0.0, min(100.0, float(score)))

            elapsed = time.monotonic() - start
            surging = sum(
                1 for demand in demands
                if demand.get("demand_trend") == "surging"
            )
            logger.info(
                "Market demand analyzed: %d skills, %d surging (%.2fs)",
                len(demands),
                surging,
                elapsed,
            )
            return demands

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Market demand analysis failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── Skill Velocity Computation ─────────────────────────────

    @staticmethod
    async def compute_skill_velocity(
        *,
        freshness_data: str,
        demand_data: str,
        professional_context: str,
    ) -> list[dict[str, Any]]:
        """
        Compute skill velocity by combining freshness and demand.

        Args:
            freshness_data: Formatted freshness scores per skill.
            demand_data: Formatted demand analysis per skill.
            professional_context: Career context for the user.

        Returns:
            List of dicts with: skill_name, velocity_score,
            velocity_direction, composite_health, acceleration, reasoning.
        """
        clean_freshness, _ = sanitize_user_text(
            freshness_data, max_length=3000, context="velocity_freshness",
        )
        clean_demand, _ = sanitize_user_text(
            demand_data, max_length=3000, context="velocity_demand",
        )
        clean_context, _ = sanitize_user_text(
            professional_context, max_length=1500, context="velocity_context",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=SKILL_VELOCITY_USER_PROMPT.format(
                    freshness_data=clean_freshness,
                    demand_data=clean_demand,
                    professional_context=clean_context,
                ),
                system_prompt=SKILL_DECAY_SYSTEM_PROMPT,
                tier=LLMTier.FAST,
                temperature=0.1,
                max_tokens=2048,
            )

            velocities: list[dict[str, Any]] = data.get("velocities", [])

            # Clamp velocity scores and composite health
            for entry in velocities:
                velocity = entry.get("velocity_score", 0.0)
                entry["velocity_score"] = max(-100.0, min(100.0, float(velocity)))
                health = entry.get("composite_health", 50.0)
                entry["composite_health"] = max(0.0, min(100.0, float(health)))

            elapsed = time.monotonic() - start
            accelerating = sum(
                1 for velocity in velocities
                if velocity.get("velocity_direction") == "accelerating"
            )
            logger.info(
                "Skill velocity computed: %d skills, %d accelerating (%.2fs)",
                len(velocities),
                accelerating,
                elapsed,
            )
            return velocities

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Skill velocity computation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── Reskilling Pathway Generation ──────────────────────────

    @staticmethod
    async def generate_reskilling_paths(
        *,
        velocity_data: str,
        freshness_data: str,
        demand_data: str,
        current_skills: str,
        experience_level: str,
        industry_context: str,
    ) -> list[dict[str, Any]]:
        """
        Generate personalized reskilling pathways via LLM.

        Design principle: pathways EMPOWER, never prescribe.
        Users always see 2-3+ options, never a single mandate.

        Args:
            velocity_data: Formatted skill velocity map.
            freshness_data: Formatted freshness scores.
            demand_data: Formatted demand analysis.
            current_skills: Current skill portfolio summary.
            experience_level: Professional experience level.
            industry_context: Primary industry context.

        Returns:
            List of pathway dicts with: target_skill, current_level,
            target_level, priority, rationale, estimated_effort_hours,
            prerequisite_skills, learning_resources, career_impact,
            freshness_gain, demand_alignment.
        """
        clean_velocity, _ = sanitize_user_text(
            velocity_data, max_length=2000, context="reskill_velocity",
        )
        clean_freshness, _ = sanitize_user_text(
            freshness_data, max_length=2000, context="reskill_freshness",
        )
        clean_demand, _ = sanitize_user_text(
            demand_data, max_length=2000, context="reskill_demand",
        )
        clean_skills, _ = sanitize_user_text(
            current_skills, max_length=1500, context="reskill_skills",
        )
        clean_level, _ = sanitize_user_text(
            experience_level, max_length=100, context="reskill_level",
        )
        clean_industry, _ = sanitize_user_text(
            industry_context, max_length=200, context="reskill_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=RESKILLING_PATHWAY_USER_PROMPT.format(
                    velocity_data=clean_velocity,
                    freshness_data=clean_freshness,
                    demand_data=clean_demand,
                    current_skills=clean_skills,
                    experience_level=clean_level,
                    industry_context=clean_industry,
                ),
                system_prompt=SKILL_DECAY_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.2,
                max_tokens=3072,
            )

            pathways: list[dict[str, Any]] = data.get("pathways", [])

            # Validate and clamp pathway fields
            for pathway in pathways:
                # Cap demand alignment at 1.0
                alignment = pathway.get("demand_alignment", 0.5)
                pathway["demand_alignment"] = max(0.0, min(1.0, float(alignment)))

                # Cap freshness gain at 100
                gain = pathway.get("freshness_gain", 0.0)
                pathway["freshness_gain"] = max(0.0, min(100.0, float(gain)))

                # Ensure effort hours is reasonable
                hours = pathway.get("estimated_effort_hours", 40)
                pathway["estimated_effort_hours"] = max(5, min(500, int(hours)))

            elapsed = time.monotonic() - start
            critical = sum(
                1 for pathway in pathways
                if pathway.get("priority") == "critical"
            )
            logger.info(
                "Reskilling pathways generated: %d total, %d critical (%.2fs)",
                len(pathways),
                critical,
                elapsed,
            )
            return pathways

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Reskilling pathway generation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []
