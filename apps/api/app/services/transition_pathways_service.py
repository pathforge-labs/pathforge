"""
PathForge — Transition Pathways Service
==========================================
Pipeline orchestration for the Transition Pathways module.

Coordinates AI analyzer calls with database persistence,
Career DNA integration, and user preference management.

Primary pipeline: explore_transition()
    1. Load Career DNA context (skills, role, seniority)
    2. Analyze transition feasibility (LLM #1)
    3. Generate skill bridge (LLM #2)
    4. Create milestones (LLM #3)
    5. Compare roles (LLM #4)
    6. Persist all results
    7. Return composite response
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer
from app.models.career_dna import CareerDNA
from app.models.transition_pathways import (
    SkillBridgeEntry,
    TransitionComparison,
    TransitionMilestone,
    TransitionPath,
    TransitionPreference,
)
from app.schemas.transition_pathways import (
    TransitionPreferenceUpdateRequest,
)

logger = logging.getLogger(__name__)


# ── Private Helpers ────────────────────────────────────────────


async def _get_career_dna_with_genome(
    database: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Fetch CareerDNA with eager-loaded skill genome."""
    result = await database.execute(
        select(CareerDNA)
        .where(CareerDNA.user_id == user_id)
        .options(selectinload(CareerDNA.skill_genome))
    )
    return result.scalar_one_or_none()


def _format_skills_for_prompt(career_dna: CareerDNA) -> str:
    """Format Career DNA skill genome as comma-separated string."""
    if not career_dna.skill_genome:
        return "No skills recorded"
    return ", ".join(
        f"{entry.skill_name} ({entry.proficiency_level})"
        for entry in career_dna.skill_genome
    )


def _get_skill_names(career_dna: CareerDNA) -> list[str]:
    """Extract skill names from Career DNA genome."""
    if not career_dna.skill_genome:
        return []
    return [entry.skill_name for entry in career_dna.skill_genome]


def _get_years_experience(career_dna: CareerDNA) -> int:
    """Estimate years of experience from Career DNA context."""
    if career_dna.skill_genome:
        max_years = max(
            (entry.years_experience or 0 for entry in career_dna.skill_genome),
            default=0,
        )
        return max_years
    return 3  # Conservative default


# ── Public Service Methods ─────────────────────────────────────


