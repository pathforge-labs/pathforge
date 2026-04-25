"""
PathForge — Salary Intelligence Engine™ Tests
=================================================
Test suite for:
    - Salary intelligence model creation (5 entities)
    - Static analyzer helpers (percentile, confidence, delta, currency)
    - Schema validation
    - API endpoint auth gates
    - API endpoint empty-state responses
"""


import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_salary_estimate_model_creation(db_session):
    """Test SalaryEstimate model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.salary_intelligence import SalaryEstimate
    from app.models.user import User

    user = User(
        email="estimate@salary.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Estimate User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    estimate = SalaryEstimate(
        career_dna_id=career_dna.id,
        role_title="Senior Python Developer",
        location="Amsterdam, Netherlands",
        seniority_level="senior",
        industry="Technology",
        estimated_min=65000.0,
        estimated_max=95000.0,
        estimated_median=78000.0,
        currency="EUR",
        confidence=0.72,
        data_points_count=150,
        market_percentile=68.5,
    )
    db_session.add(estimate)
    await db_session.flush()

    assert estimate.id is not None
    assert estimate.role_title == "Senior Python Developer"
    assert estimate.estimated_median == 78000.0
    assert estimate.confidence == 0.72


@pytest.mark.asyncio
async def test_skill_salary_impact_model_creation(db_session):
    """Test SkillSalaryImpact model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.salary_intelligence import SkillSalaryImpact
    from app.models.user import User

    user = User(
        email="impact@salary.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Impact User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    impact = SkillSalaryImpact(
        career_dna_id=career_dna.id,
        skill_name="Kubernetes",
        category="technical",
        salary_impact_amount=8500.0,
        salary_impact_percent=10.9,
        demand_premium=88.0,
        scarcity_factor=0.72,
        impact_direction="positive",
    )
    db_session.add(impact)
    await db_session.flush()

    assert impact.id is not None
    assert impact.skill_name == "Kubernetes"
    assert impact.salary_impact_amount == 8500.0
    assert impact.scarcity_factor == 0.72


@pytest.mark.asyncio
async def test_salary_history_entry_model_creation(db_session):
    """Test SalaryHistoryEntry model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.salary_intelligence import SalaryHistoryEntry
    from app.models.user import User

    user = User(
        email="history@salary.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="History User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    entry = SalaryHistoryEntry(
        career_dna_id=career_dna.id,
        estimated_min=60000.0,
        estimated_max=90000.0,
        estimated_median=75000.0,
        currency="EUR",
        confidence=0.68,
        role_title="Python Developer",
        location="Netherlands",
        seniority_level="mid",
        skills_count=12,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.id is not None
    assert entry.estimated_median == 75000.0
    assert entry.skills_count == 12


@pytest.mark.asyncio
async def test_salary_scenario_model_creation(db_session):
    """Test SalaryScenario model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.salary_intelligence import SalaryScenario
    from app.models.user import User

    user = User(
        email="scenario@salary.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Scenario User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    scenario = SalaryScenario(
        career_dna_id=career_dna.id,
        scenario_type="add_skill",
        scenario_label="What if I learn Rust?",
        scenario_input={"skill": "Rust"},
        projected_min=68000.0,
        projected_max=98000.0,
        projected_median=82000.0,
        currency="EUR",
        delta_amount=4000.0,
        delta_percent=5.1,
        confidence=0.65,
    )
    db_session.add(scenario)
    await db_session.flush()

    assert scenario.id is not None
    assert scenario.scenario_type == "add_skill"
    assert scenario.delta_amount == 4000.0


@pytest.mark.asyncio
async def test_salary_preference_model_creation(db_session):
    """Test SalaryPreference defaults."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.salary_intelligence import SalaryPreference
    from app.models.user import User

    user = User(
        email="pref@salary.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pref User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = SalaryPreference(
        user_id=user.id,
        career_dna_id=career_dna.id,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.preferred_currency == "EUR"
    assert pref.include_benefits is False
    assert pref.notification_enabled is True
    assert pref.notification_frequency == "monthly"
    assert pref.comparison_market == "Netherlands"


# ── Static Analyzer Helper Tests ──────────────────────────────


def test_market_percentile_midpoint():
    """Median at midpoint of range = 50th percentile."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    percentile = SalaryIntelligenceAnalyzer.compute_market_percentile(
        estimated_median=75000.0,
        market_min=50000.0,
        market_max=100000.0,
    )
    assert percentile == 50.0


