"""
PathForge — Career Workflow Automation Engine™ Integration Tests
=================================================================
Async integration tests for the WF service layer, exercising business
logic with a real (SQLite) async session.  Uses the ``db_session`` and
``authenticated_user`` fixtures from ``conftest.py``.

Coverage:
    - create_workflow from template + custom
    - update_workflow_status transition state-machine
    - update_step_status (complete / skip / auto-complete)
    - list / detail / executions / dashboard
    - get_preferences / update_preferences (upsert)
    - Error paths: invalid template, invalid transitions, not-found
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.workflow_automation_service import (
    WorkflowAutomationService as WFService,
)

# ── Helpers ───────────────────────────────────────────────────


async def _create_template_workflow(
    db_session: AsyncSession, user_id: uuid.UUID,
) -> str:
    """Create a workflow from skill_acceleration template, return its id."""
    workflow = await WFService.create_workflow(
        db_session, user_id=user_id, template_id="skill_acceleration",
    )
    return str(workflow.id)


# ── Create Workflow ───────────────────────────────────────────


@pytest.mark.asyncio
class TestCreateWorkflow:
    """Integration tests for workflow creation."""

    async def test_create_from_template(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        workflow = await WFService.create_workflow(
            db_session,
            user_id=authenticated_user.id,
            template_id="skill_acceleration",
        )
        assert workflow.name == "Skill Acceleration Pipeline"
        assert workflow.total_steps == 5
        assert workflow.workflow_status == "draft"
        assert workflow.template_category == "skill_development"

    async def test_create_from_template_auto_activate(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        workflow = await WFService.create_workflow(
            db_session,
            user_id=authenticated_user.id,
            template_id="threat_response",
            auto_activate=True,
        )
        assert workflow.workflow_status == "active"

    async def test_create_custom_workflow(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        workflow = await WFService.create_workflow(
            db_session,
            user_id=authenticated_user.id,
            name="My Custom Career Plan",
            trigger_type="manual",
        )
        assert workflow.name == "My Custom Career Plan"
        assert workflow.total_steps == 0
        assert workflow.workflow_status == "draft"

    async def test_create_invalid_template_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            await WFService.create_workflow(
                db_session,
                user_id=authenticated_user.id,
                template_id="nonexistent_template",
            )


# ── Status Transitions ────────────────────────────────────────


@pytest.mark.asyncio
class TestWorkflowStatusTransitions:
    """Validate the workflow status transition state-machine."""

    async def test_draft_to_active(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        updated = await WFService.update_workflow_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            new_status="active",
        )
        assert updated.workflow_status == "active"

    async def test_active_to_paused(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        await WFService.update_workflow_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            new_status="active",
        )
        updated = await WFService.update_workflow_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            new_status="paused",
        )
        assert updated.workflow_status == "paused"

    async def test_paused_to_active_resume(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        await WFService.update_workflow_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            new_status="active",
        )
        await WFService.update_workflow_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            new_status="paused",
        )
        updated = await WFService.update_workflow_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            new_status="active",
        )
        assert updated.workflow_status == "active"

    async def test_invalid_transition_draft_to_completed_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            await WFService.update_workflow_status(
                db_session,
                user_id=authenticated_user.id,
                workflow_id=uuid.UUID(wf_id),
                new_status="completed",
            )

    async def test_nonexistent_workflow_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        with pytest.raises(ValueError, match="not found"):
            await WFService.update_workflow_status(
                db_session,
                user_id=authenticated_user.id,
                workflow_id=uuid.uuid4(),
                new_status="active",
            )


# ── Step Management ───────────────────────────────────────────


@pytest.mark.asyncio
class TestStepManagement:
    """Test step completion, skipping, and auto-complete."""

    async def test_complete_step(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        detail = await WFService.get_workflow_detail(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
        )
        first_step = detail.steps[0]
        step = await WFService.update_step_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            step_id=first_step.id,
            action="complete",
        )
        assert step.is_completed is True

    async def test_skip_step(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        detail = await WFService.get_workflow_detail(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
        )
        step = await WFService.update_step_status(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
            step_id=detail.steps[0].id,
            action="skip",
        )
        assert step.is_skipped is True

    async def test_invalid_action_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        detail = await WFService.get_workflow_detail(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
        )
        with pytest.raises(ValueError, match="Invalid action"):
            await WFService.update_step_status(
                db_session,
                user_id=authenticated_user.id,
                workflow_id=uuid.UUID(wf_id),
                step_id=detail.steps[0].id,
                action="delete",
            )

    async def test_nonexistent_step_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        with pytest.raises(ValueError, match="not found"):
            await WFService.update_step_status(
                db_session,
                user_id=authenticated_user.id,
                workflow_id=uuid.UUID(wf_id),
                step_id=uuid.uuid4(),
                action="complete",
            )


# ── Queries ───────────────────────────────────────────────────


@pytest.mark.asyncio
class TestWorkflowQueries:
    """Integration tests for read operations."""

    async def test_get_workflow_detail_with_steps(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        wf_id = await _create_template_workflow(
            db_session, authenticated_user.id,
        )
        detail = await WFService.get_workflow_detail(
            db_session,
            user_id=authenticated_user.id,
            workflow_id=uuid.UUID(wf_id),
        )
        assert detail is not None
        assert len(detail.steps) == 5

    async def test_list_workflows_with_status_filter(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        await WFService.create_workflow(
            db_session,
            user_id=authenticated_user.id,
            template_id="skill_acceleration",
        )
        drafts = await WFService.list_workflows(
            db_session,
            user_id=authenticated_user.id,
            status_filter="draft",
        )
        assert all(wf.workflow_status == "draft" for wf in drafts)


# ── Dashboard ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestWorkflowDashboard:
    """Integration tests for the dashboard aggregation."""

    async def test_dashboard_returns_structure(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        dashboard = await WFService.get_dashboard(
            db_session, user_id=authenticated_user.id,
        )
        assert "total_active" in dashboard
        assert "available_templates" in dashboard


# ── Preferences ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestWorkflowPreferences:
    """Integration tests for preference CRUD (upsert pattern)."""

    async def test_get_preferences_returns_none_when_empty(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        prefs = await WFService.get_preferences(
            db_session, user_id=authenticated_user.id,
        )
        assert prefs is None

    async def test_update_preferences_creates_new(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        updated = await WFService.update_preferences(
            db_session,
            user_id=authenticated_user.id,
            updates={"automation_enabled": True},
        )
        assert updated.automation_enabled is True

    async def test_update_preferences_upserts_existing(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        await WFService.update_preferences(
            db_session,
            user_id=authenticated_user.id,
            updates={"max_concurrent_workflows": 3},
        )
        updated = await WFService.update_preferences(
            db_session,
            user_id=authenticated_user.id,
            updates={"max_concurrent_workflows": 10},
        )
        assert updated.max_concurrent_workflows == 10
