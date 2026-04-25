"""
PathForge — Cross-Border Career Passport™ Tests
=================================================
Test suite for:
    - Career Passport model creation (5 entities)
    - Static analyzer helpers (passport score, credential confidence, etc.)
    - Clamping validators (credential, comparison, visa, demand)
    - Schema validation (request + response)
    - API endpoint auth gates (11 endpoints)
    - Enum completeness checks (4 enums)

~56 tests covering the full Career Passport pipeline.
"""

import uuid

import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_credential_mapping_model_creation(db_session):
    """Test CredentialMapping model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_passport import CredentialMapping
    from app.models.user import User

    user = User(
        email="cred@passport.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Credential User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    mapping = CredentialMapping(
        career_dna_id=career_dna.id,
        user_id=user.id,
        source_qualification="BSc Computer Science",
        source_country="Netherlands",
        target_country="Germany",
        equivalent_level="Bachelor of Science",
        eqf_level="level_6",
        confidence_score=0.72,
    )
    db_session.add(mapping)
    await db_session.flush()

    assert mapping.id is not None
    assert mapping.source_qualification == "BSc Computer Science"
    assert mapping.eqf_level == "level_6"
    assert mapping.confidence_score == 0.72
    assert "AI-powered" in mapping.data_source
    assert "AI-estimated equivalency" in mapping.disclaimer


@pytest.mark.asyncio
async def test_country_comparison_model_creation(db_session):
    """Test CountryComparison model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_passport import CountryComparison
    from app.models.user import User

    user = User(
        email="compare@passport.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Compare User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    comparison = CountryComparison(
        career_dna_id=career_dna.id,
        user_id=user.id,
        source_country="Netherlands",
        target_country="Germany",
        col_delta_pct=-5.3,
        salary_delta_pct=8.2,
        purchasing_power_delta=13.5,
        market_demand_level="high",
    )
    db_session.add(comparison)
    await db_session.flush()

    assert comparison.id is not None
    assert comparison.source_country == "Netherlands"
    assert comparison.purchasing_power_delta == 13.5
    assert comparison.market_demand_level == "high"


@pytest.mark.asyncio
async def test_visa_assessment_model_creation(db_session):
    """Test VisaAssessment model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_passport import VisaAssessment
    from app.models.user import User

    user = User(
        email="visa@passport.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Visa User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    assessment = VisaAssessment(
        career_dna_id=career_dna.id,
        user_id=user.id,
        nationality="Turkish",
        target_country="Germany",
        visa_type="blue_card",
        eligibility_score=0.75,
        processing_time_weeks=12,
    )
    db_session.add(assessment)
    await db_session.flush()

    assert assessment.id is not None
    assert assessment.visa_type == "blue_card"
    assert assessment.eligibility_score == 0.75
    assert "NOT legal or immigration advice" in assessment.disclaimer


@pytest.mark.asyncio
async def test_market_demand_entry_model_creation(db_session):
    """Test MarketDemandEntry model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_passport import MarketDemandEntry
    from app.models.user import User

    user = User(
        email="demand@passport.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Demand User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    entry = MarketDemandEntry(
        career_dna_id=career_dna.id,
        user_id=user.id,
        country="Germany",
        role="Backend Engineer",
        demand_level="very_high",
        open_positions_estimate=1500,
        currency="EUR",
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.id is not None
    assert entry.demand_level == "very_high"
    assert entry.open_positions_estimate == 1500


@pytest.mark.asyncio
async def test_career_passport_preference_model_creation(db_session):
    """Test CareerPassportPreference model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.career_passport import CareerPassportPreference
    from app.models.user import User

    user = User(
        email="pref@passport.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pref User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = CareerPassportPreference(
        career_dna_id=career_dna.id,
        user_id=user.id,
        nationality="Dutch",
        include_visa_info=True,
        include_col_comparison=True,
        include_market_demand=False,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.nationality == "Dutch"
    assert pref.include_visa_info is True
    assert pref.include_market_demand is False


# ── Static Helper Tests ────────────────────────────────────────


def test_passport_score_full():
    """High inputs produce strong passport score."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_passport_score(
        credential_confidence=0.85,
        visa_eligibility=0.85,
        demand_level="very_high",
        purchasing_power_delta=25.0,
    )
    assert score["overall_score"] <= 1.0
    assert score["overall_score"] >= 0.8


def test_passport_score_zero_inputs():
    """Zero inputs produce low passport score."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_passport_score(
        credential_confidence=0.0,
        visa_eligibility=0.0,
        demand_level="low",
        purchasing_power_delta=-30.0,
    )
    assert score["overall_score"] >= 0.0
    assert score["overall_score"] <= 0.15


def test_passport_score_moderate():
    """Moderate inputs produce mid-range score."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_passport_score(
        credential_confidence=0.5,
        visa_eligibility=0.5,
        demand_level="moderate",
        purchasing_power_delta=0.0,
    )
    assert 0.3 <= score["overall_score"] <= 0.7


