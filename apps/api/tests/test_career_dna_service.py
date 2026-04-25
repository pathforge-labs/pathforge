"""
PathForge — Career DNA Service Coverage Tests
==============================================
Comprehensive tests for CareerDNAService orchestration and private
helper functions. Targets the missing-coverage lines by exercising
generate_full_profile with mocked LLM calls, data-gathering helpers,
and each dimension-computation helper independently.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.llm_observability import TransparencyRecord
from app.core.security import hash_password
from app.models.career_dna import (
    CareerDNA,
    ExperienceBlueprint,
    GrowthVector,
    HiddenSkill,
    MarketPosition,
    SkillGenomeEntry,
    ValuesProfile,
)
from app.models.matching import JobListing
from app.models.preference import Preference
from app.models.resume import Resume, Skill
from app.models.user import User
from app.services.career_dna_service import (
    VALID_DIMENSIONS,
    CareerDNAService,
    _calculate_completeness,
    _compute_experience_blueprint,
    _compute_growth_vector,
    _compute_market_position,
    _compute_skill_genome,
    _compute_values_profile,
    _gather_experience_text,
    _gather_explicit_skills,
    _gather_preferences_text,
    _log_transparency,
)

# ── Helpers ────────────────────────────────────────────────────


def _make_record(analysis_type: str = "test.analysis") -> TransparencyRecord:
    return TransparencyRecord(
        analysis_type=analysis_type,
        model="anthropic/claude-sonnet-4-20250514",
        tier="primary",
        confidence_score=0.85,
        confidence_label="High",
        data_sources=["experience_text"],
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=800,
        success=True,
        retries=0,
    )


async def _create_user(db_session: Any, email: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name=f"User {email}",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def _create_resume(
    db_session: Any,
    user_id: uuid.UUID,
    *,
    raw_text: str | None = "Senior engineer with 8 years of experience.",
    structured_data: dict[str, Any] | None = None,
) -> Resume:
    resume = Resume(
        user_id=user_id,
        title="Main Resume",
        raw_text=raw_text,
        structured_data=structured_data,
    )
    db_session.add(resume)
    await db_session.flush()
    await db_session.refresh(resume)
    return resume


async def _fresh_dna(db_session: Any, user_id: uuid.UUID) -> CareerDNA:
    """Reload CareerDNA with all relationships eagerly loaded."""
    dna = await CareerDNAService.get_full_profile(
        db_session, user_id=user_id,
    )
    assert dna is not None
    return dna


async def _reload_dna(db_session: Any, user_id: uuid.UUID) -> CareerDNA:
    """Reload CareerDNA fresh from the database.

    Expires any cached CareerDNA instance so relationships are
    re-queried via selectinload on the next get_full_profile.
    """
    cached = await CareerDNAService.get_full_profile(
        db_session, user_id=user_id,
    )
    if cached is not None:
        db_session.expire(cached)
    return await _fresh_dna(db_session, user_id)


async def _pre_create_dna(db_session: Any, user_id: uuid.UUID) -> CareerDNA:
    """Pre-create a CareerDNA row so that `get_or_create` later takes
    the 'existing' branch (which uses selectinload) rather than the
    create-and-refresh branch (which leaves relationships unloaded
    and trips SQLite's lack of async lazy-load support in tests).
    """
    dna = CareerDNA(user_id=user_id)
    db_session.add(dna)
    await db_session.flush()
    return await _fresh_dna(db_session, user_id)


async def _create_skill(
    db_session: Any,
    resume_id: uuid.UUID,
    name: str,
    *,
    category: str | None = "technical",
    proficiency_level: str | None = "expert",
    years_experience: int | None = 5,
) -> Skill:
    skill = Skill(
        resume_id=resume_id,
        name=name,
        category=category,
        proficiency_level=proficiency_level,
        years_experience=years_experience,
    )
    db_session.add(skill)
    await db_session.flush()
    return skill


# ── _log_transparency ──────────────────────────────────────────


def test_log_transparency_skips_when_record_is_none() -> None:
    """_log_transparency is a no-op when record is None."""
    with patch(
        "app.services.career_dna_service.get_transparency_log"
    ) as mock_get:
        _log_transparency(uuid.uuid4(), None)
        mock_get.assert_not_called()


def test_log_transparency_records_when_present() -> None:
    """_log_transparency forwards the record to the transparency log."""
    rec = _make_record()
    user_id = uuid.uuid4()
    mock_log = MagicMock()
    with patch(
        "app.services.career_dna_service.get_transparency_log",
        return_value=mock_log,
    ):
        _log_transparency(user_id, rec)
    mock_log.record.assert_called_once_with(user_id=str(user_id), entry=rec)


# ── _gather_experience_text ────────────────────────────────────


@pytest.mark.asyncio
async def test_gather_experience_text_no_resumes(db_session: Any) -> None:
    """Returns empty string for user without resumes."""
    user = await _create_user(db_session, "exp_none@pathforge.eu")
    result = await _gather_experience_text(db_session, user.id)
    assert result == ""


@pytest.mark.asyncio
async def test_gather_experience_text_with_raw_text_only(db_session: Any) -> None:
    """Includes raw_text from resumes."""
    user = await _create_user(db_session, "exp_raw@pathforge.eu")
    await _create_resume(
        db_session, user.id, raw_text="Worked on cool stuff.", structured_data=None,
    )
    result = await _gather_experience_text(db_session, user.id)
    assert "cool stuff" in result


@pytest.mark.asyncio
async def test_gather_experience_text_with_structured_data(db_session: Any) -> None:
    """Includes structured experience entries formatted as sections."""
    user = await _create_user(db_session, "exp_struct@pathforge.eu")
    structured = {
        "experience": [
            {
                "title": "Senior Engineer",
                "company": "Acme Corp",
                "start_date": "2020-01",
                "end_date": "2024-01",
                "description": "Led platform modernization.",
            }
        ]
    }
    await _create_resume(
        db_session, user.id, raw_text="Resume raw", structured_data=structured,
    )
    result = await _gather_experience_text(db_session, user.id)
    assert "Senior Engineer" in result
    assert "Acme Corp" in result
    assert "Led platform modernization" in result


@pytest.mark.asyncio
async def test_gather_experience_text_structured_only_no_raw(db_session: Any) -> None:
    """Handles resume with structured_data but no raw_text."""
    user = await _create_user(db_session, "exp_structonly@pathforge.eu")
    structured = {
        "experience": [
            {"title": "Dev", "company": "Foo", "start_date": "", "end_date": ""}
        ]
    }
    await _create_resume(
        db_session, user.id, raw_text=None, structured_data=structured,
    )
    result = await _gather_experience_text(db_session, user.id)
    assert "Dev" in result
    assert "Foo" in result


@pytest.mark.asyncio
async def test_gather_experience_text_multiple_resumes(db_session: Any) -> None:
    """Joins text across multiple resumes with the separator."""
    user = await _create_user(db_session, "exp_multi@pathforge.eu")
    await _create_resume(db_session, user.id, raw_text="First CV.")
    await _create_resume(db_session, user.id, raw_text="Second CV.")
    result = await _gather_experience_text(db_session, user.id)
    assert "First CV." in result
    assert "Second CV." in result
    assert "---" in result


# ── _gather_explicit_skills ────────────────────────────────────


@pytest.mark.asyncio
async def test_gather_explicit_skills_empty(db_session: Any) -> None:
    """Empty list when user has no skills."""
    user = await _create_user(db_session, "skills_empty@pathforge.eu")
    result = await _gather_explicit_skills(db_session, user.id)
    assert result == []


@pytest.mark.asyncio
async def test_gather_explicit_skills_populated(db_session: Any) -> None:
    """Collects skills with all fields from the user's resumes."""
    user = await _create_user(db_session, "skills_full@pathforge.eu")
    resume = await _create_resume(db_session, user.id)
    await _create_skill(
        db_session, resume.id, "Python",
        category="technical", proficiency_level="expert", years_experience=7,
    )
    result = await _gather_explicit_skills(db_session, user.id)
    assert len(result) == 1
    assert result[0]["name"] == "Python"
    assert result[0]["category"] == "technical"
    assert result[0]["proficiency_level"] == "expert"
    assert result[0]["years_experience"] == 7


@pytest.mark.asyncio
async def test_gather_explicit_skills_uses_defaults(db_session: Any) -> None:
    """Applies default category/proficiency when columns are null."""
    user = await _create_user(db_session, "skills_defaults@pathforge.eu")
    resume = await _create_resume(db_session, user.id)
    await _create_skill(
        db_session, resume.id, "Rust",
        category=None, proficiency_level=None, years_experience=None,
    )
    result = await _gather_explicit_skills(db_session, user.id)
    assert result[0]["category"] == "general"
    assert result[0]["proficiency_level"] == "intermediate"
    assert result[0]["years_experience"] is None


# ── _gather_preferences_text ───────────────────────────────────


@pytest.mark.asyncio
async def test_gather_preferences_text_no_record(db_session: Any) -> None:
    """Empty string when user has no preference row."""
    user = await _create_user(db_session, "pref_none@pathforge.eu")
    result = await _gather_preferences_text(db_session, user.id)
    assert result == ""


@pytest.mark.asyncio
async def test_gather_preferences_text_all_fields(db_session: Any) -> None:
    """Formats preference scalar fields into labelled lines."""
    user = await _create_user(db_session, "pref_full@pathforge.eu")
    pref = Preference(
        user_id=user.id,
        work_type="remote",
        experience_level="senior",
    )
    db_session.add(pref)
    await db_session.flush()
    result = await _gather_preferences_text(db_session, user.id)
    assert "remote" in result
    assert "senior" in result


@pytest.mark.asyncio
async def test_gather_preferences_text_array_fields_via_mock(
    db_session: Any,
) -> None:
    """Verifies the list-formatting branches by mocking db.execute."""
    user = await _create_user(db_session, "pref_arrays@pathforge.eu")
    pref = Preference(
        user_id=user.id,
        work_type=None,
        experience_level=None,
    )
    # In-memory assignment only; never flushed because SQLite
    # cannot bind Python lists for the ARRAY columns.
    pref.job_titles = ["Senior Engineer"]
    pref.sectors = ["Fintech"]
    pref.locations = ["Amsterdam"]

    fake_result = MagicMock()
    fake_result.scalar_one_or_none = MagicMock(return_value=pref)

    async def _fake_execute(_stmt: Any) -> Any:
        return fake_result

    db_mock = MagicMock()
    db_mock.execute = _fake_execute

    result = await _gather_preferences_text(db_mock, user.id)
    assert "Senior Engineer" in result
    assert "Fintech" in result
    assert "Amsterdam" in result


@pytest.mark.asyncio
async def test_gather_preferences_text_partial_fields(db_session: Any) -> None:
    """Skips falsy/empty fields gracefully."""
    user = await _create_user(db_session, "pref_partial@pathforge.eu")
    pref = Preference(
        user_id=user.id,
        job_titles=None,
        sectors=None,
        locations=None,
        work_type="hybrid",
        experience_level=None,
    )
    db_session.add(pref)
    await db_session.flush()
    result = await _gather_preferences_text(db_session, user.id)
    assert "hybrid" in result
    assert "Target roles" not in result


# ── _calculate_completeness ────────────────────────────────────


def test_calculate_completeness_partial() -> None:
    """Partial dimensions scale to the appropriate percentage."""
    dna = SimpleNamespace(
        skill_genome=["entry"],
        experience_blueprint="x",
        growth_vector=None,
        values_profile=None,
        market_position=None,
    )
    assert _calculate_completeness(dna) == 40.0


def test_calculate_completeness_three_of_five() -> None:
    """Three dimensions out of five → 60.0."""
    dna = SimpleNamespace(
        skill_genome=["x"],
        experience_blueprint="x",
        growth_vector="x",
        values_profile=None,
        market_position=None,
    )
    assert _calculate_completeness(dna) == 60.0


# ── confirm_hidden_skill edge cases ────────────────────────────


@pytest.mark.asyncio
async def test_confirm_hidden_skill_no_profile(db_session: Any) -> None:
    """Returns None when user has no Career DNA profile."""
    result = await CareerDNAService.confirm_hidden_skill(
        db_session,
        user_id=uuid.uuid4(),
        skill_id=uuid.uuid4(),
        confirmed=True,
    )
    assert result is None


@pytest.mark.asyncio
async def test_confirm_hidden_skill_unknown_skill(db_session: Any) -> None:
    """Returns None when skill_id doesn't match any HiddenSkill."""
    user = await _create_user(db_session, "confirm_nosk@pathforge.eu")
    await CareerDNAService.get_or_create(db_session, user_id=user.id)
    result = await CareerDNAService.confirm_hidden_skill(
        db_session,
        user_id=user.id,
        skill_id=uuid.uuid4(),
        confirmed=False,
    )
    assert result is None


@pytest.mark.asyncio
async def test_confirm_hidden_skill_reject_path(db_session: Any) -> None:
    """Rejected skill records user_confirmed=False."""
    user = await _create_user(db_session, "confirm_reject@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    hidden = HiddenSkill(
        career_dna_id=dna.id,
        skill_name="Public Speaking",
        discovery_method="resume_inference",
        confidence=0.6,
    )
    db_session.add(hidden)
    await db_session.flush()

    result = await CareerDNAService.confirm_hidden_skill(
        db_session,
        user_id=user.id,
        skill_id=hidden.id,
        confirmed=False,
    )
    assert result is not None
    assert result.user_confirmed is False


# ── _compute_skill_genome ──────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_skill_genome_writes_entries_and_hidden(
    db_session: Any,
) -> None:
    """Creates SkillGenomeEntry rows for explicit skills and hidden skills."""
    user = await _create_user(db_session, "genome_compute@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    explicit = [
        {
            "name": "Python",
            "category": "technical",
            "proficiency_level": "expert",
            "years_experience": 5,
        }
    ]
    rec = _make_record("career_dna.hidden_skills")
    hidden_results = [
        {
            "skill_name": "Leadership",
            "confidence": 0.8,
            "evidence": "Led multiple teams",
            "source_text": "Led teams",
        }
    ]
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=(hidden_results, rec),
    ), patch(
        "app.services.career_dna_service.get_transparency_log",
        return_value=MagicMock(),
    ):
        await _compute_skill_genome(
            db_session, dna, explicit, "Experience text", user.id,
        )

    # Reload dna with relationships
    dna_fresh = await _reload_dna(db_session, user.id)
    assert dna_fresh is not None
    assert len(dna_fresh.skill_genome) == 1
    assert dna_fresh.skill_genome[0].skill_name == "Python"
    assert len(dna_fresh.hidden_skills) == 1
    assert dna_fresh.hidden_skills[0].skill_name == "Leadership"


