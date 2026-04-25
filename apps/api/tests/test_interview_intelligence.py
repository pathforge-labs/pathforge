"""
PathForge - Interview Intelligence Engine Tests
=================================================
Test suite for:
    - Interview Intelligence model creation (5 entities)
    - Static analyzer helpers (confidence, culture alignment, STAR validation)
    - Clamping validators (company analysis, questions, STAR, negotiation)
    - Schema validation (request + response)
    - API endpoint auth gates (11 endpoints)
    - Enum completeness checks (4 enums)

~55 tests covering the full Interview Intelligence Engine pipeline.
"""


import uuid

import pytest
from httpx import AsyncClient

# ── Model Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interview_prep_model_creation(db_session):
    """Test InterviewPrep model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.interview_intelligence import InterviewPrep
    from app.models.user import User

    user = User(
        email="prep@interview.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Prep User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    prep = InterviewPrep(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="Acme Corp",
        target_role="Senior Engineer",
        status="completed",
        prep_depth="standard",
        confidence_score=0.72,
        culture_alignment_score=0.65,
        interview_format="3-round panel",
        company_brief="Acme is a leading tech company.",
    )
    db_session.add(prep)
    await db_session.flush()

    assert prep.id is not None
    assert prep.company_name == "Acme Corp"
    assert prep.confidence_score == 0.72
    assert prep.status == "completed"
    assert "AI-generated" in prep.data_source
    assert "not a guarantee" in prep.disclaimer


@pytest.mark.asyncio
async def test_company_insight_model_creation(db_session):
    """Test CompanyInsight model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.interview_intelligence import CompanyInsight, InterviewPrep
    from app.models.user import User

    user = User(
        email="insight@interview.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Insight User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    prep = InterviewPrep(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="TechCo",
        target_role="Backend Developer",
        confidence_score=0.60,
    )
    db_session.add(prep)
    await db_session.flush()

    insight = CompanyInsight(
        interview_prep_id=prep.id,
        insight_type="culture",
        title="Remote-first culture",
        content={"workstyle": "remote", "collaboration": "async"},
        summary="TechCo is a remote-first company with async collaboration.",
        source="glassdoor_reviews",
        confidence=0.70,
    )
    db_session.add(insight)
    await db_session.flush()

    assert insight.id is not None
    assert insight.insight_type == "culture"
    assert insight.title == "Remote-first culture"
    assert insight.confidence == 0.70


