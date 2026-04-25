"""
PathForge — Skill Decay & Growth Tracker Tests
=================================================
Test suite for:
    - Skill decay model creation (5 entities)
    - Exponential decay math (base freshness, half-life, urgency)
    - Decay rate classification
    - Days-since-active computation
    - Schema validation
    - API endpoint auth gates
    - API endpoint empty-state responses
"""


import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skill_freshness_model_creation(db_session):
    """Test SkillFreshness model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.skill_decay import SkillFreshness
    from app.models.user import User

    user = User(
        email="freshness@skilldecay.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Freshness User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    freshness = SkillFreshness(
        career_dna_id=career_dna.id,
        skill_name="Python",
        category="technical",
        freshness_score=85.5,
        half_life_days=912,
        decay_rate="fast",
        days_since_active=120,
        refresh_urgency=0.35,
    )
    db_session.add(freshness)
    await db_session.flush()

    assert freshness.id is not None
    assert freshness.skill_name == "Python"
    assert freshness.freshness_score == 85.5
    assert freshness.half_life_days == 912


@pytest.mark.asyncio
async def test_market_demand_snapshot_model_creation(db_session):
    """Test MarketDemandSnapshot model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.skill_decay import MarketDemandSnapshot
    from app.models.user import User

    user = User(
        email="demand@skilldecay.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Demand User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    demand = MarketDemandSnapshot(
        career_dna_id=career_dna.id,
        skill_name="Kubernetes",
        demand_score=88.0,
        demand_trend="surging",
        trend_confidence=0.82,
        growth_projection_6m=15.0,
        growth_projection_12m=25.0,
    )
    db_session.add(demand)
    await db_session.flush()

    assert demand.id is not None
    assert demand.skill_name == "Kubernetes"
    assert demand.demand_score == 88.0
    assert demand.demand_trend == "surging"


@pytest.mark.asyncio
async def test_skill_velocity_entry_model_creation(db_session):
    """Test SkillVelocityEntry model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.skill_decay import SkillVelocityEntry
    from app.models.user import User

    user = User(
        email="velocity@skilldecay.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Velocity User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    velocity = SkillVelocityEntry(
        career_dna_id=career_dna.id,
        skill_name="TypeScript",
        velocity_score=42.5,
        velocity_direction="accelerating",
        freshness_component=90.0,
        demand_component=85.0,
        composite_health=87.5,
        acceleration=12.0,
    )
    db_session.add(velocity)
    await db_session.flush()

    assert velocity.id is not None
    assert velocity.velocity_direction == "accelerating"
    assert velocity.composite_health == 87.5


@pytest.mark.asyncio
async def test_reskilling_pathway_model_creation(db_session):
    """Test ReskillingPathway model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.skill_decay import ReskillingPathway
    from app.models.user import User

    user = User(
        email="pathway@skilldecay.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pathway User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pathway = ReskillingPathway(
        career_dna_id=career_dna.id,
        target_skill="Rust",
        current_level="beginner",
        target_level="intermediate",
        priority="recommended",
        rationale="Systems programming gaining traction in your domain.",
        estimated_effort_hours=80,
        freshness_gain=60.0,
        demand_alignment=0.78,
    )
    db_session.add(pathway)
    await db_session.flush()

    assert pathway.id is not None
    assert pathway.target_skill == "Rust"
    assert pathway.priority == "recommended"
    assert pathway.estimated_effort_hours == 80


@pytest.mark.asyncio
async def test_skill_decay_preference_model_creation(db_session):
    """Test SkillDecayPreference defaults."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.skill_decay import SkillDecayPreference
    from app.models.user import User

    user = User(
        email="pref@skilldecay.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pref User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = SkillDecayPreference(
        user_id=user.id,
        career_dna_id=career_dna.id,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.tracking_enabled is True
    assert pref.notification_frequency == "weekly"
    assert pref.decay_alert_threshold == 40.0


# ── Exponential Decay Math Tests ──────────────────────────────


def test_base_freshness_zero_days():
    """Freshness should be 100.0 when days=0."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    score = SkillDecayAnalyzer.compute_base_freshness(
        days_since_active=0, half_life_days=912,
    )
    assert score == 100.0