def test_passport_score_components_present():
    """All component scores are returned."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_passport_score(
        credential_confidence=0.6,
        visa_eligibility=0.7,
        demand_level="high",
        purchasing_power_delta=10.0,
    )
    assert "credential_score" in score
    assert "visa_score" in score
    assert "demand_score" in score
    assert "financial_score" in score
    assert "overall_score" in score


def test_credential_confidence_caps_at_085():
    """Even perfect inputs cannot exceed 0.85."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    confidence = CareerPassportAnalyzer.compute_credential_confidence(
        llm_confidence=1.0,
        eqf_level_known=True,
        career_dna_completeness=1.0,
    )
    assert confidence <= 0.85


def test_credential_confidence_zero_inputs():
    """Zero inputs produce very low confidence."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    confidence = CareerPassportAnalyzer.compute_credential_confidence(
        llm_confidence=0.0,
        eqf_level_known=False,
        career_dna_completeness=0.0,
    )
    assert confidence >= 0.0
    assert confidence <= 0.15


def test_credential_confidence_eqf_bonus():
    """Known EQF level gives higher confidence than unknown."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    known = CareerPassportAnalyzer.compute_credential_confidence(
        llm_confidence=0.6,
        eqf_level_known=True,
        career_dna_completeness=0.5,
    )
    unknown = CareerPassportAnalyzer.compute_credential_confidence(
        llm_confidence=0.6,
        eqf_level_known=False,
        career_dna_completeness=0.5,
    )
    assert known > unknown


def test_financial_score_positive_delta():
    """Positive purchasing power gives score > 0.5."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_financial_score(
        purchasing_power_delta=20.0,
    )
    assert score > 0.5


def test_financial_score_negative_delta():
    """Negative purchasing power gives score < 0.5."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_financial_score(
        purchasing_power_delta=-20.0,
    )
    assert score < 0.5


def test_financial_score_zero_delta():
    """Zero purchasing power gives score of 0.5."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    score = CareerPassportAnalyzer.compute_financial_score(
        purchasing_power_delta=0.0,
    )
    assert score == 0.5


def test_demand_score_all_levels():
    """All demand levels map to expected scores."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    assert CareerPassportAnalyzer.compute_demand_score(demand_level="low") == 0.2
    assert CareerPassportAnalyzer.compute_demand_score(demand_level="moderate") == 0.5
    assert CareerPassportAnalyzer.compute_demand_score(demand_level="high") == 0.75
    assert CareerPassportAnalyzer.compute_demand_score(demand_level="very_high") == 1.0


def test_demand_score_unknown_level():
    """Unknown demand level defaults to 0.5."""
    from app.ai.career_passport_analyzer import CareerPassportAnalyzer

    assert CareerPassportAnalyzer.compute_demand_score(demand_level="unknown") == 0.5


# ── Clamping Validator Tests ───────────────────────────────────


def test_clamp_credential_mapping_caps_confidence():
    """Credential confidence above 0.85 is clamped."""
    from app.ai.career_passport_analyzer import _clamp_credential_mapping

    data = {"confidence": 0.95, "eqf_level": "level_6", "equivalent_level": "BSc"}
    _clamp_credential_mapping(data)
    assert data["confidence"] <= 0.85


def test_clamp_credential_mapping_validates_eqf():
    """Invalid EQF level defaults to level_6."""
    from app.ai.career_passport_analyzer import _clamp_credential_mapping

    data = {"confidence": 0.5, "eqf_level": "invalid", "equivalent_level": "BSc"}
    _clamp_credential_mapping(data)
    assert data["eqf_level"] == "level_6"


def test_clamp_credential_mapping_ensures_notes():
    """Missing recognition_notes gets fallback."""
    from app.ai.career_passport_analyzer import _clamp_credential_mapping

    data = {"confidence": 0.5, "eqf_level": "level_7"}
    _clamp_credential_mapping(data)
    assert "ENIC-NARIC" in data["recognition_notes"]


def test_clamp_country_comparison_defaults():
    """Missing numeric fields default to 0.0."""
    from app.ai.career_passport_analyzer import _clamp_country_comparison

    data = {"market_demand_level": "invalid"}
    _clamp_country_comparison(data)
    assert data["col_delta_pct"] == 0.0
    assert data["salary_delta_pct"] == 0.0
    assert data["purchasing_power_delta"] == 0.0
    assert data["market_demand_level"] == "moderate"


def test_clamp_country_comparison_validates_demand():
    """Invalid demand level defaults to moderate."""
    from app.ai.career_passport_analyzer import _clamp_country_comparison

    data = {"market_demand_level": "super_high"}
    _clamp_country_comparison(data)
    assert data["market_demand_level"] == "moderate"


def test_clamp_visa_assessment_caps_score():
    """Visa eligibility above 0.85 is clamped."""
    from app.ai.career_passport_analyzer import _clamp_visa_assessment

    data = {"eligibility_score": 0.95, "visa_type": "blue_card"}
    _clamp_visa_assessment(data)
    assert data["eligibility_score"] <= 0.85


def test_clamp_visa_assessment_validates_type():
    """Invalid visa type defaults to other."""
    from app.ai.career_passport_analyzer import _clamp_visa_assessment

    data = {"eligibility_score": 0.5, "visa_type": "magic_visa"}
    _clamp_visa_assessment(data)
    assert data["visa_type"] == "other"


def test_clamp_visa_assessment_clamps_weeks():
    """Processing weeks clamped to 1-52 range."""
    from app.ai.career_passport_analyzer import _clamp_visa_assessment

    data = {"eligibility_score": 0.5, "visa_type": "work_permit", "processing_time_weeks": 100}
    _clamp_visa_assessment(data)
    assert data["processing_time_weeks"] == 52


def test_clamp_market_demand_validates_demand():
    """Invalid demand level defaults to moderate."""
    from app.ai.career_passport_analyzer import _clamp_market_demand

    data = {"demand_level": "extreme"}
    _clamp_market_demand(data)
    assert data["demand_level"] == "moderate"


def test_clamp_market_demand_clamps_positions():
    """Negative positions clamped to 0."""
    from app.ai.career_passport_analyzer import _clamp_market_demand

    data = {"demand_level": "high", "open_positions_estimate": -5}
    _clamp_market_demand(data)
    assert data["open_positions_estimate"] == 0


def test_clamp_market_demand_null_salary():
    """Invalid salary values become None."""
    from app.ai.career_passport_analyzer import _clamp_market_demand

    data = {"demand_level": "high", "salary_range_min": "not a number", "salary_range_max": -100}
    _clamp_market_demand(data)
    assert data["salary_range_min"] is None
    assert data["salary_range_max"] is None


def test_clamp_market_demand_valid_salary():
    """Valid salary values are preserved."""
    from app.ai.career_passport_analyzer import _clamp_market_demand

    data = {
        "demand_level": "high",
        "salary_range_min": 50000.0,
        "salary_range_max": 80000.0,
    }
    _clamp_market_demand(data)
    assert data["salary_range_min"] == 50000.0
    assert data["salary_range_max"] == 80000.0


# ── Schema Validation Tests ────────────────────────────────────


def test_credential_mapping_request_schema():
    """CredentialMappingRequest validates correctly."""
    from app.schemas.career_passport import CredentialMappingRequest

    request = CredentialMappingRequest(
        source_qualification="BSc Computer Science",
        source_country="Netherlands",
        target_country="Germany",
    )
    assert request.source_qualification == "BSc Computer Science"
    assert request.target_country == "Germany"


def test_credential_mapping_request_rejects_empty():
    """CredentialMappingRequest rejects empty qualification."""
    from pydantic import ValidationError

    from app.schemas.career_passport import CredentialMappingRequest

    with pytest.raises(ValidationError):
        CredentialMappingRequest(
            source_qualification="",
            source_country="NL",
            target_country="DE",
        )


def test_country_comparison_request_schema():
    """CountryComparisonRequest validates correctly."""
    from app.schemas.career_passport import CountryComparisonRequest

    request = CountryComparisonRequest(
        source_country="Netherlands",
        target_country="Germany",
    )
    assert request.source_country == "Netherlands"


def test_multi_country_request_schema():
    """MultiCountryComparisonRequest validates correctly."""
    from app.schemas.career_passport import MultiCountryComparisonRequest

    request = MultiCountryComparisonRequest(
        source_country="Netherlands",
        target_countries=["Germany", "UK", "Sweden"],
    )
    assert len(request.target_countries) == 3


def test_multi_country_request_max_countries():
    """MultiCountryComparisonRequest rejects more than 5."""
    from pydantic import ValidationError

    from app.schemas.career_passport import MultiCountryComparisonRequest

    with pytest.raises(ValidationError):
        MultiCountryComparisonRequest(
            source_country="NL",
            target_countries=["DE", "UK", "SE", "FR", "ES", "IT"],
        )


def test_visa_assessment_request_schema():
    """VisaAssessmentRequest validates correctly."""
    from app.schemas.career_passport import VisaAssessmentRequest

    request = VisaAssessmentRequest(
        nationality="Turkish",
        target_country="Germany",
    )
    assert request.nationality == "Turkish"


def test_market_demand_request_schema():
    """MarketDemandRequest validates correctly."""
    from app.schemas.career_passport import MarketDemandRequest

    request = MarketDemandRequest(
        country="Germany",
        role="Backend Engineer",
        industry="Technology",
    )
    assert request.country == "Germany"
    assert request.role == "Backend Engineer"


def test_preference_update_partial():
    """CareerPassportPreferenceUpdate handles partial updates."""
    from app.schemas.career_passport import CareerPassportPreferenceUpdate

    request = CareerPassportPreferenceUpdate(
        nationality="Dutch",
        include_visa_info=True,
    )
    assert request.nationality == "Dutch"
    assert request.include_visa_info is True
    assert request.preferred_countries is None


def test_passport_score_response_bounds():
    """PassportScoreResponse enforces 0-1 bounds."""
    from pydantic import ValidationError

    from app.schemas.career_passport import PassportScoreResponse

    with pytest.raises(ValidationError):
        PassportScoreResponse(
            credential_score=1.5,
            visa_score=0.5,
            demand_score=0.5,
            financial_score=0.5,
            overall_score=0.5,
            target_country="Germany",
        )


def test_dashboard_response_defaults():
    """CareerPassportDashboardResponse has correct defaults."""
    from app.schemas.career_passport import CareerPassportDashboardResponse

    response = CareerPassportDashboardResponse()
    assert response.credential_mappings == []
    assert response.country_comparisons == []
    assert response.visa_assessments == []
    assert response.market_demand == []
    assert response.preferences is None
    assert "AI-powered" in response.data_source
    assert "85%" in response.disclaimer


# ── API Auth Gate Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_passport_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-passport/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_full_scan_requires_auth(client: AsyncClient):
    """Full scan endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-passport/scan",
        json={
            "source_qualification": "BSc CS",
            "source_country": "NL",
            "target_country": "DE",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_credential_mapping_requires_auth(client: AsyncClient):
    """Credential mapping endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-passport/credential-mapping",
        json={
            "source_qualification": "BSc CS",
            "source_country": "NL",
            "target_country": "DE",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_get_credential_mapping_requires_auth(client: AsyncClient):
    """Get credential mapping endpoint returns 401 without auth."""
    mapping_id = uuid.uuid4()
    response = await client.get(f"/api/v1/career-passport/credential-mapping/{mapping_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_delete_credential_mapping_requires_auth(client: AsyncClient):
    """Delete credential mapping endpoint returns 401 without auth."""
    mapping_id = uuid.uuid4()
    response = await client.delete(f"/api/v1/career-passport/credential-mapping/{mapping_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_country_comparison_requires_auth(client: AsyncClient):
    """Country comparison endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-passport/country-comparison",
        json={"source_country": "NL", "target_country": "DE"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_multi_country_requires_auth(client: AsyncClient):
    """Multi-country comparison endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-passport/multi-country-comparison",
        json={"source_country": "NL", "target_countries": ["DE", "UK"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_visa_assessment_requires_auth(client: AsyncClient):
    """Visa assessment endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/career-passport/visa-assessment",
        json={"nationality": "Turkish", "target_country": "DE"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_market_demand_requires_auth(client: AsyncClient):
    """Market demand endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-passport/market-demand/Germany")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_get_preferences_requires_auth(client: AsyncClient):
    """Get preferences endpoint returns 401 without auth."""
    response = await client.get("/api/v1/career-passport/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passport_update_preferences_requires_auth(client: AsyncClient):
    """Update preferences endpoint returns 401 without auth."""
    response = await client.put(
        "/api/v1/career-passport/preferences",
        json={"nationality": "Dutch"},
    )
    assert response.status_code == 401


# ── Enum Completeness Tests ────────────────────────────────────


def test_eqf_level_enum_completeness():
    """EQFLevel enum has all 8 EQF levels."""
    from app.models.career_passport import EQFLevel

    levels = list(EQFLevel)
    assert len(levels) == 8
    assert EQFLevel.LEVEL_1 in levels
    assert EQFLevel.LEVEL_8 in levels


def test_demand_level_enum_completeness():
    """DemandLevel enum has 4 levels."""
    from app.models.career_passport import DemandLevel

    levels = list(DemandLevel)
    assert len(levels) == 4
    assert DemandLevel.LOW in levels
    assert DemandLevel.VERY_HIGH in levels


def test_visa_category_enum_completeness():
    """VisaCategory enum has 6 categories."""
    from app.models.career_passport import VisaCategory

    categories = list(VisaCategory)
    assert len(categories) == 6
    assert VisaCategory.FREE_MOVEMENT in categories
    assert VisaCategory.BLUE_CARD in categories


def test_comparison_status_enum_completeness():
    """ComparisonStatus enum has 3 statuses."""
    from app.models.career_passport import ComparisonStatus

    statuses = list(ComparisonStatus)
    assert len(statuses) == 3
    assert ComparisonStatus.DRAFT in statuses
    assert ComparisonStatus.ACTIVE in statuses
    assert ComparisonStatus.ARCHIVED in statuses
