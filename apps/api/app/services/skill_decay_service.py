"""
PathForge — Skill Decay & Growth Tracker Service
===================================================
Decay Intelligence Engine: orchestrates the skill freshness
analysis pipeline, computes velocity maps, and generates
personalized reskilling pathways.

Pipeline flow:
    1. Score skill freshness (exponential decay + LLM contextual)
    2. Analyze market demand (LLM intelligence)
    3. Compute skill velocity (composite freshness + demand)
    4. Generate reskilling pathways (LLM personalization)
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.skill_decay_analyzer import SkillDecayAnalyzer
from app.models.career_dna import CareerDNA
from app.models.skill_decay import (
    MarketDemandSnapshot,
    ReskillingPathway,
    SkillDecayPreference,
    SkillFreshness,
    SkillVelocityEntry,
)

logger = logging.getLogger(__name__)


class SkillDecayService:
    """
    Decay Intelligence Engine for Skill Decay & Growth Tracker.

    Orchestrates the full pipeline from freshness scoring through
    velocity computation to reskilling pathway generation.
    """

    # ── Full Scan ──────────────────────────────────────────────

    @staticmethod
    async def run_full_scan(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Execute full Skill Decay & Growth Tracker analysis pipeline.

        Args:
            db: Database session.
            user_id: User's UUID.

        Returns:
            Dict with all analysis results for response building.
        """
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            logger.warning(
                "Skill decay scan requested but no Career DNA for user %s",
                user_id,
            )
            return {"status": "error", "detail": "Career DNA profile required"}

        # Gather context
        skills_data = _format_skills_with_dates(career_dna)
        experience_summary = _format_experience_summary(career_dna)
        industry_context = _get_industry_context(career_dna)
        skill_names = _extract_skill_names(career_dna)
        experience_level = _estimate_experience_level(career_dna)

        if not skill_names:
            return {"status": "error", "detail": "No skills found in Career DNA"}

        # Step 1: LLM contextual freshness assessment
        freshness_adjustments = await SkillDecayAnalyzer.score_skill_freshness(
            skills_data=skills_data,
            experience_summary=experience_summary,
            industry_context=industry_context,
        )

        # Step 2: Compute and persist freshness scores
        freshness_entries = await _persist_freshness_scores(
            db, career_dna, freshness_adjustments,
        )

        # Step 3: Market demand analysis
        skills_list = "\n".join(
            f"{idx + 1}. {name}" for idx, name in enumerate(skill_names)
        )
        demand_data = await SkillDecayAnalyzer.analyze_market_demand(
            skills_list=skills_list,
            industry_context=industry_context,
            experience_level=experience_level,
        )
        demand_entries = await _persist_demand_snapshots(
            db, career_dna.id, demand_data,
        )

        # Step 4: Velocity computation
        freshness_summary = _format_freshness_data(freshness_entries)
        demand_summary = _format_demand_data(demand_entries)
        professional_context = (
            f"Industry: {industry_context}, "
            f"Level: {experience_level}, "
            f"Skills: {len(skill_names)}"
        )

        velocity_data = await SkillDecayAnalyzer.compute_skill_velocity(
            freshness_data=freshness_summary,
            demand_data=demand_summary,
            professional_context=professional_context,
        )
        velocity_entries = await _persist_velocity_entries(
            db, career_dna.id, velocity_data, freshness_entries, demand_entries,
        )

        # Step 5: Reskilling pathways
        velocity_summary = _format_velocity_data(velocity_entries)
        pathway_data = await SkillDecayAnalyzer.generate_reskilling_paths(
            velocity_data=velocity_summary,
            freshness_data=freshness_summary,
            demand_data=demand_summary,
            current_skills=skills_data,
            experience_level=experience_level,
            industry_context=industry_context,
        )
        pathway_entries = await _persist_pathways(
            db, career_dna.id, pathway_data,
        )

        await db.flush()

        return {
            "status": "completed",
            "freshness": freshness_entries,
            "market_demand": demand_entries,
            "velocity": velocity_entries,
            "reskilling_pathways": pathway_entries,
            "skills_analyzed": len(skill_names),
        }

    # ── Dashboard (Read-Only) ──────────────────────────────────

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get full Skill Decay dashboard data."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return {}

        career_dna_id = career_dna.id

        freshness = await _get_all(db, SkillFreshness, career_dna_id)
        demands = await _get_all(db, MarketDemandSnapshot, career_dna_id)
        velocities = await _get_all(db, SkillVelocityEntry, career_dna_id)
        pathways = await _get_all(db, ReskillingPathway, career_dna_id)
        preference = await _get_preference(db, user_id)

        # Compute aggregates for freshness
        freshness_scores = [entry.freshness_score for entry in freshness]
        avg_freshness = (
            sum(freshness_scores) / len(freshness_scores)
            if freshness_scores else 0.0
        )

        threshold = preference.decay_alert_threshold if preference else 40.0
        at_risk = sum(1 for score in freshness_scores if score < threshold)

        freshest = max(freshness, key=lambda x: x.freshness_score).skill_name if freshness else None
        stalest = min(freshness, key=lambda x: x.freshness_score).skill_name if freshness else None

        # Compute last scan time
        last_scan = (
            max(entry.computed_at for entry in freshness)
            if freshness else None
        )

        return {
            "freshness": freshness,
            "freshness_summary": {
                "total_skills": len(freshness),
                "average_freshness": round(avg_freshness, 1),
                "skills_at_risk": at_risk,
                "freshest_skill": freshest,
                "stalest_skill": stalest,
            },
            "market_demand": demands,
            "velocity": velocities,
            "reskilling_pathways": pathways,
            "preference": preference,
            "last_scan_at": last_scan,
        }

    # ── Individual Queries ─────────────────────────────────────

    @staticmethod
    async def get_freshness_scores(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[SkillFreshness]:
        """Get all skill freshness scores."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return []
        return await _get_all(db, SkillFreshness, career_dna.id)

    @staticmethod
    async def get_market_demand(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[MarketDemandSnapshot]:
        """Get all market demand snapshots."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return []
        return await _get_all(db, MarketDemandSnapshot, career_dna.id)

    @staticmethod
    async def get_velocity_map(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[SkillVelocityEntry]:
        """Get full skill velocity map."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return []
        return await _get_all(db, SkillVelocityEntry, career_dna.id)

    @staticmethod
    async def get_reskilling_paths(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> list[ReskillingPathway]:
        """Get prioritized reskilling pathways."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return []
        pathways = await _get_all(db, ReskillingPathway, career_dna.id)
        # Sort by priority: critical > recommended > optional
        priority_order = {"critical": 0, "recommended": 1, "optional": 2}
        return sorted(
            pathways,
            key=lambda pathway: priority_order.get(pathway.priority, 3),
        )

    # ── Preferences ────────────────────────────────────────────

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> SkillDecayPreference | None:
        """Get user's skill decay tracking preferences."""
        return await _get_preference(db, user_id)

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> SkillDecayPreference | None:
        """Update or create skill decay preferences."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return None

        pref = await _get_preference(db, user_id)

        if pref is None:
            pref = SkillDecayPreference(
                user_id=user_id,
                career_dna_id=career_dna.id,
            )
            db.add(pref)

        for key, value in updates.items():
            if value is not None and hasattr(pref, key):
                setattr(pref, key, value)

        await db.flush()
        return pref

    # ── Skill Refresh ──────────────────────────────────────────

    @staticmethod
    async def refresh_skill(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skill_name: str,
    ) -> SkillFreshness | None:
        """Manually mark a skill as refreshed (reset freshness to 100)."""
        career_dna = await _get_career_dna_with_genome(db, user_id)
        if career_dna is None:
            return None

        result = await db.execute(
            select(SkillFreshness).where(
                SkillFreshness.career_dna_id == career_dna.id,
                SkillFreshness.skill_name == skill_name,
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return None

        entry.freshness_score = 100.0
        entry.days_since_active = 0
        entry.refresh_urgency = 0.0
        entry.last_active_date = datetime.now(UTC).strftime("%Y-%m-%d")
        entry.computed_at = datetime.now(UTC)
        await db.flush()
        return entry


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
            selectinload(CareerDNA.growth_vector),
        )
    )
    return result.scalar_one_or_none()


def _format_skills_with_dates(career_dna: CareerDNA) -> str:
    """Format skills with last-used dates for decay analysis."""
    if not career_dna.skill_genome:
        return "No skills data available"
    lines = []
    for entry in career_dna.skill_genome[:30]:
        last_used = entry.last_used_date or "Unknown"
        years = entry.years_experience or 0
        lines.append(
            f"- {entry.skill_name} ({entry.category}, "
            f"{entry.proficiency_level}, "
            f"last used: {last_used}, "
            f"{years}yr exp)"
        )
    return "\n".join(lines)


def _format_experience_summary(career_dna: CareerDNA) -> str:
    """Format experience blueprint into text."""
    if not career_dna.experience_blueprint:
        return "No experience data available"
    blueprint = career_dna.experience_blueprint
    return str(blueprint.pattern_analysis or "Experience data available")


def _get_industry_context(career_dna: CareerDNA) -> str:
    """Extract industry context from Career DNA."""
    if career_dna.experience_blueprint:
        direction = career_dna.experience_blueprint.career_direction
        return f"{direction} career trajectory"
    return "General professional"


def _extract_skill_names(career_dna: CareerDNA) -> list[str]:
    """Extract skill names from genome."""
    if not career_dna.skill_genome:
        return []
    return [entry.skill_name for entry in career_dna.skill_genome[:30]]


def _estimate_experience_level(career_dna: CareerDNA) -> str:
    """Estimate experience level from years."""
    years = 5.0
    if career_dna.experience_blueprint:
        total = career_dna.experience_blueprint.total_years
        years = float(total) if total else 5.0

    if years < 2:
        return "Junior"
    if years < 5:
        return "Mid-level"
    if years < 10:
        return "Senior"
    return "Staff/Principal"


def _format_freshness_data(entries: list[SkillFreshness]) -> str:
    """Format freshness entries for velocity prompt."""
    if not entries:
        return "No freshness data available"
    lines = []
    for entry in entries:
        lines.append(
            f"- {entry.skill_name}: score={entry.freshness_score:.0f}/100, "
            f"decay_rate={entry.decay_rate}, "
            f"days_inactive={entry.days_since_active}"
        )
    return "\n".join(lines)


def _format_demand_data(entries: list[MarketDemandSnapshot]) -> str:
    """Format demand entries for velocity prompt."""
    if not entries:
        return "No demand data available"
    lines = []
    for entry in entries:
        lines.append(
            f"- {entry.skill_name}: demand={entry.demand_score:.0f}/100, "
            f"trend={entry.demand_trend}, "
            f"6m={entry.growth_projection_6m:+.0f}%"
        )
    return "\n".join(lines)


def _format_velocity_data(entries: list[SkillVelocityEntry]) -> str:
    """Format velocity entries for reskilling prompt."""
    if not entries:
        return "No velocity data available"
    lines = []
    for entry in entries:
        lines.append(
            f"- {entry.skill_name}: velocity={entry.velocity_score:.1f}, "
            f"direction={entry.velocity_direction}, "
            f"health={entry.composite_health:.0f}/100"
        )
    return "\n".join(lines)


async def _persist_freshness_scores(
    db: AsyncSession,
    career_dna: CareerDNA,
    adjustments: list[dict[str, Any]],
) -> list[SkillFreshness]:
    """Compute and persist freshness scores with LLM adjustments."""
    # Clear existing scores
    await db.execute(
        delete(SkillFreshness).where(
            SkillFreshness.career_dna_id == career_dna.id,
        )
    )

    # Build adjustment lookup
    adj_lookup: dict[str, dict[str, Any]] = {}
    for adj in adjustments:
        name = adj.get("skill_name", "")
        adj_lookup[name.lower()] = adj

    entries: list[SkillFreshness] = []
    now = datetime.now(UTC)

    for genome_entry in (career_dna.skill_genome or [])[:30]:
        category = genome_entry.category or "technical"
        half_life = SkillDecayAnalyzer.get_half_life_for_category(category)
        decay_rate = SkillDecayAnalyzer.classify_decay_rate(half_life)

        # Compute days since active
        days_since = _compute_days_since(genome_entry.last_used_date, now)

        # Base freshness from exponential decay
        base_score = SkillDecayAnalyzer.compute_base_freshness(
            days_since_active=days_since,
            half_life_days=half_life,
        )

        # Apply LLM contextual adjustment
        adj = adj_lookup.get(genome_entry.skill_name.lower(), {})
        adjustment = adj.get("freshness_adjustment", 0.0)
        adjusted_score = max(0.0, min(100.0, base_score + adjustment))
        reasoning = adj.get("adjusted_reasoning", "Base exponential decay only")

        # Compute refresh urgency
        urgency = SkillDecayAnalyzer.compute_refresh_urgency(adjusted_score)

        entry = SkillFreshness(
            career_dna_id=career_dna.id,
            skill_name=genome_entry.skill_name,
            category=category,
            last_active_date=genome_entry.last_used_date,
            freshness_score=round(adjusted_score, 2),
            half_life_days=half_life,
            decay_rate=decay_rate,
            days_since_active=days_since,
            refresh_urgency=urgency,
            analysis_reasoning=reasoning,
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    return entries


async def _persist_demand_snapshots(
    db: AsyncSession,
    career_dna_id: uuid.UUID,
    data: list[dict[str, Any]],
) -> list[MarketDemandSnapshot]:
    """Replace and persist market demand snapshots."""
    await db.execute(
        delete(MarketDemandSnapshot).where(
            MarketDemandSnapshot.career_dna_id == career_dna_id,
        )
    )

    entries: list[MarketDemandSnapshot] = []
    for item in data:
        entry = MarketDemandSnapshot(
            career_dna_id=career_dna_id,
            skill_name=item.get("skill_name", "Unknown"),
            demand_score=item.get("demand_score", 50.0),
            demand_trend=item.get("demand_trend", "stable"),
            trend_confidence=item.get("trend_confidence", 0.5),
            job_posting_signal=item.get("job_posting_signal"),
            industry_relevance=item.get("industry_relevance"),
            growth_projection_6m=item.get("growth_projection_6m", 0.0),
            growth_projection_12m=item.get("growth_projection_12m", 0.0),
            data_sources=item.get("data_sources"),
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    return entries


async def _persist_velocity_entries(
    db: AsyncSession,
    career_dna_id: uuid.UUID,
    data: list[dict[str, Any]],
    freshness_entries: list[SkillFreshness],
    demand_entries: list[MarketDemandSnapshot],
) -> list[SkillVelocityEntry]:
    """Replace and persist velocity entries with component data."""
    await db.execute(
        delete(SkillVelocityEntry).where(
            SkillVelocityEntry.career_dna_id == career_dna_id,
        )
    )

    # Build lookups for component data
    freshness_lookup = {
        entry.skill_name.lower(): entry.freshness_score
        for entry in freshness_entries
    }
    demand_lookup = {
        entry.skill_name.lower(): entry.demand_score
        for entry in demand_entries
    }

    entries: list[SkillVelocityEntry] = []
    for item in data:
        skill_name = item.get("skill_name", "Unknown")
        freshness_component = freshness_lookup.get(skill_name.lower(), 50.0)
        demand_component = demand_lookup.get(skill_name.lower(), 50.0)

        entry = SkillVelocityEntry(
            career_dna_id=career_dna_id,
            skill_name=skill_name,
            velocity_score=item.get("velocity_score", 0.0),
            velocity_direction=item.get("velocity_direction", "steady"),
            freshness_component=freshness_component,
            demand_component=demand_component,
            composite_health=item.get("composite_health", 50.0),
            acceleration=item.get("acceleration", 0.0),
            reasoning=item.get("reasoning"),
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    return entries


async def _persist_pathways(
    db: AsyncSession,
    career_dna_id: uuid.UUID,
    data: list[dict[str, Any]],
) -> list[ReskillingPathway]:
    """Replace and persist reskilling pathways."""
    await db.execute(
        delete(ReskillingPathway).where(
            ReskillingPathway.career_dna_id == career_dna_id,
        )
    )

    entries: list[ReskillingPathway] = []
    for item in data:
        entry = ReskillingPathway(
            career_dna_id=career_dna_id,
            target_skill=item.get("target_skill", "Unknown"),
            current_level=item.get("current_level", "beginner"),
            target_level=item.get("target_level", "intermediate"),
            priority=item.get("priority", "recommended"),
            rationale=item.get("rationale", "Strategic skill development"),
            estimated_effort_hours=item.get("estimated_effort_hours", 40),
            prerequisite_skills=item.get("prerequisite_skills"),
            learning_resources=item.get("learning_resources"),
            career_impact=item.get("career_impact"),
            freshness_gain=item.get("freshness_gain", 0.0),
            demand_alignment=item.get("demand_alignment", 0.5),
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    return entries


async def _get_all(
    db: AsyncSession,
    model_class: type,
    career_dna_id: uuid.UUID,
) -> list[Any]:
    """Get all records of a model type for a career DNA."""
    result: Any = await db.execute(
        select(model_class)
        .where(model_class.career_dna_id == career_dna_id)  # type: ignore[attr-defined]
        .order_by(model_class.created_at.desc())  # type: ignore[attr-defined]
    )
    return list(result.scalars().all())


async def _get_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> SkillDecayPreference | None:
    """Get user's skill decay preferences."""
    result = await db.execute(
        select(SkillDecayPreference).where(
            SkillDecayPreference.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


def _compute_days_since(
    last_used_date: str | None,
    now: datetime,
) -> int:
    """Compute days since last active date string."""
    if not last_used_date:
        return 365  # Default: ~1 year if unknown

    try:
        # Parse date formats: YYYY-MM-DD, YYYY-MM, YYYY
        date_str = last_used_date.strip()
        if len(date_str) == 4:
            # Year only — assume mid-year
            last_date = datetime(int(date_str), 7, 1, tzinfo=UTC)
        elif len(date_str) == 7:
            # Year-month — assume 15th
            parts = date_str.split("-")
            last_date = datetime(int(parts[0]), int(parts[1]), 15, tzinfo=UTC)
        else:
            # Full date YYYY-MM-DD
            parts = date_str.split("-")
            last_date = datetime(
                int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=UTC,
            )

        delta = now - last_date
        return max(0, delta.days)
    except (ValueError, IndexError):
        return 365
