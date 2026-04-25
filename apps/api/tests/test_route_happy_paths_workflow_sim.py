"""
PathForge — Workflow Automation, Transition Pathways,
            Career Simulation & Interview Intelligence Route Tests
==================================================================
Happy-path and error-path coverage for 4 route modules.
Service calls are mocked; route-handler bodies are exercised.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.schemas.career_simulation import (
    CareerSimulationResponse,
    SimulationPreferenceResponse,
)
from app.schemas.interview_intelligence import (
    InterviewPreferenceResponse,
    InterviewPrepResponse,
)
from app.schemas.transition_pathways import (
    TransitionPathResponse,
    TransitionPreferenceResponse,
)
from app.schemas.workflow_automation import (
    CareerWorkflowResponse,
    WorkflowPreferenceResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _now() -> datetime:
    return datetime.now(UTC)


# ── Schema factories ───────────────────────────────────────────────────────────


def _wf_response() -> CareerWorkflowResponse:
    return CareerWorkflowResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Job Application Workflow",
        description="Automates job search",
        workflow_status="active",
        trigger_type="manual",
        data_source="AI",
        disclaimer="For guidance only",
        created_at=_now(),
        updated_at=_now(),
    )


def _wf_pref() -> WorkflowPreferenceResponse:
    return WorkflowPreferenceResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        created_at=_now(),
        updated_at=_now(),
    )


def _transition_path() -> TransitionPathResponse:
    return TransitionPathResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        from_role="Software Engineer",
        to_role="Product Manager",
        confidence_score=0.78,
        difficulty="medium",
        status="active",
        skill_overlap_percent=45.0,
        skills_to_acquire_count=8,
        success_probability=0.65,
        data_source="AI Analysis",
        disclaimer="For guidance only",
        computed_at=_now(),
    )


def _transition_pref() -> TransitionPreferenceResponse:
    return TransitionPreferenceResponse(
        id=uuid.uuid4(),
        min_confidence=0.6,
        max_timeline_months=24,
        notification_enabled=True,
    )


def _simulation() -> CareerSimulationResponse:
    return CareerSimulationResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        scenario_type="role_change",
        status="completed",
        confidence_score=0.80,
        feasibility_rating=0.8,
        data_source="AI Analysis",
        disclaimer="For guidance only",
        computed_at=_now(),
    )


def _sim_pref() -> SimulationPreferenceResponse:
    return SimulationPreferenceResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        max_scenarios=10,
        notification_enabled=True,
    )


def _interview_prep() -> InterviewPrepResponse:
    return InterviewPrepResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        company_name="TechCorp",
        target_role="Staff Engineer",
        status="completed",
        prep_depth="deep",
        confidence_score=0.82,
        data_source="AI Analysis",
        disclaimer="For guidance only",
        computed_at=_now(),
    )


def _interview_pref() -> InterviewPreferenceResponse:
    return InterviewPreferenceResponse(
        id=uuid.uuid4(),
        career_dna_id=uuid.uuid4(),
        max_saved_preps=5,
        include_salary_negotiation=True,
        notification_enabled=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Automation
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowAutomationRoutes:
    """Coverage for app/api/v1/workflow_automation.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-dash@example.com")
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_dashboard",
            new_callable=AsyncMock,
            return_value={
                "active_workflows": [],
                "available_templates": [],
                "total_active": 0,
                "total_completed": 0,
                "total_draft": 0,
                "preferences": None,
            },
        ):
            resp = await client.get(
                "/api/v1/workflows/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_workflows_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-list@example.com")
        wf = MagicMock()
        wf.id = uuid.uuid4()
        wf.name = "Test Workflow"
        wf.workflow_status = "active"
        wf.trigger_type = "manual"
        wf.total_steps = 3
        wf.completed_steps = 1
        wf.is_template = False
        wf.created_at = _now()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.list_workflows",
            new_callable=AsyncMock,
            return_value=[wf],
        ):
            resp = await client.get("/api/v1/workflows", headers=_auth(user))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_templates_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-tmpl@example.com")
        resp = await client.get("/api/v1/workflows/templates", headers=_auth(user))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_workflow_detail_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-detail@example.com")
        wf_id = uuid.uuid4()
        wf = _wf_response()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_workflow_detail",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.workflow_automation.CareerWorkflowResponse.model_validate",
            return_value=wf,
        ):
            resp = await client.get(
                f"/api/v1/workflows/{wf_id}", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_workflow_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-404@example.com")
        wf_id = uuid.uuid4()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_workflow_detail",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/workflows/{wf_id}", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_workflow_status_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-status@example.com")
        wf_id = uuid.uuid4()
        wf = _wf_response()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.update_workflow_status",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.workflow_automation.CareerWorkflowResponse.model_validate",
            return_value=wf,
        ):
            resp = await client.put(
                f"/api/v1/workflows/{wf_id}/status",
                headers=_auth(user),
                json={"workflow_status": "paused"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-pref@example.com")
        pref = _wf_pref()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.workflow_automation.WorkflowPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/workflows/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_preferences_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-pref-404@example.com")
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_preferences",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/workflows/preferences", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-upref@example.com")
        pref = _wf_pref()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.workflow_automation.WorkflowPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/workflows/preferences",
                headers=_auth(user),
                json={"max_active_workflows": 5},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_workflows_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/workflows/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Transition Pathways
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransitionPathwaysRoutes:
    """Coverage for app/api/v1/transition_pathways.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-dash@example.com")
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_dashboard",
            new_callable=AsyncMock,
            return_value={
                "transitions": [],
                "preferences": None,
                "total_explored": 0,
            },
        ):
            resp = await client.get(
                "/api/v1/transition-pathways/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_transitions_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-list@example.com")
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transitions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                "/api/v1/transition-pathways/", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_transition_detail_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-detail@example.com")
        t_id = uuid.uuid4()
        tp = _transition_path()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.transition_pathways.TransitionPathResponse.model_validate",
            return_value=tp,
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_transition_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-404@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_transition_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-del@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.delete_transition",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.delete(
                f"/api/v1/transition-pathways/{t_id}", headers=_auth(user)
            )
        assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-pref@example.com")
        pref = _transition_pref()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.transition_pathways.TransitionPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/transition-pathways/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-upref@example.com")
        pref = _transition_pref()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.transition_pathways.TransitionPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/transition-pathways/preferences",
                headers=_auth(user),
                json={"max_timeline_months": 36},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_transition_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/transition-pathways/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Career Simulation
# ═══════════════════════════════════════════════════════════════════════════════


class TestCareerSimulationRoutes:
    """Coverage for app/api/v1/career_simulation.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-dash@example.com")
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.get_dashboard",
            new_callable=AsyncMock,
            return_value={
                "simulations": [],
                "preferences": None,
                "total_simulations": 0,
                "scenario_type_counts": {},
            },
        ):
            resp = await client.get(
                "/api/v1/career-simulation/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_simulate_role_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-role@example.com")
        sim = _simulation()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.career_simulation.career_simulation_service.simulate_role_transition",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=sim,
        ), patch(
            "app.api.v1.career_simulation.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_simulation.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.career_simulation.settings",
            billing_enabled=False,
        ):
            resp = await client.post(
                "/api/v1/career-simulation/simulate/role",
                headers=_auth(user),
                json={"target_role": "Staff Engineer"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_simulation_detail_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-detail@example.com")
        sim_id = uuid.uuid4()
        sim = _simulation()
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.get_simulation",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=sim,
        ):
            resp = await client.get(
                f"/api/v1/career-simulation/{sim_id}", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_simulation_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-404@example.com")
        sim_id = uuid.uuid4()
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.get_simulation",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=_simulation(),
        ):
            resp = await client.get(
                f"/api/v1/career-simulation/{sim_id}", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_simulation_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-del@example.com")
        sim_id = uuid.uuid4()
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.delete_simulation",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.delete(
                f"/api/v1/career-simulation/{sim_id}", headers=_auth(user)
            )
        assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-pref@example.com")
        pref = _sim_pref()
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation.SimulationPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/career-simulation/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-upref@example.com")
        pref = _sim_pref()
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation.SimulationPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/career-simulation/preferences",
                headers=_auth(user),
                json={"max_scenarios": 15},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_simulation_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/career-simulation/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Interview Intelligence
# ═══════════════════════════════════════════════════════════════════════════════


class TestInterviewIntelligenceRoutes:
    """Coverage for app/api/v1/interview_intelligence.py handler bodies."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-dash@example.com")
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.get_dashboard",
            new_callable=AsyncMock,
            return_value={
                "preps": [],
                "preferences": None,
                "total_preps": 0,
                "company_counts": {},
            },
        ):
            resp = await client.get(
                "/api/v1/interview-intelligence/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_prep_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-prep@example.com")
        prep = _interview_prep()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.create_interview_prep",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.interview_intelligence.InterviewPrepResponse.model_validate",
            return_value=prep,
        ), patch(
            "app.api.v1.interview_intelligence.BillingService.check_scan_limit",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.interview_intelligence.BillingService.record_usage",
            new_callable=AsyncMock,
        ), patch(
            "app.api.v1.interview_intelligence.settings",
            billing_enabled=False,
        ):
            resp = await client.post(
                "/api/v1/interview-intelligence/prep",
                headers=_auth(user),
                json={
                    "company_name": "TechCorp",
                    "target_role": "Staff Engineer",
                },
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_prep_detail_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-detail@example.com")
        prep_id = uuid.uuid4()
        prep = _interview_prep()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.get_interview_prep",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.interview_intelligence.InterviewPrepResponse.model_validate",
            return_value=prep,
        ):
            resp = await client.get(
                f"/api/v1/interview-intelligence/{prep_id}", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_prep_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-404@example.com")
        prep_id = uuid.uuid4()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.get_interview_prep",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/interview-intelligence/{prep_id}", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_prep_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-del@example.com")
        prep_id = uuid.uuid4()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.delete_interview_prep",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.delete(
                f"/api/v1/interview-intelligence/{prep_id}", headers=_auth(user)
            )
        assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_get_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-pref@example.com")
        pref = _interview_pref()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.get_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.interview_intelligence.InterviewPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.get(
                "/api/v1/interview-intelligence/preferences", headers=_auth(user)
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_preferences_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-upref@example.com")
        pref = _interview_pref()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.update_preferences",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.interview_intelligence.InterviewPreferenceResponse.model_validate",
            return_value=pref,
        ):
            resp = await client.put(
                "/api/v1/interview-intelligence/preferences",
                headers=_auth(user),
                json={"max_saved_preps": 10},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_interview_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/interview-intelligence/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Additional Coverage — workflow create + steps + executions
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowExtraRoutes:
    """Coverage for missing workflow_automation handlers."""

    @pytest.mark.asyncio
    async def test_create_workflow_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-create@example.com")
        wf = _wf_response()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.create_workflow",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.workflow_automation.CareerWorkflowResponse.model_validate",
            return_value=wf,
        ):
            resp = await client.post(
                "/api/v1/workflows",
                headers=_auth(user),
                json={"name": "My Workflow", "trigger_type": "manual"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_create_workflow_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-create-err@example.com")
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.create_workflow",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid template"),
        ):
            resp = await client.post(
                "/api/v1/workflows",
                headers=_auth(user),
                json={"name": "X", "trigger_type": "manual"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_step_status_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-step@example.com")
        wf_id = uuid.uuid4()
        step_id = uuid.uuid4()
        from app.schemas.workflow_automation import WorkflowStepResponse
        step = WorkflowStepResponse(
            id=step_id,
            workflow_id=wf_id,
            step_order=0,
            step_type="action",
            title="Step 1",
            description="Do something",
            created_at=_now(),
            updated_at=_now(),
        )
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.update_step_status",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.workflow_automation.WorkflowStepResponse.model_validate",
            return_value=step,
        ):
            resp = await client.put(
                f"/api/v1/workflows/{wf_id}/steps/{step_id}/status",
                headers=_auth(user),
                json={"action": "complete"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_step_status_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-step-err@example.com")
        wf_id = uuid.uuid4()
        step_id = uuid.uuid4()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.update_step_status",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid step action"),
        ):
            resp = await client.put(
                f"/api/v1/workflows/{wf_id}/steps/{step_id}/status",
                headers=_auth(user),
                json={"action": "complete"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_executions_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-exec@example.com")
        wf_id = uuid.uuid4()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_executions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                f"/api/v1/workflows/{wf_id}/executions",
                headers=_auth(user),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_workflow_status_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-stat-err@example.com")
        wf_id = uuid.uuid4()
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.update_workflow_status",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid status transition"),
        ):
            resp = await client.put(
                f"/api/v1/workflows/{wf_id}/status",
                headers=_auth(user),
                json={"workflow_status": "unknown"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_preferences_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-pref-err@example.com")
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.update_preferences",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid preference"),
        ):
            resp = await client.put(
                "/api/v1/workflows/preferences",
                headers=_auth(user),
                json={"max_active_workflows": 999},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_dashboard_400_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "wf-dash-err@example.com")
        with patch(
            "app.api.v1.workflow_automation.WorkflowAutomationService.get_dashboard",
            new_callable=AsyncMock,
            side_effect=ValueError("Bad state"),
        ):
            resp = await client.get(
                "/api/v1/workflows/dashboard", headers=_auth(user)
            )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# Additional Coverage — transition pathways: explore + what-if + sub-routes
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransitionPathwaysExtraRoutes:
    """Coverage for missing transition_pathways handlers."""

    @pytest.mark.asyncio
    async def test_explore_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-explore@example.com")
        from app.schemas.transition_pathways import TransitionScanResponse
        scan = TransitionScanResponse(
            transition_path=_transition_path(),
            skill_bridge=[],
            milestones=[],
            comparisons=[],
        )
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.explore_transition",
            new_callable=AsyncMock,
            return_value={"transition_path": MagicMock(), "skill_bridge": [], "milestones": [], "comparisons": []},
        ), patch(
            "app.api.v1.transition_pathways._build_scan_response",
            return_value=scan,
        ):
            resp = await client.post(
                "/api/v1/transition-pathways/explore",
                headers=_auth(user),
                json={"target_role": "Product Manager"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_explore_404_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-explore-err@example.com")
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.explore_transition",
            new_callable=AsyncMock,
            side_effect=ValueError("DNA not found"),
        ):
            resp = await client.post(
                "/api/v1/transition-pathways/explore",
                headers=_auth(user),
                json={"target_role": "Product Manager"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_what_if_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-whatif@example.com")
        from app.schemas.transition_pathways import TransitionScanResponse
        scan = TransitionScanResponse(
            transition_path=_transition_path(),
            skill_bridge=[],
            milestones=[],
            comparisons=[],
        )
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.explore_transition",
            new_callable=AsyncMock,
            return_value={"transition_path": MagicMock(), "skill_bridge": [], "milestones": [], "comparisons": []},
        ), patch(
            "app.api.v1.transition_pathways._build_scan_response",
            return_value=scan,
        ):
            resp = await client.post(
                "/api/v1/transition-pathways/what-if",
                headers=_auth(user),
                json={"target_role": "Designer"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_what_if_404_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-whatif-err@example.com")
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.explore_transition",
            new_callable=AsyncMock,
            side_effect=ValueError("not found"),
        ):
            resp = await client.post(
                "/api/v1/transition-pathways/what-if",
                headers=_auth(user),
                json={"target_role": "Designer"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_preferences_404_on_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-pref-err@example.com")
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.update_preferences",
            new_callable=AsyncMock,
            side_effect=ValueError("DNA not found"),
        ):
            resp = await client.put(
                "/api/v1/transition-pathways/preferences",
                headers=_auth(user),
                json={"max_timeline_months": 36},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_transition_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-del-404@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.delete_transition",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.delete(
                f"/api/v1/transition-pathways/{t_id}", headers=_auth(user)
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_skill_bridge_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-sb@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_skill_bridge",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}/skill-bridge",
                headers=_auth(user),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_skill_bridge_404_when_no_transition(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-sb-404@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}/skill-bridge",
                headers=_auth(user),
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_milestones_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-ms@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_milestones",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}/milestones",
                headers=_auth(user),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_milestones_404_when_no_transition(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-ms-404@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}/milestones",
                headers=_auth(user),
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_comparison_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-comp@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_comparisons",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}/comparison",
                headers=_auth(user),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_comparison_404_when_no_transition(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "tp-comp-404@example.com")
        t_id = uuid.uuid4()
        with patch(
            "app.api.v1.transition_pathways.transition_pathways_service.get_transition",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/transition-pathways/{t_id}/comparison",
                headers=_auth(user),
            )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Additional Coverage — career_simulation: geo, skill, industry, seniority, compare
# ═══════════════════════════════════════════════════════════════════════════════


class TestCareerSimulationExtraRoutes:
    """Coverage for missing career_simulation handlers."""

    @pytest.mark.asyncio
    async def test_simulate_geo_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-geo@example.com")
        sim = _simulation()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.career_simulation.career_simulation_service.simulate_geo_move",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=sim,
        ):
            resp = await client.post(
                "/api/v1/career-simulation/simulate/geo",
                headers=_auth(user),
                json={"target_location": "Berlin, Germany", "keep_role": True},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_simulate_skill_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-skill@example.com")
        sim = _simulation()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.career_simulation.career_simulation_service.simulate_skill_investment",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=sim,
        ):
            resp = await client.post(
                "/api/v1/career-simulation/simulate/skill",
                headers=_auth(user),
                json={"skills": ["Rust", "Kubernetes"]},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_simulate_industry_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-ind@example.com")
        sim = _simulation()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.career_simulation.career_simulation_service.simulate_industry_pivot",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=sim,
        ):
            resp = await client.post(
                "/api/v1/career-simulation/simulate/industry",
                headers=_auth(user),
                json={"target_industry": "Healthcare"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_simulate_seniority_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-sen@example.com")
        sim = _simulation()
        with patch("app.core.feature_gate.get_user_tier", return_value="premium"), patch(
            "app.api.v1.career_simulation.career_simulation_service.simulate_seniority_jump",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.career_simulation._build_full_response",
            return_value=sim,
        ):
            resp = await client.post(
                "/api/v1/career-simulation/simulate/seniority",
                headers=_auth(user),
                json={"target_seniority": "staff"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_compare_simulations_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-cmp@example.com")
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.compare_simulations",
            new_callable=AsyncMock,
            return_value={"simulations": [], "ranking": [], "trade_off_analysis": "n/a"},
        ):
            resp = await client.post(
                "/api/v1/career-simulation/compare",
                headers=_auth(user),
                json={"simulation_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_simulation_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cs-del-404@example.com")
        sim_id = uuid.uuid4()
        with patch(
            "app.api.v1.career_simulation.career_simulation_service.delete_simulation",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.delete(
                f"/api/v1/career-simulation/{sim_id}", headers=_auth(user)
            )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Additional Coverage — interview intelligence: compare + generate handlers
# ═══════════════════════════════════════════════════════════════════════════════


class TestInterviewIntelligenceExtraRoutes:
    """Coverage for missing interview_intelligence handlers."""

    @pytest.mark.asyncio
    async def test_compare_preps_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-cmp@example.com")
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.compare_interview_preps",
            new_callable=AsyncMock,
            return_value={"preps": [], "ranking": [], "comparison_summary": None},
        ):
            resp = await client.post(
                "/api/v1/interview-intelligence/compare",
                headers=_auth(user),
                json={"prep_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_questions_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-q@example.com")
        prep_id = uuid.uuid4()
        prep = _interview_prep()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.generate_questions_for_prep",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.interview_intelligence.InterviewPrepResponse.model_validate",
            return_value=prep,
        ):
            resp = await client.post(
                f"/api/v1/interview-intelligence/{prep_id}/questions",
                headers=_auth(user),
                json={"max_questions": 5},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_generate_questions_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-q-404@example.com")
        prep_id = uuid.uuid4()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.generate_questions_for_prep",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                f"/api/v1/interview-intelligence/{prep_id}/questions",
                headers=_auth(user),
                json={"max_questions": 5},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_star_examples_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-star@example.com")
        prep_id = uuid.uuid4()
        prep = _interview_prep()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.generate_star_examples_for_prep",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ), patch(
            "app.api.v1.interview_intelligence.InterviewPrepResponse.model_validate",
            return_value=prep,
        ):
            resp = await client.post(
                f"/api/v1/interview-intelligence/{prep_id}/star-examples",
                headers=_auth(user),
                json={"max_examples": 3},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_generate_star_examples_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-star-404@example.com")
        prep_id = uuid.uuid4()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.generate_star_examples_for_prep",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                f"/api/v1/interview-intelligence/{prep_id}/star-examples",
                headers=_auth(user),
                json={"max_examples": 3},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_negotiation_script_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-neg@example.com")
        prep_id = uuid.uuid4()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.generate_negotiation_script",
            new_callable=AsyncMock,
            return_value={
                "interview_prep_id": prep_id,
                "company_name": "TechCorp",
                "target_role": "Staff Engineer",
                "currency": "USD",
                "opening_script": "Hello",
                "counteroffer_script": "Counter",
                "fallback_script": "Fallback",
                "data_source": "AI",
                "disclaimer": "For guidance only",
            },
        ):
            resp = await client.post(
                f"/api/v1/interview-intelligence/{prep_id}/negotiation-script",
                headers=_auth(user),
                json={"target_salary": 150000, "currency": "USD"},
            )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_delete_prep_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "ii-del-404@example.com")
        prep_id = uuid.uuid4()
        with patch(
            "app.api.v1.interview_intelligence.interview_intelligence_service.delete_interview_prep",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.delete(
                f"/api/v1/interview-intelligence/{prep_id}", headers=_auth(user)
            )
        assert resp.status_code == 404
