"""
PathForge — Career Passport Service Unit Tests
===============================================
Service-layer tests for career_passport_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.user import User
from app.schemas.career_passport import CareerPassportPreferenceUpdate
from app.services.career_passport_service import (
    _format_skills_for_prompt,
    _get_education_level,
    _get_salary_context,
    _get_years_experience,
    get_dashboard,
    get_preferences,
    map_credential,
    update_preferences,
)

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    skill_count: int = 2,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Passport Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Software Engineer",
        primary_industry="Technology",
        seniority_level="senior",
        location="Amsterdam",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        for i in range(skill_count):
            skill = SkillGenomeEntry(
                career_dna_id=dna.id,
                skill_name=f"Skill{i}",
                category="technical",
                proficiency_level="advanced",
                confidence=0.85,
                source="resume",
            )
            db.add(skill)
        await db.flush()

    return user, dna


# ── Pure helpers ──────────────────────────────────────────────────


class TestFormatSkillsForPrompt:
    def test_no_skills_returns_fallback(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_formats_with_proficiency(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skill = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="TypeScript",
            category="technical",
            proficiency_level="expert",
            confidence=0.95,
            source="resume",
        )
        dna.skill_genome = [skill]
        result = _format_skills_for_prompt(dna)
        assert "TypeScript" in result
        assert "expert" in result


class TestGetYearsExperience:
    def test_returns_default_when_no_blueprint(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        # experience_blueprint is an ORM relationship; None triggers default
        assert _get_years_experience(dna) == 3


class TestGetSalaryContext:
    def test_returns_not_provided_when_no_salary(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        result = _get_salary_context(dna)
        assert result == "Not provided"


class TestGetEducationLevel:
    def test_returns_bachelor_as_default(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        result = _get_education_level(dna)
        assert result == "bachelor"

    def test_returns_education_level_when_set(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.education_level = "master"
        assert _get_education_level(dna) == "master"


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result["credential_mappings"] == []
        assert result["country_comparisons"] == []
        assert result["visa_assessments"] == []
        assert result["market_demand"] == []
        assert result["preferences"] is None
        assert result["passport_scores"] == []

    @pytest.mark.asyncio
    async def test_returns_empty_collections_when_none_exist(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pp-dash@test.com")
        result = await get_dashboard(db_session, user_id=_user.id)
        assert result["credential_mappings"] == []
        assert result["passport_scores"] == []


# ── map_credential ────────────────────────────────────────────────


class TestMapCredential:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await map_credential(
                db_session,
                user_id=uuid.uuid4(),
                source_qualification="MSc Computer Science",
                source_country="Turkey",
                target_country="Netherlands",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_mapping(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pp-cred@test.com")

        fake_result = {
            "equivalent_level": "Master's degree",
            "eqf_level": "level_7",
            "recognition_notes": "Fully recognized",
            "confidence": 0.9,
        }

        with (
            patch(
                "app.services.career_passport_service"
                ".CareerPassportAnalyzer.analyze_credential_mapping",
                new=AsyncMock(return_value=fake_result),
            ),
            patch(
                "app.services.career_passport_service"
                ".CareerPassportAnalyzer.compute_credential_confidence",
                MagicMock(return_value=0.80),
            ),
        ):
            mapping = await map_credential(
                db_session,
                user_id=_user.id,
                source_qualification="MSc Computer Science",
                source_country="Turkey",
                target_country="Netherlands",
            )

        assert mapping.id is not None
        assert mapping.eqf_level == "level_7"
        assert mapping.source_country == "Turkey"
        assert mapping.target_country == "Netherlands"


# ── preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_preferences(db_session, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_preferences_returns_none_when_not_created(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pp-pref-get@test.com")
        result = await get_preferences(db_session, user_id=_user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        update = CareerPassportPreferenceUpdate()
        with pytest.raises(ValueError, match="Career DNA"):
            await update_preferences(
                db_session, user_id=uuid.uuid4(), update_data=update,
            )

    @pytest.mark.asyncio
    async def test_update_preferences_creates_record(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pp-pref-create@test.com")
        update = CareerPassportPreferenceUpdate(nationality="Turkish")
        pref = await update_preferences(
            db_session, user_id=_user.id, update_data=update,
        )
        assert pref is not None
        assert pref.nationality == "Turkish"

    @pytest.mark.asyncio
    async def test_update_preferences_idempotent(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pp-pref-idem@test.com")
        update = CareerPassportPreferenceUpdate()
        pref1 = await update_preferences(
            db_session, user_id=_user.id, update_data=update,
        )
        pref2 = await update_preferences(
            db_session, user_id=_user.id, update_data=update,
        )
        assert pref1.id == pref2.id