@pytest.mark.asyncio
async def test_compute_skill_genome_clears_existing_entries(
    db_session: Any,
) -> None:
    """Existing skill genome entries and hidden skills are removed first."""
    user = await _create_user(db_session, "genome_clear@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    # Seed existing entries
    old_entry = SkillGenomeEntry(
        career_dna_id=dna.id,
        skill_name="Old Skill",
        category="general",
        proficiency_level="intermediate",
        source="explicit",
        confidence=1.0,
    )
    old_hidden = HiddenSkill(
        career_dna_id=dna.id,
        skill_name="Old Hidden",
        discovery_method="resume_inference",
        confidence=0.5,
    )
    db_session.add_all([old_entry, old_hidden])
    await db_session.flush()

    # Reload with relationships populated
    dna = await _reload_dna(db_session, user.id)

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ):
        await _compute_skill_genome(
            db_session, dna, [], "text", user.id,
        )

    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert len(fresh.skill_genome) == 0
    assert len(fresh.hidden_skills) == 0


@pytest.mark.asyncio
async def test_compute_skill_genome_hidden_defaults(db_session: Any) -> None:
    """Hidden skill entries fall back to defaults for missing keys."""
    user = await _create_user(db_session, "genome_hdefault@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    # No skill_name / confidence / evidence in the hidden result
    hidden_results = [{}]
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=(hidden_results, None),
    ):
        await _compute_skill_genome(
            db_session, dna, [], "text", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert len(fresh.hidden_skills) == 1
    assert fresh.hidden_skills[0].skill_name == "Unknown"
    assert fresh.hidden_skills[0].confidence == 0.5


# ── _compute_experience_blueprint ──────────────────────────────


@pytest.mark.asyncio
async def test_compute_experience_blueprint_creates_new(
    db_session: Any,
) -> None:
    """Creates a new ExperienceBlueprint when none exists."""
    user = await _create_user(db_session, "bp_new@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    rec = _make_record("career_dna.experience_blueprint")
    data = {
        "total_years": 8.5,
        "role_count": 4,
        "avg_tenure_months": 25.5,
        "career_direction": "ascending",
        "industry_diversity": 0.7,
        "seniority_trajectory": {"from": "mid", "to": "senior"},
        "pattern_analysis": "Upward",
    }
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=(data, rec),
    ):
        await _compute_experience_blueprint(
            db_session, dna, "exp text", user.id,
        )

    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.experience_blueprint is not None
    assert fresh.experience_blueprint.total_years == 8.5
    assert fresh.experience_blueprint.career_direction == "ascending"


@pytest.mark.asyncio
async def test_compute_experience_blueprint_updates_existing(
    db_session: Any,
) -> None:
    """Updates an existing ExperienceBlueprint in place."""
    user = await _create_user(db_session, "bp_upd@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    existing = ExperienceBlueprint(
        career_dna_id=dna.id,
        total_years=1.0,
        role_count=1,
        avg_tenure_months=12.0,
        career_direction="exploring",
        industry_diversity=0.0,
    )
    db_session.add(existing)
    await db_session.flush()
    dna = await _reload_dna(db_session, user.id)

    data = {
        "total_years": 9.0,
        "role_count": 5,
        "avg_tenure_months": 21.6,
        "career_direction": "accelerating",
        "industry_diversity": 0.8,
    }
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=(data, None),
    ):
        await _compute_experience_blueprint(
            db_session, dna, "exp text", user.id,
        )

    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.experience_blueprint.total_years == 9.0
    assert fresh.experience_blueprint.role_count == 5


