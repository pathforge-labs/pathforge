"""
PathForge — Cross-Engine Recommendation Intelligence™ Test Suite
==================================================================
Tests for Sprint 23 Feature 1: models, enums, priority scoring algorithm,
template structure, and schema validation.

Coverage:
    - StrEnum values (RecommendationType, RecommendationStatus, EffortLevel)
    - Model creation (CrossEngineRecommendation, RecommendationCorrelation,
      RecommendationBatch, RecommendationPreference)
    - Priority score algorithm (compute_priority_score — module-level)
    - Schema validation (request + response models)
    - Template structure validation (_get_recommendation_templates)
    - Confidence capping at MAX_RECOMMENDATION_CONFIDENCE
    - Engine display name mapping
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.recommendation_intelligence import (
    CrossEngineRecommendation,
    EffortLevel,
    RecommendationBatch,
    RecommendationCorrelation,
    RecommendationPreference,
    RecommendationStatus,
    RecommendationType,
)
from app.schemas.recommendation_intelligence import (
    CrossEngineRecommendationResponse,
    GenerateRecommendationsRequest,
    RecommendationBatchResponse,
    RecommendationCorrelationResponse,
    RecommendationDashboardResponse,
    RecommendationPreferenceResponse,
    RecommendationPreferenceUpdate,
    RecommendationSummary,
    UpdateRecommendationStatusRequest,
)
from app.services.recommendation_intelligence_service import (
    ENGINE_DISPLAY_NAMES,
    MAX_RECOMMENDATION_CONFIDENCE,
    _get_recommendation_templates,
    compute_priority_score,
)

# ── Enum Tests ─────────────────────────────────────────────────


class TestRecommendationEnums:
    """Test StrEnum definitions for Recommendation Intelligence."""

    def test_recommendation_type_values(self) -> None:
        assert RecommendationType.SKILL_GAP == "skill_gap"
        assert RecommendationType.THREAT_MITIGATION == "threat_mitigation"
        assert RecommendationType.OPPORTUNITY == "opportunity"
        assert RecommendationType.SALARY_OPTIMIZATION == "salary_optimization"
        assert RecommendationType.CAREER_ACCELERATION == "career_acceleration"
        assert RecommendationType.NETWORK_BUILDING == "network_building"
        assert len(RecommendationType) == 6

    def test_recommendation_status_values(self) -> None:
        assert RecommendationStatus.PENDING == "pending"
        assert RecommendationStatus.IN_PROGRESS == "in_progress"
        assert RecommendationStatus.COMPLETED == "completed"
        assert RecommendationStatus.DISMISSED == "dismissed"
        assert RecommendationStatus.EXPIRED == "expired"
        assert len(RecommendationStatus) == 5

    def test_effort_level_values(self) -> None:
        assert EffortLevel.QUICK_WIN == "quick_win"
        assert EffortLevel.MODERATE == "moderate"
        assert EffortLevel.SIGNIFICANT == "significant"
        assert EffortLevel.MAJOR_INITIATIVE == "major_initiative"
        assert len(EffortLevel) == 4


# ── Model Creation Tests ──────────────────────────────────────


class TestCrossEngineRecommendationModel:
    """Test CrossEngineRecommendation model instantiation."""

    def test_create_recommendation(self) -> None:
        user_id = str(uuid.uuid4())
        rec = CrossEngineRecommendation(
            user_id=user_id,
            recommendation_type=RecommendationType.SKILL_GAP.value,
            status=RecommendationStatus.PENDING.value,
            priority_score=78.0,
            urgency=75.0,
            impact_score=80.0,
            confidence_score=0.72,
            effort_level=EffortLevel.MODERATE.value,
            title="Boost Python proficiency",
            description="Enhance Python skills to match market demand.",
            source_engines=["skill_decay", "market_demand"],
            action_items=["Take advanced course", "Build portfolio project"],
        )
        assert rec.user_id == user_id
        assert rec.recommendation_type == "skill_gap"
        assert rec.status == "pending"
        assert rec.priority_score == 78.0
        assert rec.effort_level == "moderate"
        assert rec.__tablename__ == "ri_recommendations"

    def test_recommendation_explicit_transparency_fields(self) -> None:
        data_source = "Intelligence Fusion Engine™ — cross-engine recommendation"
        disclaimer = "AI-generated test disclaimer."
        rec = CrossEngineRecommendation(
            user_id=str(uuid.uuid4()),
            recommendation_type="skill_gap",
            status="pending",
            priority_score=50.0,
            urgency=50.0,
            impact_score=50.0,
            confidence_score=0.6,
            effort_level="quick_win",
            title="Test recommendation",
            description="Test",
            source_engines=[],
            data_source=data_source,
            disclaimer=disclaimer,
        )
        assert rec.data_source == data_source
        assert rec.disclaimer == disclaimer

    def test_recommendation_tablename(self) -> None:
        assert CrossEngineRecommendation.__tablename__ == "ri_recommendations"


class TestRecommendationCorrelationModel:
    """Test RecommendationCorrelation model instantiation."""

    def test_create_correlation(self) -> None:
        rec_id = str(uuid.uuid4())
        corr = RecommendationCorrelation(
            recommendation_id=rec_id,
            engine_name="skill_decay",
            correlation_strength=0.82,
            insight_summary="Cloud architecture freshness declined 15%.",
        )
        assert corr.recommendation_id == rec_id
        assert corr.engine_name == "skill_decay"
        assert corr.correlation_strength == 0.82
        assert corr.insight_summary == "Cloud architecture freshness declined 15%."
        assert corr.__tablename__ == "ri_correlations"

    def test_correlation_without_insight(self) -> None:
        corr = RecommendationCorrelation(
            recommendation_id=str(uuid.uuid4()),
            engine_name="threat_radar",
            correlation_strength=0.5,
        )
        # SQLAlchemy default="" only applies at INSERT, not instantiation
        assert corr.engine_name == "threat_radar"
        assert corr.correlation_strength == 0.5


class TestRecommendationBatchModel:
    """Test RecommendationBatch model instantiation."""

    def test_create_batch(self) -> None:
        batch = RecommendationBatch(
            user_id=str(uuid.uuid4()),
            batch_type="manual",
            total_recommendations=5,
            career_vitals_at_generation=72.5,
        )
        assert batch.batch_type == "manual"
        assert batch.total_recommendations == 5
        assert batch.career_vitals_at_generation == 72.5
        assert batch.__tablename__ == "ri_batches"

    def test_batch_explicit_type(self) -> None:
        batch = RecommendationBatch(
            user_id=str(uuid.uuid4()),
            batch_type="scheduled",
            total_recommendations=8,
        )
        assert batch.batch_type == "scheduled"
        assert batch.total_recommendations == 8


class TestRecommendationPreferenceModel:
    """Test RecommendationPreference model instantiation."""

    def test_create_preference(self) -> None:
        pref = RecommendationPreference(
            user_id=str(uuid.uuid4()),
            enabled_categories=["skill_gap", "opportunity"],
            min_priority_threshold=30.0,
            max_recommendations_per_batch=10,
        )
        assert pref.min_priority_threshold == 30.0
        assert pref.max_recommendations_per_batch == 10
        assert pref.__tablename__ == "ri_preferences"

    def test_preference_explicit_values(self) -> None:
        pref = RecommendationPreference(
            user_id=str(uuid.uuid4()),
            min_priority_threshold=25.0,
            notifications_enabled=False,
        )
        assert pref.min_priority_threshold == 25.0
        assert pref.notifications_enabled is False


# ── Priority Score Algorithm Tests ────────────────────────────


class TestPriorityScoreAlgorithm:
    """Test the Intelligence Fusion Engine™ priority scoring."""

    def test_compute_basic_priority(self) -> None:
        score = compute_priority_score(
            urgency=75.0,
            impact=80.0,
            effort_level="moderate",
        )
        assert 0.0 <= score <= 100.0

    def test_higher_urgency_yields_higher_score(self) -> None:
        low = compute_priority_score(urgency=20.0, impact=50.0, effort_level="moderate")
        high = compute_priority_score(urgency=90.0, impact=50.0, effort_level="moderate")
        assert high > low

    def test_higher_impact_yields_higher_score(self) -> None:
        low = compute_priority_score(urgency=50.0, impact=20.0, effort_level="moderate")
        high = compute_priority_score(urgency=50.0, impact=80.0, effort_level="moderate")
        assert high > low

    def test_quick_win_has_effort_bonus(self) -> None:
        quick = compute_priority_score(
            urgency=50.0, impact=50.0, effort_level="quick_win",
        )
        major = compute_priority_score(
            urgency=50.0, impact=50.0, effort_level="major_initiative",
        )
        assert quick > major

    def test_score_bounded_zero_to_one_hundred(self) -> None:
        extreme = compute_priority_score(
            urgency=100.0, impact=100.0, effort_level="quick_win",
        )
        assert 0.0 <= extreme <= 100.0

    def test_minimum_inputs(self) -> None:
        score = compute_priority_score(
            urgency=0.0, impact=0.0, effort_level="major_initiative",
        )
        assert score >= 0.0

    def test_unknown_effort_uses_default(self) -> None:
        score = compute_priority_score(
            urgency=50.0, impact=50.0, effort_level="unknown",
        )
        assert 0.0 <= score <= 100.0


# ── Confidence Capping Test ───────────────────────────────────


class TestConfidenceCapping:
    """Test that confidence is capped at MAX_RECOMMENDATION_CONFIDENCE."""

    def test_max_confidence_constant(self) -> None:
        assert MAX_RECOMMENDATION_CONFIDENCE == 0.85

    def test_confidence_below_one(self) -> None:
        assert MAX_RECOMMENDATION_CONFIDENCE < 1.0


# ── Template Structure Tests ─────────────────────────────────


class TestRecommendationTemplates:
    """Test recommendation template structure from _get_recommendation_templates."""

    def test_templates_exist(self) -> None:
        templates = _get_recommendation_templates()
        assert len(templates) >= 5

    def test_template_required_keys(self) -> None:
        required_keys = {
            "type", "title", "description",
            "urgency", "impact", "effort_level",
        }
        templates = _get_recommendation_templates()
        for idx, template in enumerate(templates):
            missing = required_keys - set(template.keys())
            assert not missing, (
                f"Template {idx} missing keys: {missing}"
            )

    def test_template_action_items_non_empty(self) -> None:
        templates = _get_recommendation_templates()
        for idx, template in enumerate(templates):
            items = template.get("action_items", [])
            assert len(items) > 0, (
                f"Template {idx} has no action items"
            )

    def test_template_effort_levels_valid(self) -> None:
        valid_levels = {e.value for e in EffortLevel}
        templates = _get_recommendation_templates()
        for idx, template in enumerate(templates):
            assert template["effort_level"] in valid_levels, (
                f"Template {idx} has invalid effort: {template['effort_level']}"
            )

    def test_template_types_valid(self) -> None:
        valid_types = {e.value for e in RecommendationType}
        templates = _get_recommendation_templates()
        for idx, template in enumerate(templates):
            assert template["type"] in valid_types, (
                f"Template {idx} has invalid type: {template['type']}"
            )

    def test_focus_category_filtering(self) -> None:
        all_templates = _get_recommendation_templates()
        filtered = _get_recommendation_templates(focus_categories=["skill_gap"])
        assert len(filtered) < len(all_templates)
        for template in filtered:
            assert template["type"] == "skill_gap"

    def test_correlations_structure(self) -> None:
        templates = _get_recommendation_templates()
        for idx, template in enumerate(templates):
            correlations = template.get("correlations", [])
            for corr in correlations:
                assert "engine" in corr, f"Template {idx} correlation missing 'engine'"
                assert "strength" in corr, f"Template {idx} correlation missing 'strength'"
                assert 0.0 <= corr["strength"] <= 1.0


# ── Engine Display Names Tests ────────────────────────────────


class TestEngineDisplayNames:
    """Test engine display name mapping."""

    def test_display_names_count(self) -> None:
        assert len(ENGINE_DISPLAY_NAMES) >= 10

    def test_known_engines_present(self) -> None:
        expected = [
            "career_dna", "skill_decay", "salary_intelligence",
            "threat_radar", "hidden_job_market",
        ]
        for engine in expected:
            assert engine in ENGINE_DISPLAY_NAMES, (
                f"Engine '{engine}' missing from display names"
            )

    def test_display_names_have_trademark(self) -> None:
        for engine, display in ENGINE_DISPLAY_NAMES.items():
            assert "™" in display, (
                f"Engine '{engine}' display name missing trademark symbol"
            )


# ── Schema Validation Tests ──────────────────────────────────


class TestRecommendationSchemas:
    """Test Pydantic schema validation."""

    def test_recommendation_summary_schema(self) -> None:
        summary = RecommendationSummary(
            id=uuid.uuid4(),
            recommendation_type="skill_gap",
            status="pending",
            priority_score=80.0,
            effort_level="moderate",
            title="Learn TypeScript",
            confidence_score=0.75,
            created_at=datetime.now(UTC),
        )
        assert summary.priority_score == 80.0
        assert summary.recommendation_type == "skill_gap"

    def test_generate_request_defaults(self) -> None:
        request = GenerateRecommendationsRequest()
        assert request.batch_type == "manual"
        assert request.focus_categories is None

    def test_generate_request_with_categories(self) -> None:
        request = GenerateRecommendationsRequest(
            focus_categories=["skill_gap", "opportunity"],
        )
        assert len(request.focus_categories) == 2

    def test_update_status_request(self) -> None:
        request = UpdateRecommendationStatusRequest(
            status="in_progress",
        )
        assert request.status == "in_progress"

    def test_preference_update_excludes_unset(self) -> None:
        update = RecommendationPreferenceUpdate(
            min_priority_threshold=30.0,
        )
        dumped = update.model_dump(exclude_unset=True)
        assert "min_priority_threshold" in dumped
        assert "max_recommendations_per_batch" not in dumped

    def test_dashboard_response_defaults(self) -> None:
        dashboard = RecommendationDashboardResponse(
            total_pending=0,
            total_in_progress=0,
            total_completed=0,
        )
        assert dashboard.recent_recommendations == []
        assert dashboard.latest_batch is None
        assert "Intelligence Fusion Engine" in dashboard.data_source

    def test_correlation_response_schema(self) -> None:
        corr = RecommendationCorrelationResponse(
            id=uuid.uuid4(),
            recommendation_id=uuid.uuid4(),
            engine_name="skill_decay",
            correlation_strength=0.85,
            insight_summary="Cloud architecture freshness declined 15%.",
            created_at=datetime.now(UTC),
        )
        assert corr.correlation_strength == 0.85
        assert corr.engine_name == "skill_decay"

    def test_batch_response_schema(self) -> None:
        batch = RecommendationBatchResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            batch_type="manual",
            total_recommendations=5,
            career_vitals_at_generation=72.5,
            data_source="Intelligence Fusion Engine™",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert batch.total_recommendations == 5

    def test_preference_response_schema(self) -> None:
        pref = RecommendationPreferenceResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            enabled_categories=["skill_gap"],
            min_priority_threshold=30.0,
            max_recommendations_per_batch=10,
            notifications_enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert pref.min_priority_threshold == 30.0

    def test_full_recommendation_response_schema(self) -> None:
        rec = CrossEngineRecommendationResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            batch_id=uuid.uuid4(),
            recommendation_type="skill_gap",
            status="pending",
            effort_level="moderate",
            priority_score=85.0,
            urgency=75.0,
            impact_score=80.0,
            confidence_score=0.75,
            title="Boost Python proficiency",
            description="Enhance Python skills.",
            source_engines=["skill_decay", "market_demand"],
            action_items=["Take course", "Build project"],
            data_source="Intelligence Fusion Engine™",
            disclaimer="AI-generated recommendation",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert rec.priority_score == 85.0
        assert len(rec.source_engines) == 2
