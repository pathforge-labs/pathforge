"""
PathForge — Career Action Planner™ Service
=============================================
Pipeline orchestration for the Career Action Planner™.

Coordinates AI analyzer calls with database persistence,
Career DNA context extraction, and response composition.

Pipeline Methods:
    get_dashboard          — Active plans with stats and recommendations
    generate_plan          — Full plan generation pipeline
    get_plan               — Retrieve plan with milestones + progress
    update_plan_status     — Activate, pause, complete, or archive
    get_milestones         — List milestones for a plan
    update_milestone       — Update milestone status/fields
    log_progress           — Log progress against a milestone
    get_preferences        — Get user planner preferences
    update_preferences     — Update user planner preferences

Delegated to helpers:
    compare_plans          → _career_action_planner_helpers
    aggregate_intelligence → _career_action_planner_helpers
    compute_stats          → _career_action_planner_helpers
    compute_priority_score → _career_action_planner_helpers
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.career_action_planner_analyzer import CareerActionPlannerAnalyzer
from app.models.career_action_planner import (
    CareerActionPlan,
    CareerActionPlannerPreference,
    MilestoneProgress,
    MilestoneStatus,
    PlanMilestone,
    PlanRecommendation,
    PlanStatus,
    PlanType,
)
from app.models.career_dna import CareerDNA
from app.schemas.career_action_planner import (
    CareerActionPlannerPreferenceUpdate,
    GeneratePlanRequest,
    LogProgressRequest,
    UpdateMilestoneRequest,
)
from app.services._career_action_planner_helpers import (
    ComparePlansResult,  # noqa: F401 — re-exported for service.compare_plans
    DashboardResult,
    GeneratePlanResult,
    aggregate_intelligence,
    compare_plans,  # noqa: F401 — re-exported for service.compare_plans
    compute_priority_score,
    compute_stats,
)

logger = logging.getLogger(__name__)

# ── Plan type label mapping ────────────────────────────────────

PLAN_TYPE_LABELS: dict[str, str] = {
    PlanType.SKILL_DEVELOPMENT.value: "Skill Development Sprint",
    PlanType.ROLE_TRANSITION.value: "Role Transition Plan",
    PlanType.SALARY_GROWTH.value: "Salary Growth Strategy",
    PlanType.THREAT_MITIGATION.value: "Threat Mitigation Plan",
    PlanType.OPPORTUNITY_CAPTURE.value: "Opportunity Capture Sprint",
}

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    PlanStatus.DRAFT.value: {
        PlanStatus.ACTIVE.value, PlanStatus.ARCHIVED.value,
    },
    PlanStatus.ACTIVE.value: {
        PlanStatus.PAUSED.value, PlanStatus.COMPLETED.value,
        PlanStatus.ARCHIVED.value,
    },
    PlanStatus.PAUSED.value: {
        PlanStatus.ACTIVE.value, PlanStatus.ARCHIVED.value,
    },
    PlanStatus.COMPLETED.value: {PlanStatus.ARCHIVED.value},
    PlanStatus.ARCHIVED.value: set(),
}


# ── Private Helpers ────────────────────────────────────────────


async def _get_career_dna_with_context(
    database: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Fetch CareerDNA with eager-loaded skill genome."""
    result = await database.execute(
        select(CareerDNA)
        .where(CareerDNA.user_id == user_id)
        .options(
            selectinload(CareerDNA.skill_genome),
            selectinload(CareerDNA.experience_blueprint),
        )
    )
    return result.scalar_one_or_none()


def _format_skills_for_prompt(career_dna: CareerDNA) -> str:
    """Format skill genome as comma-separated string for prompts."""
    if not career_dna.skill_genome:
        return "No skills recorded"
    return ", ".join(
        f"{entry.skill_name} ({entry.proficiency_level})"
        for entry in career_dna.skill_genome[:20]
    )