def test_market_percentile_high():
    """Salary near top of range = high percentile."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    percentile = SalaryIntelligenceAnalyzer.compute_market_percentile(
        estimated_median=95000.0,
        market_min=50000.0,
        market_max=100000.0,
    )
    assert percentile == 90.0


def test_market_percentile_below_min():
    """Salary below market min = clamp to 0."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    percentile = SalaryIntelligenceAnalyzer.compute_market_percentile(
        estimated_median=40000.0,
        market_min=50000.0,
        market_max=100000.0,
    )
    assert percentile == 0.0


def test_market_percentile_equal_bounds():
    """Equal min/max should return 50.0 (fallback)."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    percentile = SalaryIntelligenceAnalyzer.compute_market_percentile(
        estimated_median=50000.0,
        market_min=50000.0,
        market_max=50000.0,
    )
    assert percentile == 50.0


def test_confidence_interval_no_data():
    """Zero data points should reduce confidence."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    conf = SalaryIntelligenceAnalyzer.compute_confidence_interval(
        data_points_count=0,
        base_confidence=0.6,
    )
    assert conf < 0.6


def test_confidence_interval_many_points():
    """Many data points should boost confidence, capped at 0.85."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    conf = SalaryIntelligenceAnalyzer.compute_confidence_interval(
        data_points_count=1000,
        base_confidence=0.7,
    )
    assert conf <= 0.85
    assert conf > 0.7


def test_salary_delta_positive():
    """Positive salary change computes correctly."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
        current_median=80000.0,
        projected_median=88000.0,
    )
    assert amount == 8000.0
    assert percent == 10.0


def test_salary_delta_negative():
    """Negative salary change computes correctly."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
        current_median=80000.0,
        projected_median=72000.0,
    )
    assert amount == -8000.0
    assert percent == -10.0


def test_salary_delta_zero_current():
    """Zero current median avoids division by zero."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    amount, percent = SalaryIntelligenceAnalyzer.compute_salary_delta(
        current_median=0.0,
        projected_median=50000.0,
    )
    assert amount == 50000.0
    assert percent == 0.0


def test_currency_same():
    """Same-currency conversion returns same amount."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    result = SalaryIntelligenceAnalyzer.normalize_currency(
        amount=80000.0,
        from_currency="EUR",
        to_currency="EUR",
    )
    assert result == 80000.0


def test_currency_conversion():
    """EUR→USD conversion uses fallback rates."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    result = SalaryIntelligenceAnalyzer.normalize_currency(
        amount=80000.0,
        from_currency="EUR",
        to_currency="USD",
    )
    # EUR→EUR (rate=1.0) × EUR→USD (rate=1.09) = 87200
    assert result == 87200.0


def test_currency_unknown_defaults():
    """Unknown currency defaults to 1.0 rates."""
    from app.ai.salary_intelligence_analyzer import SalaryIntelligenceAnalyzer

    result = SalaryIntelligenceAnalyzer.normalize_currency(
        amount=80000.0,
        from_currency="JPY",
        to_currency="KRW",
    )
    # Both rates default to 1.0
    assert result == 80000.0


# ── Schema Validation Tests ───────────────────────────────────


def test_salary_scenario_request_schema():
    """SalaryScenarioRequest validates correctly."""
    from app.schemas.salary_intelligence import SalaryScenarioRequest

    request = SalaryScenarioRequest(
        scenario_type="add_skill",
        scenario_label="Add Kubernetes",
        scenario_input={"skill": "Kubernetes"},
    )
    assert request.scenario_type == "add_skill"
    assert request.scenario_label == "Add Kubernetes"


def test_skill_what_if_request_schema():
    """SkillWhatIfRequest validates skill_name."""
    from app.schemas.salary_intelligence import SkillWhatIfRequest

    request = SkillWhatIfRequest(skill_name="Rust")
    assert request.skill_name == "Rust"


def test_location_what_if_request_schema():
    """LocationWhatIfRequest validates location."""
    from app.schemas.salary_intelligence import LocationWhatIfRequest

    request = LocationWhatIfRequest(location="Berlin, Germany")
    assert request.location == "Berlin, Germany"


def test_preference_update_partial():
    """SalaryPreferenceUpdateRequest allows partial updates."""
    from app.schemas.salary_intelligence import SalaryPreferenceUpdateRequest

    update = SalaryPreferenceUpdateRequest(
        preferred_currency="USD",
    )
    assert update.preferred_currency == "USD"
    assert update.include_benefits is None


def test_preference_update_empty():
    """SalaryPreferenceUpdateRequest with no fields."""
    from app.schemas.salary_intelligence import SalaryPreferenceUpdateRequest

    update = SalaryPreferenceUpdateRequest()
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {}


# ── Validation Clamping Tests ─────────────────────────────────