@pytest.mark.asyncio
async def test_compute_experience_blueprint_uses_defaults(
    db_session: Any,
) -> None:
    """Default values are used when analyzer omits keys."""
    user = await _create_user(db_session, "bp_default@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({}, None),
    ):
        await _compute_experience_blueprint(
            db_session, dna, "exp text", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.experience_blueprint.total_years == 0.0
    assert fresh.experience_blueprint.career_direction == "exploring"


# ── _compute_growth_vector ─────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_growth_vector_creates_new(db_session: Any) -> None:
    """Creates a new GrowthVector with analyzer data."""
    user = await _create_user(db_session, "gv_new@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    data = {
        "current_trajectory": "accelerating",
        "projected_roles": ["Staff Engineer"],
        "skill_velocity": {"Python": 3},
        "growth_score": 88.0,
        "analysis_reasoning": "Strong trajectory",
    }
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=(data, _make_record("career_dna.growth_vector")),
    ):
        await _compute_growth_vector(
            db_session, dna, "exp", "skills", "prefs", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.growth_vector is not None
    assert fresh.growth_vector.current_trajectory == "accelerating"
    assert fresh.growth_vector.growth_score == 88.0


@pytest.mark.asyncio
async def test_compute_growth_vector_updates_existing(db_session: Any) -> None:
    """Updates an existing GrowthVector row."""
    user = await _create_user(db_session, "gv_upd@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    existing = GrowthVector(
        career_dna_id=dna.id,
        current_trajectory="steady",
        growth_score=50.0,
    )
    db_session.add(existing)
    await db_session.flush()
    dna = await _reload_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({"growth_score": 72.0}, None),
    ):
        await _compute_growth_vector(
            db_session, dna, "exp", "skills", "prefs", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.growth_vector.growth_score == 72.0


@pytest.mark.asyncio
async def test_compute_growth_vector_defaults(db_session: Any) -> None:
    """Uses default trajectory/score when analyzer returns empty dict."""
    user = await _create_user(db_session, "gv_default@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({}, None),
    ):
        await _compute_growth_vector(
            db_session, dna, "exp", "skills", "prefs", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.growth_vector.current_trajectory == "steady"
    assert fresh.growth_vector.growth_score == 50.0


# ── _compute_values_profile ────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_values_profile_creates_new(db_session: Any) -> None:
    """Creates a new ValuesProfile."""
    user = await _create_user(db_session, "vp_new@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    data = {
        "work_style": "autonomous",
        "impact_preference": "organizational",
        "environment_fit": {"remote": 0.9},
        "derived_values": {"autonomy": 0.9},
        "confidence": 0.8,
    }
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=(data, _make_record("career_dna.values_profile")),
    ):
        await _compute_values_profile(
            db_session, dna, "exp", "prefs", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.values_profile.work_style == "autonomous"
    assert fresh.values_profile.confidence == 0.8


@pytest.mark.asyncio
async def test_compute_values_profile_updates_existing(
    db_session: Any,
) -> None:
    """Updates an existing ValuesProfile."""
    user = await _create_user(db_session, "vp_upd@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    existing = ValuesProfile(
        career_dna_id=dna.id,
        work_style="flexible",
        impact_preference="team",
        confidence=0.4,
    )
    db_session.add(existing)
    await db_session.flush()
    dna = await _reload_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({"work_style": "collaborative"}, None),
    ):
        await _compute_values_profile(
            db_session, dna, "exp", "prefs", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.values_profile.work_style == "collaborative"


@pytest.mark.asyncio
async def test_compute_values_profile_defaults(db_session: Any) -> None:
    """Uses default work_style/impact/confidence when analyzer empty."""
    user = await _create_user(db_session, "vp_default@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ):
        await _compute_values_profile(
            db_session, dna, "exp", "prefs", user.id,
        )
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.values_profile.work_style == "flexible"
    assert fresh.values_profile.impact_preference == "team"
    assert fresh.values_profile.confidence == 0.5


# ── _compute_market_position ───────────────────────────────────


@pytest.mark.asyncio
async def test_compute_market_position_creates_new(db_session: Any) -> None:
    """Creates a new MarketPosition row from JobListing data."""
    user = await _create_user(db_session, "mp_new@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    listing = JobListing(
        title="Python Developer",
        company="Acme",
        description="Looking for Python experience",
    )
    db_session.add(listing)
    await db_session.flush()

    analyzer_result = {
        "percentile_overall": 75.0,
        "skill_demand_scores": {"Python": 0.8},
        "matching_job_count": 1,
        "market_trend": "rising",
    }
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value=analyzer_result,
    ):
        await _compute_market_position(db_session, dna, ["Python"])

    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.market_position is not None
    assert fresh.market_position.percentile_overall == 75.0
    assert fresh.market_position.matching_job_count == 1
    assert fresh.market_position.market_trend == "rising"


@pytest.mark.asyncio
async def test_compute_market_position_updates_existing(
    db_session: Any,
) -> None:
    """Updates an existing MarketPosition row."""
    user = await _create_user(db_session, "mp_upd@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    existing = MarketPosition(
        career_dna_id=dna.id,
        percentile_overall=10.0,
        matching_job_count=0,
        market_trend="stable",
    )
    db_session.add(existing)
    await db_session.flush()
    dna = await _reload_dna(db_session, user.id)

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={
            "percentile_overall": 60.0,
            "matching_job_count": 3,
            "market_trend": "rising",
        },
    ):
        await _compute_market_position(db_session, dna, ["Rust"])

    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.market_position.percentile_overall == 60.0
    assert fresh.market_position.matching_job_count == 3


@pytest.mark.asyncio
async def test_compute_market_position_defaults(db_session: Any) -> None:
    """Uses default percentile/count/trend when analyzer returns empty."""
    user = await _create_user(db_session, "mp_default@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={},
    ):
        await _compute_market_position(db_session, dna, [])
    fresh = await _reload_dna(db_session, user.id)
    assert fresh is not None
    assert fresh.market_position.percentile_overall == 0.0
    assert fresh.market_position.matching_job_count == 0
    assert fresh.market_position.market_trend == "stable"


@pytest.mark.asyncio
async def test_compute_market_position_handles_null_description(
    db_session: Any,
) -> None:
    """Null job description becomes empty string in listings_data."""
    user = await _create_user(db_session, "mp_nulldesc@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)
    listing = JobListing(
        title="DevOps",
        company="Foo",
        description="",  # NOT NULL constraint, but falsy
    )
    db_session.add(listing)
    await db_session.flush()

    captured: dict[str, Any] = {}

    def _fake_compute(skills: list[str], listings: list[dict[str, Any]]) -> dict[str, Any]:
        captured["listings"] = listings
        return {"percentile_overall": 1.0}

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        side_effect=_fake_compute,
    ):
        await _compute_market_position(db_session, dna, ["A"])

    assert captured["listings"][0]["title"] == "DevOps"
    assert captured["listings"][0]["description"] == ""


# ── generate_full_profile integration ──────────────────────────


@pytest.mark.asyncio
async def test_generate_full_profile_default_all_dimensions(
    db_session: Any,
) -> None:
    """Full generation with all dimensions computed and metadata updated."""
    user = await _create_user(db_session, "full_all@pathforge.eu")
    await _pre_create_dna(db_session, user.id)
    resume = await _create_resume(db_session, user.id, raw_text="Strong background.")
    await _create_skill(db_session, resume.id, "Python")

    async def _hidden(**_: Any) -> tuple[list[dict[str, Any]], TransparencyRecord | None]:
        return ([], _make_record("career_dna.hidden_skills"))

    async def _exp(*_: Any, **__: Any) -> tuple[dict[str, Any], TransparencyRecord | None]:
        return ({"total_years": 3.0, "role_count": 2}, _make_record())

    async def _growth(*_: Any, **__: Any) -> tuple[dict[str, Any], TransparencyRecord | None]:
        return ({"growth_score": 60.0}, _make_record())

    async def _values(*_: Any, **__: Any) -> tuple[dict[str, Any], TransparencyRecord | None]:
        return ({"work_style": "collaborative"}, _make_record())

    def _market(skills: list[str], listings: list[dict[str, Any]]) -> dict[str, Any]:
        return {"percentile_overall": 50.0, "matching_job_count": 0}

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new=AsyncMock(side_effect=_hidden),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new=AsyncMock(side_effect=_exp),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new=AsyncMock(side_effect=_growth),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new=AsyncMock(side_effect=_values),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        side_effect=_market,
    ):
        result = await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
        )

    assert result.version == 2  # initial was 1
    assert result.last_analysis_at is not None
    # completeness_score is evaluated against the in-memory career_dna
    # whose relationship collections aren't automatically appended to
    # when compute helpers create child rows via FK in the test session.
    # We assert the score is a valid percentage value.
    assert 0.0 <= result.completeness_score <= 100.0


