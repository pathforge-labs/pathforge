"""
PathForge — Cross-Engine Recommendation Intelligence™ Service
==============================================================
Service layer for the Intelligence Fusion Engine™ — correlates
insights from all 12 intelligence engines into prioritized,
actionable career recommendations.

Methods:
    get_dashboard()                 — Dashboard with latest batch + stats
    generate_recommendations()      — Trigger new recommendation batch
    get_recommendation_detail()     — Single recommendation with correlations
    update_recommendation_status()  — Update recommendation lifecycle
    list_recommendations()          — Paginated list with filters
    get_correlations()              — Cross-Engine Correlation Map™
    get_batches()                   — List recommendation batches
    get_preferences()               — User preference retrieval
    update_preferences()            — User preference update

Proprietary Algorithms:
    compute_priority_score()        — urgency × impact × inverse_effort
    aggregate_engine_signals()      — Collect data from ENGINE_REGISTRY
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_intelligence import (
    CrossEngineRecommendation,
    EffortLevel,
    RecommendationBatch,
    RecommendationCorrelation,
    RecommendationPreference,
    RecommendationStatus,
    RecommendationType,
)

# ── Constants ─────────────────────────────────────────────────

MAX_RECOMMENDATION_CONFIDENCE = 0.85
PRIORITY_WEIGHT_URGENCY = 0.40
PRIORITY_WEIGHT_IMPACT = 0.35
PRIORITY_WEIGHT_EFFORT = 0.25

EFFORT_INVERSE_MAP: dict[str, float] = {
    EffortLevel.QUICK_WIN.value: 100.0,
    EffortLevel.MODERATE.value: 70.0,
    EffortLevel.SIGNIFICANT.value: 40.0,
    EffortLevel.MAJOR_INITIATIVE.value: 15.0,
}

# Engine display names for correlation mapping
ENGINE_DISPLAY_NAMES: dict[str, str] = {
    "career_dna": "Career DNA™",
    "threat_radar": "Threat Radar™",
    "skill_decay": "Skill Decay Tracker™",
    "transition_pathways": "Transition Pathways™",
    "salary_intelligence": "Salary Intelligence™",
    "hidden_job_market": "Hidden Job Market™",
    "interview_intelligence": "Interview Intelligence™",
    "career_simulation": "Career Simulation™",
    "collective_intelligence": "Collective Intelligence™",
    "predictive_career": "Predictive Career™",
    "career_action_planner": "Career Action Planner™",
    "career_passport": "Career Passport™",
}


# ── Priority Score Algorithm ──────────────────────────────────


def compute_priority_score(
    urgency: float,
    impact: float,
    effort_level: str,
) -> float:
    """Compute Priority-Weighted Score™.

    Formula: urgency (0.40) × impact (0.35) × inverse_effort (0.25)

    Args:
        urgency: Urgency component (0-100).
        impact: Impact component (0-100).
        effort_level: EffortLevel enum value.

    Returns:
        Priority score (0-100), clamped to valid range.
    """
    inverse_effort = EFFORT_INVERSE_MAP.get(effort_level, 50.0)

    score = (
        PRIORITY_WEIGHT_URGENCY * urgency
        + PRIORITY_WEIGHT_IMPACT * impact
        + PRIORITY_WEIGHT_EFFORT * inverse_effort
    )

    return max(0.0, min(100.0, score))


# ── Service Class ─────────────────────────────────────────────


class RecommendationIntelligenceService:
    """Intelligence Fusion Engine™ — Recommendation Service.

    Orchestrates cross-engine recommendation generation,
    scoring, and lifecycle management.
    """

    # ── Dashboard ─────────────────────────────────────────

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get Recommendation Intelligence dashboard.

        Returns latest batch, recent recommendations, status counts,
        and user preferences.
        """
        # Latest batch
        batch_result = await db.execute(
            select(RecommendationBatch)
            .where(RecommendationBatch.user_id == str(user_id))
            .order_by(desc(RecommendationBatch.created_at))
            .limit(1)
        )
        latest_batch = batch_result.scalar_one_or_none()

        # Recent recommendations (top 10 by priority)
        recs_result = await db.execute(
            select(CrossEngineRecommendation)
            .where(CrossEngineRecommendation.user_id == str(user_id))
            .order_by(desc(CrossEngineRecommendation.priority_score))
            .limit(10)
        )
        recent_recs = list(recs_result.scalars().all())

        # Status counts
        counts: dict[str, int] = {}
        for status_val in [
            RecommendationStatus.PENDING.value,
            RecommendationStatus.IN_PROGRESS.value,
            RecommendationStatus.COMPLETED.value,
        ]:
            count_result = await db.execute(
                select(func.count())
                .select_from(CrossEngineRecommendation)
                .where(
                    CrossEngineRecommendation.user_id == str(user_id),
                    CrossEngineRecommendation.status == status_val,
                )
            )
            counts[status_val] = count_result.scalar_one()

        # Preferences
        pref = await RecommendationIntelligenceService.get_preferences(
            db, user_id=user_id,
        )

        return {
            "latest_batch": latest_batch,
            "recent_recommendations": recent_recs,
            "total_pending": counts.get("pending", 0),
            "total_in_progress": counts.get("in_progress", 0),
            "total_completed": counts.get("completed", 0),
            "preferences": pref,
        }

    # ── Generate Recommendations ──────────────────────────

    @staticmethod
    async def generate_recommendations(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        batch_type: str = "manual",
        focus_categories: list[str] | None = None,
    ) -> RecommendationBatch:
        """Generate cross-engine recommendations.

        Pipeline:
            1. Create batch record
            2. Aggregate engine signals (placeholder — no DB query)
            3. Generate recommendation entries
            4. Compute priority scores
            5. Create correlation mappings
            6. Return batch

        Note: In production, step 2 would query all 12 engines.
        For Sprint 23, we generate structured placeholder data
        to establish the pipeline architecture.
        """
        # Get user preferences for max count
        pref = await RecommendationIntelligenceService.get_preferences(
            db, user_id=user_id,
        )
        max_recs = 10
        if pref is not None:
            max_recs = pref.max_recommendations_per_batch

        # Create batch
        batch = RecommendationBatch(
            user_id=str(user_id),
            batch_type=batch_type,
            engine_snapshot={"generated_at": datetime.now(UTC).isoformat()},
            total_recommendations=0,
            career_vitals_at_generation=None,
        )
        db.add(batch)
        await db.flush()

        # Generate structured placeholder recommendations
        recommendation_templates = _get_recommendation_templates(
            focus_categories=focus_categories,
        )

        created_count = 0
        for template in recommendation_templates[:max_recs]:
            priority = compute_priority_score(
                urgency=template["urgency"],
                impact=template["impact"],
                effort_level=template["effort_level"],
            )

            rec = CrossEngineRecommendation(
                user_id=str(user_id),
                batch_id=str(batch.id),
                recommendation_type=template["type"],
                status=RecommendationStatus.PENDING.value,
                effort_level=template["effort_level"],
                priority_score=priority,
                urgency=template["urgency"],
                impact_score=template["impact"],
                confidence_score=min(
                    template.get("confidence", 0.70),
                    MAX_RECOMMENDATION_CONFIDENCE,
                ),
                title=template["title"],
                description=template["description"],
                action_items=template.get("action_items"),
                source_engines=template.get("source_engines"),
            )
            db.add(rec)
            await db.flush()

            # Create correlations for contributing engines
            for engine_data in template.get("correlations", []):
                correlation = RecommendationCorrelation(
                    recommendation_id=str(rec.id),
                    engine_name=engine_data["engine"],
                    correlation_strength=engine_data["strength"],
                    insight_summary=engine_data.get("insight", ""),
                )
                db.add(correlation)

            created_count += 1

        # Update batch count
        batch.total_recommendations = created_count
        await db.commit()
        await db.refresh(batch)

        return batch

    # ── Recommendation Detail ─────────────────────────────

    @staticmethod
    async def get_recommendation_detail(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        recommendation_id: uuid.UUID,
    ) -> CrossEngineRecommendation | None:
        """Get single recommendation with correlations."""
        result = await db.execute(
            select(CrossEngineRecommendation)
            .where(
                CrossEngineRecommendation.id == str(recommendation_id),
                CrossEngineRecommendation.user_id == str(user_id),
            )
        )
        return result.scalar_one_or_none()

    # ── Update Status ─────────────────────────────────────

    @staticmethod
    async def update_recommendation_status(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        recommendation_id: uuid.UUID,
        new_status: str,
    ) -> CrossEngineRecommendation:
        """Update recommendation lifecycle status.

        Valid transitions:
            pending → in_progress, dismissed
            in_progress → completed, dismissed
        """
        result = await db.execute(
            select(CrossEngineRecommendation)
            .where(
                CrossEngineRecommendation.id == str(recommendation_id),
                CrossEngineRecommendation.user_id == str(user_id),
            )
        )
        rec = result.scalar_one_or_none()
        if rec is None:
            msg = f"Recommendation {recommendation_id} not found."
            raise ValueError(msg)

        # Validate status transition
        valid_transitions: dict[str, list[str]] = {
            "pending": ["in_progress", "dismissed"],
            "in_progress": ["completed", "dismissed"],
            "completed": [],
            "dismissed": [],
            "expired": [],
        }
        allowed = valid_transitions.get(rec.status, [])
        if new_status not in allowed:
            msg = (
                f"Cannot transition from '{rec.status}' to '{new_status}'. "
                f"Allowed: {allowed}"
            )
            raise ValueError(msg)

        rec.status = new_status
        await db.commit()
        await db.refresh(rec)
        return rec

    # ── List Recommendations ──────────────────────────────

    @staticmethod
    async def list_recommendations(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        status_filter: str | None = None,
        type_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CrossEngineRecommendation]:
        """List recommendations with optional filters."""
        query = (
            select(CrossEngineRecommendation)
            .where(CrossEngineRecommendation.user_id == str(user_id))
        )

        if status_filter:
            query = query.where(
                CrossEngineRecommendation.status == status_filter,
            )
        if type_filter:
            query = query.where(
                CrossEngineRecommendation.recommendation_type == type_filter,
            )

        query = (
            query
            .order_by(desc(CrossEngineRecommendation.priority_score))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    # ── Correlations ──────────────────────────────────────

    @staticmethod
    async def get_correlations(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        recommendation_id: uuid.UUID,
    ) -> list[RecommendationCorrelation]:
        """Get Cross-Engine Correlation Map™ for a recommendation."""
        # Verify ownership
        rec_result = await db.execute(
            select(CrossEngineRecommendation.id)
            .where(
                CrossEngineRecommendation.id == str(recommendation_id),
                CrossEngineRecommendation.user_id == str(user_id),
            )
        )
        if rec_result.scalar_one_or_none() is None:
            msg = f"Recommendation {recommendation_id} not found."
            raise ValueError(msg)

        result = await db.execute(
            select(RecommendationCorrelation)
            .where(
                RecommendationCorrelation.recommendation_id
                == str(recommendation_id),
            )
            .order_by(desc(RecommendationCorrelation.correlation_strength))
        )
        return list(result.scalars().all())

    # ── Batches ───────────────────────────────────────────

    @staticmethod
    async def get_batches(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[RecommendationBatch]:
        """List recommendation batches."""
        result = await db.execute(
            select(RecommendationBatch)
            .where(RecommendationBatch.user_id == str(user_id))
            .order_by(desc(RecommendationBatch.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Preferences ───────────────────────────────────────

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> RecommendationPreference | None:
        """Get user's Recommendation Intelligence preferences."""
        result = await db.execute(
            select(RecommendationPreference)
            .where(RecommendationPreference.user_id == str(user_id))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> RecommendationPreference:
        """Update or create Recommendation Intelligence preferences."""
        result = await db.execute(
            select(RecommendationPreference)
            .where(RecommendationPreference.user_id == str(user_id))
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = RecommendationPreference(
                user_id=str(user_id),
                **updates,
            )
            db.add(pref)
        else:
            for key, value in updates.items():
                if hasattr(pref, key):
                    setattr(pref, key, value)

        await db.commit()
        await db.refresh(pref)
        return pref


# ── Recommendation Templates ────────────────────────────────
# Structured templates for generating cross-engine recommendations.
# In production, these would be generated by the LLM pipeline.


def _get_recommendation_templates(
    focus_categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Get recommendation templates for generation.

    Returns structured templates that follow the cross-engine
    correlation pattern. Each template includes source engines,
    correlation strengths, and action items.
    """
    templates: list[dict[str, Any]] = [
        {
            "type": RecommendationType.SKILL_GAP.value,
            "title": "Bridge critical skill gap in cloud architecture",
            "description": (
                "Your Skill Decay Tracker shows declining freshness in "
                "cloud architecture skills, while Career DNA identifies "
                "this as a core competency. Bridging this gap could "
                "improve your Career Vitals score by 8-12 points."
            ),
            "urgency": 75.0,
            "impact": 80.0,
            "effort_level": EffortLevel.SIGNIFICANT.value,
            "confidence": 0.78,
            "action_items": [
                "Complete AWS Solutions Architect certification",
                "Build a cloud-native side project",
                "Attend 2 cloud architecture meetups this month",
            ],
            "source_engines": ["skill_decay", "career_dna", "salary_intelligence"],
            "correlations": [
                {
                    "engine": "skill_decay",
                    "strength": 0.85,
                    "insight": "Cloud architecture freshness declined 15% in 90 days",
                },
                {
                    "engine": "career_dna",
                    "strength": 0.72,
                    "insight": "Cloud architecture identified as top-3 core competency",
                },
                {
                    "engine": "salary_intelligence",
                    "strength": 0.58,
                    "insight": "Cloud skills command 18% salary premium in your market",
                },
            ],
        },
        {
            "type": RecommendationType.THREAT_MITIGATION.value,
            "title": "Mitigate emerging automation risk in data processing",
            "description": (
                "Threat Radar detects growing automation risk for manual "
                "data processing tasks. Cross-referencing with Predictive "
                "Career shows this trend accelerating in 2026-2027."
            ),
            "urgency": 85.0,
            "impact": 70.0,
            "effort_level": EffortLevel.MODERATE.value,
            "confidence": 0.72,
            "action_items": [
                "Learn AI/ML pipeline automation tools",
                "Transition 2 manual workflows to automated pipelines",
                "Document automation expertise for resume update",
            ],
            "source_engines": ["threat_radar", "predictive_career", "skill_decay"],
            "correlations": [
                {
                    "engine": "threat_radar",
                    "strength": 0.90,
                    "insight": "Automation risk score increased from 35 to 62 in Q4",
                },
                {
                    "engine": "predictive_career",
                    "strength": 0.68,
                    "insight": "Data processing automation trend accelerating 2026-2027",
                },
                {
                    "engine": "skill_decay",
                    "strength": 0.45,
                    "insight": "Automation tool skills need refreshing (stale 45 days)",
                },
            ],
        },
        {
            "type": RecommendationType.OPPORTUNITY.value,
            "title": "Pursue hidden senior engineering opportunities",
            "description": (
                "Hidden Job Market detected 3 unlisted senior positions "
                "matching your Career DNA profile. Combined with strong "
                "Salary Intelligence data, these represent a 15-25% "
                "compensation uplift opportunity."
            ),
            "urgency": 65.0,
            "impact": 90.0,
            "effort_level": EffortLevel.MODERATE.value,
            "confidence": 0.68,
            "action_items": [
                "Reach out to identified company contacts",
                "Update resume with latest project highlights",
                "Prepare STAR examples for interview readiness",
            ],
            "source_engines": [
                "hidden_job_market", "career_dna", "salary_intelligence",
            ],
            "correlations": [
                {
                    "engine": "hidden_job_market",
                    "strength": 0.82,
                    "insight": "3 unlisted senior positions match 80%+ of your profile",
                },
                {
                    "engine": "salary_intelligence",
                    "strength": 0.75,
                    "insight": "Target roles offer 15-25% above current compensation",
                },
                {
                    "engine": "career_dna",
                    "strength": 0.70,
                    "insight": "Your Career DNA strongly aligns with target role profiles",
                },
            ],
        },
        {
            "type": RecommendationType.SALARY_OPTIMIZATION.value,
            "title": "Optimize compensation through strategic skill positioning",
            "description": (
                "Salary Intelligence shows your current compensation is "
                "12% below market median for your experience band. Adding "
                "two high-demand skills could close this gap."
            ),
            "urgency": 55.0,
            "impact": 85.0,
            "effort_level": EffortLevel.SIGNIFICANT.value,
            "confidence": 0.75,
            "action_items": [
                "Acquire Kubernetes certification (high salary impact)",
                "Complete system design portfolio project",
                "Prepare compensation negotiation data package",
            ],
            "source_engines": ["salary_intelligence", "skill_decay", "collective_intelligence"],
            "correlations": [
                {
                    "engine": "salary_intelligence",
                    "strength": 0.88,
                    "insight": "Current compensation 12% below market median",
                },
                {
                    "engine": "skill_decay",
                    "strength": 0.62,
                    "insight": "Two high-impact skills identified for salary leverage",
                },
                {
                    "engine": "collective_intelligence",
                    "strength": 0.55,
                    "insight": "Peer cohort with these skills earns 20% more on average",
                },
            ],
        },
        {
            "type": RecommendationType.CAREER_ACCELERATION.value,
            "title": "Accelerate promotion readiness with leadership signals",
            "description": (
                "Career Simulation projects promotion eligibility in 6-9 "
                "months if leadership visibility is increased. Interview "
                "Intelligence confirms strong behavioral competencies."
            ),
            "urgency": 50.0,
            "impact": 75.0,
            "effort_level": EffortLevel.MODERATE.value,
            "confidence": 0.65,
            "action_items": [
                "Volunteer to lead next quarter's team initiative",
                "Mentor a junior team member (document impact)",
                "Present technical findings at team/company level",
            ],
            "source_engines": [
                "career_simulation", "interview_intelligence", "career_action_planner",
            ],
            "correlations": [
                {
                    "engine": "career_simulation",
                    "strength": 0.78,
                    "insight": "Promotion probability 72% within 6-9 months with leadership",
                },
                {
                    "engine": "interview_intelligence",
                    "strength": 0.65,
                    "insight": "Strong behavioral scores; leadership examples needed",
                },
                {
                    "engine": "career_action_planner",
                    "strength": 0.58,
                    "insight": "Current plan lacks leadership milestone targets",
                },
            ],
        },
        {
            "type": RecommendationType.NETWORK_BUILDING.value,
            "title": "Expand professional network in target industry segment",
            "description": (
                "Collective Intelligence shows your peer network is thin "
                "in the AI/ML segment, which Predictive Career flags as "
                "your highest-growth opportunity area."
            ),
            "urgency": 40.0,
            "impact": 60.0,
            "effort_level": EffortLevel.QUICK_WIN.value,
            "confidence": 0.62,
            "action_items": [
                "Attend 2 AI/ML industry events this month",
                "Connect with 5 professionals in target companies",
                "Join relevant online communities and contribute weekly",
            ],
            "source_engines": [
                "collective_intelligence", "predictive_career", "hidden_job_market",
            ],
            "correlations": [
                {
                    "engine": "collective_intelligence",
                    "strength": 0.72,
                    "insight": "Network density 40% below peers in AI/ML segment",
                },
                {
                    "engine": "predictive_career",
                    "strength": 0.65,
                    "insight": "AI/ML identified as highest-growth opportunity area",
                },
                {
                    "engine": "hidden_job_market",
                    "strength": 0.48,
                    "insight": "Network expansion improves hidden opportunity discovery 35%",
                },
            ],
        },
    ]

    # Filter by focus categories if provided
    if focus_categories:
        templates = [
            template for template in templates
            if template["type"] in focus_categories
        ]

    return templates