async def explore_transition(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_role: str,
    target_industry: str | None = None,
    target_location: str | None = None,
) -> dict[str, Any]:
    """
    Full exploration pipeline: analyze → skill bridge → milestones → compare.

    This is the primary entry point for the Transition Pathways module.
    Orchestrates 4 LLM calls and persists all results.

    Args:
        database: Async database session.
        user_id: Current user ID.
        target_role: Target role to explore transition to.
        target_industry: Optional target industry.
        target_location: Optional target location.

    Returns:
        Dict with transition_path, skill_bridge, milestones, comparisons.

    Raises:
        ValueError: If CareerDNA not found for user.
    """
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found. Please complete Career DNA analysis first.")

    from_role = career_dna.primary_role or "Unknown Role"
    location = career_dna.location or "Netherlands"
    industry = career_dna.primary_industry or "Technology"
    seniority = career_dna.seniority_level or "mid"
    skills_text = _format_skills_for_prompt(career_dna)
    skill_names = _get_skill_names(career_dna)
    years_exp = _get_years_experience(career_dna)

    logger.info(
        "Exploring transition: %s → %s (user=%s)",
        from_role, target_role, user_id,
    )

    # ── Step 1: Analyze transition feasibility ─────────────
    analysis = await TransitionPathwaysAnalyzer.analyze_transition(
        from_role=from_role,
        to_role=target_role,
        seniority_level=seniority,
        location=location,
        industry=industry,
        years_experience=years_exp,
        current_skills=skills_text,
        target_industry=target_industry,
        target_location=target_location,
    )

    if not analysis:
        logger.warning("Transition analysis returned empty — using defaults")
        analysis = _default_analysis(from_role, target_role)

    # Recompute confidence with static helpers
    target_skills_from_analysis: list[str] = [
        skill for skill in analysis.get("factors", {})
        if skill != "skill_match"
    ]
    static_overlap = TransitionPathwaysAnalyzer.compute_skill_overlap(
        current_skills=skill_names,
        target_skills=target_skills_from_analysis or [target_role],
    )
    final_confidence = TransitionPathwaysAnalyzer.compute_transition_confidence(
        skill_overlap_percent=analysis.get("skill_overlap_percent", static_overlap),
        llm_confidence=analysis.get("confidence_score", 0.5),
    )
    analysis["confidence_score"] = final_confidence

    # ── Step 2: Generate skill bridge ──────────────────────
    skill_bridge_data = await TransitionPathwaysAnalyzer.generate_skill_bridge(
        current_skills=skills_text,
        from_role=from_role,
        to_role=target_role,
        target_industry=target_industry,
    )

    # ── Step 3: Create milestones ──────────────────────────
    skills_to_acquire_names = ", ".join(
        skill["skill_name"]
        for skill in skill_bridge_data
        if not skill.get("is_already_held", False)
    ) or "No additional skills needed"

    milestones_data = await TransitionPathwaysAnalyzer.create_milestones(
        from_role=from_role,
        to_role=target_role,
        skills_to_acquire=skills_to_acquire_names,
        estimated_months=analysis.get("estimated_duration_months", 12),
        difficulty=analysis.get("difficulty", "moderate"),
    )

    # ── Step 4: Compare roles ──────────────────────────────
    comparisons_data = await TransitionPathwaysAnalyzer.compare_roles(
        from_role=from_role,
        to_role=target_role,
        location=target_location or location,
        seniority_level=seniority,
        industry=target_industry or industry,
    )

    # ── Step 5: Persist to database ────────────────────────
    transition_path = TransitionPath(
        career_dna_id=career_dna.id,
        from_role=from_role,
        to_role=target_role,
        confidence_score=analysis.get("confidence_score", 0.0),
        difficulty=analysis.get("difficulty", "moderate"),
        skill_overlap_percent=analysis.get("skill_overlap_percent", 0.0),
        skills_to_acquire_count=analysis.get("skills_to_acquire_count", 0),
        estimated_duration_months=analysis.get("estimated_duration_months"),
        optimistic_months=analysis.get("optimistic_months"),
        realistic_months=analysis.get("realistic_months"),
        conservative_months=analysis.get("conservative_months"),
        salary_impact_percent=analysis.get("salary_impact_percent"),
        success_probability=analysis.get("success_probability", 0.0),
        reasoning=analysis.get("reasoning"),
        factors=analysis.get("factors"),
    )
    database.add(transition_path)
    await database.flush()

    # Persist skill bridge entries
    skill_entries: list[SkillBridgeEntry] = []
    for skill_data in skill_bridge_data:
        entry = SkillBridgeEntry(
            transition_path_id=transition_path.id,
            skill_name=skill_data.get("skill_name", "Unknown"),
            category=skill_data.get("category", "technical"),
            is_already_held=skill_data.get("is_already_held", False),
            current_level=skill_data.get("current_level"),
            required_level=skill_data.get("required_level"),
            acquisition_method=skill_data.get("acquisition_method"),
            estimated_weeks=skill_data.get("estimated_weeks"),
            recommended_resources=skill_data.get("recommended_resources"),
            priority=skill_data.get("priority", "medium"),
            impact_on_confidence=skill_data.get("impact_on_confidence"),
        )
        database.add(entry)
        skill_entries.append(entry)

    # Persist milestones
    milestone_entries: list[TransitionMilestone] = []
    for milestone_data in milestones_data:
        milestone = TransitionMilestone(
            transition_path_id=transition_path.id,
            phase=milestone_data.get("phase", "preparation"),
            title=milestone_data.get("title", "Milestone"),
            description=milestone_data.get("description"),
            target_week=milestone_data.get("target_week", 1),
            order_index=milestone_data.get("order_index", 0),
        )
        database.add(milestone)
        milestone_entries.append(milestone)

    # Persist comparisons
    comparison_entries: list[TransitionComparison] = []
    for comp_data in comparisons_data:
        comparison = TransitionComparison(
            transition_path_id=transition_path.id,
            dimension=comp_data.get("dimension", "unknown"),
            source_value=comp_data.get("source_value", 0.0),
            target_value=comp_data.get("target_value", 0.0),
            delta=comp_data.get("delta", 0.0),
            unit=comp_data.get("unit"),
            reasoning=comp_data.get("reasoning"),
        )
        database.add(comparison)
        comparison_entries.append(comparison)

    await database.commit()

    logger.info(
        "Transition explored: %s → %s — confidence=%.2f, "
        "%d skills, %d milestones, %d comparisons",
        from_role, target_role,
        transition_path.confidence_score,
        len(skill_entries),
        len(milestone_entries),
        len(comparison_entries),
    )

    return {
        "transition_path": transition_path,
        "skill_bridge": skill_entries,
        "milestones": milestone_entries,
        "comparisons": comparison_entries,
    }


