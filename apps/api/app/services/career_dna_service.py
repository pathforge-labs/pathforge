"""
PathForge — Career DNA Service
=================================
Business logic orchestrating Career DNA™ profile creation,
dimension computation, and lifecycle management.

AI Trust Layer™ Integration:
    Each dimension computation logs a TransparencyRecord into the
    per-user TransparencyLog, enabling user-facing explainability
    for all AI-driven analyses.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.career_dna_analyzer import CareerDNAAnalyzer
from app.core.llm_observability import TransparencyRecord, get_transparency_log
from app.models.career_dna import (
    CareerDNA,
    ExperienceBlueprint,
    GrowthVector,
    HiddenSkill,
    MarketPosition,
    SkillGenomeEntry,
    ValuesProfile,
)
from app.models.matching import JobListing
from app.models.preference import Preference
from app.models.resume import Resume, Skill

logger = logging.getLogger(__name__)

# Dimensions that can be individually refreshed
VALID_DIMENSIONS = frozenset(
    {
        "skill_genome",
        "experience_blueprint",
        "growth_vector",
        "values_profile",
        "market_position",
    }
)


def _log_transparency(
    user_id: uuid.UUID,
    record: TransparencyRecord | None,
) -> None:
    """Log a TransparencyRecord to the per-user transparency log.

    Silently skips if record is None (e.g. empty input fallback).
    """
    if record is None:
        return
    log = get_transparency_log()
    log.record(user_id=str(user_id), entry=record)


class CareerDNAService:
    """Orchestrates Career DNA™ lifecycle and dimension computation."""

    # ── Profile Lifecycle ──────────────────────────────────────

    @staticmethod
    async def get_or_create(
        db: AsyncSession, *, user_id: uuid.UUID
    ) -> CareerDNA:
        """Get existing Career DNA or create a new blank profile."""
        result = await db.execute(
            select(CareerDNA)
            .where(CareerDNA.user_id == user_id)
            .options(
                selectinload(CareerDNA.skill_genome),
                selectinload(CareerDNA.hidden_skills),
                selectinload(CareerDNA.experience_blueprint),
                selectinload(CareerDNA.growth_vector),
                selectinload(CareerDNA.values_profile),
                selectinload(CareerDNA.market_position),
            )
        )
        career_dna = result.scalar_one_or_none()

        if career_dna is None:
            career_dna = CareerDNA(user_id=user_id)
            db.add(career_dna)
            await db.flush()
            await db.refresh(career_dna)
            logger.info("Created new Career DNA profile for user %s", user_id)

        return career_dna

    @staticmethod
    async def get_full_profile(
        db: AsyncSession, *, user_id: uuid.UUID
    ) -> CareerDNA | None:
        """Get full Career DNA profile with all dimensions eagerly loaded."""
        result = await db.execute(
            select(CareerDNA)
            .where(CareerDNA.user_id == user_id)
            .options(
                selectinload(CareerDNA.skill_genome),
                selectinload(CareerDNA.hidden_skills),
                selectinload(CareerDNA.experience_blueprint),
                selectinload(CareerDNA.growth_vector),
                selectinload(CareerDNA.values_profile),
                selectinload(CareerDNA.market_position),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_profile(
        db: AsyncSession, *, user_id: uuid.UUID
    ) -> bool:
        """Delete Career DNA profile (GDPR erasure support)."""
        career_dna = await CareerDNAService.get_full_profile(
            db, user_id=user_id
        )
        if career_dna is None:
            return False
        await db.delete(career_dna)
        await db.flush()
        logger.info("Deleted Career DNA profile for user %s", user_id)
        return True

    # ── Full Analysis ──────────────────────────────────────────

    @staticmethod
    async def generate_full_profile(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        dimensions: list[str] | None = None,
    ) -> CareerDNA:
        """
        Generate or refresh Career DNA dimensions.

        Collects user data (resumes, skills, preferences, job listings),
        dispatches AI analysis for each dimension, persists results,
        and logs TransparencyRecords for the AI Trust Layer™.

        Args:
            db: Database session.
            user_id: Target user.
            dimensions: Optional subset of dimensions to compute.
                If None/empty, all dimensions are computed.
        """
        career_dna = await CareerDNAService.get_or_create(
            db, user_id=user_id
        )

        # Validate requested dimensions
        target_dims = set(dimensions or VALID_DIMENSIONS)
        target_dims = target_dims.intersection(VALID_DIMENSIONS)
        if not target_dims:
            target_dims = set(VALID_DIMENSIONS)

        # Gather source data
        experience_text = await _gather_experience_text(db, user_id)
        explicit_skills = await _gather_explicit_skills(db, user_id)
        preferences_text = await _gather_preferences_text(db, user_id)

        # ── Skill Genome ───────────────────────────────────────
        if "skill_genome" in target_dims:
            await _compute_skill_genome(
                db, career_dna, explicit_skills, experience_text, user_id
            )

        # ── Experience Blueprint ───────────────────────────────
        if "experience_blueprint" in target_dims:
            await _compute_experience_blueprint(
                db, career_dna, experience_text, user_id
            )

        # ── Growth Vector ──────────────────────────────────────
        if "growth_vector" in target_dims:
            skills_text = ", ".join(
                s.get("name", "") for s in explicit_skills
            )
            await _compute_growth_vector(
                db, career_dna, experience_text,
                skills_text, preferences_text, user_id,
            )

        # ── Values Profile ─────────────────────────────────────
        if "values_profile" in target_dims:
            await _compute_values_profile(
                db, career_dna, experience_text, preferences_text, user_id
            )

        # ── Market Position ────────────────────────────────────
        if "market_position" in target_dims:
            skill_names = [s.get("name", "") for s in explicit_skills]
            await _compute_market_position(db, career_dna, skill_names)

        # ── Update metadata ────────────────────────────────────
        career_dna.last_analysis_at = datetime.now(UTC)
        career_dna.version += 1
        career_dna.completeness_score = _calculate_completeness(career_dna)

        await db.flush()
        await db.refresh(career_dna)

        logger.info(
            "Career DNA analysis complete for user %s (v%d, %.0f%% complete)",
            user_id,
            career_dna.version,
            career_dna.completeness_score,
        )
        return career_dna

    # ── Hidden Skill Confirmation ──────────────────────────────

    @staticmethod
    async def confirm_hidden_skill(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skill_id: uuid.UUID,
        confirmed: bool,
    ) -> HiddenSkill | None:
        """Let the user confirm or reject a discovered hidden skill."""
        career_dna = await CareerDNAService.get_full_profile(
            db, user_id=user_id
        )
        if career_dna is None:
            return None

        result = await db.execute(
            select(HiddenSkill).where(
                HiddenSkill.id == skill_id,
                HiddenSkill.career_dna_id == career_dna.id,
            )
        )
        skill = result.scalar_one_or_none()
        if skill is None:
            return None

        skill.user_confirmed = confirmed
        await db.flush()
        await db.refresh(skill)
        logger.info(
            "Hidden skill %s %s by user %s",
            skill.skill_name,
            "confirmed" if confirmed else "rejected",
            user_id,
        )
        return skill


# ── Private Helpers ────────────────────────────────────────────


async def _gather_experience_text(
    db: AsyncSession, user_id: uuid.UUID
) -> str:
    """Collect experience text from user's resumes."""
    result = await db.execute(
        select(Resume).where(Resume.user_id == user_id)
    )
    resumes = list(result.scalars().all())

    experience_parts: list[str] = []
    for resume in resumes:
        if resume.raw_text:
            experience_parts.append(resume.raw_text)
        if resume.structured_data:
            experiences = resume.structured_data.get("experience", [])
            for exp in experiences:
                parts = [
                    f"Role: {exp.get('title', '')}",
                    f"Company: {exp.get('company', '')}",
                    f"Period: {exp.get('start_date', '')} - "
                    f"{exp.get('end_date', '')}",
                    f"Description: {exp.get('description', '')}",
                ]
                experience_parts.append("\n".join(parts))

    return "\n\n---\n\n".join(experience_parts)


