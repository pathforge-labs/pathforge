"""
PathForge — Career Action Planner™ Service Helpers
=====================================================
Extracted helper functions for Career Action Planner™ service layer.

Contains:
    _aggregate_intelligence  — Gather intelligence engine outputs
    _compute_stats           — Compute aggregate plan statistics
    _compute_priority_score  — Compute priority score from analysis
    compare_plans            — Compare multiple career plan scenarios
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career_action_planner import (
    CareerActionPlan,
    CareerActionPlannerPreference,
    MilestoneStatus,
    PlanRecommendation,
    PlanStatus,
)
from app.models.career_dna import CareerDNA

# ── Typed Pipeline Result DTOs ─────────────────────────────────


@dataclass(frozen=True, slots=True)
class DashboardResult:
    """Typed result from get_dashboard pipeline."""

    active_plans: list[dict[str, Any]]
    recent_recommendations: list[PlanRecommendation]
    stats: dict[str, int | float]
    preferences: CareerActionPlannerPreference | None


@dataclass(frozen=True, slots=True)
class GeneratePlanResult:
    """Typed result from generate_plan pipeline."""

    plan: CareerActionPlan
    recommendations: list[PlanRecommendation]


@dataclass(frozen=True, slots=True)
class ComparePlansResult:
    """Typed result from compare_plans pipeline."""

    plans: list[CareerActionPlan]
    recommended_plan_id: uuid.UUID | None
    recommendation_reasoning: str


# ── Intelligence Aggregation ──────────────────────────────────


async def aggregate_intelligence(
    database: AsyncSession,
    career_dna: CareerDNA,
) -> str:
    """Gather latest outputs from intelligence engines as summary string.

    Collects recent data from Threat Radar, Skill Decay, Salary Intelligence,
    and other engines linked to the Career DNA profile.

    Args:
        database: Async database session.
        career_dna: User's career DNA profile.

    Returns:
        Formatted intelligence summary string for LLM prompts.
    """
    _ = database  # Available for future engine queries

    summary_parts: list[str] = []

    # Threat Radar context
    if hasattr(career_dna, "automation_risk") and career_dna.automation_risk:
        risk = career_dna.automation_risk
        risk_score = getattr(risk, "risk_score", None)
        if risk_score is not None:
            summary_parts.append(
                f"Automation Risk: {risk_score:.0f}% "
                f"({getattr(risk, 'risk_level', 'unknown')} level)"
            )

    # Recent threat alerts
    if hasattr(career_dna, "threat_alerts") and career_dna.threat_alerts:
        recent_alerts = career_dna.threat_alerts[:3]
        alert_titles = [
            getattr(alert, "title", "Unknown") for alert in recent_alerts
        ]
        if alert_titles:
            summary_parts.append(
                f"Recent Threat Alerts: {', '.join(alert_titles)}"
            )

    # Skill Decay context
    if hasattr(career_dna, "skill_freshness") and career_dna.skill_freshness:
        decaying = [
            entry for entry in career_dna.skill_freshness
            if getattr(entry, "freshness_score", 1.0) < 0.5
        ]
        if decaying:
            skill_names = [
                getattr(entry, "skill_name", "Unknown")
                for entry in decaying[:5]
            ]
            summary_parts.append(
                f"Decaying Skills: {', '.join(skill_names)}"
            )

    # Growth vector context
    if hasattr(career_dna, "growth_vector") and career_dna.growth_vector:
        vector = career_dna.growth_vector
        trajectory = getattr(vector, "current_trajectory", "steady")
        growth_score = getattr(vector, "growth_score", 50.0)
        summary_parts.append(
            f"Growth Trajectory: {trajectory} (score: {growth_score:.1f})"
        )

    # Market position context
    if hasattr(career_dna, "market_position") and career_dna.market_position:
        position = career_dna.market_position
        percentile = getattr(position, "percentile_overall", 50.0)
        trend = getattr(position, "market_trend", "stable")
        summary_parts.append(
            f"Market Position: {percentile:.0f}th percentile ({trend})"
        )

    if not summary_parts:
        return "No recent intelligence data available."

    return "\n".join(f"- {part}" for part in summary_parts)


# ── Statistics Computation ────────────────────────────────────


def compute_stats(plans: list[CareerActionPlan]) -> dict[str, int | float]:
    """Compute aggregate statistics from plans."""
    total = len(plans)
    active = sum(
        1 for plan in plans
        if plan.status == PlanStatus.ACTIVE.value
    )
    completed = sum(
        1 for plan in plans
        if plan.status == PlanStatus.COMPLETED.value
    )

    total_milestones = 0
    completed_milestones = 0
    for plan in plans:
        if plan.milestones:
            total_milestones += len(plan.milestones)
            completed_milestones += sum(
                1 for milestone in plan.milestones
                if milestone.status == MilestoneStatus.COMPLETED.value
            )

    progress = (
        (completed_milestones / total_milestones * 100.0)
        if total_milestones > 0 else 0.0
    )

    return {
        "total_plans": total,
        "active_plans": active,
        "completed_plans": completed,
        "total_milestones": total_milestones,
        "completed_milestones": completed_milestones,
        "overall_progress_percent": round(progress, 2),
    }


def compute_priority_score(priorities_result: dict[str, Any]) -> float:
    """Compute overall priority score from priority analysis result."""
    priorities = priorities_result.get("priorities", [])
    if not priorities:
        return 50.0

    impact_scores = [
        p.get("impact_score", 50.0)
        for p in priorities
        if isinstance(p, dict)
    ]

    if not impact_scores:
        return 50.0

    avg_impact = sum(impact_scores) / len(impact_scores)
    return float(round(max(0.0, min(avg_impact, 100.0)), 2))


# ── Plan Comparison ───────────────────────────────────────────


async def compare_plans(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    plan_ids: list[uuid.UUID] | None = None,
) -> ComparePlansResult:
    """Compare user's plans for recommendation.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        plan_ids: Optional specific plan IDs to compare.

    Returns:
        ComparePlansResult with plans, recommended_plan_id, and reasoning.
    """
    if plan_ids:
        plans_result = await database.execute(
            select(CareerActionPlan)
            .where(
                CareerActionPlan.user_id == user_id,
                CareerActionPlan.id.in_([str(pid) for pid in plan_ids]),
            )
            .options(
                selectinload(CareerActionPlan.milestones),
                selectinload(CareerActionPlan.recommendations),
            )
        )
    else:
        plans_result = await database.execute(
            select(CareerActionPlan)
            .where(CareerActionPlan.user_id == user_id)
            .options(
                selectinload(CareerActionPlan.milestones),
                selectinload(CareerActionPlan.recommendations),
            )
            .order_by(CareerActionPlan.priority_score.desc())
            .limit(5)
        )

    plans = list(plans_result.scalars().all())

    if len(plans) < 2:
        return ComparePlansResult(
            plans=plans,
            recommended_plan_id=plans[0].id if plans else None,
            recommendation_reasoning=(
                "Only one plan available — no comparison needed."
                if plans else "No plans found."
            ),
        )

    # Recommend the plan with the highest priority score
    best_plan = max(plans, key=lambda p: p.priority_score)

    return ComparePlansResult(
        plans=plans,
        recommended_plan_id=best_plan.id,
        recommendation_reasoning=(
            f"'{best_plan.title}' has the highest priority score "
            f"({best_plan.priority_score:.1f}/100) based on career "
            f"intelligence analysis."
        ),
    )