def test_base_freshness_at_half_life():
    """Freshness should be ~50.0 at exactly one half-life."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    score = SkillDecayAnalyzer.compute_base_freshness(
        days_since_active=912, half_life_days=912,
    )
    # Exponential decay: 100 * exp(-ln(2)) = 100 * 0.5 = 50.0
    assert abs(score - 50.0) < 0.5


def test_base_freshness_double_half_life():
    """Freshness should be ~25.0 at two half-lives."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    score = SkillDecayAnalyzer.compute_base_freshness(
        days_since_active=1824, half_life_days=912,
    )
    assert abs(score - 25.0) < 0.5


def test_base_freshness_negative_days():
    """Negative days should clamp to 100.0."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    score = SkillDecayAnalyzer.compute_base_freshness(
        days_since_active=-10, half_life_days=912,
    )
    assert score == 100.0


def test_base_freshness_very_old_skill():
    """Very old skill (10 half-lives) should approach 0."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    score = SkillDecayAnalyzer.compute_base_freshness(
        days_since_active=9120, half_life_days=912,
    )
    assert score < 1.0


# ── Half-Life Category Tests ──────────────────────────────────


def test_half_life_technical():
    """Technical skills should have ~2.5 year half-life."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    half_life = SkillDecayAnalyzer.get_half_life_for_category("technical")
    assert half_life == 912


def test_half_life_soft_skills():
    """Soft skills should have ~7 year half-life."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    half_life = SkillDecayAnalyzer.get_half_life_for_category("soft")
    assert half_life == 2555


def test_half_life_unknown_category():
    """Unknown category should return default half-life."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    half_life = SkillDecayAnalyzer.get_half_life_for_category("quantum")
    assert half_life == 1095  # default


# ── Decay Rate Classification Tests ──────────────────────────


def test_classify_fast_decay():
    """Short half-life classified as 'fast'."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    assert SkillDecayAnalyzer.classify_decay_rate(800) == "fast"


def test_classify_moderate_decay():
    """Medium half-life classified as 'moderate'."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    assert SkillDecayAnalyzer.classify_decay_rate(1200) == "moderate"


def test_classify_slow_decay():
    """Longer half-life classified as 'slow'."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    assert SkillDecayAnalyzer.classify_decay_rate(2000) == "slow"


def test_classify_stable():
    """Very long half-life classified as 'stable'."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    assert SkillDecayAnalyzer.classify_decay_rate(3500) == "stable"


# ── Refresh Urgency Tests ────────────────────────────────────


def test_urgency_fresh_skill():
    """Fresh skill (freshness=100) should have low urgency."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    urgency = SkillDecayAnalyzer.compute_refresh_urgency(100.0, 50.0)
    assert urgency < 0.3


