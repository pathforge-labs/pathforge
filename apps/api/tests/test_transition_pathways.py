"""
PathForge — Transition Pathways Tests
========================================
Test suite for:
    - Transition pathway model creation (5 entities)
    - Static analyzer helpers (overlap, difficulty, timeline, confidence)
    - Schema validation
    - Validation clamping functions
    - API endpoint auth gates
    - API endpoint empty-state responses
"""


import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transition_path_model_creation(db_session):
    """Test TransitionPath model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.transition_pathways import TransitionPath
    from app.models.user import User

    user = User(
        email="transition@path.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Transition User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    path = TransitionPath(
        career_dna_id=career_dna.id,
        from_role="QA Engineer",
        to_role="DevOps Engineer",
        confidence_score=0.62,
        difficulty="moderate",
        skill_overlap_percent=45.0,
        skills_to_acquire_count=5,
        estimated_duration_months=10,
        success_probability=0.58,
    )
    db_session.add(path)
    await db_session.flush()

    assert path.id is not None
    assert path.from_role == "QA Engineer"
    assert path.to_role == "DevOps Engineer"
    assert path.confidence_score == 0.62
    assert path.difficulty == "moderate"


@pytest.mark.asyncio
async def test_skill_bridge_entry_model_creation(db_session):
    """Test SkillBridgeEntry model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.transition_pathways import SkillBridgeEntry, TransitionPath
    from app.models.user import User

    user = User(
        email="bridge@skill.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Bridge User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    path = TransitionPath(
        career_dna_id=career_dna.id,
        from_role="Backend Dev",
        to_role="ML Engineer",
        confidence_score=0.45,
        difficulty="challenging",
    )
    db_session.add(path)
    await db_session.flush()

    entry = SkillBridgeEntry(
        transition_path_id=path.id,
        skill_name="TensorFlow",
        category="technical",
        is_already_held=False,
        required_level="intermediate",
        acquisition_method="Coursera course",
        estimated_weeks=8,
        priority="critical",
        impact_on_confidence=0.12,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.id is not None
    assert entry.skill_name == "TensorFlow"
    assert entry.is_already_held is False
    assert entry.priority == "critical"


@pytest.mark.asyncio
async def test_transition_milestone_model_creation(db_session):
    """Test TransitionMilestone model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.transition_pathways import TransitionMilestone, TransitionPath
    from app.models.user import User

    user = User(
        email="milestone@test.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Milestone User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    path = TransitionPath(
        career_dna_id=career_dna.id,
        from_role="QA",
        to_role="SDET",
        confidence_score=0.70,
        difficulty="easy",
    )
    db_session.add(path)
    await db_session.flush()

    milestone = TransitionMilestone(
        transition_path_id=path.id,
        phase="preparation",
        title="Research SDET landscape",
        description="Understand market demand and required skills.",
        target_week=2,
        order_index=0,
    )
    db_session.add(milestone)
    await db_session.flush()

    assert milestone.id is not None
    assert milestone.phase == "preparation"
    assert milestone.title == "Research SDET landscape"
    assert milestone.is_completed is False


@pytest.mark.asyncio
async def test_transition_comparison_model_creation(db_session):
    """Test TransitionComparison model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.transition_pathways import TransitionComparison, TransitionPath
    from app.models.user import User

    user = User(
        email="compare@test.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Compare User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    path = TransitionPath(
        career_dna_id=career_dna.id,
        from_role="Dev",
        to_role="PM",
        confidence_score=0.55,
        difficulty="moderate",
    )
    db_session.add(path)
    await db_session.flush()

    comparison = TransitionComparison(
        transition_path_id=path.id,
        dimension="salary",
        source_value=80000.0,
        target_value=90000.0,
        delta=10000.0,
        unit="EUR/year",
        reasoning="PMs typically earn more in enterprise.",
    )
    db_session.add(comparison)
    await db_session.flush()

    assert comparison.id is not None
    assert comparison.dimension == "salary"
    assert comparison.delta == 10000.0


@pytest.mark.asyncio
async def test_transition_preference_model_defaults(db_session):
    """Test TransitionPreference defaults."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.transition_pathways import TransitionPreference
    from app.models.user import User

    user = User(
        email="tpref@test.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pref User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = TransitionPreference(
        career_dna_id=career_dna.id,
        user_id=user.id,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.min_confidence == 0.3
    assert pref.max_timeline_months == 36
    assert pref.notification_enabled is True


# ── Static Analyzer Helper Tests ──────────────────────────────


def test_skill_overlap_full_match():
    """100% overlap when all target skills are held."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    overlap = TransitionPathwaysAnalyzer.compute_skill_overlap(
        current_skills=["Python", "Docker", "Kubernetes"],
        target_skills=["Python", "Docker", "Kubernetes"],
    )
    assert overlap == 100.0


