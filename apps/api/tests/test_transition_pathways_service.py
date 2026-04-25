"""
PathForge — Transition Pathways Service Unit Tests
====================================================
Service-layer tests for transition_pathways_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.

Coverage targets:
    - Pure helpers: _format_skills_for_prompt, _get_skill_names,
      _get_years_experience
    - explore_transition (happy path, no CareerDNA, empty LLM response)
    - get_dashboard (no CareerDNA, with data)
    - get_transition, get_transitions
    - get_skill_bridge, get_milestones, get_comparisons
    - delete_transition
    - get_preferences, update_preferences
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.user import User
from app.schemas.transition_pathways import TransitionPreferenceUpdateRequest
from app.services.transition_pathways_service import (
    _format_skills_for_prompt,
    _get_skill_names,
    _get_years_experience,
    delete_transition,
    explore_transition,
    get_comparisons,
    get_dashboard,
    get_milestones,
    get_preferences,
    get_skill_bridge,
    get_transition,
    get_transitions,
    update_preferences,
)

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Transition Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Backend Developer",
        primary_industry="Technology",
        seniority_level="mid",
        location="Amsterdam",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        skill = SkillGenomeEntry(
            career_dna_id=dna.id,
            skill_name="Python",
            category="technical",
            proficiency_level="advanced",
            confidence=0.9,
            years_experience=4,
            source="resume",
        )
        db.add(skill)
        await db.flush()

    return user, dna


def _fake_analysis() -> dict[str, Any]:
    return {
        "confidence_score": 0.72,
        "difficulty": "moderate",
        "skill_overlap_percent": 60.0,
        "skills_to_acquire_count": 3,
        "estimated_duration_months": 9,
        "success_probability": 0.68,
    }


# ── Pure helper tests ─────────────────────────────────────────────


class TestPureHelpers:
    def test_format_skills_no_genome(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_format_skills_with_entries(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        entry = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Rust",
            category="systems",
            proficiency_level="intermediate",
            confidence=0.7,
            source="resume",
        )
        dna.skill_genome = [entry]
        result = _format_skills_for_prompt(dna)
        assert "Rust" in result
        assert "intermediate" in result

    def test_get_skill_names_no_genome_returns_empty(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _get_skill_names(dna) == []

    def test_get_skill_names_returns_names(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        entry = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Go",
            category="technical",
            proficiency_level="intermediate",
            confidence=0.8,
            source="resume",
        )
        dna.skill_genome = [entry]
        assert _get_skill_names(dna) == ["Go"]

    def test_get_years_experience_no_skills_returns_default(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _get_years_experience(dna) == 3

    def test_get_years_experience_uses_max_from_skills(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        skills = []
        for years in [2, 5, 3]:
            entry = SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name=f"Skill{years}",
                category="technical",
                proficiency_level="intermediate",
                confidence=0.7,
                years_experience=years,
                source="resume",
            )
            skills.append(entry)
        dna.skill_genome = skills
        assert _get_years_experience(dna) == 5


# ── explore_transition ────────────────────────────────────────────


class TestExploreTransition:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await explore_transition(
                db_session,
                user_id=uuid.uuid4(),
                target_role="ML Engineer",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_all_records(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="explore-happy@test.com")

        skill_bridge: list[dict[str, Any]] = [
            {"skill_name": "PyTorch", "category": "ml", "is_already_held": False,
             "priority": "high"},
        ]
        milestones: list[dict[str, Any]] = [
            {"phase": "preparation", "title": "Learn basics",
             "target_week": 4, "order_index": 0},
        ]
        comparisons: list[dict[str, Any]] = [
            {"dimension": "salary", "source_value": 60000.0,
             "target_value": 80000.0, "delta": 20000.0},
        ]

        with (
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.analyze_transition",
                new=AsyncMock(return_value=_fake_analysis()),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.generate_skill_bridge",
                new=AsyncMock(return_value=skill_bridge),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.create_milestones",
                new=AsyncMock(return_value=milestones),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.compare_roles",
                new=AsyncMock(return_value=comparisons),
            ),
        ):
            result = await explore_transition(
                db_session,
                user_id=_user.id,
                target_role="ML Engineer",
            )

        assert result["transition_path"].to_role == "ML Engineer"
        assert result["transition_path"].confidence_score == pytest.approx(0.72, abs=0.1)
        assert len(result["skill_bridge"]) == 1
        assert len(result["milestones"]) == 1
        assert len(result["comparisons"]) == 1

    @pytest.mark.asyncio
    async def test_uses_default_analysis_when_llm_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="explore-none@test.com")

        with (
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.analyze_transition",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.generate_skill_bridge",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.create_milestones",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.compare_roles",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await explore_transition(
                db_session,
                user_id=_user.id,
                target_role="DevOps Engineer",
            )

        assert result["transition_path"] is not None
        assert result["transition_path"].to_role == "DevOps Engineer"


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_state_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result["transitions"] == []
        assert result["total_explored"] == 0
        assert result["preferences"] is None

    @pytest.mark.asyncio
    async def test_returns_empty_transitions_before_any_exploration(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="dash-empty@test.com")
        result = await get_dashboard(db_session, user_id=_user.id)
        assert result["total_explored"] == 0


# ── get_transition / get_transitions ─────────────────────────────


class TestGetTransition:
    @pytest.mark.asyncio
    async def test_get_transitions_no_career_dna_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_transitions(db_session, user_id=uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_get_transition_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_transition(
            db_session, transition_id=uuid.uuid4(), user_id=uuid.uuid4()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_transitions_returns_saved_transitions(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="get-trans@test.com")

        with (
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.analyze_transition",
                new=AsyncMock(return_value=_fake_analysis()),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.generate_skill_bridge",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.create_milestones",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.compare_roles",
                new=AsyncMock(return_value=[]),
            ),
        ):
            await explore_transition(
                db_session, user_id=_user.id, target_role="Data Scientist"
            )

        transitions = await get_transitions(db_session, user_id=_user.id)
        assert len(transitions) == 1
        assert transitions[0].to_role == "Data Scientist"


# ── get_skill_bridge / get_milestones / get_comparisons ──────────


class TestGetSubItems:
    @pytest.mark.asyncio
    async def test_get_skill_bridge_unknown_id_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_skill_bridge(db_session, transition_id=uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_get_milestones_unknown_id_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_milestones(db_session, transition_id=uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_get_comparisons_unknown_id_returns_empty(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_comparisons(db_session, transition_id=uuid.uuid4())
        assert result == []


# ── delete_transition ─────────────────────────────────────────────


class TestDeleteTransition:
    @pytest.mark.asyncio
    async def test_returns_false_when_transition_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="del-notfound@test.com")
        result = await delete_transition(
            db_session, transition_id=uuid.uuid4(), user_id=_user.id
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_and_removes_transition(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="del-ok@test.com")

        with (
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.analyze_transition",
                new=AsyncMock(return_value=_fake_analysis()),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.generate_skill_bridge",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.create_milestones",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.services.transition_pathways_service"
                ".TransitionPathwaysAnalyzer.compare_roles",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await explore_transition(
                db_session, user_id=_user.id, target_role="SRE"
            )
        path_id = result["transition_path"].id

        deleted = await delete_transition(
            db_session, transition_id=path_id, user_id=_user.id
        )
        assert deleted is True

        # Verify gone
        remaining = await get_transitions(db_session, user_id=_user.id)
        assert all(t.id != path_id for t in remaining)


# ── preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_preferences(db_session, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_no_career_dna_raises(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await update_preferences(
                db_session,
                user_id=uuid.uuid4(),
                update_data=TransitionPreferenceUpdateRequest(),
            )

    @pytest.mark.asyncio
    async def test_update_preferences_creates_on_first_call(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pref-create@test.com")
        pref = await update_preferences(
            db_session,
            user_id=_user.id,
            update_data=TransitionPreferenceUpdateRequest(
                preferred_industries=["Finance", "Tech"],
            ),
        )
        assert pref is not None
        assert pref.id is not None
