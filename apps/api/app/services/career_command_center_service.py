"""
PathForge — Career Command Center™ Service
============================================
Orchestration Engine: aggregates all 12 intelligence engines into
a unified Career Vitals™ composite health score, Engine Heartbeat™
freshness monitoring, and actionable strengths/attention areas.

Pipeline flow:
    1. Collect engine heartbeats (latest record per engine)
    2. Compute engine health scores (recency + native score + trend)
    3. Calculate Career Vitals™ composite (weighted average)
    4. Classify health band (thriving → critical)
    5. Identify top-3 strengths and attention areas
    6. Compute trend direction vs previous snapshot
    7. Cache snapshot for fast retrieval
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_action_planner import CareerActionPlan
from app.models.career_command_center import (
    CareerSnapshot,
    CommandCenterPreference,
    HealthBand,
    HeartbeatStatus,
    TrendDirection,
)
from app.models.career_dna import CareerDNA
from app.models.career_passport import CountryComparison
from app.models.career_simulation import CareerSimulation
from app.models.collective_intelligence import PeerCohortAnalysis
from app.models.hidden_job_market import CompanySignal
from app.models.interview_intelligence import InterviewPrep
from app.models.predictive_career import CareerForecast
from app.models.salary_intelligence import SalaryEstimate
from app.models.skill_decay import SkillFreshness
from app.models.threat_radar import CareerResilienceSnapshot
from app.models.transition_pathways import TransitionPath

logger = logging.getLogger(__name__)


# ── Engine Registry ────────────────────────────────────────────
# Each engine is defined by its model, score field, and weight.

ENGINE_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "career_dna",
        "display_name": "Career DNA™",
        "model": CareerDNA,
        "score_field": None,
        "weight": 1.5,
        "user_id_field": "user_id",
    },
    {
        "name": "threat_radar",
        "display_name": "Threat Radar™",
        "model": CareerResilienceSnapshot,
        "score_field": "overall_score",
        "weight": 1.3,
        "user_id_field": None,
    },
    {
        "name": "predictive_career",
        "display_name": "Predictive Career™",
        "model": CareerForecast,
        "score_field": "outlook_score",
        "weight": 1.2,
        "user_id_field": "user_id",
    },
    {
        "name": "skill_decay",
        "display_name": "Skill Decay Detector™",
        "model": SkillFreshness,
        "score_field": "freshness_score",
        "weight": 1.2,
        "user_id_field": None,
    },
    {
        "name": "career_action_planner",
        "display_name": "Career Action Planner™",
        "model": CareerActionPlan,
        "score_field": "completion_pct",
        "weight": 1.1,
        "user_id_field": "user_id",
    },
    {
        "name": "salary_intelligence",
        "display_name": "Salary Intelligence™",
        "model": SalaryEstimate,
        "score_field": "confidence_score",
        "weight": 1.0,
        "user_id_field": "user_id",
    },
    {
        "name": "hidden_job_market",
        "display_name": "Hidden Job Market™",
        "model": CompanySignal,
        "score_field": "signal_strength",
        "weight": 1.0,
        "user_id_field": "user_id",
    },
    {
        "name": "collective_intelligence",
        "display_name": "Collective Intelligence™",
        "model": PeerCohortAnalysis,
        "score_field": "percentile_rank",
        "weight": 0.9,
        "user_id_field": "user_id",
    },
    {
        "name": "career_simulation",
        "display_name": "Career Simulation™",
        "model": CareerSimulation,
        "score_field": "confidence_score",
        "weight": 0.8,
        "user_id_field": "user_id",
    },
    {
        "name": "interview_intelligence",
        "display_name": "Interview Intelligence™",
        "model": InterviewPrep,
        "score_field": "readiness_score",
        "weight": 0.8,
        "user_id_field": "user_id",
    },
    {
        "name": "transition_pathways",
        "display_name": "Transition Pathways™",
        "model": TransitionPath,
        "score_field": "viability_score",
        "weight": 0.8,
        "user_id_field": "user_id",
    },
    {
        "name": "career_passport",
        "display_name": "Career Passport™",
        "model": CountryComparison,
        "score_field": "overall_match_score",
        "weight": 0.7,
        "user_id_field": "user_id",
    },
]

# Heartbeat thresholds (days)
HEARTBEAT_ACTIVE_DAYS = 7
HEARTBEAT_STALE_DAYS = 30


class CareerCommandCenterService:
    """Orchestration Engine for Career Command Center™.

    Aggregates all 12 intelligence engines into a unified
    dashboard with Career Vitals™ and Engine Heartbeat™.
    """

    # ── Dashboard ──────────────────────────────────────────────

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get full Career Command Center dashboard.

        Returns Career Vitals™ snapshot, all engine heartbeats,
        strengths, attention areas, and user preferences.
        """
        # Get or create snapshot
        snapshot = await CareerCommandCenterService._get_latest_snapshot(
            db, user_id,
        )

        # If no snapshot exists, generate one
        if snapshot is None:
            snapshot = await CareerCommandCenterService.refresh_snapshot(
                db, user_id=user_id,
            )

        # Get preferences
        preferences = await CareerCommandCenterService.get_preferences(
            db, user_id=user_id,
        )

        return {
            "snapshot": snapshot,
            "preferences": preferences,
        }

    # ── Health Summary ─────────────────────────────────────────

    @staticmethod
    async def get_health_summary(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get lightweight career health summary."""
        snapshot = await CareerCommandCenterService._get_latest_snapshot(
            db, user_id,
        )

        if snapshot is None:
            snapshot = await CareerCommandCenterService.refresh_snapshot(
                db, user_id=user_id,
            )

        engine_statuses = snapshot.engine_statuses or {}
        engines_active = sum(
            1 for engine_data in engine_statuses.values()
            if isinstance(engine_data, dict)
            and engine_data.get("heartbeat") == HeartbeatStatus.ACTIVE.value
        )

        strengths = snapshot.strengths or {}
        attention = snapshot.attention_areas or {}

        top_strength_items = strengths.get("items", []) if isinstance(strengths, dict) else []
        top_attention_items = attention.get("items", []) if isinstance(attention, dict) else []

        return {
            "health_score": snapshot.health_score,
            "health_band": snapshot.health_band,
            "trend_direction": snapshot.trend_direction,
            "engines_active": engines_active,
            "engines_total": len(ENGINE_REGISTRY),
            "top_strength": top_strength_items[0]["engine"] if top_strength_items else None,
            "top_attention": top_attention_items[0]["engine"] if top_attention_items else None,
        }

    # ── Engine Detail ──────────────────────────────────────────

    @staticmethod
    async def get_engine_detail(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        engine_name: str,
    ) -> dict[str, Any] | None:
        """Get detailed status for a single engine."""
        engine_config = _find_engine_config(engine_name)
        if engine_config is None:
            return None

        heartbeat = await _collect_single_heartbeat(
            db, user_id, engine_config,
        )

        # Get recent records
        recent = await _get_recent_records(
            db, user_id, engine_config, limit=5,
        )

        return {
            "engine_name": engine_config["name"],
            "display_name": engine_config["display_name"],
            "heartbeat": heartbeat["heartbeat"],
            "score": heartbeat["score"],
            "last_updated": heartbeat["last_updated"],
            "record_count": heartbeat["record_count"],
            "recent_records": recent,
        }

    # ── Refresh Snapshot ───────────────────────────────────────

    @staticmethod
    async def refresh_snapshot(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> CareerSnapshot:
        """Force re-computation of Career Vitals™ snapshot.

        Pipeline:
            1. Check Career DNA exists
            2. Collect all engine heartbeats
            3. Compute weighted health score
            4. Classify health band
            5. Identify strengths & attention areas
            6. Compute trend direction
            7. Persist snapshot
        """
        # Check Career DNA
        career_dna = await _get_career_dna(db, user_id)
        career_dna_id = str(career_dna.id) if career_dna else ""

        # Collect heartbeats
        heartbeats = await _collect_all_heartbeats(db, user_id)

        # Compute Career Vitals™
        health_score = _compute_career_health_score(heartbeats)
        health_band = _classify_health_band(health_score)

        # Strengths & attention
        strengths = _identify_strengths(heartbeats)
        attention_areas = _identify_attention_areas(heartbeats)

        # Trend direction
        previous = await CareerCommandCenterService._get_latest_snapshot(
            db, user_id,
        )
        trend = _compute_trend_direction(health_score, previous)

        # Build engine statuses map
        engine_statuses = {
            heartbeat["engine_name"]: {
                "display_name": heartbeat["display_name"],
                "heartbeat": heartbeat["heartbeat"],
                "score": heartbeat["score"],
                "last_updated": (
                    heartbeat["last_updated"].isoformat()
                    if heartbeat["last_updated"] else None
                ),
            }
            for heartbeat in heartbeats
        }

        # Persist
        snapshot = CareerSnapshot(
            user_id=str(user_id),
            career_dna_id=career_dna_id,
            health_score=health_score,
            health_band=health_band,
            engine_statuses=engine_statuses,
            strengths=strengths,
            attention_areas=attention_areas,
            trend_direction=trend,
        )
        db.add(snapshot)
        await db.flush()

        return snapshot

    # ── Preferences ────────────────────────────────────────────

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> CommandCenterPreference | None:
        """Get user's Command Center preferences."""
        result = await db.execute(
            select(CommandCenterPreference).where(
                CommandCenterPreference.user_id == str(user_id),
            ),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> CommandCenterPreference:
        """Update or create Command Center preferences."""
        result = await db.execute(
            select(CommandCenterPreference).where(
                CommandCenterPreference.user_id == str(user_id),
            ),
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = CommandCenterPreference(user_id=str(user_id))
            db.add(pref)

        for key, value in updates.items():
            if value is not None and hasattr(pref, key):
                setattr(pref, key, value)

        await db.flush()
        return pref

    # ── Private Helpers ────────────────────────────────────────

    @staticmethod
    async def _get_latest_snapshot(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> CareerSnapshot | None:
        """Get the most recent career snapshot."""
        result = await db.execute(
            select(CareerSnapshot)
            .where(CareerSnapshot.user_id == str(user_id))
            .order_by(CareerSnapshot.created_at.desc())
            .limit(1),
        )
        return result.scalar_one_or_none()


# ── Career Vitals™ Algorithm ──────────────────────────────────


def _compute_career_health_score(
    heartbeats: list[dict[str, Any]],
) -> float:
    """Compute Career Vitals™ composite health score.

    CHS = Σ(engine_weight × engine_health) / Σ engine_weight

    Engine Health = f(recency, score, trend):
        - recency:  0-100 based on days since last analysis
        - score:    0-100 from engine's native scoring
        - trend:    +10 improving, 0 stable, -10 declining
    """
    total_weighted = 0.0
    total_weight = 0.0

    for heartbeat in heartbeats:
        weight = heartbeat.get("weight", 1.0)
        engine_health = _compute_engine_health(heartbeat)

        total_weighted += weight * engine_health
        total_weight += weight

    if total_weight == 0:
        return 0.0

    raw_score = total_weighted / total_weight
    return round(max(0.0, min(100.0, raw_score)), 1)


def _compute_engine_health(heartbeat: dict[str, Any]) -> float:
    """Compute individual engine health from heartbeat data."""
    # Base score from engine's native scoring
    score = heartbeat.get("score")
    if score is None:
        return 0.0

    # Recency factor (0-100)
    last_updated = heartbeat.get("last_updated")
    if last_updated is None:
        recency = 0.0
    else:
        days_ago = (datetime.now(UTC) - last_updated).days
        if days_ago <= HEARTBEAT_ACTIVE_DAYS:
            recency = 100.0
        elif days_ago <= HEARTBEAT_STALE_DAYS:
            recency = max(
                30.0,
                100.0 - ((days_ago - HEARTBEAT_ACTIVE_DAYS) * 3.0),
            )
        else:
            recency = max(10.0, 30.0 - (days_ago - HEARTBEAT_STALE_DAYS))

    # Combine: 60% score + 40% recency
    combined = float(score * 0.6) + float(recency * 0.4)
    return max(0.0, min(100.0, combined))


def _classify_health_band(score: float) -> str:
    """Map Career Vitals™ score to health band."""
    if score >= 80:
        return HealthBand.THRIVING.value
    if score >= 60:
        return HealthBand.HEALTHY.value
    if score >= 40:
        return HealthBand.ATTENTION.value
    if score >= 20:
        return HealthBand.AT_RISK.value
    return HealthBand.CRITICAL.value


def _identify_strengths(
    heartbeats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify top-3 strengths from engine scores."""
    scored = [
        heartbeat for heartbeat in heartbeats
        if heartbeat.get("score") is not None
        and heartbeat["score"] >= 60.0
    ]
    scored.sort(key=lambda item: item.get("score", 0), reverse=True)

    items = [
        {
            "engine": item["display_name"],
            "engine_name": item["engine_name"],
            "score": item["score"],
        }
        for item in scored[:3]
    ]

    return {"items": items, "count": len(items)}


def _identify_attention_areas(
    heartbeats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify top-3 areas needing attention."""
    needing_attention = [
        heartbeat for heartbeat in heartbeats
        if heartbeat.get("score") is not None
        and heartbeat["score"] < 50.0
    ]
    needing_attention.sort(key=lambda item: item.get("score", 100))

    # Also include dormant/never-run engines
    dormant = [
        heartbeat for heartbeat in heartbeats
        if heartbeat.get("heartbeat") in (
            HeartbeatStatus.DORMANT.value,
            HeartbeatStatus.NEVER_RUN.value,
        )
        and heartbeat not in needing_attention
    ]

    combined = needing_attention + dormant
    items = [
        {
            "engine": item["display_name"],
            "engine_name": item["engine_name"],
            "score": item.get("score"),
            "reason": (
                "Low score"
                if item.get("score") is not None and item["score"] < 50
                else "Not yet activated"
            ),
        }
        for item in combined[:3]
    ]

    return {"items": items, "count": len(items)}


def _compute_trend_direction(
    current_score: float,
    previous_snapshot: CareerSnapshot | None,
) -> str:
    """Compute trend direction vs previous snapshot."""
    if previous_snapshot is None:
        return TrendDirection.STABLE.value

    delta = current_score - previous_snapshot.health_score
    if delta >= 3.0:
        return TrendDirection.IMPROVING.value
    if delta <= -3.0:
        return TrendDirection.DECLINING.value
    return TrendDirection.STABLE.value


def _find_engine_config(engine_name: str) -> dict[str, Any] | None:
    """Find engine config by name."""
    for engine in ENGINE_REGISTRY:
        if engine["name"] == engine_name:
            return engine
    return None


# ── Data Collection Helpers ────────────────────────────────────


async def _get_career_dna(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> CareerDNA | None:
    """Get user's Career DNA."""
    result = await db.execute(
        select(CareerDNA).where(CareerDNA.user_id == str(user_id)),
    )
    return result.scalar_one_or_none()


async def _collect_all_heartbeats(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Collect heartbeats for all 12 engines."""
    heartbeats = []
    for engine_config in ENGINE_REGISTRY:
        heartbeat = await _collect_single_heartbeat(
            db, user_id, engine_config,
        )
        heartbeats.append(heartbeat)
    return heartbeats


async def _collect_single_heartbeat(
    db: AsyncSession,
    user_id: uuid.UUID,
    engine_config: dict[str, Any],
) -> dict[str, Any]:
    """Collect heartbeat for a single engine."""
    model_class = engine_config["model"]
    score_field_name = engine_config.get("score_field")
    user_field = engine_config.get("user_id_field")

    # Build query for latest record
    try:
        if user_field:
            filter_condition = getattr(model_class, user_field) == str(user_id)
        else:
            # For models that use career_dna_id, look up via CareerDNA
            career_dna = await _get_career_dna(db, user_id)
            if career_dna is None:
                return _empty_heartbeat(engine_config)
            filter_condition = (
                model_class.career_dna_id == str(career_dna.id)
            )

        # Get latest record
        query = (
            select(model_class)
            .where(filter_condition)
            .order_by(model_class.created_at.desc())
            .limit(1)
        )
        result = await db.execute(query)
        latest = result.scalar_one_or_none()

        # Count total records
        count_query = (
            select(func.count(model_class.id))
            .where(filter_condition)
        )
        count_result = await db.execute(count_query)
        record_count = count_result.scalar() or 0

    except Exception:
        logger.warning(
            "Failed to collect heartbeat for %s",
            engine_config["name"],
        )
        return _empty_heartbeat(engine_config)

    if latest is None:
        return _empty_heartbeat(engine_config)

    # Extract score
    score: float | None = None
    if score_field_name and hasattr(latest, score_field_name):
        raw_score = getattr(latest, score_field_name)
        if raw_score is not None:
            score = float(raw_score)
            # Normalize scores that are 0-1 range to 0-100
            if score <= 1.0 and score_field_name in (
                "confidence_score", "signal_strength",
            ):
                score = score * 100.0
    elif engine_config["name"] == "career_dna":
        # Career DNA: score based on genome completeness
        score = 75.0  # Exists = baseline healthy

    # Determine heartbeat status
    last_updated = latest.created_at
    heartbeat_status = _classify_heartbeat(last_updated)

    return {
        "engine_name": engine_config["name"],
        "display_name": engine_config["display_name"],
        "heartbeat": heartbeat_status,
        "score": round(score, 1) if score is not None else None,
        "last_updated": last_updated,
        "weight": engine_config["weight"],
        "record_count": record_count,
    }


def _empty_heartbeat(engine_config: dict[str, Any]) -> dict[str, Any]:
    """Return a heartbeat for an engine with no data."""
    return {
        "engine_name": engine_config["name"],
        "display_name": engine_config["display_name"],
        "heartbeat": HeartbeatStatus.NEVER_RUN.value,
        "score": None,
        "last_updated": None,
        "weight": engine_config["weight"],
        "record_count": 0,
    }


def _classify_heartbeat(last_updated: datetime) -> str:
    """Classify engine freshness from last update timestamp."""
    now = datetime.now(UTC)
    delta = now - last_updated

    if delta <= timedelta(days=HEARTBEAT_ACTIVE_DAYS):
        return HeartbeatStatus.ACTIVE.value
    if delta <= timedelta(days=HEARTBEAT_STALE_DAYS):
        return HeartbeatStatus.STALE.value
    return HeartbeatStatus.DORMANT.value


async def _get_recent_records(
    db: AsyncSession,
    user_id: uuid.UUID,
    engine_config: dict[str, Any],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Get recent records for a specific engine."""
    model_class = engine_config["model"]
    user_field = engine_config.get("user_id_field")

    try:
        if user_field:
            filter_condition = getattr(model_class, user_field) == str(user_id)
        else:
            career_dna = await _get_career_dna(db, user_id)
            if career_dna is None:
                return []
            filter_condition = (
                model_class.career_dna_id == str(career_dna.id)
            )

        query = (
            select(model_class)
            .where(filter_condition)
            .order_by(model_class.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        records = list(result.scalars().all())

        return [
            {
                "id": str(record.id),
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ]
    except Exception:
        logger.warning(
            "Failed to get recent records for %s",
            engine_config["name"],
        )
        return []
