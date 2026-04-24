"""
PathForge — Career Simulation Service Unit Tests
==================================================
Service-layer tests for career_simulation_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.

Coverage targets:
    - Pure helpers: _format_skills_for_prompt, _get_skill_names,
      _get_years_experience, _build_scenario_params, _store_inputs,
      _store_outcomes, _store_recommendations, _default_analysis
    - Simulation pipelines: role_transition, geo_move, skill_investment,
      industry_pivot, seniority_jump
    - Dashboard / list / get / delete / compare
    - Preferences: get_preferences, update_preferences
    - Default/fallback behaviors on None LLM responses
    - Error handling when CareerDNA missing
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.career_simulation import (
    CareerSimulation,
    SimulationInput,
    SimulationOutcome,
    SimulationRecommendation,
)
from app.models.user import User
from app.schemas.career_simulation import SimulationPreferenceUpdateRequest
from app.services.career_simulation_service import (
    _build_scenario_params,
    _default_analysis,
    _format_skills_for_prompt,
    _get_skill_names,
    _get_years_experience,
    _store_inputs,
    _store_outcomes,
    _store_recommendations,
    compare_simulations,
    delete_simulation,
    get_dashboard,
    get_preferences,
    get_simulation,
    list_simulations,
    simulate_geo_move,
    simulate_industry_pivot,
    simulate_role_transition,
    simulate_seniority_jump,
    simulate_skill_investment,
    update_preferences,
)

_ANALYZER_PATH = (
    "app.services.career_simulation_service.CareerSimulationAnalyzer"
)


# ── Helpers ───────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    role: str | None = "Backend Developer",
    seniority: str | None = "mid",
    industry: str | None = "Technology",
    location: str | None = "Amsterdam",
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Simulation Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role=role,
        primary_industry=industry,
        seniority_level=seniority,
        location=location,
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
        "feasibility_rating": 68.0,
        "salary_impact_percent": 15.0,
        "estimated_months": 8,
        "reasoning": "Analyzed by test.",
        "factors": {"key": "value"},
    }


def _fake_outcomes() -> list[dict[str, Any]]:
    return [
        {
            "dimension": "salary",
            "current_value": 60000.0,
            "projected_value": 75000.0,
            "delta": 15000.0,
            "unit": "EUR",
            "reasoning": "Market-rate bump.",
        },
        {
            "dimension": "market_demand",
            "current_value": 50.0,
            "projected_value": 70.0,
            "delta": 20.0,
        },
    ]


def _fake_recommendations() -> list[dict[str, Any]]:
    return [
        {
            "priority": "high",
            "title": "Learn Kubernetes",
            "description": "It will help.",
            "estimated_weeks": 12,
            "order_index": 0,
        },
        {
            # Intentionally missing fields to exercise defaults
            "description": "Something else",
        },
    ]


_UNSET: Any = object()


def _patch_pipeline(
    analysis: Any = _UNSET,
    outcomes: Any = _UNSET,
    recs: Any = _UNSET,
) -> Any:
    """Context managers patching all four analyzer methods plus the
    years-experience helper (avoids async lazy-load of the unloaded
    experience_blueprint relationship when the pipeline runs against
    the test fixture DB). Pass None explicitly to simulate an LLM
    returning nothing — the default sentinel uses fake data.
    """
    if analysis is _UNSET:
        analysis = _fake_analysis()
    if outcomes is _UNSET:
        outcomes = _fake_outcomes()
    if recs is _UNSET:
        recs = _fake_recommendations()

    return (
        patch(
            f"{_ANALYZER_PATH}.analyze_scenario",
            new=AsyncMock(return_value=analysis),
        ),
        patch(
            f"{_ANALYZER_PATH}.project_outcomes",
            new=AsyncMock(return_value=outcomes),
        ),
        patch(
            f"{_ANALYZER_PATH}.generate_recommendations",
            new=AsyncMock(return_value=recs),
        ),
        patch(
            "app.services.career_simulation_service._get_years_experience",
            return_value=4,
        ),
    )


# ── Pure helper tests ─────────────────────────────────────────────


class TestFormatSkillsForPrompt:
    def test_no_skill_genome_returns_placeholder(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_empty_list_returns_placeholder(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _format_skills_for_prompt(dna) == "No skills recorded"

    def test_single_entry(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        entry = SkillGenomeEntry(
            career_dna_id=uuid.uuid4(),
            skill_name="Rust",
            proficiency_level="intermediate",
        )
        dna.skill_genome = [entry]
        result = _format_skills_for_prompt(dna)
        assert "Rust" in result
        assert "intermediate" in result

    def test_multiple_entries_comma_separated(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Python",
                proficiency_level="advanced",
            ),
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Go",
                proficiency_level="beginner",
            ),
        ]
        result = _format_skills_for_prompt(dna)
        assert "Python" in result
        assert "Go" in result
        assert "," in result


class TestGetSkillNames:
    def test_no_genome_returns_empty(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        assert _get_skill_names(dna) == []

    def test_returns_skill_names(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="Go",
                proficiency_level="intermediate",
            ),
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name="K8s",
                proficiency_level="beginner",
            ),
        ]
        assert _get_skill_names(dna) == ["Go", "K8s"]


class TestGetYearsExperience:
    def test_no_blueprint_returns_default(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        # Ensure experience_blueprint is falsy
        dna.experience_blueprint = None
        assert _get_years_experience(dna) == 3

    def test_with_blueprint_returns_total_years(self) -> None:
        from app.models.career_dna import ExperienceBlueprint

        dna = CareerDNA(user_id=uuid.uuid4())
        blueprint = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=7.4,
        )
        # Bypass ORM backref event to avoid touching session state
        dna.__dict__["experience_blueprint"] = blueprint
        assert _get_years_experience(dna) == 7

    def test_with_blueprint_zero_clamps_to_one(self) -> None:
        from app.models.career_dna import ExperienceBlueprint

        dna = CareerDNA(user_id=uuid.uuid4())
        blueprint = ExperienceBlueprint(
            career_dna_id=uuid.uuid4(),
            total_years=0.0,
        )
        dna.__dict__["experience_blueprint"] = blueprint
        assert _get_years_experience(dna) == 1


class TestBuildScenarioParams:
    def test_only_scenario_type_when_no_kwargs(self) -> None:
        result = _build_scenario_params("role_transition")
        assert result == "Scenario type: role_transition"

    def test_includes_non_none_params(self) -> None:
        result = _build_scenario_params(
            "geo_move",
            target_location="Berlin",
            keep_role=True,
        )
        assert "Scenario type: geo_move" in result
        assert "- Target Location: Berlin" in result
        assert "- Keep Role: True" in result

    def test_skips_none_values(self) -> None:
        result = _build_scenario_params(
            "skill_investment",
            skills="Python, Go",
            target_role=None,
        )
        assert "Skills" in result
        assert "Target Role" not in result

    def test_formats_label_with_title_case(self) -> None:
        result = _build_scenario_params(
            "industry_pivot",
            target_industry="AI/ML",
        )
        assert "- Target Industry: AI/ML" in result


class TestStoreInputs:
    def test_creates_input_records_for_each_non_none_param(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        params: dict[str, Any] = {
            "target_role": "ML Engineer",
            "target_industry": None,
            "target_location": "Berlin",
        }
        inputs = _store_inputs(sim, params)
        assert len(inputs) == 2
        names = {i.parameter_name for i in inputs}
        assert names == {"target_role", "target_location"}

    def test_stores_parameter_type_name(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="geo_move",
        )
        inputs = _store_inputs(sim, {"keep_role": True, "target_role": "Dev"})
        types = {i.parameter_name: i.parameter_type for i in inputs}
        assert types["keep_role"] == "bool"
        assert types["target_role"] == "str"

    def test_empty_dict_returns_empty_list(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        assert _store_inputs(sim, {}) == []

    def test_all_none_returns_empty(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        inputs = _store_inputs(sim, {"a": None, "b": None})
        assert inputs == []

    def test_values_coerced_to_string(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="skill_investment",
        )
        inputs = _store_inputs(sim, {"count": 7})
        assert inputs[0].parameter_value == "7"
        assert inputs[0].parameter_type == "int"


class TestStoreOutcomes:
    def test_creates_outcome_records(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        outcomes = _store_outcomes(sim, _fake_outcomes())
        assert len(outcomes) == 2
        assert outcomes[0].dimension == "salary"
        assert outcomes[0].projected_value == 75000.0
        assert outcomes[0].unit == "EUR"

    def test_empty_list_returns_empty(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        assert _store_outcomes(sim, []) == []

    def test_uses_defaults_for_missing_fields(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        outcomes = _store_outcomes(sim, [{}])
        assert outcomes[0].dimension == "unknown"
        assert outcomes[0].current_value == 0.0
        assert outcomes[0].projected_value == 0.0
        assert outcomes[0].delta == 0.0
        assert outcomes[0].unit is None
        assert outcomes[0].reasoning is None


class TestStoreRecommendations:
    def test_creates_recommendation_records(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        recs = _store_recommendations(sim, _fake_recommendations())
        assert len(recs) == 2
        assert recs[0].title == "Learn Kubernetes"
        assert recs[0].priority == "high"

    def test_uses_defaults_for_missing_fields(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        recs = _store_recommendations(sim, [{}])
        assert recs[0].priority == "medium"
        assert recs[0].title == "Untitled"
        assert recs[0].order_index == 0
        assert recs[0].description is None

    def test_empty_list_returns_empty(self) -> None:
        sim = CareerSimulation(
            id=uuid.uuid4(),
            career_dna_id=uuid.uuid4(),
            scenario_type="role_transition",
        )
        assert _store_recommendations(sim, []) == []


class TestDefaultAnalysis:
    def test_returns_safe_defaults(self) -> None:
        result = _default_analysis("role_transition")
        assert result["confidence_score"] == 0.5
        assert result["feasibility_rating"] == 50.0
        assert result["salary_impact_percent"] == 0.0
        assert result["estimated_months"] == 6
        assert "Detailed AI analysis was unavailable" in result["reasoning"]
        assert "role_transition" in result["factors"]["note"]

    def test_scenario_type_appears_in_factors(self) -> None:
        result = _default_analysis("geo_move")
        assert "geo_move" in result["factors"]["note"]


# ── simulate_role_transition ─────────────────────────────────────


class TestSimulateRoleTransition:
    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await simulate_role_transition(
                db_session,
                user_id=uuid.uuid4(),
                target_role="ML Engineer",
            )

    @pytest.mark.asyncio
    async def test_happy_path_persists_simulation(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="role@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session,
                user_id=user.id,
                target_role="ML Engineer",
                target_industry="AI",
                target_location="Berlin",
            )
        assert sim.scenario_type == "role_transition"
        assert sim.confidence_score == 0.72
        assert len(sim.inputs) == 3
        assert len(sim.outcomes) == 2
        assert len(sim.recommendations) == 2

    @pytest.mark.asyncio
    async def test_uses_default_analysis_when_llm_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="role-none@test.com")
        p1, p2, p3, p4 = _patch_pipeline(analysis=None, outcomes=[], recs=[])
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session,
                user_id=user.id,
                target_role="Data Engineer",
            )
        assert sim.confidence_score == 0.5
        assert sim.feasibility_rating == 50.0
        assert sim.estimated_months == 6

    @pytest.mark.asyncio
    async def test_works_without_optional_params(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="role-min@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session,
                user_id=user.id,
                target_role="Solo Role",
            )
        assert len(sim.inputs) == 1  # only target_role
        assert sim.inputs[0].parameter_name == "target_role"

    @pytest.mark.asyncio
    async def test_uses_career_dna_defaults_for_missing_context(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(
            db_session,
            email="role-nullctx@test.com",
            role=None,
            seniority=None,
            industry=None,
            location=None,
            with_skills=False,
        )
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session,
                user_id=user.id,
                target_role="Engineer",
            )
        assert sim is not None


# ── simulate_geo_move ─────────────────────────────────────────────


class TestSimulateGeoMove:
    @pytest.mark.asyncio
    async def test_happy_path(self, db_session: AsyncSession) -> None:
        user, _dna = await _make_dna(db_session, email="geo@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_geo_move(
                db_session,
                user_id=user.id,
                target_location="Berlin",
                keep_role=True,
                target_role="Dev",
            )
        assert sim.scenario_type == "geo_move"
        # target_location + keep_role + target_role
        assert len(sim.inputs) == 3

    @pytest.mark.asyncio
    async def test_raises_when_no_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError):
            await simulate_geo_move(
                db_session,
                user_id=uuid.uuid4(),
                target_location="Berlin",
            )


# ── simulate_skill_investment ────────────────────────────────────


class TestSimulateSkillInvestment:
    @pytest.mark.asyncio
    async def test_happy_path_joins_skills(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="skill@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_skill_investment(
                db_session,
                user_id=user.id,
                skills=["Python", "Rust", "Kubernetes"],
            )
        assert sim.scenario_type == "skill_investment"
        skill_input = next(
            (i for i in sim.inputs if i.parameter_name == "skills"), None,
        )
        assert skill_input is not None
        assert "Python" in skill_input.parameter_value
        assert "Rust" in skill_input.parameter_value

    @pytest.mark.asyncio
    async def test_raises_when_no_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError):
            await simulate_skill_investment(
                db_session,
                user_id=uuid.uuid4(),
                skills=["x"],
            )


# ── simulate_industry_pivot ──────────────────────────────────────


class TestSimulateIndustryPivot:
    @pytest.mark.asyncio
    async def test_happy_path(self, db_session: AsyncSession) -> None:
        user, _dna = await _make_dna(db_session, email="pivot@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_industry_pivot(
                db_session,
                user_id=user.id,
                target_industry="Finance",
                target_role="Quant",
            )
        assert sim.scenario_type == "industry_pivot"
        names = {i.parameter_name for i in sim.inputs}
        assert names == {"target_industry", "target_role"}

    @pytest.mark.asyncio
    async def test_raises_when_no_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError):
            await simulate_industry_pivot(
                db_session,
                user_id=uuid.uuid4(),
                target_industry="Finance",
            )


# ── simulate_seniority_jump ──────────────────────────────────────


class TestSimulateSeniorityJump:
    @pytest.mark.asyncio
    async def test_happy_path(self, db_session: AsyncSession) -> None:
        user, _dna = await _make_dna(db_session, email="sen@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_seniority_jump(
                db_session,
                user_id=user.id,
                target_seniority="Staff",
            )
        assert sim.scenario_type == "seniority_jump"
        assert len(sim.inputs) == 1
        assert sim.inputs[0].parameter_name == "target_seniority"

    @pytest.mark.asyncio
    async def test_raises_when_no_dna(self, db_session: AsyncSession) -> None:
        with pytest.raises(ValueError):
            await simulate_seniority_jump(
                db_session,
                user_id=uuid.uuid4(),
                target_seniority="Staff",
            )


# ── get_dashboard ─────────────────────────────────────────────────


class TestGetDashboard:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_dashboard(db_session, user_id=uuid.uuid4())
        assert result["simulations"] == []
        assert result["preferences"] is None
        assert result["total_simulations"] == 0
        assert result["scenario_type_counts"] == {}

    @pytest.mark.asyncio
    async def test_dashboard_empty_with_dna_no_sims(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="dash-empty@test.com")
        result = await get_dashboard(db_session, user_id=user.id)
        assert result["simulations"] == []
        assert result["total_simulations"] == 0
        assert result["scenario_type_counts"] == {}

    @pytest.mark.asyncio
    async def test_dashboard_returns_sims_and_counts(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="dash-full@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            await simulate_role_transition(
                db_session, user_id=user.id, target_role="R1",
            )
            await simulate_geo_move(
                db_session, user_id=user.id, target_location="Berlin",
            )
            await simulate_role_transition(
                db_session, user_id=user.id, target_role="R2",
            )

        result = await get_dashboard(db_session, user_id=user.id)
        assert result["total_simulations"] == 3
        assert result["scenario_type_counts"]["role_transition"] == 2
        assert result["scenario_type_counts"]["geo_move"] == 1

    @pytest.mark.asyncio
    async def test_dashboard_pagination(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="dash-page@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            for idx in range(3):
                await simulate_role_transition(
                    db_session, user_id=user.id, target_role=f"R{idx}",
                )

        result = await get_dashboard(
            db_session, user_id=user.id, page=1, per_page=2,
        )
        assert len(result["simulations"]) == 2
        assert result["total_simulations"] == 3

        page2 = await get_dashboard(
            db_session, user_id=user.id, page=2, per_page=2,
        )
        assert len(page2["simulations"]) == 1


# ── get_simulation ───────────────────────────────────────────────


class TestGetSimulation:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_simulation(
            db_session,
            simulation_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_id(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="get-none@test.com")
        result = await get_simulation(
            db_session,
            simulation_id=uuid.uuid4(),
            user_id=user.id,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_simulation_with_relationships(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="get-ok@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            created = await simulate_role_transition(
                db_session, user_id=user.id, target_role="ML Engineer",
            )

        fetched = await get_simulation(
            db_session, simulation_id=created.id, user_id=user.id,
        )
        assert fetched is not None
        assert fetched.id == created.id
        assert len(fetched.inputs) >= 1
        assert len(fetched.outcomes) >= 1


# ── list_simulations ─────────────────────────────────────────────


class TestListSimulations:
    @pytest.mark.asyncio
    async def test_empty_without_dna(
        self, db_session: AsyncSession,
    ) -> None:
        sims, total = await list_simulations(
            db_session, user_id=uuid.uuid4(),
        )
        assert sims == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_empty_with_dna_no_sims(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="list-empty@test.com")
        sims, total = await list_simulations(db_session, user_id=user.id)
        assert sims == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_returns_list_with_pagination(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="list-ok@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            for idx in range(3):
                await simulate_role_transition(
                    db_session, user_id=user.id, target_role=f"R{idx}",
                )

        sims, total = await list_simulations(
            db_session, user_id=user.id, page=1, per_page=2,
        )
        assert total == 3
        assert len(sims) == 2


# ── delete_simulation ────────────────────────────────────────────


class TestDeleteSimulation:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        ok = await delete_simulation(
            db_session,
            simulation_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert ok is False

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_id(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="del-404@test.com")
        ok = await delete_simulation(
            db_session,
            simulation_id=uuid.uuid4(),
            user_id=user.id,
        )
        assert ok is False

    @pytest.mark.asyncio
    async def test_deletes_existing_simulation(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="del-ok@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session, user_id=user.id, target_role="Doomed",
            )

        ok = await delete_simulation(
            db_session, simulation_id=sim.id, user_id=user.id,
        )
        assert ok is True

        gone = await get_simulation(
            db_session, simulation_id=sim.id, user_id=user.id,
        )
        assert gone is None


# ── compare_simulations ──────────────────────────────────────────


class TestCompareSimulations:
    @pytest.mark.asyncio
    async def test_raises_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await compare_simulations(
                db_session,
                user_id=uuid.uuid4(),
                simulation_ids=[uuid.uuid4(), uuid.uuid4()],
            )

    @pytest.mark.asyncio
    async def test_raises_when_less_than_two_valid(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cmp-fewer@test.com")
        with pytest.raises(ValueError, match="At least 2"):
            await compare_simulations(
                db_session,
                user_id=user.id,
                simulation_ids=[uuid.uuid4(), uuid.uuid4()],
            )

    @pytest.mark.asyncio
    async def test_happy_path_returns_ranking(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cmp-ok@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim1 = await simulate_role_transition(
                db_session, user_id=user.id, target_role="R1",
            )
            sim2 = await simulate_geo_move(
                db_session, user_id=user.id, target_location="Berlin",
            )

        comparison_payload = {
            "ranking": [str(sim1.id), str(sim2.id)],
            "trade_off_analysis": "Sim1 is better overall.",
        }

        with patch(
            f"{_ANALYZER_PATH}.compare_scenarios",
            new=AsyncMock(return_value=comparison_payload),
        ):
            result = await compare_simulations(
                db_session,
                user_id=user.id,
                simulation_ids=[sim1.id, sim2.id],
            )

        assert len(result["simulations"]) == 2
        assert result["ranking"] == [str(sim1.id), str(sim2.id)]
        assert result["trade_off_analysis"] == "Sim1 is better overall."

    @pytest.mark.asyncio
    async def test_defaults_when_comparison_empty(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="cmp-empty@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim1 = await simulate_role_transition(
                db_session, user_id=user.id, target_role="R1",
            )
            sim2 = await simulate_role_transition(
                db_session, user_id=user.id, target_role="R2",
            )

        with patch(
            f"{_ANALYZER_PATH}.compare_scenarios",
            new=AsyncMock(return_value={}),
        ):
            result = await compare_simulations(
                db_session,
                user_id=user.id,
                simulation_ids=[sim1.id, sim2.id],
            )

        assert result["ranking"] == []
        assert result["trade_off_analysis"] is None


# ── get_preferences ──────────────────────────────────────────────


class TestGetPreferences:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        prefs = await get_preferences(db_session, user_id=uuid.uuid4())
        assert prefs is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_preferences(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="pref-none@test.com")
        prefs = await get_preferences(db_session, user_id=user.id)
        assert prefs is None

    @pytest.mark.asyncio
    async def test_returns_existing_preferences(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="pref-ok@test.com")
        payload = SimulationPreferenceUpdateRequest(
            default_scenario_type="role_transition",
            max_scenarios=25,
            notification_enabled=False,
        )
        await update_preferences(
            db_session, user_id=user.id, update_data=payload,
        )

        prefs = await get_preferences(db_session, user_id=user.id)
        assert prefs is not None
        assert prefs.default_scenario_type == "role_transition"
        assert prefs.max_scenarios == 25
        assert prefs.notification_enabled is False


# ── update_preferences ───────────────────────────────────────────


class TestUpdatePreferences:
    @pytest.mark.asyncio
    async def test_raises_when_no_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await update_preferences(
                db_session,
                user_id=uuid.uuid4(),
                update_data=SimulationPreferenceUpdateRequest(
                    max_scenarios=10,
                ),
            )

    @pytest.mark.asyncio
    async def test_creates_preference_when_missing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="upd-create@test.com")
        prefs = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=SimulationPreferenceUpdateRequest(
                default_scenario_type="geo_move",
                max_scenarios=15,
                notification_enabled=True,
            ),
        )
        assert prefs.default_scenario_type == "geo_move"
        assert prefs.max_scenarios == 15
        assert prefs.notification_enabled is True

    @pytest.mark.asyncio
    async def test_partial_update_preserves_existing(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="upd-partial@test.com")

        # Seed baseline
        await update_preferences(
            db_session,
            user_id=user.id,
            update_data=SimulationPreferenceUpdateRequest(
                default_scenario_type="role_transition",
                max_scenarios=40,
                notification_enabled=True,
            ),
        )

        # Partial update: only max_scenarios
        prefs = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=SimulationPreferenceUpdateRequest(max_scenarios=50),
        )

        assert prefs.max_scenarios == 50
        assert prefs.default_scenario_type == "role_transition"
        assert prefs.notification_enabled is True

    @pytest.mark.asyncio
    async def test_empty_update_is_noop(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="upd-empty@test.com")
        prefs = await update_preferences(
            db_session,
            user_id=user.id,
            update_data=SimulationPreferenceUpdateRequest(),
        )
        # Defaults apply
        assert prefs.max_scenarios == 50
        assert prefs.notification_enabled is True


# ── Persistence integrity ────────────────────────────────────────


class TestPipelinePersistence:
    @pytest.mark.asyncio
    async def test_children_attached_to_simulation(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="persist@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session, user_id=user.id, target_role="ML Engineer",
            )

        # Verify children types
        assert all(isinstance(i, SimulationInput) for i in sim.inputs)
        assert all(isinstance(o, SimulationOutcome) for o in sim.outcomes)
        assert all(
            isinstance(r, SimulationRecommendation)
            for r in sim.recommendations
        )
        # Verify FK wiring
        for child in [*sim.inputs, *sim.outcomes, *sim.recommendations]:
            assert child.simulation_id == sim.id

    @pytest.mark.asyncio
    async def test_analysis_fields_populated_from_llm(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="persist-llm@test.com")
        p1, p2, p3, p4 = _patch_pipeline()
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session, user_id=user.id, target_role="ML",
            )
        assert sim.confidence_score == 0.72
        assert sim.feasibility_rating == 68.0
        assert sim.salary_impact_percent == 15.0
        assert sim.estimated_months == 8
        assert sim.reasoning == "Analyzed by test."
        assert sim.factors == {"key": "value"}
        assert sim.roi_score is None  # Always None after pipeline

    @pytest.mark.asyncio
    async def test_partial_analysis_keys_fall_back_to_defaults(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_dna(db_session, email="persist-partial@test.com")
        # Analysis missing several keys
        partial: dict[str, Any] = {"confidence_score": 0.33}
        p1, p2, p3, p4 = _patch_pipeline(analysis=partial, outcomes=[], recs=[])
        with p1, p2, p3, p4:
            sim = await simulate_role_transition(
                db_session, user_id=user.id, target_role="Partial",
            )
        assert sim.confidence_score == 0.33
        assert sim.feasibility_rating == 50.0  # default
        assert sim.estimated_months is None
        assert sim.reasoning is None