@pytest.mark.asyncio
async def test_interview_question_model_creation(db_session):
    """Test InterviewQuestion model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.interview_intelligence import InterviewPrep, InterviewQuestion
    from app.models.user import User

    user = User(
        email="question@interview.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Question User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    prep = InterviewPrep(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="BigTech",
        target_role="Staff Engineer",
        confidence_score=0.80,
    )
    db_session.add(prep)
    await db_session.flush()

    question = InterviewQuestion(
        interview_prep_id=prep.id,
        category="behavioral",
        question_text="Tell me about a time you led a complex project.",
        suggested_answer="Use STAR format...",
        answer_strategy="Focus on leadership and collaboration.",
        frequency_weight=0.85,
        difficulty_level="hard",
        order_index=0,
    )
    db_session.add(question)
    await db_session.flush()

    assert question.id is not None
    assert question.category == "behavioral"
    assert question.frequency_weight == 0.85
    assert question.order_index == 0


@pytest.mark.asyncio
async def test_star_example_model_creation(db_session):
    """Test STARExample model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.interview_intelligence import InterviewPrep, STARExample
    from app.models.user import User

    user = User(
        email="star@interview.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="STAR User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    prep = InterviewPrep(
        career_dna_id=career_dna.id,
        user_id=user.id,
        company_name="StartupXYZ",
        target_role="Full-Stack Developer",
        confidence_score=0.68,
    )
    db_session.add(prep)
    await db_session.flush()

    star = STARExample(
        interview_prep_id=prep.id,
        situation="Our e-commerce platform was experiencing 30% cart abandonment.",
        task="I was tasked with reducing abandonment by improving the checkout flow.",
        action="I redesigned the checkout to a single-page with progress indicators.",
        result="Cart abandonment dropped by 40%, increasing revenue by 25%.",
        career_dna_dimension="experience_blueprint",
        source_experience="E-commerce platform lead, 2024",
        relevance_score=0.82,
        order_index=0,
    )
    db_session.add(star)
    await db_session.flush()

    assert star.id is not None
    assert star.career_dna_dimension == "experience_blueprint"
    assert star.relevance_score == 0.82


@pytest.mark.asyncio
async def test_interview_preference_model_creation(db_session):
    """Test InterviewPreference model can be created."""
    from app.core.security import hash_password
    from app.models.career_dna import CareerDNA
    from app.models.interview_intelligence import InterviewPreference
    from app.models.user import User

    user = User(
        email="pref@interview.test",
        hashed_password=hash_password("TestPass123!"),
        full_name="Preference User",
    )
    db_session.add(user)
    await db_session.flush()

    career_dna = CareerDNA(user_id=user.id)
    db_session.add(career_dna)
    await db_session.flush()

    pref = InterviewPreference(
        career_dna_id=career_dna.id,
        user_id=user.id,
        default_prep_depth="comprehensive",
        max_saved_preps=30,
        include_salary_negotiation=True,
        notification_enabled=False,
    )
    db_session.add(pref)
    await db_session.flush()

    assert pref.id is not None
    assert pref.default_prep_depth == "comprehensive"
    assert pref.max_saved_preps == 30
    assert pref.include_salary_negotiation is True
    assert pref.notification_enabled is False


# ── Static Helper Tests ────────────────────────────────────────


def test_interview_confidence_full_match():
    """100% Career DNA completeness with high LLM confidence near ceiling."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    confidence = InterviewIntelligenceAnalyzer.compute_interview_confidence(
        llm_confidence=0.85,
        data_quality_factor=1.0,
        career_dna_completeness=1.0,
    )
    assert confidence <= 0.85


def test_interview_confidence_caps_at_085():
    """Even perfect inputs cannot exceed 0.85."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    confidence = InterviewIntelligenceAnalyzer.compute_interview_confidence(
        llm_confidence=1.0,
        data_quality_factor=1.0,
        career_dna_completeness=1.0,
    )
    assert confidence <= 0.85


def test_interview_confidence_zero_inputs():
    """Zero inputs produce zero confidence."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    confidence = InterviewIntelligenceAnalyzer.compute_interview_confidence(
        llm_confidence=0.0,
        data_quality_factor=0.0,
        career_dna_completeness=0.0,
    )
    assert confidence == 0.0


def test_interview_confidence_partial():
    """Partial data produces moderate confidence."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    confidence = InterviewIntelligenceAnalyzer.compute_interview_confidence(
        llm_confidence=0.6,
        data_quality_factor=0.5,
        career_dna_completeness=0.5,
    )
    assert 0.15 <= confidence <= 0.85


def test_culture_alignment_perfect():
    """Perfect values overlap + LLM alignment = max alignment."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    alignment = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
        llm_alignment=1.0,
        values_overlap_count=5,
        total_values=5,
    )
    assert alignment == 1.0


def test_culture_alignment_no_overlap():
    """Zero overlap reduces alignment score."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    alignment = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
        llm_alignment=0.8,
        values_overlap_count=0,
        total_values=5,
    )
    assert alignment < 0.6


def test_culture_alignment_capped_at_1():
    """Alignment never exceeds 1.0."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    alignment = InterviewIntelligenceAnalyzer.calculate_culture_alignment(
        llm_alignment=1.5,
        values_overlap_count=10,
        total_values=5,
    )
    assert alignment <= 1.0


def test_validate_star_structure_complete():
    """Complete STAR structure validates successfully."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    star = {
        "situation": "We had a production outage.",
        "task": "I was responsible for recovery.",
        "action": "I identified the root cause and deployed a fix.",
        "result": "Downtime reduced from 4 hours to 30 minutes.",
    }
    assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is True