async def _gather_explicit_skills(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Collect explicit skills from user's resumes."""
    result = await db.execute(
        select(Skill)
        .join(Resume, Skill.resume_id == Resume.id)
        .where(Resume.user_id == user_id)
    )
    skills = list(result.scalars().all())

    return [
        {
            "name": skill.name,
            "category": skill.category or "general",
            "proficiency_level": skill.proficiency_level or "intermediate",
            "years_experience": skill.years_experience,
        }
        for skill in skills
    ]


async def _gather_preferences_text(
    db: AsyncSession, user_id: uuid.UUID
) -> str:
    """Collect user preferences as text."""
    result = await db.execute(
        select(Preference).where(Preference.user_id == user_id).limit(1)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        return ""

    parts: list[str] = []
    if pref.job_titles:
        parts.append(f"Target roles: {', '.join(pref.job_titles)}")
    if pref.sectors:
        parts.append(f"Target sectors: {', '.join(pref.sectors)}")
    if pref.locations:
        parts.append(f"Preferred locations: {', '.join(pref.locations)}")
    if pref.work_type:
        parts.append(f"Work type: {pref.work_type}")
    if pref.experience_level:
        parts.append(f"Experience level: {pref.experience_level}")
    return "\n".join(parts)


async def _compute_skill_genome(
    db: AsyncSession,
    career_dna: CareerDNA,
    explicit_skills: list[dict[str, Any]],
    experience_text: str,
    user_id: uuid.UUID,
) -> None:
    """Populate skill genome from explicit skills + hidden skills discovery."""
    # Clear existing entries
    for entry in list(career_dna.skill_genome):
        await db.delete(entry)
    for skill in list(career_dna.hidden_skills):
        await db.delete(skill)
    await db.flush()

    # Add explicit skills to genome
    for skill_data in explicit_skills:
        entry = SkillGenomeEntry(
            career_dna_id=career_dna.id,
            skill_name=skill_data["name"],
            category=skill_data.get("category", "general"),
            proficiency_level=skill_data.get("proficiency_level", "intermediate"),
            source="explicit",
            confidence=1.0,
            years_experience=skill_data.get("years_experience"),
        )
        db.add(entry)

    # Discover hidden skills via LLM (with transparency)
    explicit_names = [s["name"] for s in explicit_skills]
    hidden_results, record = await CareerDNAAnalyzer.discover_hidden_skills(
        explicit_skills=explicit_names,
        experience_text=experience_text,
    )
    _log_transparency(user_id, record)

    for hidden_data in hidden_results:
        hidden = HiddenSkill(
            career_dna_id=career_dna.id,
            skill_name=hidden_data.get("skill_name", "Unknown"),
            discovery_method="resume_inference",
            confidence=hidden_data.get("confidence", 0.5),
            evidence={
                "reasoning": hidden_data.get("evidence", ""),
            },
            source_text=hidden_data.get("source_text", ""),
        )
        db.add(hidden)

    await db.flush()


async def _compute_experience_blueprint(
    db: AsyncSession,
    career_dna: CareerDNA,
    experience_text: str,
    user_id: uuid.UUID,
) -> None:
    """Analyze experience patterns."""
    data, record = await CareerDNAAnalyzer.analyze_experience_blueprint(
        experience_text,
    )
    _log_transparency(user_id, record)

    if career_dna.experience_blueprint:
        blueprint = career_dna.experience_blueprint
    else:
        blueprint = ExperienceBlueprint(career_dna_id=career_dna.id)
        db.add(blueprint)

    blueprint.total_years = float(data.get("total_years", 0))
    blueprint.role_count = int(data.get("role_count", 0))
    blueprint.avg_tenure_months = float(data.get("avg_tenure_months", 0))
    blueprint.career_direction = data.get("career_direction", "exploring")
    blueprint.industry_diversity = float(data.get("industry_diversity", 0))
    blueprint.seniority_trajectory = data.get("seniority_trajectory")
    blueprint.pattern_analysis = data.get("pattern_analysis")

    await db.flush()


async def _compute_growth_vector(
    db: AsyncSession,
    career_dna: CareerDNA,
    experience_text: str,
    skills_text: str,
    preferences_text: str,
    user_id: uuid.UUID,
) -> None:
    """Compute career trajectory projection."""
    data, record = await CareerDNAAnalyzer.compute_growth_vector(
        experience_text, skills_text, preferences_text,
    )
    _log_transparency(user_id, record)

    if career_dna.growth_vector:
        vector = career_dna.growth_vector
    else:
        vector = GrowthVector(career_dna_id=career_dna.id)
        db.add(vector)

    vector.current_trajectory = data.get("current_trajectory", "steady")
    vector.projected_roles = data.get("projected_roles")
    vector.skill_velocity = data.get("skill_velocity")
    vector.growth_score = float(data.get("growth_score", 50.0))
    vector.analysis_reasoning = data.get("analysis_reasoning")

    await db.flush()


async def _compute_values_profile(
    db: AsyncSession,
    career_dna: CareerDNA,
    experience_text: str,
    preferences_text: str,
    user_id: uuid.UUID,
) -> None:
    """Extract values from career patterns."""
    data, record = await CareerDNAAnalyzer.extract_values_profile(
        experience_text, preferences_text,
    )
    _log_transparency(user_id, record)

    if career_dna.values_profile:
        profile = career_dna.values_profile
    else:
        profile = ValuesProfile(career_dna_id=career_dna.id)
        db.add(profile)

    profile.work_style = data.get("work_style", "flexible")
    profile.impact_preference = data.get("impact_preference", "team")
    profile.environment_fit = data.get("environment_fit")
    profile.derived_values = data.get("derived_values")
    profile.confidence = float(data.get("confidence", 0.5))

    await db.flush()


async def _compute_market_position(
    db: AsyncSession,
    career_dna: CareerDNA,
    skill_names: list[str],
) -> None:
    """Compute market position from job listing data."""
    # Gather job listings
    result = await db.execute(select(JobListing).limit(500))
    listings = list(result.scalars().all())

    listings_data = [
        {
            "title": listing.title,
            "description": listing.description or "",
        }
        for listing in listings
    ]

    data = CareerDNAAnalyzer.compute_market_position(
        skill_names, listings_data
    )

    if career_dna.market_position:
        position = career_dna.market_position
    else:
        position = MarketPosition(career_dna_id=career_dna.id)
        db.add(position)

    position.percentile_overall = float(data.get("percentile_overall", 0.0))
    position.skill_demand_scores = data.get("skill_demand_scores")
    position.matching_job_count = int(data.get("matching_job_count", 0))
    position.market_trend = data.get("market_trend", "stable")
    position.computed_at = datetime.now(UTC)

    await db.flush()


def _calculate_completeness(career_dna: CareerDNA) -> float:
    """Calculate profile completeness as percentage (0-100)."""
    dimensions_present = 0
    total_dimensions = 5

    if career_dna.skill_genome:
        dimensions_present += 1
    if career_dna.experience_blueprint:
        dimensions_present += 1
    if career_dna.growth_vector:
        dimensions_present += 1
    if career_dna.values_profile:
        dimensions_present += 1
    if career_dna.market_position:
        dimensions_present += 1

    return round((dimensions_present / total_dimensions) * 100, 1)
