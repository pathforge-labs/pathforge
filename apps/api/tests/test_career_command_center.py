"""
PathForge — Career Command Center™ Test Suite
================================================
Tests for Sprint 22: models, enums, health algorithm, service helpers.

Coverage:
    - StrEnum values (HealthBand, HeartbeatStatus, TrendDirection)
    - Model creation (CareerSnapshot, CommandCenterPreference)
    - Career Vitals™ algorithm (health score, band, trend)
    - Engine health computation
    - Strengths & attention area identification
    - Schema validation (response models)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.career_command_center import (
    CareerSnapshot,
    CommandCenterPreference,
    HealthBand,
    HeartbeatStatus,
    TrendDirection,
)
from app.schemas.career_command_center import (
    CareerHealthSummaryResponse,
    CareerSnapshotResponse,
    CommandCenterPreferenceResponse,
    EngineStatusResponse,
)
from app.services.career_command_center_service import (
    HEARTBEAT_ACTIVE_DAYS,
    _classify_health_band,
    _classify_heartbeat,
    _compute_career_health_score,
    _compute_engine_health,
    _compute_trend_direction,
    _identify_attention_areas,
    _identify_strengths,
)

# ── Enum Tests ─────────────────────────────────────────────────


class TestEnums:
    """Test StrEnum definitions."""

    def test_health_band_values(self) -> None:
        assert HealthBand.THRIVING == "thriving"
        assert HealthBand.HEALTHY == "healthy"
        assert HealthBand.ATTENTION == "attention"
        assert HealthBand.AT_RISK == "at_risk"
        assert HealthBand.CRITICAL == "critical"

    def test_heartbeat_status_values(self) -> None:
        assert HeartbeatStatus.ACTIVE == "active"
        assert HeartbeatStatus.STALE == "stale"
        assert HeartbeatStatus.DORMANT == "dormant"
        assert HeartbeatStatus.NEVER_RUN == "never_run"

    def test_trend_direction_values(self) -> None:
        assert TrendDirection.IMPROVING == "improving"
        assert TrendDirection.STABLE == "stable"
        assert TrendDirection.DECLINING == "declining"


# ── Model Creation Tests ──────────────────────────────────────


class TestCareerSnapshotModel:
    """Test CareerSnapshot model instantiation."""

    def test_create_snapshot(self) -> None:
        snapshot = CareerSnapshot(
            user_id=str(uuid.uuid4()),
            career_dna_id=str(uuid.uuid4()),
            health_score=75.5,
            health_band="healthy",
            engine_statuses={"career_dna": {"heartbeat": "active"}},
            trend_direction="improving",
        )
        assert snapshot.health_score == 75.5
        assert snapshot.health_band == "healthy"
        assert snapshot.trend_direction == "improving"
        assert snapshot.__tablename__ == "cc_career_snapshots"

    def test_default_transparency_fields(self) -> None:
        snapshot = CareerSnapshot(
            user_id=str(uuid.uuid4()),
            career_dna_id=str(uuid.uuid4()),
            health_score=50.0,
            health_band="attention",
        )
        if snapshot.data_source is not None:
            assert "Career Vitals" in snapshot.data_source


class TestCommandCenterPreferenceModel:
    """Test CommandCenterPreference model instantiation."""

    def test_create_preference(self) -> None:
        pref = CommandCenterPreference(
            user_id=str(uuid.uuid4()),
            pinned_engines=["career_dna", "threat_radar"],
            hidden_engines=["career_passport"],
        )
        assert pref.pinned_engines == ["career_dna", "threat_radar"]
        assert pref.hidden_engines == ["career_passport"]
        assert pref.__tablename__ == "cc_preferences"


# ── Career Vitals™ Algorithm Tests ────────────────────────────


class TestComputeCareerHealthScore:
    """Test Career Vitals™ composite health score computation."""

    def test_all_engines_healthy(self) -> None:
        heartbeats = [
            {
                "engine_name": "career_dna",
                "display_name": "Career DNA™",
                "heartbeat": "active",
                "score": 80.0,
                "last_updated": datetime.now(UTC),
                "weight": 1.5,
                "record_count": 1,
            },
            {
                "engine_name": "threat_radar",
                "display_name": "Threat Radar™",
                "heartbeat": "active",
                "score": 70.0,
                "last_updated": datetime.now(UTC),
                "weight": 1.3,
                "record_count": 1,
            },
        ]
        score = _compute_career_health_score(heartbeats)
        assert 0.0 <= score <= 100.0
        assert score > 50.0  # Both engines healthy

    def test_empty_heartbeats(self) -> None:
        score = _compute_career_health_score([])
        assert score == 0.0

    def test_no_scores(self) -> None:
        heartbeats = [
            {
                "engine_name": "career_dna",
                "display_name": "Career DNA™",
                "heartbeat": "never_run",
                "score": None,
                "last_updated": None,
                "weight": 1.5,
                "record_count": 0,
            },
        ]
        score = _compute_career_health_score(heartbeats)
        assert score == 0.0

    def test_score_bounded_0_100(self) -> None:
        heartbeats = [
            {
                "engine_name": "test",
                "display_name": "Test",
                "heartbeat": "active",
                "score": 100.0,
                "last_updated": datetime.now(UTC),
                "weight": 1.0,
                "record_count": 1,
            },
        ]
        score = _compute_career_health_score(heartbeats)
        assert 0.0 <= score <= 100.0


class TestComputeEngineHealth:
    """Test individual engine health computation."""

    def test_active_with_high_score(self) -> None:
        heartbeat = {
            "score": 90.0,
            "last_updated": datetime.now(UTC),
        }
        health = _compute_engine_health(heartbeat)
        assert health > 80.0

    def test_no_score_returns_zero(self) -> None:
        heartbeat = {
            "score": None,
            "last_updated": datetime.now(UTC),
        }
        health = _compute_engine_health(heartbeat)
        assert health == 0.0

    def test_stale_engine_penalized(self) -> None:
        stale_date = datetime.now(UTC) - timedelta(days=20)
        heartbeat_stale = {
            "score": 80.0,
            "last_updated": stale_date,
        }
        heartbeat_active = {
            "score": 80.0,
            "last_updated": datetime.now(UTC),
        }
        health_stale = _compute_engine_health(heartbeat_stale)
        health_active = _compute_engine_health(heartbeat_active)
        assert health_stale < health_active

    def test_no_last_updated_low_recency(self) -> None:
        heartbeat = {
            "score": 80.0,
            "last_updated": None,
        }
        health = _compute_engine_health(heartbeat)
        # 60% of 80 + 40% of 0 = 48
        assert health == 48.0


class TestClassifyHealthBand:
    """Test Career Vitals™ score → health band mapping."""

    def test_thriving(self) -> None:
        assert _classify_health_band(85.0) == "thriving"

    def test_healthy(self) -> None:
        assert _classify_health_band(65.0) == "healthy"

    def test_attention(self) -> None:
        assert _classify_health_band(45.0) == "attention"

    def test_at_risk(self) -> None:
        assert _classify_health_band(25.0) == "at_risk"

    def test_critical(self) -> None:
        assert _classify_health_band(10.0) == "critical"

    def test_boundary_80_is_thriving(self) -> None:
        assert _classify_health_band(80.0) == "thriving"

    def test_boundary_60_is_healthy(self) -> None:
        assert _classify_health_band(60.0) == "healthy"

    def test_boundary_40_is_attention(self) -> None:
        assert _classify_health_band(40.0) == "attention"

    def test_boundary_20_is_at_risk(self) -> None:
        assert _classify_health_band(20.0) == "at_risk"


class TestClassifyHeartbeat:
    """Test engine heartbeat freshness classification."""

    def test_active_within_threshold(self) -> None:
        recent = datetime.now(UTC) - timedelta(days=3)
        assert _classify_heartbeat(recent) == "active"

    def test_stale_past_active_threshold(self) -> None:
        stale = datetime.now(UTC) - timedelta(days=15)
        assert _classify_heartbeat(stale) == "stale"

    def test_dormant_past_stale_threshold(self) -> None:
        dormant = datetime.now(UTC) - timedelta(days=60)
        assert _classify_heartbeat(dormant) == "dormant"

    def test_boundary_active_days(self) -> None:
        # Use slightly less than threshold to avoid timing race
        boundary = datetime.now(UTC) - timedelta(
            days=HEARTBEAT_ACTIVE_DAYS - 0.01,
        )
        assert _classify_heartbeat(boundary) == "active"


class TestIdentifyStrengths:
    """Test top-3 strengths identification."""

    def test_top_three_by_score(self) -> None:
        heartbeats = [
            {"display_name": "A", "engine_name": "a", "score": 90.0},
            {"display_name": "B", "engine_name": "b", "score": 80.0},
            {"display_name": "C", "engine_name": "c", "score": 70.0},
            {"display_name": "D", "engine_name": "d", "score": 60.0},
            {"display_name": "E", "engine_name": "e", "score": 40.0},
        ]
        result = _identify_strengths(heartbeats)
        items = result["items"]
        assert len(items) == 3
        assert items[0]["engine"] == "A"
        assert items[0]["score"] == 90.0
        assert items[2]["engine"] == "C"

    def test_no_engines_above_threshold(self) -> None:
        heartbeats = [
            {"display_name": "A", "engine_name": "a", "score": 50.0},
            {"display_name": "B", "engine_name": "b", "score": 30.0},
        ]
        result = _identify_strengths(heartbeats)
        assert result["count"] == 0


class TestIdentifyAttentionAreas:
    """Test attention area identification."""

    def test_low_scores_identified(self) -> None:
        heartbeats = [
            {
                "display_name": "A",
                "engine_name": "a",
                "score": 30.0,
                "heartbeat": "active",
            },
            {
                "display_name": "B",
                "engine_name": "b",
                "score": 45.0,
                "heartbeat": "stale",
            },
            {
                "display_name": "C",
                "engine_name": "c",
                "score": 80.0,
                "heartbeat": "active",
            },
        ]
        result = _identify_attention_areas(heartbeats)
        items = result["items"]
        assert len(items) == 2
        assert items[0]["engine"] == "A"

    def test_dormant_engines_included(self) -> None:
        heartbeats = [
            {
                "display_name": "A",
                "engine_name": "a",
                "score": 80.0,
                "heartbeat": "active",
            },
            {
                "display_name": "B",
                "engine_name": "b",
                "score": None,
                "heartbeat": "never_run",
            },
        ]
        result = _identify_attention_areas(heartbeats)
        assert result["count"] == 1
        assert result["items"][0]["engine"] == "B"


class TestComputeTrendDirection:
    """Test trend direction computation."""

    def test_improving_trend(self) -> None:
        previous = CareerSnapshot(
            user_id=str(uuid.uuid4()),
            career_dna_id=str(uuid.uuid4()),
            health_score=50.0,
            health_band="attention",
        )
        assert _compute_trend_direction(55.0, previous) == "improving"

    def test_declining_trend(self) -> None:
        previous = CareerSnapshot(
            user_id=str(uuid.uuid4()),
            career_dna_id=str(uuid.uuid4()),
            health_score=70.0,
            health_band="healthy",
        )
        assert _compute_trend_direction(65.0, previous) == "declining"

    def test_stable_trend(self) -> None:
        previous = CareerSnapshot(
            user_id=str(uuid.uuid4()),
            career_dna_id=str(uuid.uuid4()),
            health_score=60.0,
            health_band="healthy",
        )
        assert _compute_trend_direction(61.0, previous) == "stable"

    def test_no_previous_is_stable(self) -> None:
        assert _compute_trend_direction(75.0, None) == "stable"


# ── Schema Validation Tests ──────────────────────────────────


class TestSchemaValidation:
    """Test Pydantic response schemas accept model-like data."""

    def test_snapshot_response(self) -> None:
        now = datetime.now(UTC)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "career_dna_id": str(uuid.uuid4()),
            "health_score": 72.3,
            "health_band": "healthy",
            "engine_statuses": {},
            "strengths": {"items": [], "count": 0},
            "attention_areas": {"items": [], "count": 0},
            "trend_direction": "stable",
            "data_source": "Career Vitals™",
            "disclaimer": "AI-generated composite metric.",
            "created_at": now,
            "updated_at": now,
        }
        response = CareerSnapshotResponse(**data)
        assert response.health_score == 72.3
        assert response.health_band == "healthy"

    def test_health_summary_response(self) -> None:
        data = {
            "health_score": 65.0,
            "health_band": "healthy",
            "trend_direction": "improving",
            "engines_active": 8,
            "engines_total": 12,
            "top_strength": "Career DNA™",
            "top_attention": "Career Passport™",
        }
        response = CareerHealthSummaryResponse(**data)
        assert response.engines_active == 8

    def test_engine_status_response(self) -> None:
        data = {
            "engine_name": "career_dna",
            "display_name": "Career DNA™",
            "heartbeat": "active",
            "score": 85.0,
            "last_updated": datetime.now(UTC).isoformat(),
        }
        response = EngineStatusResponse(**data)
        assert response.engine_name == "career_dna"

    def test_preference_response(self) -> None:
        now = datetime.now(UTC)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "pinned_engines": ["career_dna"],
            "hidden_engines": [],
            "created_at": now,
            "updated_at": now,
        }
        response = CommandCenterPreferenceResponse(**data)
        assert response.pinned_engines == ["career_dna"]
