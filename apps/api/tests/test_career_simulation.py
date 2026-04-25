"""
PathForge — Career Simulation Engine™ Tests
===============================================
Test suite for:
    - Career simulation model creation (5 entities)
    - Static analyzer helpers (confidence, ROI, feasibility, salary norm)
    - Clamping validators (analysis, outcomes, recommendations)
    - Schema validation (request + response)
    - API endpoint auth gates (11 endpoints)
    - API endpoint empty-state responses

~53 tests covering the full Career Simulation Engine pipeline.
"""


import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_career_simulation_model_creation(db_session):
    """Test CareerSimulation model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_simulation import CareerSimulation
    from app.models.user import User

    user = User(
        email="sim@career.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Simulation User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    simulation = CareerSimulation(
        career_dna_id=career_dna.id,
        scenario_type="role_transition",
        confidence_score=0.72,
        feasibility_rating=68.5,
        salary_impact_percent=15.0,
        estimated_months=8,
        reasoning="AI analysis reasoning text",
    )
    db_session.add(simulation)
    await db_session.flush()

    assert simulation.id is not None
    assert simulation.scenario_type == "role_transition"
    assert simulation.confidence_score == 0.72
    assert simulation.feasibility_rating == 68.5
    assert simulation.status == "completed"
    assert simulation.data_source == "AI-generated projection based on Career DNA and market data"


@pytest.mark.asyncio
async def test_simulation_input_model_creation(db_session):
    """Test SimulationInput model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_simulation import CareerSimulation, SimulationInput
    from app.models.user import User

    user = User(
        email="input@sim.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Input User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    simulation = CareerSimulation(
        career_dna_id=career_dna.id,
        scenario_type="geo_move",
        confidence_score=0.65,
        feasibility_rating=55.0,
    )
    db_session.add(simulation)
    await db_session.flush()

    sim_input = SimulationInput(
        simulation_id=simulation.id,
        parameter_name="target_location",
        parameter_value="Berlin, Germany",
        parameter_type="str",
    )
    db_session.add(sim_input)
    await db_session.flush()

    assert sim_input.id is not None
    assert sim_input.parameter_name == "target_location"
    assert sim_input.parameter_value == "Berlin, Germany"


@pytest.mark.asyncio
async def test_simulation_outcome_model_creation(db_session):
    """Test SimulationOutcome model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_simulation import CareerSimulation, SimulationOutcome
    from app.models.user import User

    user = User(
        email="outcome@sim.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Outcome User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    simulation = CareerSimulation(
        career_dna_id=career_dna.id,
        scenario_type="skill_investment",
        confidence_score=0.60,
        feasibility_rating=70.0,
    )
    db_session.add(simulation)
    await db_session.flush()

    outcome = SimulationOutcome(
        simulation_id=simulation.id,
        dimension="salary",
        current_value=75000.0,
        projected_value=92000.0,
        delta=17000.0,
        unit="EUR/year",
        reasoning="Skill investment typically increases salary by 20-25%.",
    )
    db_session.add(outcome)
    await db_session.flush()

    assert outcome.id is not None
    assert outcome.dimension == "salary"
    assert outcome.delta == 17000.0


@pytest.mark.asyncio
async def test_simulation_recommendation_model_creation(db_session):
    """Test SimulationRecommendation model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_simulation import (
        CareerSimulation,
        SimulationRecommendation,
    )
    from app.models.user import User

    user = User(
        email="rec@sim.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Recommendation User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    simulation = CareerSimulation(
        career_dna_id=career_dna.id,
        scenario_type="industry_pivot",
        confidence_score=0.55,
        feasibility_rating=45.0,
    )
    db_session.add(simulation)
    await db_session.flush()

    rec = SimulationRecommendation(
        simulation_id=simulation.id,
        priority="high",
        title="Learn cloud architecture",
        description="Study AWS or Azure fundamentals",
        estimated_weeks=12,
        order_index=0,
    )
    db_session.add(rec)
    await db_session.flush()

    assert rec.id is not None
    assert rec.priority == "high"
    assert rec.title == "Learn cloud architecture"
    assert rec.estimated_weeks == 12


