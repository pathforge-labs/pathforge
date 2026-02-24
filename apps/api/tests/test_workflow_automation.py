"""
PathForge — Career Workflow Automation Engine™ Test Suite
==========================================================
Tests for Sprint 23 Feature 2: models, enums, service logic,
template structure, and schema validation.

Coverage:
    - StrEnum values (WorkflowTriggerType, WorkflowStatus, StepType)
    - Model creation (CareerWorkflow, WorkflowStep, WorkflowExecution,
      WorkflowPreference)
    - Smart Workflow Templates™ structure and metadata
    - Status transition validation logic
    - Schema validation (request + response models)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.workflow_automation import (
    CareerWorkflow,
    StepType,
    WorkflowExecution,
    WorkflowPreference,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTriggerType,
)
from app.schemas.workflow_automation import (
    CareerWorkflowResponse,
    CreateWorkflowRequest,
    UpdateStepStatusRequest,
    UpdateWorkflowStatusRequest,
    WorkflowDashboardResponse,
    WorkflowExecutionResponse,
    WorkflowPreferenceResponse,
    WorkflowPreferenceUpdate,
    WorkflowStepResponse,
    WorkflowSummary,
    WorkflowTemplateInfo,
)
from app.services.workflow_automation_service import (
    WORKFLOW_TEMPLATES,
    _get_template_info_list,
)

# ── Enum Tests ─────────────────────────────────────────────────


class TestWorkflowEnums:
    """Test StrEnum definitions for Workflow Automation."""

    def test_trigger_type_values(self) -> None:
        assert WorkflowTriggerType.VITALS_THRESHOLD == "vitals_threshold"
        assert WorkflowTriggerType.ENGINE_CHANGE == "engine_change"
        assert WorkflowTriggerType.SCHEDULED == "scheduled"
        assert WorkflowTriggerType.MANUAL == "manual"
        assert len(WorkflowTriggerType) == 4

    def test_workflow_status_values(self) -> None:
        assert WorkflowStatus.DRAFT == "draft"
        assert WorkflowStatus.ACTIVE == "active"
        assert WorkflowStatus.PAUSED == "paused"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.ARCHIVED == "archived"
        assert len(WorkflowStatus) == 5

    def test_step_type_values(self) -> None:
        assert StepType.ACTION == "action"
        assert StepType.NOTIFICATION == "notification"
        assert StepType.CHECK == "check"
        assert StepType.DECISION == "decision"
        assert len(StepType) == 4


# ── Model Creation Tests ──────────────────────────────────────


class TestCareerWorkflowModel:
    """Test CareerWorkflow model instantiation."""

    def test_create_workflow(self) -> None:
        user_id = str(uuid.uuid4())
        workflow = CareerWorkflow(
            user_id=user_id,
            name="Skill Acceleration Pipeline",
            description="Accelerate declining skills.",
            workflow_status=WorkflowStatus.DRAFT.value,
            trigger_type=WorkflowTriggerType.ENGINE_CHANGE.value,
            total_steps=5,
        )
        assert workflow.user_id == user_id
        assert workflow.name == "Skill Acceleration Pipeline"
        assert workflow.workflow_status == "draft"
        assert workflow.trigger_type == "engine_change"
        assert workflow.total_steps == 5
        assert workflow.__tablename__ == "wf_workflows"

    def test_workflow_explicit_values(self) -> None:
        workflow = CareerWorkflow(
            user_id=str(uuid.uuid4()),
            name="Test Workflow",
            description="Testing values.",
            completed_steps=3,
            is_template=True,
            template_category="skill_development",
        )
        assert workflow.completed_steps == 3
        assert workflow.is_template is True
        assert workflow.template_category == "skill_development"

    def test_workflow_explicit_transparency_fields(self) -> None:
        data_source = "Career Workflow Automation Engine™"
        disclaimer = "AI-generated workflow test."
        workflow = CareerWorkflow(
            user_id=str(uuid.uuid4()),
            name="Test",
            description="Test",
            data_source=data_source,
            disclaimer=disclaimer,
        )
        assert workflow.data_source == data_source
        assert workflow.disclaimer == disclaimer

    def test_workflow_repr(self) -> None:
        workflow = CareerWorkflow(
            user_id=str(uuid.uuid4()),
            name="Test",
            description="Test",
            workflow_status="active",
            trigger_type="manual",
            completed_steps=2,
            total_steps=5,
        )
        repr_str = repr(workflow)
        assert "Test" in repr_str
        assert "active" in repr_str


class TestWorkflowStepModel:
    """Test WorkflowStep model instantiation."""

    def test_create_step(self) -> None:
        wf_id = str(uuid.uuid4())
        step = WorkflowStep(
            workflow_id=wf_id,
            step_order=0,
            step_type=StepType.ACTION.value,
            title="Complete learning module",
            description="Dedicate focused time.",
        )
        assert step.workflow_id == wf_id
        assert step.step_order == 0
        assert step.step_type == "action"
        assert step.__tablename__ == "wf_steps"

    def test_step_explicit_values(self) -> None:
        step = WorkflowStep(
            workflow_id=str(uuid.uuid4()),
            step_order=0,
            step_type="check",
            title="Test step",
            description="Explicit test.",
            is_completed=True,
            is_skipped=False,
        )
        assert step.is_completed is True
        assert step.is_skipped is False

    def test_step_repr(self) -> None:
        step = WorkflowStep(
            workflow_id=str(uuid.uuid4()),
            step_order=2,
            step_type="decision",
            title="Choose path",
            description="Pick direction.",
            is_completed=True,
        )
        repr_str = repr(step)
        assert "order=2" in repr_str
        assert "decision" in repr_str


class TestWorkflowExecutionModel:
    """Test WorkflowExecution model instantiation."""

    def test_create_execution(self) -> None:
        execution = WorkflowExecution(
            workflow_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            execution_status="running",
            steps_completed=2,
            steps_total=5,
            career_vitals_at_trigger=72.5,
        )
        assert execution.execution_status == "running"
        assert execution.steps_completed == 2
        assert execution.steps_total == 5
        assert execution.career_vitals_at_trigger == 72.5
        assert execution.__tablename__ == "wf_executions"


class TestWorkflowPreferenceModel:
    """Test WorkflowPreference model instantiation."""

    def test_create_preference(self) -> None:
        pref = WorkflowPreference(
            user_id=str(uuid.uuid4()),
            automation_enabled=True,
            max_concurrent_workflows=5,
        )
        assert pref.automation_enabled is True
        assert pref.max_concurrent_workflows == 5
        assert pref.__tablename__ == "wf_preferences"

    def test_preference_explicit_values(self) -> None:
        pref = WorkflowPreference(
            user_id=str(uuid.uuid4()),
            auto_activate_templates=True,
            trigger_sensitivity="high",
            notifications_enabled=False,
        )
        assert pref.auto_activate_templates is True
        assert pref.trigger_sensitivity == "high"
        assert pref.notifications_enabled is False


# ── Smart Workflow Templates™ Tests ──────────────────────────


class TestWorkflowTemplates:
    """Test Smart Workflow Templates™ structure."""

    def test_templates_exist(self) -> None:
        assert len(WORKFLOW_TEMPLATES) >= 5

    def test_template_required_keys(self) -> None:
        required_keys = {
            "name", "description", "category", "trigger_type",
            "estimated_duration", "difficulty", "steps",
        }
        for template_id, template in WORKFLOW_TEMPLATES.items():
            missing = required_keys - set(template.keys())
            assert not missing, (
                f"Template '{template_id}' missing keys: {missing}"
            )

    def test_template_steps_are_non_empty(self) -> None:
        for template_id, template in WORKFLOW_TEMPLATES.items():
            assert len(template["steps"]) > 0, (
                f"Template '{template_id}' has no steps"
            )

    def test_template_step_required_keys(self) -> None:
        step_required_keys = {"type", "title", "description"}
        for template_id, template in WORKFLOW_TEMPLATES.items():
            for idx, step in enumerate(template["steps"]):
                missing = step_required_keys - set(step.keys())
                assert not missing, (
                    f"Template '{template_id}' step {idx} "
                    f"missing keys: {missing}"
                )

    def test_template_step_types_valid(self) -> None:
        valid_types = {e.value for e in StepType}
        for template_id, template in WORKFLOW_TEMPLATES.items():
            for step in template["steps"]:
                assert step["type"] in valid_types, (
                    f"Template '{template_id}' has invalid step type: "
                    f"{step['type']}"
                )

    def test_template_trigger_types_valid(self) -> None:
        valid_triggers = {e.value for e in WorkflowTriggerType}
        for template_id, template in WORKFLOW_TEMPLATES.items():
            assert template["trigger_type"] in valid_triggers, (
                f"Template '{template_id}' has invalid trigger: "
                f"{template['trigger_type']}"
            )

    def test_skill_acceleration_template(self) -> None:
        template = WORKFLOW_TEMPLATES["skill_acceleration"]
        assert template["category"] == "skill_development"
        assert len(template["steps"]) == 5

    def test_threat_response_template(self) -> None:
        template = WORKFLOW_TEMPLATES["threat_response"]
        assert template["category"] == "risk_mitigation"
        assert template["trigger_type"] == "vitals_threshold"

    def test_opportunity_capture_template(self) -> None:
        template = WORKFLOW_TEMPLATES["opportunity_capture"]
        assert template["category"] == "opportunity"

    def test_salary_negotiation_template(self) -> None:
        template = WORKFLOW_TEMPLATES["salary_negotiation"]
        assert template["category"] == "compensation"
        assert template["trigger_type"] == "manual"

    def test_career_review_template(self) -> None:
        template = WORKFLOW_TEMPLATES["career_review"]
        assert template["category"] == "planning"
        assert template["trigger_type"] == "scheduled"


# ── Template Helper Tests ─────────────────────────────────────


class TestTemplateHelpers:
    """Test template info list generation."""

    def test_get_template_info_list(self) -> None:
        templates = _get_template_info_list()
        assert len(templates) == len(WORKFLOW_TEMPLATES)

    def test_template_info_required_keys(self) -> None:
        templates = _get_template_info_list()
        required = {
            "template_id", "name", "description", "category",
            "trigger_type", "total_steps", "estimated_duration",
            "difficulty",
        }
        for info in templates:
            missing = required - set(info.keys())
            assert not missing, f"Template info missing keys: {missing}"


# ── Schema Validation Tests ──────────────────────────────────


class TestWorkflowSchemas:
    """Test Pydantic schema validation."""

    def test_workflow_summary_schema(self) -> None:
        summary = WorkflowSummary(
            id=uuid.uuid4(),
            name="Skill Acceleration Pipeline",
            workflow_status="active",
            trigger_type="engine_change",
            total_steps=5,
            completed_steps=2,
            is_template=False,
            created_at=datetime.now(UTC),
        )
        assert summary.completed_steps == 2
        assert summary.workflow_status == "active"

    def test_create_workflow_request_defaults(self) -> None:
        request = CreateWorkflowRequest()
        assert request.template_id is None
        assert request.trigger_type == "manual"
        assert request.auto_activate is False

    def test_create_workflow_from_template(self) -> None:
        request = CreateWorkflowRequest(
            template_id="skill_acceleration",
            auto_activate=True,
        )
        assert request.template_id == "skill_acceleration"
        assert request.auto_activate is True

    def test_update_workflow_status_request(self) -> None:
        request = UpdateWorkflowStatusRequest(workflow_status="paused")
        assert request.workflow_status == "paused"

    def test_update_step_status_request(self) -> None:
        request = UpdateStepStatusRequest(action="complete")
        assert request.action == "complete"

    def test_update_step_skip_request(self) -> None:
        request = UpdateStepStatusRequest(
            action="skip",
            notes="Already covered through another activity.",
        )
        assert request.action == "skip"
        assert "another activity" in request.notes

    def test_preference_update_excludes_unset(self) -> None:
        update = WorkflowPreferenceUpdate(automation_enabled=False)
        dumped = update.model_dump(exclude_unset=True)
        assert "automation_enabled" in dumped
        assert "max_concurrent_workflows" not in dumped

    def test_step_response_schema(self) -> None:
        step = WorkflowStepResponse(
            id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            step_order=0,
            step_type="action",
            title="Complete learning module",
            description="Study materials.",
            is_completed=False,
            is_skipped=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert step.step_order == 0
        assert step.is_completed is False

    def test_execution_response_schema(self) -> None:
        execution = WorkflowExecutionResponse(
            id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            execution_status="running",
            steps_completed=2,
            steps_total=5,
            career_vitals_at_trigger=72.5,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert execution.steps_completed == 2
        assert execution.career_vitals_at_trigger == 72.5

    def test_preference_response_schema(self) -> None:
        pref = WorkflowPreferenceResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            automation_enabled=True,
            max_concurrent_workflows=5,
            auto_activate_templates=False,
            trigger_sensitivity="medium",
            notifications_enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert pref.max_concurrent_workflows == 5

    def test_dashboard_response_defaults(self) -> None:
        dashboard = WorkflowDashboardResponse()
        assert dashboard.active_workflows == []
        assert dashboard.available_templates == []
        assert dashboard.total_active == 0
        assert "Workflow Automation Engine" in dashboard.data_source

    def test_template_info_schema(self) -> None:
        info = WorkflowTemplateInfo(
            template_id="skill_acceleration",
            name="Skill Acceleration Pipeline",
            description="Accelerate declining skills.",
            category="skill_development",
            trigger_type="engine_change",
            total_steps=5,
            estimated_duration="2-4 weeks",
            difficulty="moderate",
        )
        assert info.total_steps == 5
        assert info.difficulty == "moderate"

    def test_full_workflow_response_schema(self) -> None:
        workflow = CareerWorkflowResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Skill Acceleration",
            description="Accelerate skills.",
            workflow_status="active",
            trigger_type="engine_change",
            total_steps=5,
            completed_steps=2,
            is_template=False,
            data_source="Career Workflow Automation Engine™",
            disclaimer="AI-generated suggestion.",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert workflow.workflow_status == "active"
        assert workflow.completed_steps == 2
