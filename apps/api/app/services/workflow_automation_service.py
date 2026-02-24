"""
PathForge — Career Workflow Automation Engine™ Service
=======================================================
Service layer for the Career Workflow Automation Engine —
converts Career Vitals™ thresholds and engine state changes
into automated, multi-step career workflows.

Methods:
    get_dashboard()               — Dashboard with active workflows + templates
    create_workflow()             — Create from template or custom
    get_workflow_detail()         — Single workflow with steps
    update_workflow_status()      — Update workflow lifecycle
    update_step_status()          — Mark step completed/skipped
    list_workflows()              — Paginated list with filters
    get_executions()              — List execution records
    get_preferences()             — User preference retrieval
    update_preferences()          — User preference update

Smart Workflow Templates™:
    Pre-built career acceleration workflows that can be
    instantiated with a single API call.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow_automation import (
    CareerWorkflow,
    StepType,
    WorkflowExecution,
    WorkflowPreference,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTriggerType,
)

# ── Smart Workflow Templates™ ────────────────────────────────

WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = {
    "skill_acceleration": {
        "name": "Skill Acceleration Pipeline",
        "description": (
            "Accelerate skill development through a structured "
            "learning-practice-validate cycle. Triggered when "
            "Skill Decay Tracker detects declining freshness."
        ),
        "category": "skill_development",
        "trigger_type": WorkflowTriggerType.ENGINE_CHANGE.value,
        "estimated_duration": "2-4 weeks",
        "difficulty": "moderate",
        "steps": [
            {
                "type": StepType.CHECK.value,
                "title": "Assess current skill freshness scores",
                "description": "Review Skill Decay Tracker for declining skills.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Select learning resources for target skills",
                "description": "Choose courses, tutorials, or certifications.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Complete learning module (week 1-2)",
                "description": "Dedicate focused time to learning materials.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Build practice project applying new skills",
                "description": "Create a real-world project demonstrating competency.",
            },
            {
                "type": StepType.NOTIFICATION.value,
                "title": "Refresh Career Vitals™ snapshot",
                "description": "Re-run skill analysis to measure improvement.",
            },
        ],
    },
    "threat_response": {
        "name": "Threat Response Workflow",
        "description": (
            "Systematic response to career threats detected by "
            "Threat Radar™. Activated when automation risk or "
            "industry disruption scores cross critical thresholds."
        ),
        "category": "risk_mitigation",
        "trigger_type": WorkflowTriggerType.VITALS_THRESHOLD.value,
        "estimated_duration": "1-3 months",
        "difficulty": "significant",
        "steps": [
            {
                "type": StepType.CHECK.value,
                "title": "Analyze threat severity and timeline",
                "description": "Review Threat Radar for specific risk factors.",
            },
            {
                "type": StepType.DECISION.value,
                "title": "Choose mitigation strategy",
                "description": "Upskill, pivot, or hedge against the threat.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Begin mitigation actions (phase 1)",
                "description": "Execute first wave of protective career actions.",
            },
            {
                "type": StepType.CHECK.value,
                "title": "Mid-point progress assessment",
                "description": "Re-evaluate threat level and mitigation effectiveness.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Complete mitigation actions (phase 2)",
                "description": "Finalize remaining protective actions.",
            },
            {
                "type": StepType.NOTIFICATION.value,
                "title": "Update resilience score",
                "description": "Refresh Career Resilience Snapshot to verify improvement.",
            },
        ],
    },
    "opportunity_capture": {
        "name": "Opportunity Capture Pipeline",
        "description": (
            "Fast-track pipeline for pursuing career opportunities "
            "detected by Hidden Job Market™ or Recommendation "
            "Intelligence. Optimized for speed."
        ),
        "category": "opportunity",
        "trigger_type": WorkflowTriggerType.ENGINE_CHANGE.value,
        "estimated_duration": "1-2 weeks",
        "difficulty": "moderate",
        "steps": [
            {
                "type": StepType.CHECK.value,
                "title": "Evaluate opportunity fit and timeline",
                "description": "Review opportunity details from source engine.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Update resume for target role",
                "description": "Tailor CV with relevant highlights and keywords.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Prepare interview materials",
                "description": "Review STAR examples and company research.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Submit application or make outreach",
                "description": "Apply directly or reach out to company contacts.",
            },
            {
                "type": StepType.NOTIFICATION.value,
                "title": "Track application status",
                "description": "Set reminder to follow up within 5 business days.",
            },
        ],
    },
    "salary_negotiation": {
        "name": "Salary Negotiation Playbook",
        "description": (
            "Data-driven salary negotiation workflow powered by "
            "Salary Intelligence™ market data. Prepares you with "
            "evidence-based compensation arguments."
        ),
        "category": "compensation",
        "trigger_type": WorkflowTriggerType.MANUAL.value,
        "estimated_duration": "1-2 weeks",
        "difficulty": "moderate",
        "steps": [
            {
                "type": StepType.CHECK.value,
                "title": "Gather market compensation data",
                "description": "Pull Salary Intelligence™ benchmarks for your role.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Document your value proposition",
                "description": "List achievements, impact metrics, and unique skills.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Prepare negotiation talking points",
                "description": "Structure your ask with market data and personal impact.",
            },
            {
                "type": StepType.DECISION.value,
                "title": "Schedule negotiation meeting",
                "description": "Choose optimal timing for the conversation.",
            },
            {
                "type": StepType.NOTIFICATION.value,
                "title": "Post-negotiation review",
                "description": "Document outcome and update salary tracking.",
            },
        ],
    },
    "career_review": {
        "name": "Quarterly Career Review",
        "description": (
            "Comprehensive quarterly career health review using all "
            "12 Career Vitals™ engines. Scheduled workflow that runs "
            "every 90 days for continuous career monitoring."
        ),
        "category": "planning",
        "trigger_type": WorkflowTriggerType.SCHEDULED.value,
        "estimated_duration": "2-3 hours",
        "difficulty": "quick_win",
        "steps": [
            {
                "type": StepType.CHECK.value,
                "title": "Refresh Career Vitals™ snapshot",
                "description": "Get latest health score and engine statuses.",
            },
            {
                "type": StepType.CHECK.value,
                "title": "Review active recommendations",
                "description": "Check pending and in-progress recommendations.",
            },
            {
                "type": StepType.ACTION.value,
                "title": "Update career goals and milestones",
                "description": "Adjust action plan based on latest data.",
            },
            {
                "type": StepType.NOTIFICATION.value,
                "title": "Generate quarterly summary",
                "description": "Create a snapshot of progress for personal records.",
            },
        ],
    },
}


# ── Service Class ─────────────────────────────────────────────


class WorkflowAutomationService:
    """Career Workflow Automation Engine™ — Service Layer.

    Orchestrates workflow creation, execution, step management,
    and template instantiation.
    """

    # ── Dashboard ─────────────────────────────────────────

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get Workflow Automation dashboard.

        Returns active workflows, available templates, status counts,
        and user preferences.
        """
        # Active workflows
        active_result = await db.execute(
            select(CareerWorkflow)
            .where(
                CareerWorkflow.user_id == str(user_id),
                CareerWorkflow.workflow_status.in_([
                    WorkflowStatus.ACTIVE.value,
                    WorkflowStatus.DRAFT.value,
                ]),
            )
            .order_by(desc(CareerWorkflow.updated_at))
            .limit(10)
        )
        active_workflows = list(active_result.scalars().all())

        # Status counts
        counts: dict[str, int] = {}
        for status_val in [
            WorkflowStatus.ACTIVE.value,
            WorkflowStatus.COMPLETED.value,
            WorkflowStatus.DRAFT.value,
        ]:
            count_result = await db.execute(
                select(func.count())
                .select_from(CareerWorkflow)
                .where(
                    CareerWorkflow.user_id == str(user_id),
                    CareerWorkflow.workflow_status == status_val,
                )
            )
            counts[status_val] = count_result.scalar_one()

        # Templates
        templates = _get_template_info_list()

        # Preferences
        pref = await WorkflowAutomationService.get_preferences(
            db, user_id=user_id,
        )

        return {
            "active_workflows": active_workflows,
            "available_templates": templates,
            "total_active": counts.get("active", 0),
            "total_completed": counts.get("completed", 0),
            "total_draft": counts.get("draft", 0),
            "preferences": pref,
        }

    # ── Create Workflow ───────────────────────────────────

    @staticmethod
    async def create_workflow(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        template_id: str | None = None,
        name: str | None = None,
        trigger_type: str = "manual",
        trigger_config: dict[str, Any] | None = None,
        auto_activate: bool = False,
    ) -> CareerWorkflow:
        """Create workflow from template or custom.

        If template_id is provided, creates from Smart Workflow
        Templates™ library. Otherwise creates an empty custom workflow.
        """
        if template_id:
            template = WORKFLOW_TEMPLATES.get(template_id)
            if template is None:
                valid_ids = ", ".join(WORKFLOW_TEMPLATES.keys())
                msg = (
                    f"Template '{template_id}' not found. "
                    f"Valid templates: {valid_ids}"
                )
                raise ValueError(msg)

            workflow_name = name or template["name"]
            workflow = CareerWorkflow(
                user_id=str(user_id),
                name=workflow_name,
                description=template["description"],
                workflow_status=(
                    WorkflowStatus.ACTIVE.value
                    if auto_activate
                    else WorkflowStatus.DRAFT.value
                ),
                trigger_type=template["trigger_type"],
                trigger_config=trigger_config,
                total_steps=len(template["steps"]),
                is_template=False,
                template_category=template["category"],
            )
            db.add(workflow)
            await db.flush()

            # Create steps
            for index, step_data in enumerate(template["steps"]):
                step = WorkflowStep(
                    workflow_id=str(workflow.id),
                    step_order=index,
                    step_type=step_data["type"],
                    title=step_data["title"],
                    description=step_data["description"],
                )
                db.add(step)

        else:
            workflow = CareerWorkflow(
                user_id=str(user_id),
                name=name or "Custom Career Workflow",
                description="User-created custom workflow.",
                workflow_status=(
                    WorkflowStatus.ACTIVE.value
                    if auto_activate
                    else WorkflowStatus.DRAFT.value
                ),
                trigger_type=trigger_type,
                trigger_config=trigger_config,
                total_steps=0,
            )
            db.add(workflow)

        await db.commit()
        await db.refresh(workflow)
        return workflow

    # ── Workflow Detail ───────────────────────────────────

    @staticmethod
    async def get_workflow_detail(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        workflow_id: uuid.UUID,
    ) -> CareerWorkflow | None:
        """Get single workflow with steps."""
        result = await db.execute(
            select(CareerWorkflow)
            .options(selectinload(CareerWorkflow.steps))
            .where(
                CareerWorkflow.id == str(workflow_id),
                CareerWorkflow.user_id == str(user_id),
            )
        )
        return result.scalar_one_or_none()

    # ── Update Workflow Status ────────────────────────────

    @staticmethod
    async def update_workflow_status(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        workflow_id: uuid.UUID,
        new_status: str,
    ) -> CareerWorkflow:
        """Update workflow lifecycle status.

        Valid transitions:
            draft → active, archived
            active → paused, completed, archived
            paused → active, archived
        """
        result = await db.execute(
            select(CareerWorkflow)
            .where(
                CareerWorkflow.id == str(workflow_id),
                CareerWorkflow.user_id == str(user_id),
            )
        )
        workflow = result.scalar_one_or_none()
        if workflow is None:
            msg = f"Workflow {workflow_id} not found."
            raise ValueError(msg)

        valid_transitions: dict[str, list[str]] = {
            "draft": ["active", "archived"],
            "active": ["paused", "completed", "archived"],
            "paused": ["active", "archived"],
            "completed": [],
            "archived": [],
        }
        allowed = valid_transitions.get(workflow.workflow_status, [])
        if new_status not in allowed:
            msg = (
                f"Cannot transition from '{workflow.workflow_status}' "
                f"to '{new_status}'. Allowed: {allowed}"
            )
            raise ValueError(msg)

        workflow.workflow_status = new_status
        await db.commit()
        await db.refresh(workflow)
        return workflow

    # ── Update Step Status ────────────────────────────────

    @staticmethod
    async def update_step_status(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        workflow_id: uuid.UUID,
        step_id: uuid.UUID,
        action: str,
    ) -> WorkflowStep:
        """Mark workflow step as completed or skipped.

        Also updates the workflow's completed_steps counter and
        auto-completes the workflow if all steps are done.
        """
        # Verify ownership
        wf_result = await db.execute(
            select(CareerWorkflow)
            .where(
                CareerWorkflow.id == str(workflow_id),
                CareerWorkflow.user_id == str(user_id),
            )
        )
        workflow = wf_result.scalar_one_or_none()
        if workflow is None:
            msg = f"Workflow {workflow_id} not found."
            raise ValueError(msg)

        # Get step
        step_result = await db.execute(
            select(WorkflowStep)
            .where(
                WorkflowStep.id == str(step_id),
                WorkflowStep.workflow_id == str(workflow_id),
            )
        )
        step = step_result.scalar_one_or_none()
        if step is None:
            msg = f"Step {step_id} not found in workflow {workflow_id}."
            raise ValueError(msg)

        if action == "complete":
            step.is_completed = True
        elif action == "skip":
            step.is_skipped = True
        else:
            msg = f"Invalid action '{action}'. Use 'complete' or 'skip'."
            raise ValueError(msg)

        # Update workflow completed count
        count_result = await db.execute(
            select(func.count())
            .select_from(WorkflowStep)
            .where(
                WorkflowStep.workflow_id == str(workflow_id),
                (WorkflowStep.is_completed.is_(True))
                | (WorkflowStep.is_skipped.is_(True)),
            )
        )
        workflow.completed_steps = count_result.scalar_one()

        # Auto-complete if all steps done
        if workflow.completed_steps >= workflow.total_steps > 0:
            workflow.workflow_status = WorkflowStatus.COMPLETED.value

        await db.commit()
        await db.refresh(step)
        return step

    # ── List Workflows ────────────────────────────────────

    @staticmethod
    async def list_workflows(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CareerWorkflow]:
        """List workflows with optional status filter."""
        query = (
            select(CareerWorkflow)
            .where(CareerWorkflow.user_id == str(user_id))
        )

        if status_filter:
            query = query.where(
                CareerWorkflow.workflow_status == status_filter,
            )

        query = (
            query
            .order_by(desc(CareerWorkflow.updated_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    # ── Executions ────────────────────────────────────────

    @staticmethod
    async def get_executions(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        workflow_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> list[WorkflowExecution]:
        """List workflow execution records."""
        query = select(WorkflowExecution).where(
            WorkflowExecution.user_id == str(user_id),
        )

        if workflow_id:
            query = query.where(
                WorkflowExecution.workflow_id == str(workflow_id),
            )

        query = (
            query
            .order_by(desc(WorkflowExecution.created_at))
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    # ── Preferences ───────────────────────────────────────

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> WorkflowPreference | None:
        """Get user's Workflow Automation preferences."""
        result = await db.execute(
            select(WorkflowPreference)
            .where(WorkflowPreference.user_id == str(user_id))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> WorkflowPreference:
        """Update or create Workflow Automation preferences."""
        result = await db.execute(
            select(WorkflowPreference)
            .where(WorkflowPreference.user_id == str(user_id))
        )
        pref = result.scalar_one_or_none()

        if pref is None:
            pref = WorkflowPreference(
                user_id=str(user_id),
                **updates,
            )
            db.add(pref)
        else:
            for key, value in updates.items():
                if hasattr(pref, key):
                    setattr(pref, key, value)

        await db.commit()
        await db.refresh(pref)
        return pref


# ── Template Helpers ─────────────────────────────────────────


def _get_template_info_list() -> list[dict[str, Any]]:
    """Get template metadata for dashboard browsing."""
    return [
        {
            "template_id": template_id,
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "trigger_type": template["trigger_type"],
            "total_steps": len(template["steps"]),
            "estimated_duration": template["estimated_duration"],
            "difficulty": template["difficulty"],
        }
        for template_id, template in WORKFLOW_TEMPLATES.items()
    ]
