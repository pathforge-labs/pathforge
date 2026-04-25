"""
PathForge — Career Action Planner™ AI Analyzer
=================================================
LLM-powered career action planning pipeline for priority analysis,
milestone generation, progress evaluation, and cross-engine recommendations.

LLM Methods (4):
    analyze_career_priorities    — Rank career priorities from Career DNA
    generate_milestones          — Create actionable milestones
    evaluate_progress            — Assess progress and recalculate
    generate_recommendations     — Cross-engine recommendation pipeline

Static Helpers (4):
    _clamp_confidence            — Enforce MAX_PLAN_CONFIDENCE = 0.85
    _clamp_impact_score          — Enforce impact score range 0-100
    _build_priority_context      — Format Career DNA for prompts
    _validate_milestone_timeline — Ensure reasonable date ranges

Proprietary Innovations:
    🔥 Career Sprint Methodology™         — Time-boxed career dev cycles
    🔥 Intelligence-to-Action Bridge™     — Converts intelligence → actions
    🔥 Adaptive Plan Recalculation™       — Dynamic re-prioritization
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

from app.ai.career_action_planner_prompts import (
    CAREER_PRIORITIES_PROMPT,
    MILESTONE_GENERATION_PROMPT,
    PROGRESS_EVALUATION_PROMPT,
    RECOMMENDATIONS_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

MAX_PLAN_CONFIDENCE = 0.85
MAX_IMPACT_SCORE = 100.0

VALID_URGENCY_LEVELS = frozenset({"critical", "high", "medium", "low"})
VALID_MILESTONE_CATEGORIES = frozenset({
    "learning", "certification", "networking",
    "project", "application", "interview_prep",
})
VALID_SOURCE_ENGINES = frozenset({
    "threat_radar", "skill_decay", "salary_intelligence",
    "transition_pathways", "career_simulation", "hidden_job_market",
    "predictive_career", "collective_intelligence",
})


class CareerActionPlannerAnalyzer:
    """AI pipeline for Career Action Planner™ plan generation and evaluation."""

    # ── LLM Methods ────────────────────────────────────────────

    @staticmethod
    async def analyze_career_priorities(
        *,
        primary_role: str,
        primary_industry: str,
        seniority_level: str,
        location: str,
        skills: str,
        plan_type: str,
        focus_area: str,
        intelligence_summary: str,
    ) -> dict[str, Any]:
        """Analyze and rank career priorities from Career DNA + intelligence data.

        Career Sprint Methodology™ — identifies the top priorities for
        a focused career sprint, ranked by urgency and impact.

        Args:
            primary_role: User's primary role.
            primary_industry: User's industry.
            seniority_level: User's seniority level.
            location: User's location.
            skills: Comma-separated skill list.
            plan_type: Requested plan type.
            focus_area: Optional focus area.
            intelligence_summary: Summary of intelligence engine outputs.

        Returns:
            Dict with priorities list, overall_assessment, and confidence.
        """
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="planner_role",
        )
        clean_focus, _ = sanitize_user_text(
            focus_area or "General career development",
            max_length=300, context="planner_focus",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "General", max_length=1000, context="planner_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=CAREER_PRIORITIES_PROMPT.format(
                    primary_role=clean_role,
                    primary_industry=primary_industry or "Technology",
                    seniority_level=seniority_level or "mid",
                    location=location or "Not specified",
                    skills=clean_skills,
                    plan_type=plan_type,
                    focus_area=clean_focus,
                    intelligence_summary=intelligence_summary or "No data",
                ),
                system_prompt=(
                    "You are the PathForge Career Sprint Strategist. "
                    "Analyze career data and rank priorities."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=1024,
            )

            _clamp_priorities(result)

            elapsed = time.monotonic() - start
            priority_count = len(result.get("priorities", []))
            logger.info(
                "Career priorities analysis completed — "
                "%d priorities, confidence %.2f (%.2fs)",
                priority_count,
                result.get("confidence", 0.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Career priorities analysis failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "priorities": [],
                "overall_assessment": (
                    "Priority analysis unavailable — "
                    "please try again or consult a career advisor."
                ),
                "confidence": 0.0,
            }

    @staticmethod
    async def generate_milestones(
        *,
        primary_role: str,
        seniority_level: str,
        skills: str,
        plan_type: str,
        plan_title: str,
        plan_objective: str,
        sprint_weeks: int,
        max_milestones: int,
        priorities_json: str,
    ) -> dict[str, Any]:
        """Generate actionable milestones for a career sprint.

        Intelligence-to-Action Bridge™ — converts prioritized career
        intelligence into concrete, time-bound milestones.

        Args:
            primary_role: User's primary role.
            seniority_level: User's seniority.
            skills: User's skills.
            plan_type: Plan type.
            plan_title: Plan title.
            plan_objective: Plan objective.
            sprint_weeks: Sprint length in weeks.
            max_milestones: Maximum milestones to generate.
            priorities_json: JSON string of priorities.

        Returns:
            Dict with milestones list, sprint_summary, and confidence.
        """
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="milestone_role",
        )
        clean_title, _ = sanitize_user_text(
            plan_title, max_length=300, context="milestone_title",
        )
        clean_objective, _ = sanitize_user_text(
            plan_objective, max_length=500, context="milestone_objective",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=MILESTONE_GENERATION_PROMPT.format(
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    skills=skills or "General",
                    plan_type=plan_type,
                    plan_title=clean_title,
                    plan_objective=clean_objective,
                    sprint_weeks=sprint_weeks,
                    max_milestones=max_milestones,
                    priorities_json=priorities_json,
                ),
                system_prompt=(
                    "You are the PathForge Milestone Architect. "
                    "Create concrete, time-bound career milestones."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=1024,
            )

            _clamp_milestones(result, max_milestones=max_milestones)

            elapsed = time.monotonic() - start
            milestone_count = len(result.get("milestones", []))
            logger.info(
                "Milestone generation completed — "
                "%d milestones for %s-week sprint (%.2fs)",
                milestone_count, sprint_weeks, elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Milestone generation failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "milestones": [],
                "sprint_summary": (
                    "Milestone generation unavailable — "
                    "please try again or create milestones manually."
                ),
                "confidence": 0.0,
            }

    @staticmethod
    async def evaluate_progress(
        *,
        plan_title: str,
        plan_type: str,
        sprint_weeks: int,
        milestones_json: str,
        intelligence_updates: str,
    ) -> dict[str, Any]:
        """Evaluate milestone progress and recalculate plan trajectory.

        Adaptive Plan Recalculation™ — assesses progress and dynamically
        re-prioritizes based on new career events and intelligence data.

        Args:
            plan_title: Plan title.
            plan_type: Plan type.
            sprint_weeks: Sprint length.
            milestones_json: JSON of current milestones with progress.
            intelligence_updates: Latest intelligence engine updates.

        Returns:
            Dict with plan_health, progress, assessments, adjustments.
        """
        clean_title, _ = sanitize_user_text(
            plan_title, max_length=300, context="eval_title",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=PROGRESS_EVALUATION_PROMPT.format(
                    plan_title=clean_title,
                    plan_type=plan_type,
                    sprint_weeks=sprint_weeks,
                    milestones_json=milestones_json,
                    intelligence_updates=intelligence_updates or "No updates",
                ),
                system_prompt=(
                    "You are the PathForge Progress Coach. "
                    "Evaluate career sprint progress honestly."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.3,
                max_tokens=768,
            )

            _clamp_progress_evaluation(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Progress evaluation completed — "
                "health: %s, progress: %.1f%% (%.2fs)",
                result.get("plan_health", "unknown"),
                result.get("overall_progress_percent", 0.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Progress evaluation failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "plan_health": "at_risk",
                "overall_progress_percent": 0.0,
                "milestone_assessments": [],
                "priority_adjustments": [],
                "confidence": 0.0,
            }

    @staticmethod
    async def generate_recommendations(
        *,
        primary_role: str,
        primary_industry: str,
        seniority_level: str,
        plan_type: str,
        plan_title: str,
        engine_outputs: str,
    ) -> dict[str, Any]:
        """Generate cross-engine recommendations for a career plan.

        Intelligence-to-Action Bridge™ — cross-references outputs from
        all 8 intelligence engines to produce contextual recommendations.

        Args:
            primary_role: User's role.
            primary_industry: User's industry.
            seniority_level: User's seniority.
            plan_type: Plan type.
            plan_title: Plan title.
            engine_outputs: JSON of intelligence engine outputs.

        Returns:
            Dict with recommendations list and confidence.
        """
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer",
            max_length=255, context="rec_role",
        )
        clean_title, _ = sanitize_user_text(
            plan_title, max_length=300, context="rec_title",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=RECOMMENDATIONS_PROMPT.format(
                    primary_role=clean_role,
                    primary_industry=primary_industry or "Technology",
                    seniority_level=seniority_level or "mid",
                    plan_type=plan_type,
                    plan_title=clean_title,
                    engine_outputs=engine_outputs or "No engine data",
                ),
                system_prompt=(
                    "You are the PathForge Intelligence Bridge Analyst. "
                    "Cross-reference career intelligence for recommendations."
                ),
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=768,
            )

            _clamp_recommendations(result)

            elapsed = time.monotonic() - start
            rec_count = len(result.get("recommendations", []))
            logger.info(
                "Recommendations generated — "
                "%d recommendations, confidence %.2f (%.2fs)",
                rec_count,
                result.get("confidence", 0.0),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Recommendations generation failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {
                "recommendations": [],
                "confidence": 0.0,
            }

    # ── Static Helpers ──────────────────────────────────────────

    @staticmethod
    def clamp_confidence(value: float) -> float:
        """Enforce MAX_PLAN_CONFIDENCE = 0.85.

        Args:
            value: Raw confidence value.

        Returns:
            Clamped confidence in range [0.0, 0.85].
        """
        if not isinstance(value, (int, float)):
            return 0.0
        return round(max(0.0, min(float(value), MAX_PLAN_CONFIDENCE)), 3)

    @staticmethod
    def clamp_impact_score(value: float) -> float:
        """Enforce impact score range [0, 100].

        Args:
            value: Raw impact score.

        Returns:
            Clamped impact score in range [0.0, 100.0].
        """
        if not isinstance(value, (int, float)):
            return 0.0
        return round(max(0.0, min(float(value), MAX_IMPACT_SCORE)), 2)

    @staticmethod
    def build_priority_context(
        *,
        primary_role: str | None,
        primary_industry: str | None,
        seniority_level: str | None,
        location: str | None,
        skills: list[str],
    ) -> dict[str, str]:
        """Format Career DNA data for prompt context.

        Args:
            primary_role: User's role.
            primary_industry: User's industry.
            seniority_level: User's seniority.
            location: User's location.
            skills: List of skill names.

        Returns:
            Dict with formatted context strings.
        """
        return {
            "primary_role": primary_role or "Not specified",
            "primary_industry": primary_industry or "Not specified",
            "seniority_level": seniority_level or "mid",
            "location": location or "Not specified",
            "skills": ", ".join(skills[:20]) if skills else "No skills listed",
        }

    @staticmethod
    def validate_milestone_timeline(
        *,
        target_date: date | None,
        sprint_weeks: int,
    ) -> date | None:
        """Ensure milestone target date is within reasonable sprint range.

        Args:
            target_date: Proposed target date.
            sprint_weeks: Sprint length in weeks.

        Returns:
            Validated date or None if invalid.
        """
        if target_date is None:
            return None

        today = date.today()
        max_date = today + timedelta(weeks=max(sprint_weeks, 1) + 2)

        if target_date < today:
            return today + timedelta(days=7)
        if target_date > max_date:
            return max_date
        return target_date


# ── Clamping Validators (module-level, testable) ──────────────


def _clamp_confidence_field(data: dict[str, Any]) -> None:
    """Clamp the confidence field in-place."""
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    data["confidence"] = round(
        max(0.0, min(float(confidence), MAX_PLAN_CONFIDENCE)), 3,
    )


def _clamp_priorities(data: dict[str, Any]) -> None:
    """Validate and clamp priority analysis fields in-place."""
    _clamp_confidence_field(data)

    priorities = data.get("priorities", [])
    if not isinstance(priorities, list):
        data["priorities"] = []
        return

    clamped_priorities: list[dict[str, Any]] = []
    for priority in priorities[:5]:
        if not isinstance(priority, dict):
            continue

        impact = priority.get("impact_score", 50.0)
        if not isinstance(impact, (int, float)):
            impact = 50.0
        priority["impact_score"] = round(
            max(0.0, min(float(impact), MAX_IMPACT_SCORE)), 2,
        )

        urgency = priority.get("urgency", "medium")
        if urgency not in VALID_URGENCY_LEVELS:
            priority["urgency"] = "medium"

        category = priority.get("category", "learning")
        if category not in VALID_MILESTONE_CATEGORIES:
            priority["category"] = "learning"

        if not priority.get("title"):
            priority["title"] = "Unnamed priority"
        if not priority.get("description"):
            priority["description"] = "No description provided."
        if not priority.get("rationale"):
            priority["rationale"] = "AI-generated priority."

        clamped_priorities.append(priority)

    data["priorities"] = clamped_priorities

    if not data.get("overall_assessment"):
        data["overall_assessment"] = "Assessment pending."


def _clamp_milestones(
    data: dict[str, Any],
    *,
    max_milestones: int = 5,
) -> None:
    """Validate and clamp milestone generation fields in-place."""
    _clamp_confidence_field(data)

    milestones = data.get("milestones", [])
    if not isinstance(milestones, list):
        data["milestones"] = []
        return

    clamped_milestones: list[dict[str, Any]] = []
    for milestone_data in milestones[:max_milestones]:
        if not isinstance(milestone_data, dict):
            continue

        category = milestone_data.get("category", "learning")
        if category not in VALID_MILESTONE_CATEGORIES:
            milestone_data["category"] = "learning"

        effort = milestone_data.get("effort_hours", 8)
        if not isinstance(effort, (int, float)):
            effort = 8
        milestone_data["effort_hours"] = max(1, min(int(effort), 120))

        priority_val = milestone_data.get("priority", 5)
        if not isinstance(priority_val, (int, float)):
            priority_val = 5
        milestone_data["priority"] = max(1, min(int(priority_val), 10))

        if not milestone_data.get("title"):
            milestone_data["title"] = "Unnamed milestone"
        if not milestone_data.get("description"):
            milestone_data["description"] = "No description provided."
        if not milestone_data.get("evidence_required"):
            milestone_data["evidence_required"] = (
                "Self-reported completion."
            )

        clamped_milestones.append(milestone_data)

    data["milestones"] = clamped_milestones

    if not data.get("sprint_summary"):
        data["sprint_summary"] = "Career sprint plan."


def _clamp_progress_evaluation(data: dict[str, Any]) -> None:
    """Validate and clamp progress evaluation fields in-place."""
    _clamp_confidence_field(data)

    health = data.get("plan_health", "at_risk")
    valid_health = {"on_track", "at_risk", "behind", "ahead"}
    if health not in valid_health:
        data["plan_health"] = "at_risk"

    progress = data.get("overall_progress_percent", 0.0)
    if not isinstance(progress, (int, float)):
        progress = 0.0
    data["overall_progress_percent"] = round(
        max(0.0, min(float(progress), 100.0)), 2,
    )

    assessments = data.get("milestone_assessments", [])
    if not isinstance(assessments, list):
        data["milestone_assessments"] = []

    adjustments = data.get("priority_adjustments", [])
    if not isinstance(adjustments, list):
        data["priority_adjustments"] = []


def _clamp_recommendations(data: dict[str, Any]) -> None:
    """Validate and clamp recommendations fields in-place."""
    _clamp_confidence_field(data)

    recommendations = data.get("recommendations", [])
    if not isinstance(recommendations, list):
        data["recommendations"] = []
        return

    clamped_recs: list[dict[str, Any]] = []
    for rec in recommendations[:5]:
        if not isinstance(rec, dict):
            continue

        engine = rec.get("source_engine", "")
        if engine not in VALID_SOURCE_ENGINES:
            rec["source_engine"] = "predictive_career"

        urgency = rec.get("urgency", "medium")
        if urgency not in VALID_URGENCY_LEVELS:
            rec["urgency"] = "medium"

        impact = rec.get("impact_score", 50.0)
        if not isinstance(impact, (int, float)):
            impact = 50.0
        rec["impact_score"] = round(
            max(0.0, min(float(impact), MAX_IMPACT_SCORE)), 2,
        )

        if not rec.get("title"):
            rec["title"] = "Unnamed recommendation"
        if not rec.get("rationale"):
            rec["rationale"] = "AI-generated recommendation."
        if not rec.get("recommendation_type"):
            rec["recommendation_type"] = "general"

        clamped_recs.append(rec)

    data["recommendations"] = clamped_recs