def test_skill_overlap_partial():
    """Partial match computes correctly."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    overlap = TransitionPathwaysAnalyzer.compute_skill_overlap(
        current_skills=["Python", "Docker"],
        target_skills=["Python", "Docker", "Kubernetes", "Terraform"],
    )
    assert overlap == 50.0


def test_skill_overlap_no_match():
    """Zero overlap when no skills match."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    overlap = TransitionPathwaysAnalyzer.compute_skill_overlap(
        current_skills=["Java", "Maven"],
        target_skills=["Python", "Docker"],
    )
    assert overlap == 0.0


def test_skill_overlap_empty_target():
    """Empty target list returns 0.0."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    overlap = TransitionPathwaysAnalyzer.compute_skill_overlap(
        current_skills=["Python"],
        target_skills=[],
    )
    assert overlap == 0.0


def test_skill_overlap_case_insensitive():
    """Case differences should not affect matching."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    overlap = TransitionPathwaysAnalyzer.compute_skill_overlap(
        current_skills=["python", "DOCKER"],
        target_skills=["Python", "Docker"],
    )
    assert overlap == 100.0


def test_difficulty_easy():
    """High overlap + low gap = easy."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    difficulty = TransitionPathwaysAnalyzer.compute_transition_difficulty(
        skill_overlap_percent=75.0,
        seniority_gap=0,
    )
    assert difficulty == "easy"


def test_difficulty_moderate():
    """Medium overlap + medium gap = moderate."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    difficulty = TransitionPathwaysAnalyzer.compute_transition_difficulty(
        skill_overlap_percent=50.0,
        seniority_gap=1,
    )
    assert difficulty == "moderate"


def test_difficulty_challenging():
    """Low overlap = challenging."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    difficulty = TransitionPathwaysAnalyzer.compute_transition_difficulty(
        skill_overlap_percent=25.0,
        seniority_gap=2,
    )
    assert difficulty == "challenging"


def test_difficulty_extreme():
    """Very low overlap + high gap = extreme."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    difficulty = TransitionPathwaysAnalyzer.compute_transition_difficulty(
        skill_overlap_percent=10.0,
        seniority_gap=5,
    )
    assert difficulty == "extreme"


def test_timeline_easy():
    """Easy transition has short base timeline."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    optimistic, realistic, conservative = (
        TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="easy",
            skills_to_acquire=2,
        )
    )
    assert optimistic == 2
    assert realistic == 4
    assert conservative == 6


def test_timeline_extreme_many_skills():
    """Extreme with many skills extends timeline."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    optimistic, realistic, conservative = (
        TransitionPathwaysAnalyzer.estimate_timeline_range(
            difficulty="extreme",
            skills_to_acquire=10,
        )
    )
    assert optimistic > 14
    assert realistic > 22
    assert conservative > 30


