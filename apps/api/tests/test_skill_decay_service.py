"""
PathForge — Skill Decay Service Unit Tests
============================================
Service-layer tests for skill_decay_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.

Coverage targets:
    - SkillDecayService.run_full_scan (no CareerDNA, no skills, happy path)
    - SkillDecayService.get_dashboard (no CareerDNA, empty, with data)
    - SkillDecayService.get_freshness_scores
    - SkillDecayService.get_market_demand
    - SkillDecayService.get_velocity_map
    - SkillDecayService.get_reskilling_paths
    - SkillDecayService.get_preferences / update_preferences
    - SkillDecayService.refresh_skill
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.skill_decay import SkillFreshness
from app.models.user import User
from app.services.skill_decay_service import SkillDecayService


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
        full_name="Decay Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Python Developer",
        primary_industry="Technology",
        seniority_level="senior",
        location="Berlin",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        for name in ["Python", "FastAPI"]:
            skill = SkillGenomeEntry(
                career_dna_id=dna.id,
                skill_name=name,
                category="technical",
                proficiency_level="advanced",
                confidence=0.88,
                years_experience=4,
                source="resume",
            )
            db.add(skill)
        await db.flush()

    return user, dna


def _freshness_adjustment(skill_name: str) -> dict[str, Any]:
    return {
        "skill_name": skill_name,
        "freshness_score": 75.0,
        "decay_rate": "moderate",
        "days_since_active": 90,
        "refresh_urgency": 30.0,
        "contextual_factor": 1.0,
        "reasoning": "Used recently",
    }


def _demand_entry(skill_name: str) -> dict[str, Any]:
    return {
        "skill_name": skill_name,
        "demand_score": 80.0,
        "demand_trend": "growing",
        "growth_projection_6m": 5.0,
        "market_saturation": 0.4,
        "reasoning": "High demand",
    }


def _velocity_entry(skill_name: str) -> dict[str, Any]:
    return {
        "skill_name": skill_name,
        "velocity_score": 70.0,
        "velocity_direction": "growing",
        "composite_health": 75.0,
        "priority_action": "maintain",
    }


def _pathway_entry() -> dict[str, Any]:
    return {
        "pathway_title": "Learn Kubernetes",
        "target_skill": "Kubernetes",
        "priority": "recommended",
        "estimated_weeks": 8,
        "learning_approach": "online_course",
        "resources": [],
    }


# ── run_full_scan ─────────────────────────────────────────────────


class TestRunFullScan:
    @pytest.mark.asyncio
    async def test_returns_error_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.run_full_scan(
            db_session, user_id=uuid.uuid4()
        )
        assert result["status"] == "error"
        assert "Career DNA" in result["detail"]

    @pytest.mark.asyncio
    async def test_returns_error_when_no_skills(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="decay-noskills@test.com", with_skills=False,
        )
        result = await SkillDecayService.run_full_scan(
            db_session, user_id=_user.id,
        )
        assert result["status"] == "error"
        assert "No skills" in result["detail"]

    @pytest.mark.asyncio
    async def test_happy_path_persists_all_stages(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="decay-happy@test.com")

        with (
            patch(
                "app.services.skill_decay_service"
                ".SkillDecayAnalyzer.score_skill_freshness",
                new=AsyncMock(return_value=[
                    _freshness_adjustment("Python"),
                    _freshness_adjustment("FastAPI"),
                ]),
            ),
            patch(
                "app.services.skill_decay_service"
                ".SkillDecayAnalyzer.analyze_market_demand",
                new=AsyncMock(return_value=[
                    _demand_entry("Python"),
                    _demand_entry("FastAPI"),
                ]),
            ),
            patch(
                "app.services.skill_decay_service"
                ".SkillDecayAnalyzer.compute_skill_velocity",
                new=AsyncMock(return_value=[
                    _velocity_entry("Python"),
                    _velocity_entry("FastAPI"),
                ]),
            ),
            patch(
                "app.services.skill_decay_service"
                ".SkillDecayAnalyzer.generate_reskilling_paths",
                new=AsyncMock(return_value=[_pathway_entry()]),
            ),
        ):
            result = await SkillDecayService.run_full_scan(
                db_session, user_id=_user.id,
            )

        assert result["status"] == "completed"
        assert result["skills_analyzed"] == 2
        assert len(result["freshness"]) == 2
        assert len(result["market_demand"]) == 2
        assert len(result["velocity"]) == 2
        assert len(result["reskilling_pathways"]) == 1


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.get_dashboard(
            db_session, user_id=uuid.uuid4()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_zeroed_summary_when_no_scan_data(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="dash-noscan@test.com")
        result = await SkillDecayService.get_dashboard(
            db_session, user_id=_user.id,
        )
        assert result["freshness_summary"]["total_skills"] == 0
        assert result["freshness_summary"]["average_freshness"] == 0.0
        assert result["freshness_summary"]["freshest_skill"] is None
        assert result["freshness_summary"]["stalest_skill"] is None
        assert result["last_scan_at"] is None

    @pytest.mark.asyncio
    async def test_computes_freshness_aggregates_correctly(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="dash-data@test.com")

        # Persist freshness scores manually
        for name, score in [("Python", 90.0), ("COBOL", 20.0)]:
            entry = SkillFreshness(
                career_dna_id=_dna.id,
                skill_name=name,
                freshness_score=score,
                decay_rate="low" if score > 50 else "high",
                days_since_active=10 if score > 50 else 500,
                refresh_urgency=100.0 - score,
            )
            db_session.add(entry)
        await db_session.flush()

        result = await SkillDecayService.get_dashboard(
            db_session, user_id=_user.id,
        )

        summary = result["freshness_summary"]
        assert summary["total_skills"] == 2
        assert summary["average_freshness"] == pytest.approx(55.0)
        assert summary["freshest_skill"] == "Python"
        assert summary["stalest_skill"] == "COBOL"
        assert summary["skills_at_risk"] == 1  # COBOL < 40.0 threshold


# ── Individual accessors ──────────────────────────────────────────


class TestIndividualAccessors:
    @pytest.mark.asyncio
    async def test_get_freshness_scores_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.get_freshness_scores(
            db_session, user_id=uuid.uuid4()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_market_demand_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.get_market_demand(
            db_session, user_id=uuid.uuid4()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_velocity_map_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.get_velocity_map(
            db_session, user_id=uuid.uuid4()
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_reskilling_paths_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.get_reskilling_paths(
            db_session, user_id=uuid.uuid4()
        )
        assert result == []


# ── refresh_skill ─────────────────────────────────────────────────


class TestRefreshSkill:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.refresh_skill(
            db_session, user_id=uuid.uuid4(), skill_name="Python"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_skill_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="refresh-notfound@test.com"
        )
        result = await SkillDecayService.refresh_skill(
            db_session, user_id=_user.id, skill_name="COBOL"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_resets_freshness_to_100(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="refresh-ok@test.com"
        )
        # Persist a stale freshness entry
        entry = SkillFreshness(
            career_dna_id=_dna.id,
            skill_name="Python",
            freshness_score=30.0,
            decay_rate="high",
            days_since_active=400,
            refresh_urgency=70.0,
        )
        db_session.add(entry)
        await db_session.flush()

        result = await SkillDecayService.refresh_skill(
            db_session, user_id=_user.id, skill_name="Python"
        )

        assert result is not None
        assert result.freshness_score == 100.0
        assert result.days_since_active == 0
        assert result.refresh_urgency == 0.0


# ── preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_no_data_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="pref-none@test.com"
        )
        result = await SkillDecayService.get_preferences(
            db_session, user_id=_user.id
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await SkillDecayService.update_preferences(
            db_session, user_id=uuid.uuid4(), updates={}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_creates_and_updates(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="pref-create@test.com"
        )
        pref = await SkillDecayService.update_preferences(
            db_session,
            user_id=_user.id,
            updates={"decay_alert_threshold": 35.0},
        )
        assert pref is not None
        assert pref.decay_alert_threshold == 35.0

    @pytest.mark.asyncio
    async def test_update_preferences_idempotent(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(
            db_session, email="pref-idem@test.com"
        )
        pref1 = await SkillDecayService.update_preferences(
            db_session, user_id=_user.id, updates={}
        )
        pref2 = await SkillDecayService.update_preferences(
            db_session, user_id=_user.id, updates={}
        )
        assert pref1 is not None
        assert pref2 is not None
        assert pref1.id == pref2.id
