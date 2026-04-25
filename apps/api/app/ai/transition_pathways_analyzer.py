"""
PathForge AI Engine — Transition Pathways Analyzer
=====================================================
AI pipeline for the Transition Pathways module.

4 LLM methods:
    1. analyze_transition — Confidence, difficulty, timeline estimation
    2. generate_skill_bridge — Skill gap identification and learning plan
    3. create_milestones — Phased action plan with weekly targets
    4. compare_roles — Multi-dimension source vs target comparison

4 Static helpers:
    1. compute_skill_overlap — % overlap between skill sets
    2. compute_transition_difficulty — Map overlap + gap → difficulty
    3. estimate_timeline_range — Optimistic/realistic/conservative months
    4. compute_transition_confidence — Combine factors into capped score

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

from app.ai.transition_pathways_prompts import (
    MILESTONES_SYSTEM_PROMPT,
    MILESTONES_USER_PROMPT,
    ROLE_COMPARISON_SYSTEM_PROMPT,
    ROLE_COMPARISON_USER_PROMPT,
    SKILL_BRIDGE_SYSTEM_PROMPT,
    SKILL_BRIDGE_USER_PROMPT,
    TRANSITION_ANALYSIS_SYSTEM_PROMPT,
    TRANSITION_ANALYSIS_USER_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────

MAX_TRANSITION_CONFIDENCE = 0.85
"""Hard ceiling for LLM-generated transition confidence scores."""


class TransitionPathwaysAnalyzer:
    """
    AI pipeline for Transition Pathways analysis.

    Each method performs a focused LLM call and returns
    validated structured data. All transition estimates include
    transparent factor breakdowns for explainability.
    """

    # ── Static Helpers ─────────────────────────────────────────

    @staticmethod
    def compute_skill_overlap(
        *,
        current_skills: list[str],
        target_skills: list[str],
    ) -> float:
        """
        Calculate percentage overlap between current and target skill sets.

        Uses case-insensitive matching. Returns 0.0 when target has
        no required skills.

        Args:
            current_skills: User's current skill names.
            target_skills: Skills required by target role.

        Returns:
            Overlap percentage from 0.0 to 100.0.
        """
        if not target_skills:
            return 0.0

        current_lower = {skill.lower().strip() for skill in current_skills}
        target_lower = {skill.lower().strip() for skill in target_skills}

        if not target_lower:
            return 0.0

        matched = current_lower & target_lower
        overlap = (len(matched) / len(target_lower)) * 100.0
        return max(0.0, min(100.0, round(overlap, 1)))

    @staticmethod
    def compute_transition_difficulty(
        *,
        skill_overlap_percent: float,
        seniority_gap: int = 0,
    ) -> str:
        """
        Map skill overlap and seniority gap to difficulty classification.

        Thresholds:
            - overlap >= 70% and gap <= 1 → easy
            - overlap >= 45% and gap <= 2 → moderate
            - overlap >= 20% or gap <= 3 → challenging
            - else → extreme

        Args:
            skill_overlap_percent: Skill overlap (0-100).
            seniority_gap: Absolute difference in seniority levels.

        Returns:
            Difficulty string: easy, moderate, challenging, extreme.
        """
        overlap = max(0.0, min(100.0, skill_overlap_percent))
        gap = abs(seniority_gap)

        if overlap >= 70.0 and gap <= 1:
            return "easy"
        if overlap >= 45.0 and gap <= 2:
            return "moderate"
        if overlap >= 20.0 or gap <= 3:
            return "challenging"
        return "extreme"

    @staticmethod
    def estimate_timeline_range(
        *,
        difficulty: str,
        skills_to_acquire: int,
    ) -> tuple[int, int, int]:
        """
        Compute optimistic/realistic/conservative month estimates.

        Base estimates per difficulty, adjusted by skill count:
            - easy: 2-4-6 months base
            - moderate: 4-8-12 months base
            - challenging: 8-14-20 months base
            - extreme: 14-22-30 months base

        Each additional skill beyond 3 adds 0.5-1 month.

        Args:
            difficulty: Difficulty classification.
            skills_to_acquire: Number of skills needing acquisition.

        Returns:
            Tuple of (optimistic, realistic, conservative) months.
        """
        base_ranges: dict[str, tuple[int, int, int]] = {
            "easy": (2, 4, 6),
            "moderate": (4, 8, 12),
            "challenging": (8, 14, 20),
            "extreme": (14, 22, 30),
        }

        optimistic, realistic, conservative = base_ranges.get(
            difficulty, (6, 12, 18)
        )

        # Adjust for skill acquisition load
        extra_skills = max(0, skills_to_acquire - 3)
        optimistic += int(extra_skills * 0.5)
        realistic += extra_skills
        conservative += int(extra_skills * 1.5)

        return optimistic, realistic, conservative

    @staticmethod
    def compute_transition_confidence(
        *,
        skill_overlap_percent: float,
        llm_confidence: float,
        market_demand_score: float = 50.0,
    ) -> float:
        """
        Combine skill overlap, LLM score, and market demand into
        a final capped confidence score.

        Formula:
            weighted = 0.4 × skill_factor + 0.4 × llm + 0.2 × market_factor
            clamped to [0.0, MAX_TRANSITION_CONFIDENCE]

        Args:
            skill_overlap_percent: Skill overlap (0-100).
            llm_confidence: Raw LLM confidence (0-1).
            market_demand_score: Market demand (0-100, default 50).

        Returns:
            Capped confidence from 0.0 to 0.85.
        """
        skill_factor = min(1.0, skill_overlap_percent / 100.0)
        llm_factor = max(0.0, min(MAX_TRANSITION_CONFIDENCE, llm_confidence))
        market_factor = min(1.0, market_demand_score / 100.0)

        weighted = (
            0.4 * skill_factor
            + 0.4 * llm_factor
            + 0.2 * market_factor
        )

        return float(
            max(0.0, min(MAX_TRANSITION_CONFIDENCE, round(weighted, 3)))
        )

    # ── LLM: Transition Analysis ──────────────────────────────

    @staticmethod
    async def analyze_transition(
        *,
        from_role: str,
        to_role: str,
        seniority_level: str,
        location: str,
        industry: str,
        years_experience: int,
        current_skills: str,
        target_industry: str | None = None,
        target_location: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze career transition feasibility via LLM intelligence.

        Produces confidence score, difficulty, skill overlap, and
        timeline estimates with transparent factor breakdown.

        Args:
            from_role: Current role title.
            to_role: Target role title.
            seniority_level: Current seniority level.
            location: Current location.
            industry: Current industry.
            years_experience: Total professional years.
            current_skills: Formatted current skills.
            target_industry: Optional target industry.
            target_location: Optional target location.

        Returns:
            Dict with analysis details or empty dict on error.
        """
        clean_from, _ = sanitize_user_text(
            from_role, max_length=255, context="transition_from",
        )
        clean_to, _ = sanitize_user_text(
            to_role, max_length=255, context="transition_to",
        )
        clean_location, _ = sanitize_user_text(
            location, max_length=255, context="transition_location",
        )
        clean_industry, _ = sanitize_user_text(
            industry, max_length=255, context="transition_industry",
        )
        clean_skills, _ = sanitize_user_text(
            current_skills, max_length=3000, context="transition_skills",
        )
        clean_target_industry, _ = sanitize_user_text(
            target_industry or industry,
            max_length=255,
            context="transition_target_industry",
        )
        clean_target_location, _ = sanitize_user_text(
            target_location or location,
            max_length=255,
            context="transition_target_location",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] = await complete_json(
                prompt=TRANSITION_ANALYSIS_USER_PROMPT.format(
                    from_role=clean_from,
                    to_role=clean_to,
                    seniority_level=seniority_level,
                    location=clean_location,
                    industry=clean_industry,
                    years_experience=years_experience,
                    current_skills=clean_skills,
                    target_industry=clean_target_industry,
                    target_location=clean_target_location,
                ),
                system_prompt=TRANSITION_ANALYSIS_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=2048,
            )

            _clamp_transition_analysis(data)

            elapsed = time.monotonic() - start
            logger.info(
                "Transition analyzed: %s → %s — "
                "confidence=%.2f, difficulty=%s (%.2fs)",
                clean_from,
                clean_to,
                data.get("confidence_score", 0),
                data.get("difficulty", "unknown"),
                elapsed,
            )
            return data

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Transition analysis failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return {}

    # ── LLM: Skill Bridge Generation ──────────────────────────

    @staticmethod
    async def generate_skill_bridge(
        *,
        current_skills: str,
        from_role: str,
        to_role: str,
        target_industry: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate skill gap analysis with acquisition strategies.

        Identifies required skills for the target role, flags which
        the user already holds, and provides learning plans for gaps.

        Args:
            current_skills: Formatted current skills.
            from_role: Current role title.
            to_role: Target role title.
            target_industry: Optional target industry.

        Returns:
            List of skill bridge dicts or empty list on error.
        """
        clean_skills, _ = sanitize_user_text(
            current_skills, max_length=3000, context="bridge_skills",
        )
        clean_from, _ = sanitize_user_text(
            from_role, max_length=255, context="bridge_from",
        )
        clean_to, _ = sanitize_user_text(
            to_role, max_length=255, context="bridge_to",
        )
        clean_industry, _ = sanitize_user_text(
            target_industry or "General",
            max_length=255,
            context="bridge_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=SKILL_BRIDGE_USER_PROMPT.format(
                    current_skills=clean_skills,
                    from_role=clean_from,
                    to_role=clean_to,
                    target_industry=clean_industry,
                ),
                system_prompt=SKILL_BRIDGE_SYSTEM_PROMPT,
                tier=LLMTier.PRIMARY,
                temperature=0.1,
                max_tokens=3072,
            )

            # Handle both list and dict responses
            skills: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("skills", [])
            )

            _clamp_skill_bridge_entries(skills)

            elapsed = time.monotonic() - start
            held = sum(1 for skill in skills if skill.get("is_already_held"))
            logger.info(
                "Skill bridge generated: %d skills (%d held, %d to acquire) "
                "(%.2fs)",
                len(skills),
                held,
                len(skills) - held,
                elapsed,
            )
            return skills

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Skill bridge generation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: Milestones Creation ──────────────────────────────

    @staticmethod
    async def create_milestones(
        *,
        from_role: str,
        to_role: str,
        skills_to_acquire: str,
        estimated_months: int,
        difficulty: str,
    ) -> list[dict[str, Any]]:
        """
        Generate phased action plan with concrete milestones.

        Creates 8-14 milestones across 4 phases: preparation,
        skill_building, transition, establishment.

        Args:
            from_role: Current role.
            to_role: Target role.
            skills_to_acquire: Comma-separated skills list.
            estimated_months: Estimated timeline.
            difficulty: Transition difficulty classification.

        Returns:
            List of milestone dicts or empty list on error.
        """
        clean_from, _ = sanitize_user_text(
            from_role, max_length=255, context="milestone_from",
        )
        clean_to, _ = sanitize_user_text(
            to_role, max_length=255, context="milestone_to",
        )
        clean_skills, _ = sanitize_user_text(
            skills_to_acquire, max_length=2000, context="milestone_skills",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=MILESTONES_USER_PROMPT.format(
                    from_role=clean_from,
                    to_role=clean_to,
                    skills_to_acquire=clean_skills,
                    estimated_months=estimated_months,
                    difficulty=difficulty,
                ),
                system_prompt=MILESTONES_SYSTEM_PROMPT,
                tier=LLMTier.FAST,
                temperature=0.2,
                max_tokens=2048,
            )

            milestones: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("milestones", [])
            )

            _clamp_milestones(milestones)

            elapsed = time.monotonic() - start
            logger.info(
                "Milestones created: %d milestones for %s → %s (%.2fs)",
                len(milestones),
                clean_from,
                clean_to,
                elapsed,
            )
            return milestones

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Milestone creation failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []

    # ── LLM: Role Comparison ──────────────────────────────────

    @staticmethod
    async def compare_roles(
        *,
        from_role: str,
        to_role: str,
        location: str,
        seniority_level: str,
        industry: str,
    ) -> list[dict[str, Any]]:
        """
        Compare source and target roles across multiple dimensions.

        Produces comparisons on salary, market demand, growth
        potential, and automation risk with delta values.

        Args:
            from_role: Source role title.
            to_role: Target role title.
            location: Geographic location for context.
            seniority_level: Seniority level for context.
            industry: Industry for context.

        Returns:
            List of comparison dimension dicts or empty list on error.
        """
        clean_from, _ = sanitize_user_text(
            from_role, max_length=255, context="compare_from",
        )
        clean_to, _ = sanitize_user_text(
            to_role, max_length=255, context="compare_to",
        )
        clean_location, _ = sanitize_user_text(
            location, max_length=255, context="compare_location",
        )
        clean_industry, _ = sanitize_user_text(
            industry, max_length=255, context="compare_industry",
        )

        start = time.monotonic()
        try:
            data: dict[str, Any] | list[dict[str, Any]] = await complete_json(
                prompt=ROLE_COMPARISON_USER_PROMPT.format(
                    from_role=clean_from,
                    to_role=clean_to,
                    location=clean_location,
                    seniority_level=seniority_level,
                    industry=clean_industry,
                ),
                system_prompt=ROLE_COMPARISON_SYSTEM_PROMPT,
                tier=LLMTier.FAST,
                temperature=0.1,
                max_tokens=1536,
            )

            comparisons: list[dict[str, Any]] = (
                data if isinstance(data, list)
                else data.get("comparisons", [])
            )

            elapsed = time.monotonic() - start
            logger.info(
                "Role comparison completed: %s → %s — %d dimensions (%.2fs)",
                clean_from,
                clean_to,
                len(comparisons),
                elapsed,
            )
            return comparisons

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Role comparison failed (%.2fs): %s",
                elapsed,
                str(exc)[:200],
            )
            return []


# ── Private Validation Helpers ─────────────────────────────────


def _clamp_transition_analysis(data: dict[str, Any]) -> None:
    """Validate and clamp transition analysis fields in-place."""
    # Cap confidence at MAX
    confidence = data.get("confidence_score", 0.5)
    data["confidence_score"] = max(
        0.0, min(MAX_TRANSITION_CONFIDENCE, float(confidence))
    )

    # Cap success probability
    probability = data.get("success_probability", 0.5)
    data["success_probability"] = max(
        0.0, min(MAX_TRANSITION_CONFIDENCE, float(probability))
    )

    # Clamp skill overlap
    overlap = data.get("skill_overlap_percent", 50.0)
    data["skill_overlap_percent"] = max(0.0, min(100.0, float(overlap)))

    # Ensure positive duration
    duration = data.get("estimated_duration_months", 12)
    data["estimated_duration_months"] = max(1, int(duration))

    # Ensure timeline ordering: optimistic <= realistic <= conservative
    optimistic = max(1, int(data.get("optimistic_months", 3)))
    realistic = max(1, int(data.get("realistic_months", 6)))
    conservative = max(1, int(data.get("conservative_months", 12)))
    values = sorted([optimistic, realistic, conservative])
    data["optimistic_months"] = values[0]
    data["realistic_months"] = values[1]
    data["conservative_months"] = values[2]

    # Validate difficulty
    valid_difficulties = {"easy", "moderate", "challenging", "extreme"}
    if data.get("difficulty", "").lower() not in valid_difficulties:
        data["difficulty"] = "moderate"

    # Ensure skills count is non-negative
    data["skills_to_acquire_count"] = max(
        0, int(data.get("skills_to_acquire_count", 0))
    )


def _clamp_skill_bridge_entries(skills: list[dict[str, Any]]) -> None:
    """Validate and clamp skill bridge entry fields in-place."""
    valid_priorities = {"critical", "high", "medium", "nice_to_have"}
    valid_categories = {"technical", "soft", "domain", "tool", "language"}

    for skill in skills:
        # Validate priority
        if skill.get("priority", "").lower() not in valid_priorities:
            skill["priority"] = "medium"

        # Validate category
        if skill.get("category", "").lower() not in valid_categories:
            skill["category"] = "technical"

        # Clamp estimated weeks
        weeks = skill.get("estimated_weeks")
        if weeks is not None:
            skill["estimated_weeks"] = max(1, min(104, int(weeks)))

        # Clamp impact on confidence
        impact = skill.get("impact_on_confidence")
        if impact is not None:
            skill["impact_on_confidence"] = max(
                0.0, min(0.15, float(impact))
            )


def _clamp_milestones(milestones: list[dict[str, Any]]) -> None:
    """Validate and clamp milestone fields in-place."""
    valid_phases = {
        "preparation", "skill_building", "transition", "establishment",
    }

    for index, milestone in enumerate(milestones):
        # Validate phase
        if milestone.get("phase", "").lower() not in valid_phases:
            milestone["phase"] = "preparation"

        # Ensure target week is positive
        week = milestone.get("target_week", 1)
        milestone["target_week"] = max(1, min(156, int(week)))

        # Ensure order index is set
        milestone["order_index"] = milestone.get("order_index", index)