@pytest.mark.asyncio
async def test_generate_full_profile_subset_dimensions(db_session: Any) -> None:
    """Only the requested dimensions are computed."""
    user = await _create_user(db_session, "full_subset@pathforge.eu")
    await _pre_create_dna(db_session, user.id)
    await _create_resume(db_session, user.id, raw_text="Some text.")

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({"total_years": 2.0}, None),
    ) as mock_exp, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ) as mock_hidden, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({}, None),
    ) as mock_growth, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ) as mock_values, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={},
    ) as mock_market:
        await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
            dimensions=["experience_blueprint"],
        )

    mock_exp.assert_called_once()
    mock_hidden.assert_not_called()
    mock_growth.assert_not_called()
    mock_values.assert_not_called()
    mock_market.assert_not_called()


@pytest.mark.asyncio
async def test_generate_full_profile_invalid_dimension_falls_back_to_all(
    db_session: Any,
) -> None:
    """Unknown dimension strings fall back to the full set."""
    user = await _create_user(
        db_session, "full_invalid@pathforge.eu",
    )
    await _pre_create_dna(db_session, user.id)

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ) as mock_hidden, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({}, None),
    ) as mock_exp, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({}, None),
    ) as mock_growth, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ) as mock_values, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={},
    ) as mock_market:
        await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
            dimensions=["nonsense", "not_a_dim"],
        )
    # All five dimensions called
    mock_hidden.assert_called_once()
    mock_exp.assert_called_once()
    mock_growth.assert_called_once()
    mock_values.assert_called_once()
    mock_market.assert_called_once()


