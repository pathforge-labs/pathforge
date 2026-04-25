"""
PathForge — Salary Intelligence Engine™ Service
===================================================
Salary Intelligence Engine: orchestrates the personalized salary
analysis pipeline, computes skill impacts, tracks salary trajectory,
and runs what-if scenario simulations.

Pipeline stages (run_full_scan):
    1. Gather Career DNA context (skills, experience, industry, location)
    2. LLM salary range estimation → SalaryEstimate
    3. LLM per-skill impact analysis → SkillSalaryImpact
    4. Auto-create SalaryHistoryEntry for trajectory tracking
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer
from app.models.career_dna import CareerDNA
from app.models.salary_intelligence import (
    SalaryEstimate,
    SalaryHistoryEntry,
    SalaryPreference,
    SalaryScenario,
    SkillSalaryImpact,
)

logger = logging.getLogger(__name__)


class SalaryIntelligenceService:
    """
    Salary Intelligence Engine for personalized salary analysis.

    Orchestrates the full pipeline from salary estimation through
    skill impact quantification to trajectory tracking and
    what-if scenario simulation.
    """

    # ── Full Scan ──────────────────────────────────────────────

    @staticmethod
    async def run_full_scan(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Execute full Salary Intelligence Engine analysis pipeline.

        Pipeline:
            1. Load Career DNA with skill genome
            2. Estimate personalized salary range (LLM)
            3. Analyze per-skill salary impacts (LLM)
            4. Create salary history entry for trajectory

        Args:
            db: Database session.
            user_id: User's UUID.

        Returns:
            Dict with all analysis results for response building.
        """
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            logger.warning(
                "Salary scan requested but no Career DNA for user %s",
                user_id,
            )
            return {"status": "error", "detail": "Career DNA profile required"}

        # Gather context
        skills_data = _format_skills_for_salary(career_dna)
        experience_summary = _format_experience_summary(career_dna)
        industry_context = _get_industry_context(career_dna)
        role_title = _get_role_title(career_dna)
        location = _get_location(career_dna)
        seniority = _estimate_seniority_level(career_dna)
        years_of_experience = _estimate_years_of_experience(career_dna)
        skill_names = _extract_skill_names(career_dna)
        preference = await _get_or_create_preference(
            db, career_dna_id=career_dna.id, user_id=user_id,
        )
        currency = preference.preferred_currency

        if not skill_names:
            return {"status": "error", "detail": "No skills found in Career DNA"}

        # Step 1: LLM salary range estimation
        estimate_data = await SalaryIntelligenceAnalyzer.analyze_salary_range(
            role_title=role_title,
            location=location,
            seniority_level=seniority,
            industry=industry_context,
            years_of_experience=years_of_experience,
            skills_data=skills_data,
            experience_summary=experience_summary,
            currency=currency,
        )

        estimate_entry: SalaryEstimate | None = None
        if estimate_data:
            estimate_entry = await _persist_estimate(
                db, career_dna_id=career_dna.id,
                role_title=role_title, location=location,
                seniority=seniority, industry=industry_context,
                data=estimate_data, currency=currency,
            )

        # Step 2: LLM per-skill impact analysis
        impact_entries: list[SkillSalaryImpact] = []
        if estimate_entry is not None:
            impacts_data = await SalaryIntelligenceAnalyzer.analyze_skill_impacts(
                skills_data=skills_data,
                role_title=role_title,
                location=location,
                seniority_level=seniority,
                industry=industry_context,
                estimated_median=estimate_entry.estimated_median,
                market_percentile=estimate_entry.market_percentile or 50.0,
                currency=currency,
            )
            if impacts_data:
                impact_entries = await _persist_skill_impacts(
                    db, career_dna_id=career_dna.id, data=impacts_data,
                )

        # Step 3: Create history entry for trajectory tracking
        history_created = False
        if estimate_entry is not None:
            await _create_history_entry(
                db, career_dna_id=career_dna.id,
                estimate=estimate_entry,
                skills_count=len(skill_names),
            )
            history_created = True

        await db.flush()

        return {
            "status": "completed",
            "estimate": estimate_entry,
            "skill_impacts": impact_entries,
            "history_entry_created": history_created,
        }

    # ── Dashboard ──────────────────────────────────────────────

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get full Salary Intelligence dashboard data."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return {
                "estimate": None,
                "skill_impacts": [],
                "trajectory": None,
                "recent_scenarios": [],
                "preference": None,
                "last_scan_at": None,
            }

        # Latest estimate
        estimate_result = await db.execute(
            select(SalaryEstimate)
            .where(SalaryEstimate.career_dna_id == career_dna.id)
            .order_by(desc(SalaryEstimate.computed_at))
            .limit(1)
        )
        estimate = estimate_result.scalar_one_or_none()

        # Skill impacts
        impacts_result = await db.execute(
            select(SkillSalaryImpact)
            .where(SkillSalaryImpact.career_dna_id == career_dna.id)
            .order_by(desc(SkillSalaryImpact.computed_at))
        )
        impacts = list(impacts_result.scalars().all())

        # Trajectory (last 12 entries)
        history_result = await db.execute(
            select(SalaryHistoryEntry)
            .where(SalaryHistoryEntry.career_dna_id == career_dna.id)
            .order_by(desc(SalaryHistoryEntry.snapshot_date))
            .limit(12)
        )
        history = list(history_result.scalars().all())

        # Recent scenarios (last 5)
        scenarios_result = await db.execute(
            select(SalaryScenario)
            .where(SalaryScenario.career_dna_id == career_dna.id)
            .order_by(desc(SalaryScenario.computed_at))
            .limit(5)
        )
        scenarios = list(scenarios_result.scalars().all())

        # Preference
        preference = await _get_preference(db, career_dna.id)

        return {
            "estimate": estimate,
            "skill_impacts": impacts,
            "trajectory": {
                "history": list(reversed(history)),
                "projected_6m_median": None,
                "projected_12m_median": None,
                "trend_direction": None,
                "trend_confidence": None,
            } if history else None,
            "recent_scenarios": scenarios,
            "preference": preference,
            "last_scan_at": estimate.computed_at if estimate else None,
        }

    # ── Individual Accessors ───────────────────────────────────

    @staticmethod
    async def get_salary_estimate(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> SalaryEstimate | None:
        """Get latest personalized salary estimate."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return None
        result = await db.execute(
            select(SalaryEstimate)
            .where(SalaryEstimate.career_dna_id == career_dna.id)
            .order_by(desc(SalaryEstimate.computed_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_skill_impacts(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[SkillSalaryImpact]:
        """Get per-skill salary impact breakdown."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return []
        result = await db.execute(
            select(SkillSalaryImpact)
            .where(SkillSalaryImpact.career_dna_id == career_dna.id)
            .order_by(desc(SkillSalaryImpact.computed_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_salary_trajectory(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get historical salary trajectory."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return {"history": []}
        result = await db.execute(
            select(SalaryHistoryEntry)
            .where(SalaryHistoryEntry.career_dna_id == career_dna.id)
            .order_by(desc(SalaryHistoryEntry.snapshot_date))
            .limit(24)
        )
        entries = list(result.scalars().all())
        return {
            "history": list(reversed(entries)),
            "projected_6m_median": None,
            "projected_12m_median": None,
            "trend_direction": None,
            "trend_confidence": None,
        }

    # ── Scenarios ──────────────────────────────────────────────

    @staticmethod
    async def run_scenario(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        scenario_type: str,
        scenario_label: str,
        scenario_input: dict[str, Any],
    ) -> SalaryScenario | None:
        """Execute a what-if salary scenario."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return None

        # Get current estimate
        estimate_result = await db.execute(
            select(SalaryEstimate)
            .where(SalaryEstimate.career_dna_id == career_dna.id)
            .order_by(desc(SalaryEstimate.computed_at))
            .limit(1)
        )
        current_estimate = estimate_result.scalar_one_or_none()
        if current_estimate is None:
            return None

        skills_data = _format_skills_for_salary(career_dna)
        role_title = _get_role_title(career_dna)
        location = _get_location(career_dna)
        preference = await _get_preference(db, career_dna.id)
        currency = preference.preferred_currency if preference else "EUR"

        # Run LLM scenario simulation
        result = await SalaryIntelligenceAnalyzer.simulate_scenario(
            current_median=current_estimate.estimated_median,
            current_min=current_estimate.estimated_min,
            current_max=current_estimate.estimated_max,
            role_title=role_title,
            location=location,
            current_skills=skills_data,
            scenario_type=scenario_type,
            scenario_label=scenario_label,
            scenario_input=json.dumps(scenario_input),
            currency=currency,
        )

        if not result:
            return None

        # Persist scenario
        scenario = SalaryScenario(
            career_dna_id=career_dna.id,
            scenario_type=scenario_type,
            scenario_label=scenario_label,
            scenario_input=scenario_input,
            projected_min=result.get("projected_min", 0.0),
            projected_max=result.get("projected_max", 0.0),
            projected_median=result.get("projected_median", 0.0),
            currency=currency,
            delta_amount=result.get("delta_amount", 0.0),
            delta_percent=result.get("delta_percent", 0.0),
            confidence=result.get("confidence", 0.0),
            reasoning=result.get("reasoning"),
            impact_breakdown=result.get("impact_breakdown"),
        )
        db.add(scenario)
        await db.flush()

        return scenario

    @staticmethod
    async def get_scenarios(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[SalaryScenario]:
        """List previous what-if scenarios."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return []
        result = await db.execute(
            select(SalaryScenario)
            .where(SalaryScenario.career_dna_id == career_dna.id)
            .order_by(desc(SalaryScenario.computed_at))
            .limit(20)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_scenario_by_id(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        scenario_id: uuid.UUID,
    ) -> SalaryScenario | None:
        """Get a specific scenario by ID."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return None
        result = await db.execute(
            select(SalaryScenario)
            .where(
                SalaryScenario.career_dna_id == career_dna.id,
                SalaryScenario.id == scenario_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Preferences ────────────────────────────────────────────

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> SalaryPreference | None:
        """Get user's salary tracking preferences."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return None
        return await _get_preference(db, career_dna.id)

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> SalaryPreference:
        """Update or create salary preferences."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            msg = "Career DNA profile required to set salary preferences"
            raise ValueError(msg)

        preference = await _get_or_create_preference(
            db, career_dna_id=career_dna.id, user_id=user_id,
        )

        for key, value in updates.items():
            if value is not None and hasattr(preference, key):
                setattr(preference, key, value)

        await db.flush()
        return preference


# ── Private Helpers ────────────────────────────────────────────


async def _get_career_dna_with_genome(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Fetch CareerDNA with skill_genome eagerly loaded."""
    result = await db.execute(
        select(CareerDNA)
        .where(CareerDNA.user_id == user_id)
        .options(
            selectinload(CareerDNA.skill_genome),
            selectinload(CareerDNA.experience_blueprint),
            selectinload(CareerDNA.market_position),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


def _format_skills_for_salary(career_dna: CareerDNA) -> str:
    """Format skills portfolio for salary analysis LLM prompts."""
    if not career_dna.skill_genome:
        return "No skills data available"
    lines: list[str] = []
    for idx, skill in enumerate(career_dna.skill_genome, 1):
        line = (
            f"{idx}. {skill.skill_name} "
            f"(Category: {skill.category}, "
            f"Proficiency: {skill.proficiency_level}, "
            f"Confidence: {skill.confidence:.0%})"
        )
        lines.append(line)
    return "\n".join(lines)


def _format_experience_summary(career_dna: CareerDNA) -> str:
    """Format experience blueprint into text for LLM."""
    blueprint = career_dna.experience_blueprint
    if blueprint is None:
        return "No experience data available"
    return (
        f"Career Direction: {blueprint.career_direction}, "
        f"Total Years: {blueprint.total_years or 'Unknown'}, "
        f"Industry Diversity: {blueprint.industry_diversity or 0}, "
        f"Roles: {blueprint.role_count or 0}"
    )


def _get_industry_context(career_dna: CareerDNA) -> str:
    """Extract primary industry from Career DNA."""
    if career_dna.primary_industry:
        return career_dna.primary_industry
    return "Technology"


def _get_role_title(career_dna: CareerDNA) -> str:
    """Extract primary role from Career DNA."""
    if career_dna.primary_role:
        return career_dna.primary_role
    return "Software Engineer"


def _get_location(career_dna: CareerDNA) -> str:
    """Extract location from Career DNA."""
    if career_dna.location:
        return career_dna.location
    return "Netherlands"


def _estimate_seniority_level(career_dna: CareerDNA) -> str:
    """Estimate seniority level from Career DNA context."""
    if career_dna.seniority_level:
        return career_dna.seniority_level
    # Derive from experience blueprint
    blueprint = career_dna.experience_blueprint
    if blueprint is not None:
        years = blueprint.total_years
        if years is not None:
            if years < 3:
                return "junior"
            if years < 6:
                return "mid"
            if years < 10:
                return "senior"
            return "staff"
    return "mid"


def _estimate_years_of_experience(career_dna: CareerDNA) -> int:
    """Estimate total years of professional experience."""
    blueprint = career_dna.experience_blueprint
    if blueprint is not None:
        years = blueprint.total_years
        if years is not None:
            return int(years)
    return 5  # Conservative default


def _extract_skill_names(career_dna: CareerDNA) -> list[str]:
    """Extract skill names from genome."""
    if not career_dna.skill_genome:
        return []
    return [skill.skill_name for skill in career_dna.skill_genome]


async def _get_preference(
    db: AsyncSession,
    career_dna_id: uuid.UUID,
) -> SalaryPreference | None:
    """Get user's salary preference record."""
    result = await db.execute(
        select(SalaryPreference)
        .where(SalaryPreference.career_dna_id == career_dna_id)
    )
    return result.scalar_one_or_none()


async def _get_or_create_preference(
    db: AsyncSession,
    *,
    career_dna_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SalaryPreference:
    """Get or create salary preference with defaults."""
    preference = await _get_preference(db, career_dna_id)
    if preference is not None:
        return preference
    preference = SalaryPreference(
        career_dna_id=career_dna_id,
        user_id=user_id,
    )
    db.add(preference)
    await db.flush()
    return preference


async def _persist_estimate(
    db: AsyncSession,
    *,
    career_dna_id: uuid.UUID,
    role_title: str,
    location: str,
    seniority: str,
    industry: str,
    data: dict[str, Any],
    currency: str,
) -> SalaryEstimate:
    """Persist a salary estimate from LLM results."""
    estimate = SalaryEstimate(
        career_dna_id=career_dna_id,
        role_title=role_title,
        location=location,
        seniority_level=seniority,
        industry=industry,
        estimated_min=data.get("estimated_min", 0.0),
        estimated_max=data.get("estimated_max", 0.0),
        estimated_median=data.get("estimated_median", 0.0),
        currency=currency,
        confidence=data.get("confidence", 0.0),
        data_points_count=data.get("data_points_count", 0),
        market_percentile=data.get("market_percentile"),
        base_salary_factor=data.get("base_salary_factor"),
        skill_premium_factor=data.get("skill_premium_factor"),
        experience_multiplier=data.get("experience_multiplier"),
        market_condition_adjustment=data.get("market_condition_adjustment"),
        analysis_reasoning=data.get("analysis_reasoning"),
        factors_detail=data.get("factors_detail"),
    )
    db.add(estimate)
    await db.flush()
    logger.info(
        "Persisted salary estimate: %.0f-%.0f %s (conf=%.2f)",
        estimate.estimated_min,
        estimate.estimated_max,
        currency,
        estimate.confidence,
    )
    return estimate


async def _persist_skill_impacts(
    db: AsyncSession,
    *,
    career_dna_id: uuid.UUID,
    data: list[dict[str, Any]],
) -> list[SkillSalaryImpact]:
    """Replace and persist per-skill salary impacts."""
    # Delete existing impacts for this career DNA
    existing = await db.execute(
        select(SkillSalaryImpact)
        .where(SkillSalaryImpact.career_dna_id == career_dna_id)
    )
    for old_entry in existing.scalars().all():
        await db.delete(old_entry)
    await db.flush()

    entries: list[SkillSalaryImpact] = []
    for item in data:
        entry = SkillSalaryImpact(
            career_dna_id=career_dna_id,
            skill_name=item.get("skill_name", "Unknown"),
            category=item.get("category", "technical"),
            salary_impact_amount=item.get("salary_impact_amount", 0.0),
            salary_impact_percent=item.get("salary_impact_percent", 0.0),
            demand_premium=item.get("demand_premium", 0.0),
            scarcity_factor=item.get("scarcity_factor", 0.0),
            impact_direction=item.get("impact_direction", "positive"),
            reasoning=item.get("reasoning"),
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    logger.info(
        "Persisted %d skill salary impacts for career_dna %s",
        len(entries),
        career_dna_id,
    )
    return entries


async def _create_history_entry(
    db: AsyncSession,
    *,
    career_dna_id: uuid.UUID,
    estimate: SalaryEstimate,
    skills_count: int,
) -> SalaryHistoryEntry:
    """Create a history entry from a salary estimate for trajectory."""
    entry = SalaryHistoryEntry(
        career_dna_id=career_dna_id,
        estimated_min=estimate.estimated_min,
        estimated_max=estimate.estimated_max,
        estimated_median=estimate.estimated_median,
        currency=estimate.currency,
        confidence=estimate.confidence,
        market_percentile=estimate.market_percentile,
        role_title=estimate.role_title,
        location=estimate.location,
        seniority_level=estimate.seniority_level,
        skills_count=skills_count,
        factors_snapshot={
            "base_salary_factor": estimate.base_salary_factor,
            "skill_premium_factor": estimate.skill_premium_factor,
            "experience_multiplier": estimate.experience_multiplier,
            "market_condition_adjustment": estimate.market_condition_adjustment,
        },
    )
    db.add(entry)
    await db.flush()
    return entry