def test_urgency_stale_high_demand():
    """Stale skill + high demand = high urgency."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    urgency = SkillDecayAnalyzer.compute_refresh_urgency(10.0, 90.0)
    assert urgency > 0.7


def test_urgency_stale_low_demand():
    """Stale skill + low demand = moderate urgency."""
    from app.ai.skill_decay_analyzer import SkillDecayAnalyzer

    urgency = SkillDecayAnalyzer.compute_refresh_urgency(10.0, 10.0)
    assert urgency < 0.6


# ── Days Since Active Tests ──────────────────────────────────


def test_days_since_full_date():
    """Full YYYY-MM-DD date parsing."""
    from datetime import UTC, datetime

    from app.services.skill_decay_service import _compute_days_since

    now = datetime(2026, 2, 20, tzinfo=UTC)
    days = _compute_days_since("2025-08-20", now)
    assert days == 184  # 6 months


def test_days_since_year_month():
    """YYYY-MM date parsing (assumes 15th)."""
    from datetime import UTC, datetime

    from app.services.skill_decay_service import _compute_days_since

    now = datetime(2026, 2, 20, tzinfo=UTC)
    days = _compute_days_since("2025-08", now)
    assert days == 189  # from Aug 15 to Feb 20


def test_days_since_year_only():
    """YYYY date parsing (assumes July 1)."""
    from datetime import UTC, datetime

    from app.services.skill_decay_service import _compute_days_since

    now = datetime(2026, 2, 20, tzinfo=UTC)
    days = _compute_days_since("2024", now)
    assert days == 599  # from Jul 1 2024 to Feb 20 2026


def test_days_since_none():
    """None last_used_date defaults to 365 days."""
    from datetime import UTC, datetime

    from app.services.skill_decay_service import _compute_days_since

    now = datetime(2026, 2, 20, tzinfo=UTC)
    days = _compute_days_since(None, now)
    assert days == 365


def test_days_since_invalid():
    """Invalid date format defaults to 365 days."""
    from datetime import UTC, datetime

    from app.services.skill_decay_service import _compute_days_since

    now = datetime(2026, 2, 20, tzinfo=UTC)
    days = _compute_days_since("not-a-date", now)
    assert days == 365


# ── Schema Validation Tests ───────────────────────────────────


def test_skill_refresh_request_schema():
    """SkillRefreshRequest requires a non-empty skill_name."""
    from app.schemas.skill_decay import SkillRefreshRequest

    request = SkillRefreshRequest(skill_name="Python")
    assert request.skill_name == "Python"


def test_preference_update_schema():
    """SkillDecayPreferenceUpdateRequest allows partial updates."""
    from app.schemas.skill_decay import SkillDecayPreferenceUpdateRequest

    update = SkillDecayPreferenceUpdateRequest(
        decay_alert_threshold=30.0,
    )
    assert update.decay_alert_threshold == 30.0
    assert update.tracking_enabled is None


# ── API Endpoint Auth Gate Tests ──────────────────────────────


@pytest.mark.asyncio
async def test_skill_decay_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/skill-decay")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_decay_scan_requires_auth(client: AsyncClient):
    """Scan endpoint returns 401 without auth."""
    response = await client.post("/api/v1/skill-decay/scan")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_decay_freshness_requires_auth(client: AsyncClient):
    """Freshness endpoint returns 401 without auth."""
    response = await client.get("/api/v1/skill-decay/freshness")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_decay_velocity_requires_auth(client: AsyncClient):
    """Velocity endpoint returns 401 without auth."""
    response = await client.get("/api/v1/skill-decay/velocity")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_skill_decay_reskilling_requires_auth(client: AsyncClient):
    """Reskilling endpoint returns 401 without auth."""
    response = await client.get("/api/v1/skill-decay/reskilling")
    assert response.status_code == 401


# ── API Endpoint Empty-State Tests ─────────────────────────────


@pytest.mark.asyncio
async def test_skill_decay_dashboard_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Dashboard returns empty state for user with no scan data."""
    response = await client.get(
        "/api/v1/skill-decay",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["freshness"] == []
    assert data["freshness_summary"]["total_skills"] == 0


@pytest.mark.asyncio
async def test_skill_decay_freshness_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Freshness returns empty list for new user."""
    response = await client.get(
        "/api/v1/skill-decay/freshness",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_skill_decay_velocity_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Velocity returns empty list for new user."""
    response = await client.get(
        "/api/v1/skill-decay/velocity",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_skill_decay_reskilling_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Reskilling returns empty list for new user."""
    response = await client.get(
        "/api/v1/skill-decay/reskilling",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_skill_decay_preferences_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Preferences returns null before setup."""
    response = await client.get(
        "/api/v1/skill-decay/preferences",
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_skill_decay_market_demand_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Market demand returns empty list for new user."""
    response = await client.get(
        "/api/v1/skill-decay/market-demand",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []
