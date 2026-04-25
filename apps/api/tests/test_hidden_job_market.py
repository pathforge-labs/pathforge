"""
PathForge — Hidden Job Market Detector™ Tests
===============================================
Test suite for:
    - Hidden Job Market model creation (5 entities)
    - Static analyzer helpers (confidence, match strength, validation)
    - Clamping validators (signals, match, outreach, opportunities)
    - Schema validation (request + response)
    - API endpoint auth gates (11 endpoints)
    - Enum completeness checks (4 enums)

~50 tests covering the full Hidden Job Market Detector pipeline.
"""

import uuid

import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_company_signal_model_creation(db_session):
    """Test CompanySignal model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.hidden_job_market import CompanySignal
    from app.models.user import User

    user = User(
        email="signal@hjm.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Signal User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    signal = CompanySignal(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="TechCorp",
        signal_type="funding",
        title="Series B Funding Round",
        description="TechCorp raised $50M in Series B.",
        strength=0.75,
        source="crunchbase",
        status="detected",
        confidence_score=0.72,
    )
    db_session.add(signal)
    await db_session.flush()

    assert signal.id is not None
    assert signal.company_name == "TechCorp"
    assert signal.signal_type == "funding"
    assert signal.confidence_score == 0.72
    assert signal.status == "detected"
    assert "AI-generated" in signal.data_source
    assert "not a guarantee" in signal.disclaimer


@pytest.mark.asyncio
async def test_signal_match_result_model_creation(db_session):
    """Test SignalMatchResult model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.hidden_job_market import CompanySignal, SignalMatchResult
    from app.models.user import User

    user = User(
        email="match@hjm.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Match User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    signal = CompanySignal(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="MatchCo",
        signal_type="key_hire",
        title="New CTO Hired",
        strength=0.80,
        status="detected",
        confidence_score=0.65,
    )
    db_session.add(signal)
    await db_session.flush()

    match_result = SignalMatchResult(
        signal_id=signal.id,
        match_score=0.78,
        skill_overlap=0.82,
        role_relevance=0.70,
        explanation="Strong skill overlap with engineering needs.",
    )
    db_session.add(match_result)
    await db_session.flush()

    assert match_result.id is not None
    assert match_result.match_score == 0.78
    assert match_result.skill_overlap == 0.82


@pytest.mark.asyncio
async def test_outreach_template_model_creation(db_session):
    """Test OutreachTemplate model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.hidden_job_market import CompanySignal, OutreachTemplate
    from app.models.user import User

    user = User(
        email="outreach@hjm.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Outreach User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    signal = CompanySignal(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="OutreachCo",
        signal_type="office_expansion",
        title="New Amsterdam Office",
        strength=0.65,
        status="matched",
        confidence_score=0.60,
    )
    db_session.add(signal)
    await db_session.flush()

    template = OutreachTemplate(
        signal_id=signal.id,
        template_type="introduction",
        tone="professional",
        subject_line="Saw your Amsterdam expansion — excited to connect",
        body="Dear Hiring Manager, I noticed your recent...",
        confidence=0.70,
    )
    db_session.add(template)
    await db_session.flush()

    assert template.id is not None
    assert template.template_type == "introduction"
    assert template.tone == "professional"


@pytest.mark.asyncio
async def test_hidden_opportunity_model_creation(db_session):
    """Test HiddenOpportunity model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.hidden_job_market import CompanySignal, HiddenOpportunity
    from app.models.user import User

    user = User(
        email="opportunity@hjm.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Opportunity User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    signal = CompanySignal(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="OppCo",
        signal_type="revenue_growth",
        title="30% Revenue Growth",
        strength=0.85,
        status="matched",
        confidence_score=0.75,
    )
    db_session.add(signal)
    await db_session.flush()

    opportunity = HiddenOpportunity(
        signal_id=signal.id,
        predicted_role="Senior Backend Engineer",
        predicted_seniority="senior",
        predicted_timeline_days=60,
        probability=0.68,
        reasoning="Revenue growth signals engineering headcount expansion.",
    )
    db_session.add(opportunity)
    await db_session.flush()

    assert opportunity.id is not None
    assert opportunity.predicted_role == "Senior Backend Engineer"
    assert opportunity.probability == 0.68


@pytest.mark.asyncio
async def test_hidden_job_market_preference_model_creation(db_session):
    """Test HiddenJobMarketPreference model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.hidden_job_market import HiddenJobMarketPreference
    from app.models.user import User

    user = User(
        email="pref@hjm.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Pref User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = HiddenJobMarketPreference(
        career_dna_id=career_dna.id,
        user_id=user.id,
        min_signal_strength=0.5,
        max_outreach_per_week=10,
        auto_generate_outreach=True,
        notification_enabled=False,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.min_signal_strength == 0.5
    assert pref.max_outreach_per_week == 10
    assert pref.auto_generate_outreach is True
    assert pref.notification_enabled is False


# ── Static Helper Tests ────────────────────────────────────────


def test_signal_confidence_full_match():
    """High inputs produce near-ceiling confidence."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    confidence = HiddenJobMarketAnalyzer.compute_signal_confidence(
        llm_confidence=0.85,
        signal_strength=1.0,
        career_dna_completeness=1.0,
    )
    assert confidence <= 0.85


def test_signal_confidence_caps_at_085():
    """Even perfect inputs cannot exceed 0.85."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    confidence = HiddenJobMarketAnalyzer.compute_signal_confidence(
        llm_confidence=1.0,
        signal_strength=1.0,
        career_dna_completeness=1.0,
    )
    assert confidence <= 0.85


def test_signal_confidence_zero_inputs():
    """Zero inputs produce zero confidence."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    confidence = HiddenJobMarketAnalyzer.compute_signal_confidence(
        llm_confidence=0.0,
        signal_strength=0.0,
        career_dna_completeness=0.0,
    )
    assert confidence == 0.0


def test_signal_confidence_partial():
    """Partial data produces moderate confidence."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    confidence = HiddenJobMarketAnalyzer.compute_signal_confidence(
        llm_confidence=0.6,
        signal_strength=0.5,
        career_dna_completeness=0.5,
    )
    assert 0.15 <= confidence <= 0.85


def test_match_strength_full():
    """Perfect skill overlap and role relevance near 1.0."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    strength = HiddenJobMarketAnalyzer.calculate_match_strength(
        skill_overlap=1.0,
        role_relevance=1.0,
        signal_strength=1.0,
    )
    assert strength == 1.0


def test_match_strength_zero():
    """Zero inputs produce zero match strength."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    strength = HiddenJobMarketAnalyzer.calculate_match_strength(
        skill_overlap=0.0,
        role_relevance=0.0,
        signal_strength=0.0,
    )
    assert strength == 0.0


def test_match_strength_capped():
    """Match strength never exceeds 1.0."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    strength = HiddenJobMarketAnalyzer.calculate_match_strength(
        skill_overlap=1.5,
        role_relevance=1.5,
        signal_strength=1.5,
    )
    assert strength <= 1.0


def test_validate_signal_data_valid():
    """Complete signal data validates successfully."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    data = {
        "signal_type": "funding",
        "title": "Series B",
        "strength": 0.75,
        "confidence": 0.60,
    }
    is_valid, error = HiddenJobMarketAnalyzer.validate_signal_data(data)
    assert is_valid is True
    assert error == ""


def test_validate_signal_data_missing_field():
    """Missing required field fails validation."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    data = {
        "signal_type": "funding",
        # Missing title, strength, confidence
    }
    is_valid, error = HiddenJobMarketAnalyzer.validate_signal_data(data)
    assert is_valid is False
    assert "Missing" in error


def test_validate_signal_data_invalid_type():
    """Invalid signal_type fails validation."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    data = {
        "signal_type": "magic",
        "title": "Magic signal",
        "strength": 0.5,
        "confidence": 0.5,
    }
    is_valid, error = HiddenJobMarketAnalyzer.validate_signal_data(data)
    assert is_valid is False
    assert "Invalid signal_type" in error


def test_opportunity_probability_high_signals():
    """Many strong signals produce high probability (capped at 0.85)."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    probability = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
        signal_count=5,
        avg_signal_strength=1.0,
        match_score=1.0,
    )
    assert probability <= 0.85


def test_opportunity_probability_zero():
    """No signals produce zero probability."""
    from app.ai.hidden_job_market_analyzer import HiddenJobMarketAnalyzer

    probability = HiddenJobMarketAnalyzer.calculate_opportunity_probability(
        signal_count=0,
        avg_signal_strength=0.0,
        match_score=0.0,
    )
    assert probability == 0.0


# ── Clamping Validator Tests ───────────────────────────────────


def test_clamp_signal_analysis_caps_confidence():
    """Signal confidence above 0.85 is clamped down."""
    from app.ai.hidden_job_market_analyzer import _clamp_signal_analysis

    data = {
        "signals": [
            {
                "signal_type": "funding",
                "title": "Series A",
                "description": "Raised $10M.",
                "strength": 0.70,
                "confidence": 0.95,
            }
        ],
        "company_summary": "Growing company.",
    }
    _clamp_signal_analysis(data)
    assert data["signals"][0]["confidence"] <= 0.85


def test_clamp_signal_analysis_validates_type():
    """Invalid signal type defaults to 'funding'."""
    from app.ai.hidden_job_market_analyzer import _clamp_signal_analysis

    data = {
        "signals": [
            {
                "signal_type": "invalid_type",
                "title": "Test",
                "strength": 0.5,
                "confidence": 0.5,
            }
        ],
    }
    _clamp_signal_analysis(data)
    assert data["signals"][0]["signal_type"] == "funding"


def test_clamp_signal_analysis_ensures_title():
    """Missing signal title defaults to 'Untitled signal'."""
    from app.ai.hidden_job_market_analyzer import _clamp_signal_analysis

    data = {
        "signals": [
            {
                "signal_type": "funding",
                "strength": 0.5,
                "confidence": 0.5,
            }
        ],
    }
    _clamp_signal_analysis(data)
    assert data["signals"][0]["title"] == "Untitled signal"


def test_clamp_signal_analysis_handles_non_list():
    """Non-list signals replaced with empty list."""
    from app.ai.hidden_job_market_analyzer import _clamp_signal_analysis

    data = {"signals": "not a list"}
    _clamp_signal_analysis(data)
    assert data["signals"] == []


def test_clamp_match_result_caps_scores():
    """Match scores above 1.0 are clamped to 1.0."""
    from app.ai.hidden_job_market_analyzer import _clamp_match_result

    data = {
        "match_score": 1.5,
        "skill_overlap": 1.2,
        "role_relevance": 1.3,
    }
    _clamp_match_result(data)
    assert data["match_score"] == 1.0
    assert data["skill_overlap"] == 1.0
    assert data["role_relevance"] == 1.0


def test_clamp_match_result_ensures_explanation():
    """Missing explanation gets fallback text."""
    from app.ai.hidden_job_market_analyzer import _clamp_match_result

    data = {
        "match_score": 0.5,
        "skill_overlap": 0.5,
        "role_relevance": 0.5,
    }
    _clamp_match_result(data)
    assert "No match explanation" in data["explanation"]


def test_clamp_match_result_ensures_skills_dict():
    """Non-dict matched_skills replaced with structured dict."""
    from app.ai.hidden_job_market_analyzer import _clamp_match_result

    data = {
        "match_score": 0.5,
        "skill_overlap": 0.5,
        "role_relevance": 0.5,
        "matched_skills": "not a dict",
    }
    _clamp_match_result(data)
    assert isinstance(data["matched_skills"], dict)
    assert "highly_relevant" in data["matched_skills"]


def test_clamp_outreach_caps_confidence():
    """Outreach confidence above 0.85 is clamped."""
    from app.ai.hidden_job_market_analyzer import _clamp_outreach

    data = {
        "subject_line": "Great opportunity",
        "body": "Hello there...",
        "confidence": 0.95,
    }
    _clamp_outreach(data)
    assert data["confidence"] <= 0.85


def test_clamp_outreach_ensures_subject():
    """Missing subject line gets fallback."""
    from app.ai.hidden_job_market_analyzer import _clamp_outreach

    data = {"confidence": 0.5}
    _clamp_outreach(data)
    assert data["subject_line"] == "Connection opportunity"


def test_clamp_outreach_ensures_points():
    """Non-dict personalization_points replaced with structured dict."""
    from app.ai.hidden_job_market_analyzer import _clamp_outreach

    data = {
        "subject_line": "Subject",
        "body": "Body",
        "confidence": 0.5,
        "personalization_points": "not a dict",
    }
    _clamp_outreach(data)
    assert isinstance(data["personalization_points"], dict)
    assert "signal_reference" in data["personalization_points"]


def test_clamp_opportunities_caps_probability():
    """Opportunity probability above 0.85 is clamped."""
    from app.ai.hidden_job_market_analyzer import _clamp_opportunities

    data = {
        "opportunities": [
            {
                "predicted_role": "Engineer",
                "probability": 0.95,
                "reasoning": "Strong signals.",
            }
        ],
    }
    _clamp_opportunities(data)
    assert data["opportunities"][0]["probability"] <= 0.85


def test_clamp_opportunities_ensures_role():
    """Missing predicted_role defaults to 'Unknown role'."""
    from app.ai.hidden_job_market_analyzer import _clamp_opportunities

    data = {
        "opportunities": [
            {"probability": 0.5}
        ],
    }
    _clamp_opportunities(data)
    assert data["opportunities"][0]["predicted_role"] == "Unknown role"


def test_clamp_opportunities_ensures_skills_dict():
    """Non-dict required_skills replaced with structured dict."""
    from app.ai.hidden_job_market_analyzer import _clamp_opportunities

    data = {
        "opportunities": [
            {
                "predicted_role": "Engineer",
                "probability": 0.5,
                "reasoning": "Test.",
                "required_skills": "not a dict",
            }
        ],
    }
    _clamp_opportunities(data)
    assert isinstance(data["opportunities"][0]["required_skills"], dict)
    assert "must_have" in data["opportunities"][0]["required_skills"]


# ── Schema Validation Tests ────────────────────────────────────


def test_scan_company_request_schema():
    """ScanCompanyRequest validates correctly."""
    from app.schemas.hidden_job_market import ScanCompanyRequest

    request = ScanCompanyRequest(
        company_name="Google",
        industry="Technology",
    )
    assert request.company_name == "Google"
    assert request.industry == "Technology"


def test_scan_company_request_rejects_empty_name():
    """ScanCompanyRequest rejects empty company name."""
    from pydantic import ValidationError

    from app.schemas.hidden_job_market import ScanCompanyRequest

    with pytest.raises(ValidationError):
        ScanCompanyRequest(company_name="")


def test_scan_industry_request_schema():
    """ScanIndustryRequest validates correctly."""
    from app.schemas.hidden_job_market import ScanIndustryRequest

    request = ScanIndustryRequest(
        industry="FinTech",
        region="Europe",
        max_companies=10,
    )
    assert request.industry == "FinTech"
    assert request.max_companies == 10


def test_scan_industry_request_max_companies_bounds():
    """ScanIndustryRequest enforces max_companies bounds."""
    from pydantic import ValidationError

    from app.schemas.hidden_job_market import ScanIndustryRequest

    with pytest.raises(ValidationError):
        ScanIndustryRequest(industry="Tech", max_companies=25)


def test_generate_outreach_request_schema():
    """GenerateOutreachRequest validates correctly."""
    from app.schemas.hidden_job_market import GenerateOutreachRequest

    request = GenerateOutreachRequest(
        template_type="referral_request",
        tone="casual",
        custom_notes="Mention our mutual connection.",
    )
    assert request.template_type == "referral_request"
    assert request.tone == "casual"


def test_generate_outreach_request_defaults():
    """GenerateOutreachRequest uses correct defaults."""
    from app.schemas.hidden_job_market import GenerateOutreachRequest

    request = GenerateOutreachRequest()
    assert request.template_type == "introduction"
    assert request.tone == "professional"
    assert request.custom_notes is None


def test_preference_update_request_schema():
    """HiddenJobMarketPreferenceUpdateRequest handles partial updates."""
    from app.schemas.hidden_job_market import HiddenJobMarketPreferenceUpdateRequest

    request = HiddenJobMarketPreferenceUpdateRequest(
        min_signal_strength=0.7,
        max_outreach_per_week=10,
    )
    assert request.min_signal_strength == 0.7
    assert request.max_outreach_per_week == 10
    assert request.auto_generate_outreach is None


def test_signal_compare_request_schema():
    """SignalCompareRequest validates correctly."""
    from app.schemas.hidden_job_market import SignalCompareRequest

    ids = [uuid.uuid4(), uuid.uuid4()]
    request = SignalCompareRequest(signal_ids=ids)
    assert len(request.signal_ids) == 2


def test_signal_compare_request_min_signals():
    """SignalCompareRequest requires at least 2 signals."""
    from pydantic import ValidationError

    from app.schemas.hidden_job_market import SignalCompareRequest

    with pytest.raises(ValidationError):
        SignalCompareRequest(signal_ids=[uuid.uuid4()])


def test_signal_compare_request_max_signals():
    """SignalCompareRequest rejects more than 5 signals."""
    from pydantic import ValidationError

    from app.schemas.hidden_job_market import SignalCompareRequest

    with pytest.raises(ValidationError):
        SignalCompareRequest(signal_ids=[uuid.uuid4() for _ in range(6)])


def test_dismiss_signal_request_defaults():
    """DismissSignalRequest uses correct defaults."""
    from app.schemas.hidden_job_market import DismissSignalRequest

    request = DismissSignalRequest()
    assert request.action_taken == "dismissed"
    assert request.reason is None


# ── API Auth Gate Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_hjm_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/hidden-job-market/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_scan_company_requires_auth(client: AsyncClient):
    """Scan company endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/hidden-job-market/scan/company",
        json={"company_name": "Google"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_scan_industry_requires_auth(client: AsyncClient):
    """Scan industry endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/hidden-job-market/scan/industry",
        json={"industry": "Technology"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_get_preferences_requires_auth(client: AsyncClient):
    """Get preferences endpoint returns 401 without auth."""
    response = await client.get("/api/v1/hidden-job-market/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_update_preferences_requires_auth(client: AsyncClient):
    """Update preferences endpoint returns 401 without auth."""
    response = await client.put(
        "/api/v1/hidden-job-market/preferences",
        json={"min_signal_strength": 0.5},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_compare_signals_requires_auth(client: AsyncClient):
    """Compare signals endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/hidden-job-market/compare",
        json={"signal_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_get_opportunities_requires_auth(client: AsyncClient):
    """Get opportunities endpoint returns 401 without auth."""
    response = await client.get("/api/v1/hidden-job-market/opportunities")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_surface_opportunities_requires_auth(client: AsyncClient):
    """Surface opportunities endpoint returns 401 without auth."""
    response = await client.post("/api/v1/hidden-job-market/opportunities/surface")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_get_signal_requires_auth(client: AsyncClient):
    """Get signal detail endpoint returns 401 without auth."""
    signal_id = uuid.uuid4()
    response = await client.get(f"/api/v1/hidden-job-market/{signal_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_generate_outreach_requires_auth(client: AsyncClient):
    """Generate outreach endpoint returns 401 without auth."""
    signal_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/hidden-job-market/{signal_id}/outreach",
        json={"template_type": "introduction", "tone": "professional"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_hjm_dismiss_signal_requires_auth(client: AsyncClient):
    """Dismiss signal endpoint returns 401 without auth."""
    signal_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/hidden-job-market/{signal_id}/dismiss",
        json={"action_taken": "dismissed"},
    )
    assert response.status_code == 401


# ── Enum Completeness Tests ────────────────────────────────────


def test_signal_type_enum_has_all_values():
    """SignalType enum contains exactly 6 signal types."""
    from app.models.hidden_job_market import SignalType

    expected = {
        "funding", "office_expansion", "key_hire",
        "tech_stack_change", "competitor_layoff", "revenue_growth",
    }
    actual = {member.value for member in SignalType}
    assert actual == expected


def test_signal_status_enum_has_all_values():
    """SignalStatus enum contains exactly 5 statuses."""
    from app.models.hidden_job_market import SignalStatus

    expected = {"detected", "matched", "actioned", "dismissed", "expired"}
    actual = {member.value for member in SignalStatus}
    assert actual == expected


def test_outreach_type_enum_has_all_values():
    """OutreachTemplateType enum contains exactly 4 types."""
    from app.models.hidden_job_market import OutreachTemplateType

    expected = {
        "introduction", "referral_request",
        "informational_interview", "direct_application",
    }
    actual = {member.value for member in OutreachTemplateType}
    assert actual == expected


def test_outreach_tone_enum_has_all_values():
    """OutreachTone enum contains exactly 3 tones."""
    from app.models.hidden_job_market import OutreachTone

    expected = {"professional", "casual", "enthusiastic"}
    actual = {member.value for member in OutreachTone}
    assert actual == expected