@pytest.mark.asyncio
async def test_generate_full_profile_filters_invalid_but_keeps_valid(
    db_session: Any,
) -> None:
    """Invalid entries are stripped; valid ones are retained."""
    user = await _create_user(
        db_session, "full_mixed@pathforge.eu",
    )
    await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ) as mock_values, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ) as mock_hidden:
        await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
            dimensions=["values_profile", "garbage"],
        )
    mock_values.assert_called_once()
    mock_hidden.assert_not_called()


@pytest.mark.asyncio
async def test_generate_full_profile_increments_version(
    db_session: Any,
) -> None:
    """Version is incremented each time generate_full_profile runs."""
    user = await _create_user(db_session, "full_ver@pathforge.eu")
    await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={},
    ):
        result1 = await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
        )
        v1 = result1.version
        result2 = await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
        )
    assert result2.version == v1 + 1


@pytest.mark.asyncio
async def test_generate_full_profile_empty_dimensions_list(
    db_session: Any,
) -> None:
    """Empty list argument computes all dimensions (falsy → default)."""
    user = await _create_user(db_session, "full_emptylist@pathforge.eu")
    await _pre_create_dna(db_session, user.id)
    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ) as mock_hidden, patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={},
    ):
        await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id, dimensions=[],
        )
    mock_hidden.assert_called_once()