def test_clamp_salary_estimate_reorders():
    """_clamp_salary_estimate fixes min/median/max ordering."""
    from app.ai.salary_intelligence_analyzer import _clamp_salary_estimate

    data = {
        "estimated_min": 90000.0,
        "estimated_max": 60000.0,
        "estimated_median": 75000.0,
        "confidence": 0.95,
        "data_points_count": -5,
        "market_percentile": 120.0,
    }
    _clamp_salary_estimate(data)

    assert data["estimated_min"] == 60000.0
    assert data["estimated_median"] == 75000.0
    assert data["estimated_max"] == 90000.0
    assert data["confidence"] == 0.85  # capped
    assert data["data_points_count"] == 0  # clamped
    assert data["market_percentile"] == 100.0  # clamped


def test_clamp_trajectory_conservative():
    """_clamp_trajectory_projection caps growth at 15% annually."""
    from app.ai.salary_intelligence_analyzer import _clamp_trajectory_projection

    data = {
        "projected_6m_median": 120000.0,  # way too optimistic
        "projected_12m_median": 150000.0,
        "trend_confidence": 0.95,
    }
    _clamp_trajectory_projection(data, current_median=80000.0)

    assert data["projected_6m_median"] <= 80000.0 * 1.075
    assert data["projected_12m_median"] <= 80000.0 * 1.15
    assert data["trend_confidence"] == 0.85  # capped


def test_clamp_scenario_reorders():
    """_clamp_scenario_result fixes ordering and caps confidence."""
    from app.ai.salary_intelligence_analyzer import _clamp_scenario_result

    data = {
        "projected_min": 90000.0,
        "projected_max": 70000.0,
        "projected_median": 80000.0,
        "confidence": 0.99,
    }
    _clamp_scenario_result(data)

    assert data["projected_min"] == 70000.0
    assert data["projected_median"] == 80000.0
    assert data["projected_max"] == 90000.0
    assert data["confidence"] == 0.85


# ── API Endpoint Auth Gate Tests ──────────────────────────────


@pytest.mark.asyncio
async def test_salary_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/salary-intelligence")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_scan_requires_auth(client: AsyncClient):
    """Scan endpoint returns 401 without auth."""
    response = await client.post("/api/v1/salary-intelligence/scan")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_estimate_requires_auth(client: AsyncClient):
    """Estimate endpoint returns 401 without auth."""
    response = await client.get("/api/v1/salary-intelligence/estimate")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_impacts_requires_auth(client: AsyncClient):
    """Impacts endpoint returns 401 without auth."""
    response = await client.get("/api/v1/salary-intelligence/impacts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_trajectory_requires_auth(client: AsyncClient):
    """Trajectory endpoint returns 401 without auth."""
    response = await client.get("/api/v1/salary-intelligence/trajectory")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_scenarios_requires_auth(client: AsyncClient):
    """Scenarios endpoint returns 401 without auth."""
    response = await client.get("/api/v1/salary-intelligence/scenarios")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_preferences_requires_auth(client: AsyncClient):
    """Preferences endpoint returns 401 without auth."""
    response = await client.get("/api/v1/salary-intelligence/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_whatif_skill_requires_auth(client: AsyncClient):
    """What-if skill endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/salary-intelligence/what-if/skill",
        json={"skill_name": "Rust"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_salary_whatif_location_requires_auth(client: AsyncClient):
    """What-if location endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/salary-intelligence/what-if/location",
        json={"location": "Berlin"},
    )
    assert response.status_code == 401


# ── API Endpoint Empty-State Tests ─────────────────────────────


@pytest.mark.asyncio
async def test_salary_dashboard_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Dashboard returns empty state for user with no scan data."""
    response = await client.get(
        "/api/v1/salary-intelligence",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["estimate"] is None
    assert data["skill_impacts"] == []


@pytest.mark.asyncio
async def test_salary_estimate_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Estimate returns null for user with no scan."""
    response = await client.get(
        "/api/v1/salary-intelligence/estimate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_salary_impacts_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Impacts returns empty analysis for new user."""
    response = await client.get(
        "/api/v1/salary-intelligence/impacts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["impacts"] == []
    assert data["total_premium_amount"] == 0.0


@pytest.mark.asyncio
async def test_salary_trajectory_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Trajectory returns empty history for new user."""
    response = await client.get(
        "/api/v1/salary-intelligence/trajectory",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["history"] == []


@pytest.mark.asyncio
async def test_salary_scenarios_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Scenarios returns empty list for new user."""
    response = await client.get(
        "/api/v1/salary-intelligence/scenarios",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_salary_preferences_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Preferences returns null before setup."""
    response = await client.get(
        "/api/v1/salary-intelligence/preferences",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_salary_preferences_update_no_fields(
    client: AsyncClient, auth_headers: dict,
):
    """Update with no fields returns 400."""
    response = await client.put(
        "/api/v1/salary-intelligence/preferences",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 400