def test_validate_star_structure_missing_field():
    """Missing STAR field fails validation."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    star = {
        "situation": "We had a production outage.",
        "task": "I was responsible for recovery.",
        "action": "I identified the root cause.",
        # Missing 'result'
    }
    assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is False


def test_validate_star_structure_empty_field():
    """Empty STAR field fails validation."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    star = {
        "situation": "We had a production outage.",
        "task": "",
        "action": "I identified the root cause.",
        "result": "Fixed it.",
    }
    assert InterviewIntelligenceAnalyzer.validate_star_structure(star) is False


def test_merge_salary_data_with_estimates():
    """Salary data formats correctly with estimates."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    estimates = [
        {
            "median_salary": 85000,
            "range_min": 70000,
            "range_max": 100000,
            "data_source": "salary_intelligence",
        }
    ]
    result = InterviewIntelligenceAnalyzer.merge_salary_data(
        salary_estimates=estimates,
        target_role="Senior Engineer",
        currency="EUR",
    )
    assert "Senior Engineer" in result
    assert "85000" in result
    assert "salary_intelligence" in result


def test_merge_salary_data_empty():
    """Empty estimates produce fallback message."""
    from app.ai.interview_intelligence_analyzer import (
        InterviewIntelligenceAnalyzer,
    )

    result = InterviewIntelligenceAnalyzer.merge_salary_data(
        salary_estimates=[],
        target_role="DevOps Engineer",
    )
    assert "No salary intelligence data" in result
    assert "DevOps Engineer" in result


# ── Clamping Validator Tests ───────────────────────────────────


def test_clamp_company_analysis_caps_confidence():
    """Confidence above 0.85 is clamped down."""
    from app.ai.interview_intelligence_analyzer import _clamp_company_analysis

    data = {
        "confidence_score": 0.95,
        "culture_alignment_score": 0.70,
        "insights": [],
    }
    _clamp_company_analysis(data)
    assert data["confidence_score"] <= 0.85


def test_clamp_company_analysis_caps_alignment():
    """Culture alignment above 1.0 is clamped to 1.0."""
    from app.ai.interview_intelligence_analyzer import _clamp_company_analysis

    data = {
        "confidence_score": 0.5,
        "culture_alignment_score": 1.5,
        "insights": [],
    }
    _clamp_company_analysis(data)
    assert data["culture_alignment_score"] == 1.0


def test_clamp_company_analysis_validates_insight_type():
    """Invalid insight type defaults to 'culture'."""
    from app.ai.interview_intelligence_analyzer import _clamp_company_analysis

    data = {
        "confidence_score": 0.5,
        "culture_alignment_score": 0.5,
        "insights": [
            {"insight_type": "invalid_type", "title": "Test", "confidence": 0.5}
        ],
    }
    _clamp_company_analysis(data)
    assert data["insights"][0]["insight_type"] == "culture"


def test_clamp_company_analysis_ensures_insight_title():
    """Missing insight title defaults to 'Untitled insight'."""
    from app.ai.interview_intelligence_analyzer import _clamp_company_analysis

    data = {
        "confidence_score": 0.5,
        "culture_alignment_score": 0.5,
        "insights": [
            {"insight_type": "format", "confidence": 0.5}
        ],
    }
    _clamp_company_analysis(data)
    assert data["insights"][0]["title"] == "Untitled insight"


def test_clamp_questions_validates_category():
    """Invalid question category defaults to 'behavioral'."""
    from app.ai.interview_intelligence_analyzer import _clamp_questions

    questions = [
        {
            "category": "invalid_category",
            "question_text": "Test question?",
            "frequency_weight": 0.5,
            "difficulty_level": "medium",
        }
    ]
    _clamp_questions(questions)
    assert questions[0]["category"] == "behavioral"


def test_clamp_questions_ensures_text():
    """Missing question text defaults to fallback."""
    from app.ai.interview_intelligence_analyzer import _clamp_questions

    questions = [
        {
            "category": "technical",
            "frequency_weight": 0.5,
        }
    ]
    _clamp_questions(questions)
    assert questions[0]["question_text"] == "No question generated"


def test_clamp_questions_caps_frequency():
    """Frequency weight above 1.0 is clamped to 1.0."""
    from app.ai.interview_intelligence_analyzer import _clamp_questions

    questions = [
        {
            "category": "behavioral",
            "question_text": "Test?",
            "frequency_weight": 1.5,
            "difficulty_level": "easy",
        }
    ]
    _clamp_questions(questions)
    assert questions[0]["frequency_weight"] == 1.0


def test_clamp_questions_validates_difficulty():
    """Invalid difficulty defaults to 'medium'."""
    from app.ai.interview_intelligence_analyzer import _clamp_questions

    questions = [
        {
            "category": "behavioral",
            "question_text": "Test?",
            "frequency_weight": 0.5,
            "difficulty_level": "impossible",
        }
    ]
    _clamp_questions(questions)
    assert questions[0]["difficulty_level"] == "medium"


def test_clamp_star_examples_ensures_components():
    """Missing STAR components get fallback text."""
    from app.ai.interview_intelligence_analyzer import _clamp_star_examples

    examples = [
        {
            "relevance_score": 0.8,
        }
    ]
    _clamp_star_examples(examples)
    assert examples[0]["situation"] == "[Situation not generated]"
    assert examples[0]["task"] == "[Task not generated]"
    assert examples[0]["action"] == "[Action not generated]"
    assert examples[0]["result"] == "[Result not generated]"


def test_clamp_star_examples_caps_relevance():
    """Relevance above 1.0 is clamped to 1.0."""
    from app.ai.interview_intelligence_analyzer import _clamp_star_examples

    examples = [
        {
            "situation": "S",
            "task": "T",
            "action": "A",
            "result": "R",
            "relevance_score": 1.5,
        }
    ]
    _clamp_star_examples(examples)
    assert examples[0]["relevance_score"] == 1.0


def test_clamp_negotiation_script_ensures_scripts():
    """Missing script fields get fallback text."""
    from app.ai.interview_intelligence_analyzer import _clamp_negotiation_script

    data = {
        "key_arguments": [],
        "skill_premiums": {},
    }
    _clamp_negotiation_script(data)
    assert "[Opening Script" in data["opening_script"]
    assert "[Counteroffer Script" in data["counteroffer_script"]
    assert "[Fallback Script" in data["fallback_script"]


def test_clamp_negotiation_script_ensures_key_arguments_list():
    """Non-list key_arguments replaced with empty list."""
    from app.ai.interview_intelligence_analyzer import _clamp_negotiation_script

    data = {
        "opening_script": "Hello",
        "counteroffer_script": "Counter",
        "fallback_script": "Fallback",
        "key_arguments": "not a list",
        "skill_premiums": {},
    }
    _clamp_negotiation_script(data)
    assert data["key_arguments"] == []


def test_clamp_negotiation_script_ensures_skill_premiums_dict():
    """Non-dict skill_premiums replaced with empty dict."""
    from app.ai.interview_intelligence_analyzer import _clamp_negotiation_script

    data = {
        "opening_script": "Hello",
        "counteroffer_script": "Counter",
        "fallback_script": "Fallback",
        "key_arguments": [],
        "skill_premiums": "not a dict",
    }
    _clamp_negotiation_script(data)
    assert data["skill_premiums"] == {}


def test_clamp_negotiation_script_salary_values():
    """Invalid salary values are set to None."""
    from app.ai.interview_intelligence_analyzer import _clamp_negotiation_script

    data = {
        "opening_script": "Hello",
        "counteroffer_script": "Counter",
        "fallback_script": "Fallback",
        "key_arguments": [],
        "skill_premiums": {},
        "salary_range_min": "not_a_number",
        "salary_range_max": 100000.0,
        "salary_range_median": -500.0,
    }
    _clamp_negotiation_script(data)
    assert data["salary_range_min"] is None
    assert data["salary_range_max"] == 100000.0
    assert data["salary_range_median"] == 0.0  # Negative clamped to 0


# ── Schema Validation Tests ────────────────────────────────────


def test_interview_prep_request_schema():
    """InterviewPrepRequest validates correctly."""
    from app.schemas.interview_intelligence import InterviewPrepRequest

    request = InterviewPrepRequest(
        company_name="Google",
        target_role="Senior SWE",
        prep_depth="comprehensive",
    )
    assert request.company_name == "Google"
    assert request.target_role == "Senior SWE"
    assert request.prep_depth == "comprehensive"


def test_interview_prep_request_defaults():
    """InterviewPrepRequest uses default prep_depth of None."""
    from app.schemas.interview_intelligence import InterviewPrepRequest

    request = InterviewPrepRequest(
        company_name="Meta",
        target_role="Product Manager",
    )
    assert request.prep_depth is None


def test_interview_prep_request_rejects_invalid_depth():
    """InterviewPrepRequest rejects invalid prep_depth values."""
    from pydantic import ValidationError

    from app.schemas.interview_intelligence import InterviewPrepRequest

    with pytest.raises(ValidationError):
        InterviewPrepRequest(
            company_name="Meta",
            target_role="Product Manager",
            prep_depth="extreme",
        )

def test_generate_questions_request_schema():
    """GenerateQuestionsRequest validates correctly."""
    from app.schemas.interview_intelligence import GenerateQuestionsRequest

    request = GenerateQuestionsRequest(
        category_filter="behavioral",
        max_questions=10,
    )
    assert request.category_filter == "behavioral"
    assert request.max_questions == 10


def test_generate_questions_request_defaults():
    """GenerateQuestionsRequest uses defaults."""
    from app.schemas.interview_intelligence import GenerateQuestionsRequest

    request = GenerateQuestionsRequest()
    assert request.category_filter is None
    assert request.max_questions == 15


def test_compare_request_schema():
    """InterviewPrepCompareRequest validates correctly."""
    from app.schemas.interview_intelligence import InterviewPrepCompareRequest

    ids = [uuid.uuid4(), uuid.uuid4()]
    request = InterviewPrepCompareRequest(prep_ids=ids)
    assert len(request.prep_ids) == 2


def test_compare_request_min_preps():
    """InterviewPrepCompareRequest requires at least 2 preps."""
    from pydantic import ValidationError

    from app.schemas.interview_intelligence import InterviewPrepCompareRequest

    with pytest.raises(ValidationError):
        InterviewPrepCompareRequest(prep_ids=[uuid.uuid4()])


def test_compare_request_max_preps():
    """InterviewPrepCompareRequest rejects more than 5 preps."""
    from pydantic import ValidationError

    from app.schemas.interview_intelligence import InterviewPrepCompareRequest

    with pytest.raises(ValidationError):
        InterviewPrepCompareRequest(
            prep_ids=[uuid.uuid4() for _ in range(6)]
        )


def test_preference_update_schema():
    """InterviewPreferenceUpdateRequest handles partial updates."""
    from app.schemas.interview_intelligence import (
        InterviewPreferenceUpdateRequest,
    )

    request = InterviewPreferenceUpdateRequest(
        max_saved_preps=20,
    )
    assert request.max_saved_preps == 20
    assert request.default_prep_depth is None


def test_negotiation_script_request_schema():
    """GenerateNegotiationScriptRequest validates correctly."""
    from app.schemas.interview_intelligence import (
        GenerateNegotiationScriptRequest,
    )

    request = GenerateNegotiationScriptRequest(
        target_salary=95000.0,
        currency="EUR",
    )
    assert request.target_salary == 95000.0
    assert request.currency == "EUR"


def test_negotiation_script_request_defaults():
    """GenerateNegotiationScriptRequest uses defaults."""
    from app.schemas.interview_intelligence import (
        GenerateNegotiationScriptRequest,
    )

    request = GenerateNegotiationScriptRequest()
    assert request.target_salary is None
    assert request.currency == "EUR"


# ── API Auth Gate Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_interview_dashboard_requires_auth(client: AsyncClient):
    """Dashboard endpoint returns 401 without auth."""
    response = await client.get("/api/v1/interview-intelligence/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_prep_requires_auth(client: AsyncClient):
    """Create prep endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/interview-intelligence/prep",
        json={"company_name": "Google", "target_role": "SWE"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_compare_preps_requires_auth(client: AsyncClient):
    """Compare preps endpoint returns 401 without auth."""
    response = await client.post(
        "/api/v1/interview-intelligence/compare",
        json={"prep_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_preferences_requires_auth(client: AsyncClient):
    """GET preferences endpoint returns 401 without auth."""
    response = await client.get("/api/v1/interview-intelligence/preferences")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_preferences_requires_auth(client: AsyncClient):
    """PUT preferences endpoint returns 401 without auth."""
    response = await client.put(
        "/api/v1/interview-intelligence/preferences",
        json={"max_saved_preps": 30},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_prep_requires_auth(client: AsyncClient):
    """GET prep detail endpoint returns 401 without auth."""
    response = await client.get(
        f"/api/v1/interview-intelligence/{uuid.uuid4()}",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_prep_requires_auth(client: AsyncClient):
    """DELETE prep endpoint returns 401 without auth."""
    response = await client.delete(
        f"/api/v1/interview-intelligence/{uuid.uuid4()}",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_questions_requires_auth(client: AsyncClient):
    """Generate questions endpoint returns 401 without auth."""
    response = await client.post(
        f"/api/v1/interview-intelligence/{uuid.uuid4()}/questions",
        json={},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_star_examples_requires_auth(client: AsyncClient):
    """Generate STAR examples endpoint returns 401 without auth."""
    response = await client.post(
        f"/api/v1/interview-intelligence/{uuid.uuid4()}/star-examples",
        json={},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_negotiation_requires_auth(client: AsyncClient):
    """Generate negotiation script endpoint returns 401 without auth."""
    response = await client.post(
        f"/api/v1/interview-intelligence/{uuid.uuid4()}/negotiation-script",
        json={},
    )
    assert response.status_code == 401


# ── Enum Tests ─────────────────────────────────────────────────


def test_prep_status_enum_values():
    """PrepStatus enum has 4 expected values."""
    from app.models.interview_intelligence import PrepStatus

    expected = {"draft", "analyzing", "completed", "failed"}
    actual = {member.value for member in PrepStatus}
    assert actual == expected


def test_insight_type_enum_values():
    """InsightType enum has 5 expected values."""
    from app.models.interview_intelligence import InsightType

    expected = {"format", "culture", "salary_band", "process", "values"}
    actual = {member.value for member in InsightType}
    assert actual == expected


def test_question_category_enum_values():
    """QuestionCategory enum has 5 expected values."""
    from app.models.interview_intelligence import QuestionCategory

    expected = {"behavioral", "technical", "situational", "culture_fit", "salary"}
    actual = {member.value for member in QuestionCategory}
    assert actual == expected


def test_prep_depth_enum_values():
    """PrepDepth enum has 3 expected values."""
    from app.models.interview_intelligence import PrepDepth

    expected = {"quick", "standard", "comprehensive"}
    actual = {member.value for member in PrepDepth}
    assert actual == expected