def _get_skill_names(career_dna: CareerDNA) -> list[str]:
    """Extract skill name list from Career DNA."""
    if not career_dna.skill_genome:
        return []
    return [entry.skill_name for entry in career_dna.skill_genome[:20]]





# ── Dashboard ──────────────────────────────────────────────────


async def get_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> DashboardResult:
    """Get Career Action Planner dashboard.

    Returns active plans with stats, recommendations, and preferences.

    Args:
        database: Async database session.
        user_id: Current user's UUID.

    Returns:
        Dict with active_plans, recent_recommendations, stats, preferences.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        return DashboardResult(
            active_plans=[],
            recent_recommendations=[],
            stats=compute_stats([]),
            preferences=None,
        )

    # Fetch all plans for this user
    plans_result = await database.execute(
        select(CareerActionPlan)
        .where(CareerActionPlan.user_id == user_id)
        .options(
            selectinload(CareerActionPlan.milestones),
            selectinload(CareerActionPlan.recommendations),
        )
        .order_by(CareerActionPlan.created_at.desc())
    )
    all_plans = list(plans_result.scalars().all())

    # Active plans
    active_plans = [
        plan for plan in all_plans
        if plan.status in {PlanStatus.ACTIVE.value, PlanStatus.DRAFT.value}
    ]

    # Build plan summaries with milestone counts
    plan_summaries: list[dict[str, Any]] = []
    for plan in active_plans:
        milestone_count = len(plan.milestones) if plan.milestones else 0
        completed_count = sum(
            1 for milestone in (plan.milestones or [])
            if milestone.status == MilestoneStatus.COMPLETED.value
        )
        plan_summaries.append({
            "id": plan.id,
            "title": plan.title,
            "plan_type": plan.plan_type,
            "status": plan.status,
            "priority_score": plan.priority_score,
            "confidence": plan.confidence,
            "milestone_count": milestone_count,
            "completed_milestone_count": completed_count,
            "created_at": plan.created_at,
        })

    # Recent recommendations (from all plans)
    recent_recs: list[PlanRecommendation] = []
    for plan in all_plans[:5]:
        if plan.recommendations:
            recent_recs.extend(plan.recommendations[:3])
    recent_recs = recent_recs[:10]

    # Preferences
    pref_result = await database.execute(
        select(CareerActionPlannerPreference)
        .where(CareerActionPlannerPreference.user_id == user_id)
    )
    pref = pref_result.scalar_one_or_none()

    return DashboardResult(
        active_plans=plan_summaries,
        recent_recommendations=recent_recs,
        stats=compute_stats(all_plans),
        preferences=pref,
    )





# ── Plan Generation ───────────────────────────────────────────


async def generate_plan(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    request_data: GeneratePlanRequest,
) -> GeneratePlanResult:
    """Generate a new career action plan.

    Full pipeline: Career DNA → priorities → milestones → recommendations.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        request_data: Plan generation request.

    Returns:
        Dict with plan and recommendations.

    Raises:
        ValueError: If CareerDNA not found or invalid plan type.
    """
    # Validate plan type
    valid_types = {member.value for member in PlanType}
    if request_data.plan_type not in valid_types:
        raise ValueError(
            f"Invalid plan type: {request_data.plan_type}. "
            f"Valid types: {', '.join(sorted(valid_types))}"
        )

    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    # Get preferences
    pref_result = await database.execute(
        select(CareerActionPlannerPreference)
        .where(CareerActionPlannerPreference.user_id == user_id)
    )
    pref = pref_result.scalar_one_or_none()

    sprint_weeks = (
        pref.preferred_sprint_length_weeks if pref
        else request_data.target_timeline_weeks
    )
    max_milestones = pref.max_milestones_per_plan if pref else 5

    # Build context
    context = CareerActionPlannerAnalyzer.build_priority_context(
        primary_role=career_dna.primary_role,
        primary_industry=career_dna.primary_industry,
        seniority_level=career_dna.seniority_level,
        location=career_dna.location,
        skills=_get_skill_names(career_dna),
    )

    # Aggregate intelligence from other engines
    intelligence_summary = await aggregate_intelligence(database, career_dna)

    # Step 1: Analyze priorities
    priorities_result = await CareerActionPlannerAnalyzer.analyze_career_priorities(
        primary_role=context["primary_role"],
        primary_industry=context["primary_industry"],
        seniority_level=context["seniority_level"],
        location=context["location"],
        skills=context["skills"],
        plan_type=request_data.plan_type,
        focus_area=request_data.focus_area or "",
        intelligence_summary=intelligence_summary,
    )

    # Build plan title and objective from priorities
    plan_label = PLAN_TYPE_LABELS.get(
        request_data.plan_type, "Career Development Plan",
    )
    overall_assessment = priorities_result.get(
        "overall_assessment", "Career development in progress.",
    )

    plan = CareerActionPlan(
        career_dna_id=str(career_dna.id),
        user_id=str(user_id),
        title=f"{plan_label} — {sprint_weeks}-Week Sprint",
        objective=overall_assessment,
        plan_type=request_data.plan_type,
        status=PlanStatus.DRAFT.value,
        priority_score=compute_priority_score(priorities_result),
        confidence=CareerActionPlannerAnalyzer.clamp_confidence(
            priorities_result.get("confidence", 0.0),
        ),
    )

    database.add(plan)
    await database.flush()

    # Step 2: Generate milestones
    milestones_result = await CareerActionPlannerAnalyzer.generate_milestones(
        primary_role=context["primary_role"],
        seniority_level=context["seniority_level"],
        skills=context["skills"],
        plan_type=request_data.plan_type,
        plan_title=plan.title,
        plan_objective=plan.objective,
        sprint_weeks=sprint_weeks,
        max_milestones=max_milestones,
        priorities_json=json.dumps(
            priorities_result.get("priorities", []), indent=2,
        ),
    )

    # Persist milestones
    today = date.today()
    for milestone_data in milestones_result.get("milestones", []):
        target_week = milestone_data.get("target_week", 1)
        target_date_val = today + timedelta(weeks=min(target_week, sprint_weeks))

        validated_date = CareerActionPlannerAnalyzer.validate_milestone_timeline(
            target_date=target_date_val,
            sprint_weeks=sprint_weeks,
        )

        milestone = PlanMilestone(
            plan_id=str(plan.id),
            title=milestone_data.get("title", "Unnamed milestone"),
            description=milestone_data.get("description"),
            category=milestone_data.get("category", "learning"),
            target_date=validated_date,
            status=MilestoneStatus.NOT_STARTED.value,
            effort_hours=milestone_data.get("effort_hours", 8),
            priority=milestone_data.get("priority", 5),
            evidence_required=milestone_data.get("evidence_required"),
        )
        database.add(milestone)

    # Step 3: Generate recommendations
    recommendations_result = await CareerActionPlannerAnalyzer.generate_recommendations(
        primary_role=context["primary_role"],
        primary_industry=context["primary_industry"],
        seniority_level=context["seniority_level"],
        plan_type=request_data.plan_type,
        plan_title=plan.title,
        engine_outputs=intelligence_summary,
    )

    recs_created: list[PlanRecommendation] = []
    for rec_data in recommendations_result.get("recommendations", []):
        rec = PlanRecommendation(
            plan_id=str(plan.id),
            source_engine=rec_data.get("source_engine", "predictive_career"),
            recommendation_type=rec_data.get("recommendation_type", "general"),
            title=rec_data.get("title", "Unnamed recommendation"),
            rationale=rec_data.get("rationale", "AI-generated."),
            urgency=rec_data.get("urgency", "medium"),
            impact_score=CareerActionPlannerAnalyzer.clamp_impact_score(
                rec_data.get("impact_score", 50.0),
            ),
        )
        database.add(rec)
        recs_created.append(rec)

    await database.commit()

    # Reload with relationships
    plan_result = await database.execute(
        select(CareerActionPlan)
        .where(CareerActionPlan.id == plan.id)
        .options(
            selectinload(CareerActionPlan.milestones),
            selectinload(CareerActionPlan.recommendations),
        )
    )
    full_plan = plan_result.scalar_one()

    return GeneratePlanResult(
        plan=full_plan,
        recommendations=list(full_plan.recommendations),
    )





# ── Plan Retrieval ─────────────────────────────────────────────


async def get_plan(
    database: AsyncSession,
    *,
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CareerActionPlan | None:
    """Retrieve a plan with milestones and progress.

    Args:
        database: Async database session.
        plan_id: Plan UUID.
        user_id: Current user's UUID.

    Returns:
        CareerActionPlan with relationships or None.
    """
    result = await database.execute(
        select(CareerActionPlan)
        .where(
            CareerActionPlan.id == plan_id,
            CareerActionPlan.user_id == user_id,
        )
        .options(
            selectinload(CareerActionPlan.milestones).selectinload(
                PlanMilestone.progress_entries,
            ),
            selectinload(CareerActionPlan.recommendations),
        )
    )
    return result.scalar_one_or_none()


# ── Plan Status Updates ────────────────────────────────────────


async def update_plan_status(
    database: AsyncSession,
    *,
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
    new_status: str,
) -> CareerActionPlan:
    """Update plan status with transition validation.

    Args:
        database: Async database session.
        plan_id: Plan UUID.
        user_id: Current user's UUID.
        new_status: Target status.

    Returns:
        Updated CareerActionPlan.

    Raises:
        ValueError: If plan not found or invalid transition.
    """
    plan = await get_plan(database, plan_id=plan_id, user_id=user_id)
    if not plan:
        raise ValueError("Plan not found.")

    allowed = VALID_STATUS_TRANSITIONS.get(plan.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{plan.status}' to '{new_status}'. "
            f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none'}."
        )

    plan.status = new_status
    await database.commit()
    await database.refresh(plan)
    return plan


# ── Milestones ─────────────────────────────────────────────────


async def get_milestones(
    database: AsyncSession,
    *,
    plan_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[PlanMilestone]:
    """List milestones for a plan.

    Args:
        database: Async database session.
        plan_id: Plan UUID.
        user_id: Current user's UUID.

    Returns:
        List of PlanMilestone with progress entries.

    Raises:
        ValueError: If plan not found.
    """
    plan = await get_plan(database, plan_id=plan_id, user_id=user_id)
    if not plan:
        raise ValueError("Plan not found.")
    return list(plan.milestones) if plan.milestones else []


async def update_milestone(
    database: AsyncSession,
    *,
    plan_id: uuid.UUID,
    milestone_id: uuid.UUID,
    user_id: uuid.UUID,
    update_data: UpdateMilestoneRequest,
) -> PlanMilestone:
    """Update a milestone's status or fields.

    Args:
        database: Async database session.
        plan_id: Plan UUID.
        milestone_id: Milestone UUID.
        user_id: Current user's UUID.
        update_data: Milestone update request.

    Returns:
        Updated PlanMilestone.

    Raises:
        ValueError: If plan or milestone not found.
    """
    plan = await get_plan(database, plan_id=plan_id, user_id=user_id)
    if not plan:
        raise ValueError("Plan not found.")

    milestone = None
    for milestone_entry in (plan.milestones or []):
        if str(milestone_entry.id) == str(milestone_id):
            milestone = milestone_entry
            break

    if not milestone:
        raise ValueError("Milestone not found in this plan.")

    if update_data.status is not None:
        valid_statuses = {member.value for member in MilestoneStatus}
        if update_data.status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {update_data.status}. "
                f"Valid: {', '.join(sorted(valid_statuses))}"
            )
        milestone.status = update_data.status

    if update_data.target_date is not None:
        milestone.target_date = update_data.target_date
    if update_data.effort_hours is not None:
        milestone.effort_hours = update_data.effort_hours
    if update_data.priority is not None:
        milestone.priority = update_data.priority

    await database.commit()
    await database.refresh(milestone)
    return milestone


# ── Progress Logging ──────────────────────────────────────────


async def log_progress(
    database: AsyncSession,
    *,
    plan_id: uuid.UUID,
    milestone_id: uuid.UUID,
    user_id: uuid.UUID,
    progress_data: LogProgressRequest,
) -> MilestoneProgress:
    """Log progress against a milestone.

    Args:
        database: Async database session.
        plan_id: Plan UUID.
        milestone_id: Milestone UUID.
        user_id: Current user's UUID.
        progress_data: Progress log request.

    Returns:
        Created MilestoneProgress entry.

    Raises:
        ValueError: If plan or milestone not found.
    """
    plan = await get_plan(database, plan_id=plan_id, user_id=user_id)
    if not plan:
        raise ValueError("Plan not found.")

    milestone = None
    for milestone_entry in (plan.milestones or []):
        if str(milestone_entry.id) == str(milestone_id):
            milestone = milestone_entry
            break

    if not milestone:
        raise ValueError("Milestone not found in this plan.")

    entry = MilestoneProgress(
        milestone_id=str(milestone.id),
        progress_percent=progress_data.progress_percent,
        notes=progress_data.notes,
        evidence_url=progress_data.evidence_url,
        logged_at=datetime.now(tz=timezone.utc),  # noqa: UP017
    )

    database.add(entry)

    # Auto-update milestone status based on progress
    if progress_data.progress_percent >= 100.0:
        milestone.status = MilestoneStatus.COMPLETED.value
    elif (
        progress_data.progress_percent > 0.0
        and milestone.status == MilestoneStatus.NOT_STARTED.value
    ):
        milestone.status = MilestoneStatus.IN_PROGRESS.value

    await database.commit()
    await database.refresh(entry)
    return entry


# ── Plan Comparison ───────────────────────────────────────────


# compare_plans has been extracted to _career_action_planner_helpers.py
# Re-exported via import at module top for backward compatibility.


# ── Preferences ────────────────────────────────────────────────


async def get_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> CareerActionPlannerPreference | None:
    """Get Career Action Planner preferences.

    Args:
        database: Async database session.
        user_id: Current user's UUID.

    Returns:
        CareerActionPlannerPreference or None.
    """
    result = await database.execute(
        select(CareerActionPlannerPreference)
        .where(CareerActionPlannerPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    update_data: CareerActionPlannerPreferenceUpdate,
) -> CareerActionPlannerPreference:
    """Update or create Career Action Planner preferences.

    Args:
        database: Async database session.
        user_id: Current user's UUID.
        update_data: Preference update payload.

    Returns:
        Updated or created preference record.

    Raises:
        ValueError: If Career DNA not found.
    """
    career_dna = await _get_career_dna_with_context(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA profile not found. Create one first.")

    result = await database.execute(
        select(CareerActionPlannerPreference)
        .where(CareerActionPlannerPreference.career_dna_id == career_dna.id)
    )
    pref = result.scalar_one_or_none()

    if not pref:
        pref = CareerActionPlannerPreference(
            career_dna_id=str(career_dna.id),
            user_id=str(user_id),
        )
        database.add(pref)

    if update_data.preferred_sprint_length_weeks is not None:
        pref.preferred_sprint_length_weeks = (
            update_data.preferred_sprint_length_weeks
        )
    if update_data.max_milestones_per_plan is not None:
        pref.max_milestones_per_plan = update_data.max_milestones_per_plan
    if update_data.focus_areas is not None:
        pref.focus_areas = update_data.focus_areas
    if update_data.notification_frequency is not None:
        pref.notification_frequency = update_data.notification_frequency
    if update_data.auto_generate_recommendations is not None:
        pref.auto_generate_recommendations = (
            update_data.auto_generate_recommendations
        )

    await database.commit()
    await database.refresh(pref)
    return pref