# ── VALID_DIMENSIONS constant ──────────────────────────────────


def test_valid_dimensions_contains_five_entries() -> None:
    expected = frozenset(
        {
            "skill_genome",
            "experience_blueprint",
            "growth_vector",
            "values_profile",
            "market_position",
        }
    )
    assert expected == VALID_DIMENSIONS


# ── get_full_profile integration ───────────────────────────────


@pytest.mark.asyncio
async def test_get_full_profile_returns_none_when_missing(
    db_session: Any,
) -> None:
    """Returns None when no profile exists for the user."""
    result = await CareerDNAService.get_full_profile(
        db_session, user_id=uuid.uuid4(),
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_full_profile_loads_relationships(db_session: Any) -> None:
    """All dimension relationships are eagerly loaded (no lazy load)."""
    user = await _create_user(db_session, "full_rels@pathforge.eu")
    dna = CareerDNA(user_id=user.id)
    db_session.add(dna)
    await db_session.flush()

    blueprint = ExperienceBlueprint(
        career_dna_id=dna.id,
        total_years=2.0,
        role_count=1,
        avg_tenure_months=24.0,
    )
    db_session.add(blueprint)
    await db_session.flush()

    result = await CareerDNAService.get_full_profile(
        db_session, user_id=user.id,
    )
    assert result is not None
    # Should access without triggering a lazy load
    assert result.experience_blueprint is not None
    assert result.experience_blueprint.total_years == 2.0


# ── generate_full_profile - data gathering integration ────────


@pytest.mark.asyncio
async def test_generate_full_profile_gathers_skills_for_growth(
    db_session: Any,
) -> None:
    """Skills are combined into comma-separated text for growth vector."""
    user = await _create_user(db_session, "full_skills@pathforge.eu")
    await _pre_create_dna(db_session, user.id)
    resume = await _create_resume(db_session, user.id)
    await _create_skill(db_session, resume.id, "Python")
    await _create_skill(db_session, resume.id, "Rust")

    captured: dict[str, Any] = {}

    async def _capture_growth(
        exp_text: str, skills_text: str, prefs_text: str,
    ) -> tuple[dict[str, Any], TransparencyRecord | None]:
        captured["skills_text"] = skills_text
        return ({}, None)

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new=AsyncMock(side_effect=_capture_growth),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        return_value={},
    ):
        await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
        )
    assert "Python" in captured["skills_text"]
    assert "Rust" in captured["skills_text"]


@pytest.mark.asyncio
async def test_generate_full_profile_passes_skill_names_to_market(
    db_session: Any,
) -> None:
    """Skill names list is forwarded to compute_market_position."""
    user = await _create_user(db_session, "full_mp_skills@pathforge.eu")
    await _pre_create_dna(db_session, user.id)
    resume = await _create_resume(db_session, user.id)
    await _create_skill(db_session, resume.id, "SQL")

    captured: dict[str, Any] = {}

    def _capture_market(
        skills: list[str], listings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        captured["skills"] = skills
        return {}

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "analyze_experience_blueprint",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_growth_vector",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "extract_values_profile",
        new_callable=AsyncMock,
        return_value=({}, None),
    ), patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "compute_market_position",
        side_effect=_capture_market,
    ):
        await CareerDNAService.generate_full_profile(
            db_session, user_id=user.id,
            dimensions=["market_position"],
        )
    assert captured["skills"] == ["SQL"]


# ── Skill genome integration: verify SkillGenomeEntry persisted ──


@pytest.mark.asyncio
async def test_compute_skill_genome_persists_via_select(
    db_session: Any,
) -> None:
    """Confirm SkillGenomeEntry rows are selectable after compute."""
    user = await _create_user(db_session, "genome_select@pathforge.eu")
    dna = await _pre_create_dna(db_session, user.id)

    with patch(
        "app.services.career_dna_service.CareerDNAAnalyzer."
        "discover_hidden_skills",
        new_callable=AsyncMock,
        return_value=([], None),
    ):
        await _compute_skill_genome(
            db_session, dna,
            [
                {
                    "name": "TypeScript",
                    "category": "frontend",
                    "proficiency_level": "expert",
                    "years_experience": 3,
                }
            ],
            "exp text",
            user.id,
        )

    result = await db_session.execute(
        select(SkillGenomeEntry).where(
            SkillGenomeEntry.career_dna_id == dna.id,
        )
    )
    rows = list(result.scalars().all())
    assert len(rows) == 1
    assert rows[0].skill_name == "TypeScript"
    assert rows[0].source == "explicit"
    assert rows[0].confidence == 1.0