async def get_dashboard(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Get all saved transitions + preferences for dashboard view."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return {"transitions": [], "preferences": None, "total_explored": 0}

    transitions = (
        (
            await database.execute(
                select(TransitionPath)
                .where(TransitionPath.career_dna_id == career_dna.id)
                .order_by(TransitionPath.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    preferences = (
        await database.execute(
            select(TransitionPreference)
            .where(TransitionPreference.career_dna_id == career_dna.id)
        )
    ).scalar_one_or_none()

    return {
        "transitions": list(transitions),
        "preferences": preferences,
        "total_explored": len(transitions),
    }


async def get_transition(
    database: AsyncSession,
    *,
    transition_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TransitionPath | None:
    """Get a specific transition path by ID."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(TransitionPath).where(
            TransitionPath.id == transition_id,
            TransitionPath.career_dna_id == career_dna.id,
        )
    )
    return result.scalar_one_or_none()


async def get_transitions(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[TransitionPath]:
    """List all transitions for a user."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return []

    result = await database.execute(
        select(TransitionPath)
        .where(TransitionPath.career_dna_id == career_dna.id)
        .order_by(TransitionPath.created_at.desc())
    )
    return list(result.scalars().all())


async def get_skill_bridge(
    database: AsyncSession,
    *,
    transition_id: uuid.UUID,
) -> list[SkillBridgeEntry]:
    """Get skill bridge entries for a transition."""
    result = await database.execute(
        select(SkillBridgeEntry)
        .where(SkillBridgeEntry.transition_path_id == transition_id)
        .order_by(SkillBridgeEntry.priority)
    )
    return list(result.scalars().all())


async def get_milestones(
    database: AsyncSession,
    *,
    transition_id: uuid.UUID,
) -> list[TransitionMilestone]:
    """Get milestones for a transition."""
    result = await database.execute(
        select(TransitionMilestone)
        .where(TransitionMilestone.transition_path_id == transition_id)
        .order_by(TransitionMilestone.order_index)
    )
    return list(result.scalars().all())


async def get_comparisons(
    database: AsyncSession,
    *,
    transition_id: uuid.UUID,
) -> list[TransitionComparison]:
    """Get role comparisons for a transition."""
    result = await database.execute(
        select(TransitionComparison)
        .where(TransitionComparison.transition_path_id == transition_id)
    )
    return list(result.scalars().all())


async def delete_transition(
    database: AsyncSession,
    *,
    transition_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a saved transition path and all children."""
    transition = await get_transition(
        database, transition_id=transition_id, user_id=user_id,
    )
    if not transition:
        return False

    await database.delete(transition)
    await database.commit()
    return True


async def get_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> TransitionPreference | None:
    """Get transition preferences for a user."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        return None

    result = await database.execute(
        select(TransitionPreference)
        .where(TransitionPreference.career_dna_id == career_dna.id)
    )
    return result.scalar_one_or_none()


async def update_preferences(
    database: AsyncSession,
    *,
    user_id: uuid.UUID,
    update_data: TransitionPreferenceUpdateRequest,
) -> TransitionPreference:
    """Update or create transition preferences."""
    career_dna = await _get_career_dna_with_genome(database, user_id)
    if not career_dna:
        raise ValueError("Career DNA not found.")

    result = await database.execute(
        select(TransitionPreference)
        .where(TransitionPreference.career_dna_id == career_dna.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        preference = TransitionPreference(
            career_dna_id=career_dna.id,
            user_id=user_id,
        )
        database.add(preference)

    # Apply partial updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(preference, field, value)

    await database.commit()
    await database.refresh(preference)
    return preference


# ── Private Defaults ───────────────────────────────────────────


def _default_analysis(from_role: str, to_role: str) -> dict[str, Any]:
    """Safe fallback analysis when LLM fails."""
    return {
        "confidence_score": 0.3,
        "difficulty": "moderate",
        "skill_overlap_percent": 30.0,
        "skills_to_acquire_count": 5,
        "estimated_duration_months": 12,
        "optimistic_months": 6,
        "realistic_months": 12,
        "conservative_months": 18,
        "salary_impact_percent": 0.0,
        "success_probability": 0.3,
        "reasoning": (
            f"Automated estimate for {from_role} → {to_role}. "
            "LLM analysis was unavailable; using conservative defaults."
        ),
        "factors": {
            "skill_match": "medium",
            "market_demand": "medium",
            "seniority_alignment": "lateral",
            "industry_proximity": "adjacent",
            "location_impact": "neutral",
        },
    }