@pytest.mark.asyncio
async def test_simulation_preference_model_creation(db_session):
    """Test SimulationPreference model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_simulation import SimulationPreference
    from app.models.user import User

    user = User(
        email="pref@sim.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Preference User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = SimulationPreference(
        career_dna_id=career_dna.id,
        user_id=user.id,
        default_scenario_type="role_transition",
        max_scenarios=25,
        notification_enabled=True,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.default_scenario_type == "role_transition"
    assert pref.max_scenarios == 25


# ── Static Helper Tests ────────────────────────────────────────


def test_scenario_confidence_full_match():
    """100% skill overlap with high LLM confidence near ceiling."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    confidence = CareerSimulationAnalyzer.compute_scenario_confidence(
        skill_overlap_percent=100.0,
        llm_confidence=0.85,
        market_demand_score=100.0,
        data_quality_factor=1.0,
    )
    assert confidence <= 0.85


def test_scenario_confidence_caps_at_085():
    """Even perfect inputs cannot exceed 0.85."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    confidence = CareerSimulationAnalyzer.compute_scenario_confidence(
        skill_overlap_percent=100.0,
        llm_confidence=1.0,
        market_demand_score=100.0,
        data_quality_factor=1.0,
    )
    assert confidence <= 0.85


def test_scenario_confidence_zero_inputs():
    """Zero inputs produce zero confidence."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    confidence = CareerSimulationAnalyzer.compute_scenario_confidence(
        skill_overlap_percent=0.0,
        llm_confidence=0.0,
        market_demand_score=0.0,
        data_quality_factor=0.0,
    )
    assert confidence == 0.0


def test_scenario_confidence_partial():
    """Partial skills and average market produce moderate confidence."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    confidence = CareerSimulationAnalyzer.compute_scenario_confidence(
        skill_overlap_percent=50.0,
        llm_confidence=0.6,
        market_demand_score=60.0,
        data_quality_factor=0.5,
    )
    assert 0.2 <= confidence <= 0.85


def test_roi_positive():
    """Positive salary delta yields positive ROI."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    roi = CareerSimulationAnalyzer.compute_roi_score(
        salary_delta_annual=20000.0,
        investment_months=6,
        monthly_opportunity_cost=2000.0,
    )
    assert roi > 0


def test_roi_no_cost():
    """No opportunity cost uses months as denominator."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    roi = CareerSimulationAnalyzer.compute_roi_score(
        salary_delta_annual=10000.0,
        investment_months=10,
        monthly_opportunity_cost=0.0,
    )
    assert roi == 1000.0  # 10000 / 10


def test_roi_zero_months():
    """Zero investment months returns 0 ROI."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    roi = CareerSimulationAnalyzer.compute_roi_score(
        salary_delta_annual=20000.0,
        investment_months=0,
    )
    assert roi == 0.0


def test_roi_negative():
    """Negative salary delta yields negative ROI."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    roi = CareerSimulationAnalyzer.compute_roi_score(
        salary_delta_annual=-5000.0,
        investment_months=6,
        monthly_opportunity_cost=1000.0,
    )
    assert roi < 0


def test_feasibility_no_gaps():
    """Zero skill gaps = high feasibility."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    feasibility = CareerSimulationAnalyzer.compute_feasibility_rating(
        skill_gap_count=0,
        estimated_months=3,
        confidence_score=0.7,
    )
    assert feasibility >= 90.0