def test_confidence_composition():
    """Combined confidence respects 0.85 ceiling."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    confidence = TransitionPathwaysAnalyzer.compute_transition_confidence(
        skill_overlap_percent=100.0,
        llm_confidence=0.85,
        market_demand_score=100.0,
    )
    assert confidence <= 0.85


def test_confidence_low_overlap():
    """Low overlap produces low confidence."""
    from app.ai.transition_pathways_analyzer import TransitionPathwaysAnalyzer

    confidence = TransitionPathwaysAnalyzer.compute_transition_confidence(
        skill_overlap_percent=10.0,
        llm_confidence=0.3,
        market_demand_score=30.0,
    )
    assert confidence < 0.3


# ── Schema Validation Tests ───────────────────────────────────


def test_explore_request_schema():
    """TransitionExploreRequest validates correctly."""
    from app.schemas.transition_pathways import TransitionExploreRequest

    request = TransitionExploreRequest(
        target_role="DevOps Engineer",
        target_industry="Cloud",
    )
    assert request.target_role == "DevOps Engineer"
    assert request.target_industry == "Cloud"
    assert request.target_location is None


def test_explore_request_min_length():
    """TransitionExploreRequest rejects too-short target_role."""
    from pydantic import ValidationError

    from app.schemas.transition_pathways import TransitionExploreRequest

    with pytest.raises(ValidationError):
        TransitionExploreRequest(target_role="X")


def test_role_whatif_request_schema():
    """RoleWhatIfRequest validates target_role."""
    from app.schemas.transition_pathways import RoleWhatIfRequest

    request = RoleWhatIfRequest(target_role="Data Scientist")
    assert request.target_role == "Data Scientist"


def test_preference_update_partial():
    """TransitionPreferenceUpdateRequest allows partial updates."""
    from app.schemas.transition_pathways import TransitionPreferenceUpdateRequest

    update = TransitionPreferenceUpdateRequest(
        min_confidence=0.5,
    )
    assert update.min_confidence == 0.5
    assert update.max_timeline_months is None


def test_preference_update_empty():
    """TransitionPreferenceUpdateRequest with no fields."""
    from app.schemas.transition_pathways import TransitionPreferenceUpdateRequest

    update = TransitionPreferenceUpdateRequest()
    dumped = update.model_dump(exclude_unset=True)
    assert dumped == {}


def test_preference_update_confidence_range():
    """min_confidence rejects out-of-range values."""
    from pydantic import ValidationError

    from app.schemas.transition_pathways import TransitionPreferenceUpdateRequest

    with pytest.raises(ValidationError):
        TransitionPreferenceUpdateRequest(min_confidence=1.5)


def test_compare_request_max_roles():
    """TransitionCompareRequest validates max 5 roles."""
    from pydantic import ValidationError

    from app.schemas.transition_pathways import TransitionCompareRequest

    with pytest.raises(ValidationError):
        TransitionCompareRequest(
            target_roles=["A", "B", "C", "D", "E", "F"]
        )


# ── Validation Clamping Tests ─────────────────────────────────


def test_clamp_transition_analysis_caps_confidence():
    """_clamp_transition_analysis caps confidence at 0.85."""
    from app.ai.transition_pathways_analyzer import _clamp_transition_analysis

    data = {
        "confidence_score": 0.95,
        "success_probability": 0.92,
        "skill_overlap_percent": 110.0,
        "estimated_duration_months": 0,
        "optimistic_months": 12,
        "realistic_months": 3,
        "conservative_months": 8,
        "difficulty": "invalid",
        "skills_to_acquire_count": -3,
    }
    _clamp_transition_analysis(data)

    assert data["confidence_score"] == 0.85
    assert data["success_probability"] == 0.85
    assert data["skill_overlap_percent"] == 100.0
    assert data["estimated_duration_months"] == 1
    assert data["optimistic_months"] == 3  # sorted
    assert data["realistic_months"] == 8
    assert data["conservative_months"] == 12
    assert data["difficulty"] == "moderate"  # defaulted
    assert data["skills_to_acquire_count"] == 0


def test_clamp_skill_bridge_entries():
    """_clamp_skill_bridge_entries validates priorities and categories."""
    from app.ai.transition_pathways_analyzer import _clamp_skill_bridge_entries

    skills = [
        {
            "priority": "invalid",
            "category": "unknown",
            "estimated_weeks": 200,
            "impact_on_confidence": 0.5,
        },
    ]
    _clamp_skill_bridge_entries(skills)

    assert skills[0]["priority"] == "medium"
    assert skills[0]["category"] == "technical"
    assert skills[0]["estimated_weeks"] == 104  # capped
    assert skills[0]["impact_on_confidence"] == 0.15  # capped


def test_clamp_milestones_validates_phase():
    """_clamp_milestones validates phase and target_week."""
    from app.ai.transition_pathways_analyzer import _clamp_milestones

    milestones = [
        {"phase": "invalid", "target_week": -5},
        {"phase": "preparation", "target_week": 200},
    ]
    _clamp_milestones(milestones)

    assert milestones[0]["phase"] == "preparation"
    assert milestones[0]["target_week"] == 1
    assert milestones[1]["target_week"] == 156


# ── API Endpoint Auth Gate Tests ──────────────────────────────


@pytest.mark.asyncio
async def test_transition_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/transition-pathways/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_explore_requires_auth(client: AsyncClient):
    """Explore endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/transition-pathways/explore",
        json={"target_role": "DevOps Engineer"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_list_requires_auth(client: AsyncClient):
    """List endpoint returns 401 without auth."""
    response = await client.get("/api/v1/transition-pathways/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_whatif_requires_auth(client: AsyncClient):
    """What-if endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/transition-pathways/what-if",
        json={"target_role": "Data Scientist"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_preferences_get_requires_auth(client: AsyncClient):
    """Preferences GET requires auth."""
    response = await client.get("/api/v1/transition-pathways/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_preferences_put_requires_auth(client: AsyncClient):
    """Preferences PUT requires auth."""
    response = await client.put(
        "/api/v1/transition-pathways/preferences",
        json={"min_confidence": 0.5},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_delete_requires_auth(client: AsyncClient):
    """Delete endpoint returns 401 without auth."""
    response = await client.delete(
        "/api/v1/transition-pathways/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_skill_bridge_requires_auth(client: AsyncClient):
    """Skill bridge endpoint returns 401 without auth."""
    response = await client.get(
        "/api/v1/transition-pathways/00000000-0000-0000-0000-000000000001/skill-bridge",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_milestones_requires_auth(client: AsyncClient):
    """Milestones endpoint returns 401 without auth."""
    response = await client.get(
        "/api/v1/transition-pathways/00000000-0000-0000-0000-000000000001/milestones",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_transition_comparison_requires_auth(client: AsyncClient):
    """Comparison endpoint returns 401 without auth."""
    response = await client.get(
        "/api/v1/transition-pathways/00000000-0000-0000-0000-000000000001/comparison",
    )
    assert response.status_code == 401


# ── API Endpoint Empty-State Tests ─────────────────────────────


@pytest.mark.asyncio
async def test_transition_dashboard_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Dashboard returns empty state for user with no transitions."""
    response = await client.get(
        "/api/v1/transition-pathways/dashboard",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["transitions"] == []
    assert data["total_explored"] == 0


@pytest.mark.asyncio
async def test_transition_list_empty(
    client: AsyncClient, auth_headers: dict,
):
    """List returns empty array for new user."""
    response = await client.get(
        "/api/v1/transition-pathways/",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_transition_get_not_found(
    client: AsyncClient, auth_headers: dict,
):
    """Get non-existent transition returns 404."""
    response = await client.get(
        "/api/v1/transition-pathways/00000000-0000-0000-0000-000000000001",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transition_delete_not_found(
    client: AsyncClient, auth_headers: dict,
):
    """Delete non-existent transition returns 404."""
    response = await client.delete(
        "/api/v1/transition-pathways/00000000-0000-0000-0000-000000000001",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_transition_preferences_empty(
    client: AsyncClient, auth_headers: dict,
):
    """Preferences returns null before setup."""
    response = await client.get(
        "/api/v1/transition-pathways/preferences",
        headers=auth_headers,
    )
    assert response.status_code == 200