def test_feasibility_many_gaps():
    """Many skill gaps + long timeline = low feasibility."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    feasibility = CareerSimulationAnalyzer.compute_feasibility_rating(
        skill_gap_count=15,
        estimated_months=30,
        confidence_score=0.3,
    )
    assert feasibility < 30.0


def test_feasibility_capped_at_100():
    """Feasibility never exceeds 100."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    feasibility = CareerSimulationAnalyzer.compute_feasibility_rating(
        skill_gap_count=0,
        estimated_months=1,
        confidence_score=0.85,
    )
    assert feasibility <= 100.0


def test_normalize_salary_equal_col():
    """Equal CoL produces same delta."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    normalized = CareerSimulationAnalyzer.normalize_salary_delta(
        salary_delta=20000.0,
        source_col_index=100.0,
        target_col_index=100.0,
    )
    assert normalized == 20000.0


def test_normalize_salary_higher_col():
    """Moving to higher CoL area reduces effective delta."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    normalized = CareerSimulationAnalyzer.normalize_salary_delta(
        salary_delta=20000.0,
        source_col_index=80.0,
        target_col_index=120.0,
    )
    assert normalized < 20000.0


def test_normalize_salary_lower_col():
    """Moving to lower CoL area increases effective delta."""
    from app.ai.career_simulation_analyzer import CareerSimulationAnalyzer

    normalized = CareerSimulationAnalyzer.normalize_salary_delta(
        salary_delta=20000.0,
        source_col_index=120.0,
        target_col_index=80.0,
    )
    assert normalized > 20000.0


# ── Clamping Validator Tests ───────────────────────────────────


def test_clamp_simulation_analysis_caps_confidence():
    """Confidence above 0.85 is clamped down."""
    from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

    data = {
        "confidence_score": 0.95,
        "feasibility_rating": 70.0,
        "estimated_months": 6,
        "salary_impact_percent": 10.0,
        "factors": {},
    }
    _clamp_simulation_analysis(data)
    assert data["confidence_score"] <= 0.85


def test_clamp_simulation_analysis_caps_feasibility():
    """Feasibility above 100 is clamped to 100."""
    from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

    data = {
        "confidence_score": 0.5,
        "feasibility_rating": 150.0,
        "estimated_months": 6,
        "salary_impact_percent": 10.0,
        "factors": {},
    }
    _clamp_simulation_analysis(data)
    assert data["feasibility_rating"] == 100.0


def test_clamp_simulation_analysis_ensures_min_months():
    """Months below 1 are clamped to 1."""
    from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

    data = {
        "confidence_score": 0.5,
        "feasibility_rating": 50.0,
        "estimated_months": 0,
        "salary_impact_percent": 0.0,
        "factors": {},
    }
    _clamp_simulation_analysis(data)
    assert data["estimated_months"] == 1


def test_clamp_simulation_analysis_default_factors():
    """Non-dict factors are replaced with empty dict."""
    from app.ai.career_simulation_analyzer import _clamp_simulation_analysis

    data = {
        "confidence_score": 0.5,
        "feasibility_rating": 50.0,
        "estimated_months": 6,
        "salary_impact_percent": 0.0,
        "factors": "not a dict",
    }
    _clamp_simulation_analysis(data)
    assert data["factors"] == {}


def test_clamp_outcomes_recalculates_delta():
    """Delta is recalculated from projected - current."""
    from app.ai.career_simulation_analyzer import _clamp_outcomes

    outcomes = [
        {
            "dimension": "salary",
            "current_value": 70000.0,
            "projected_value": 90000.0,
            "delta": 999.0,  # Wrong delta — should be corrected
        }
    ]
    _clamp_outcomes(outcomes)
    assert outcomes[0]["delta"] == 20000.0


def test_clamp_outcomes_handles_missing_dimension():
    """Missing dimension defaults to 'unknown'."""
    from app.ai.career_simulation_analyzer import _clamp_outcomes

    outcomes = [
        {
            "current_value": 50.0,
            "projected_value": 60.0,
            "delta": 10.0,
        }
    ]
    _clamp_outcomes(outcomes)
    assert outcomes[0]["dimension"] == "unknown"


def test_clamp_recommendations_validates_priority():
    """Invalid priority defaults to 'medium'."""
    from app.ai.career_simulation_analyzer import _clamp_recommendations

    recommendations = [
        {
            "priority": "invalid_priority",
            "title": "Test recommendation",
            "estimated_weeks": 4,
        }
    ]
    _clamp_recommendations(recommendations)
    assert recommendations[0]["priority"] == "medium"


def test_clamp_recommendations_caps_weeks():
    """Weeks above MAX_RECOMMENDATION_WEEKS are capped."""
    from app.ai.career_simulation_analyzer import (
        MAX_RECOMMENDATION_WEEKS,
        _clamp_recommendations,
    )

    recommendations = [
        {
            "priority": "high",
            "title": "Long-term training",
            "estimated_weeks": 500,
        }
    ]
    _clamp_recommendations(recommendations)
    assert recommendations[0]["estimated_weeks"] == MAX_RECOMMENDATION_WEEKS


def test_clamp_recommendations_ensures_title():
    """Missing title defaults to 'Untitled recommendation'."""
    from app.ai.career_simulation_analyzer import _clamp_recommendations

    recommendations = [
        {
            "priority": "medium",
        }
    ]
    _clamp_recommendations(recommendations)
    assert recommendations[0]["title"] == "Untitled recommendation"


# ── Schema Validation Tests ────────────────────────────────────


def test_role_transition_request_schema():
    """RoleTransitionSimRequest validates correctly."""
    from app.schemas.career_simulation import RoleTransitionSimRequest

    request = RoleTransitionSimRequest(
        target_role="DevOps Engineer",
        target_industry="Cloud",
    )
    assert request.target_role == "DevOps Engineer"
    assert request.target_industry == "Cloud"
    assert request.target_location is None


def test_geo_move_request_schema():
    """GeoMoveSimRequest validates correctly."""
    from app.schemas.career_simulation import GeoMoveSimRequest

    request = GeoMoveSimRequest(
        target_location="Berlin, Germany",
        keep_role=True,
    )
    assert request.target_location == "Berlin, Germany"
    assert request.keep_role is True


def test_skill_investment_request_schema():
    """SkillInvestmentSimRequest validates correctly."""
    from app.schemas.career_simulation import SkillInvestmentSimRequest

    request = SkillInvestmentSimRequest(
        skills=["Kubernetes", "Terraform", "AWS"],
    )
    assert len(request.skills) == 3
    assert "Kubernetes" in request.skills


def test_skill_investment_request_max_skills():
    """SkillInvestmentSimRequest rejects more than 10 skills."""
    from pydantic import ValidationError

    from app.schemas.career_simulation import SkillInvestmentSimRequest

    with pytest.raises(ValidationError):
        SkillInvestmentSimRequest(
            skills=[f"Skill{i}" for i in range(11)],
        )


def test_industry_pivot_request_schema():
    """IndustryPivotSimRequest validates correctly."""
    from app.schemas.career_simulation import IndustryPivotSimRequest

    request = IndustryPivotSimRequest(
        target_industry="Healthcare",
        target_role="Health Tech PM",
    )
    assert request.target_industry == "Healthcare"
    assert request.target_role == "Health Tech PM"


def test_seniority_jump_request_schema():
    """SeniorityJumpSimRequest validates correctly."""
    from app.schemas.career_simulation import SeniorityJumpSimRequest

    request = SeniorityJumpSimRequest(
        target_seniority="Senior",
    )
    assert request.target_seniority == "Senior"
    assert request.target_role is None


def test_compare_request_schema():
    """SimulationCompareRequest validates correctly."""
    import uuid

    from app.schemas.career_simulation import SimulationCompareRequest

    ids = [uuid.uuid4(), uuid.uuid4()]
    request = SimulationCompareRequest(simulation_ids=ids)
    assert len(request.simulation_ids) == 2


def test_compare_request_min_simulations():
    """SimulationCompareRequest requires at least 2 simulations."""
    import uuid

    from pydantic import ValidationError

    from app.schemas.career_simulation import SimulationCompareRequest

    with pytest.raises(ValidationError):
        SimulationCompareRequest(simulation_ids=[uuid.uuid4()])


def test_compare_request_max_simulations():
    """SimulationCompareRequest rejects more than 5 simulations."""
    import uuid

    from pydantic import ValidationError

    from app.schemas.career_simulation import SimulationCompareRequest

    with pytest.raises(ValidationError):
        SimulationCompareRequest(
            simulation_ids=[uuid.uuid4() for _ in range(6)]
        )


def test_preference_update_schema():
    """SimulationPreferenceUpdateRequest handles partial updates."""
    from app.schemas.career_simulation import SimulationPreferenceUpdateRequest

    request = SimulationPreferenceUpdateRequest(
        max_scenarios=30,
    )
    assert request.max_scenarios == 30
    assert request.default_scenario_type is None


# ── API Auth Gate Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_simulation_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-simulation/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_simulate_role_requires_auth(client: AsyncClient):
    """Role simulation endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-simulation/simulate/role",
        json={"target_role": "DevOps Engineer"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_simulate_geo_requires_auth(client: AsyncClient):
    """Geo simulation endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-simulation/simulate/geo",
        json={"target_location": "Berlin"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_simulate_skill_requires_auth(client: AsyncClient):
    """Skill simulation endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-simulation/simulate/skill",
        json={"skills": ["Python"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_simulate_industry_requires_auth(client: AsyncClient):
    """Industry simulation endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-simulation/simulate/industry",
        json={"target_industry": "Healthcare"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_simulate_seniority_requires_auth(client: AsyncClient):
    """Seniority simulation endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-simulation/simulate/seniority",
        json={"target_seniority": "Senior"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_compare_requires_auth(client: AsyncClient):
    """Compare endpoint returns 401 without auth."""
    import uuid

    response = await client.post(
        "/api/v1/career-simulation/compare",
        json={"simulation_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_preferences_requires_auth(client: AsyncClient):
    """Preferences GET endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-simulation/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_preferences_requires_auth(client: AsyncClient):
    """Preferences PUT endpoint returns 401 without auth."""
    response = await client.put(
        "/api/v1/career-simulation/preferences",
        json={"max_scenarios": 30},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_simulation_requires_auth(client: AsyncClient):
    """Get simulation endpoint returns 401 without auth."""
    import uuid

    response = await client.get(
        f"/api/v1/career-simulation/{uuid.uuid4()}",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_simulation_requires_auth(client: AsyncClient):
    """Delete simulation endpoint returns 401 without auth."""
    import uuid

    response = await client.delete(
        f"/api/v1/career-simulation/{uuid.uuid4()}",
    )
    assert response.status_code == 401


# ── Enum Tests ─────────────────────────────────────────────────


def test_scenario_type_enum_values():
    """ScenarioType enum has 5 expected values."""
    from app.models.career_simulation import ScenarioType

    expected = {
        "role_transition",
        "geo_move",
        "skill_investment",
        "industry_pivot",
        "seniority_jump",
    }
    actual = {member.value for member in ScenarioType}
    assert actual == expected


def test_simulation_status_enum_values():
    """SimulationStatus enum has expected values."""
    from app.models.career_simulation import SimulationStatus

    expected = {"draft", "running", "completed", "failed"}
    actual = {member.value for member in SimulationStatus}
    assert actual == expected


def test_recommendation_priority_enum_values():
    """RecommendationPriority enum has expected values."""
    from app.models.career_simulation import RecommendationPriority

    expected = {"critical", "high", "medium", "nice_to_have"}
    actual = {member.value for member in RecommendationPriority}
    assert actual == expected
