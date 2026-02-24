"""
PathForge — Career Workflow Automation Engine™ Schemas
=======================================================
Pydantic request/response schemas for the Workflow Automation API.

Response Schemas (7):
    CareerWorkflowResponse       — Full workflow with steps
    WorkflowStepResponse         — Individual step detail
    WorkflowExecutionResponse    — Execution run record
    WorkflowDashboardResponse    — Dashboard with active workflows
    WorkflowPreferenceResponse   — User automation preferences
    WorkflowSummary              — Lightweight workflow overview
    WorkflowTemplateInfo         — Template metadata for browsing

Request Schemas (4):
    CreateWorkflowRequest        — Create new workflow from template
    UpdateWorkflowStatusRequest  — Update workflow lifecycle
    UpdateStepStatusRequest      — Mark step completed/skipped
    WorkflowPreferenceUpdate     — Update automation preferences
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Response Schemas ─────────────────────────────────────────


class WorkflowStepResponse(BaseModel):
    """Multi-Step Career Pipeline™ — individual step detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    step_order: int = Field(..., ge=0)
    step_type: str = Field(
        ...,
        description="action | notification | check | decision",
    )
    title: str
    description: str
    is_completed: bool = False
    is_skipped: bool = False
    action_config: dict[str, object] | None = None
    condition_config: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime


class CareerWorkflowResponse(BaseModel):
    """Career Workflow Automation Engine™ — full workflow detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str
    workflow_status: str = Field(
        ...,
        description="draft | active | paused | completed | archived",
    )
    trigger_type: str = Field(
        ...,
        description="vitals_threshold | engine_change | scheduled | manual",
    )
    trigger_config: dict[str, object] | None = None
    total_steps: int = Field(0, ge=0)
    completed_steps: int = Field(0, ge=0)
    is_template: bool = False
    template_category: str | None = None
    source_engine: str | None = None
    source_recommendation_id: str | None = None
    data_source: str
    disclaimer: str
    created_at: datetime
    updated_at: datetime


class WorkflowSummary(BaseModel):
    """Lightweight workflow overview for lists."""

    id: uuid.UUID
    name: str
    workflow_status: str
    trigger_type: str
    total_steps: int = 0
    completed_steps: int = 0
    is_template: bool = False
    created_at: datetime


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution run record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    user_id: uuid.UUID
    trigger_context: dict[str, object] | None = None
    career_vitals_at_trigger: float | None = None
    execution_status: str
    steps_completed: int = 0
    steps_total: int = 0
    created_at: datetime
    updated_at: datetime


class WorkflowPreferenceResponse(BaseModel):
    """User automation preference settings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    automation_enabled: bool = True
    max_concurrent_workflows: int = Field(5, ge=1, le=20)
    auto_activate_templates: bool = False
    trigger_sensitivity: str = "medium"
    enabled_trigger_types: list[str] | None = None
    notifications_enabled: bool = True
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateInfo(BaseModel):
    """Template metadata for browsing Smart Workflow Templates™."""

    template_id: str
    name: str
    description: str
    category: str
    trigger_type: str
    total_steps: int
    estimated_duration: str
    difficulty: str


class WorkflowDashboardResponse(BaseModel):
    """Career Workflow Automation Engine™ dashboard."""

    active_workflows: list[WorkflowSummary] = Field(default_factory=list)
    available_templates: list[WorkflowTemplateInfo] = Field(
        default_factory=list,
    )
    total_active: int = 0
    total_completed: int = 0
    total_draft: int = 0
    preferences: WorkflowPreferenceResponse | None = None
    data_source: str = (
        "Career Workflow Automation Engine™ — automated career pipelines"
    )
    disclaimer: str = (
        "Workflows are AI-generated suggestions based on career "
        "intelligence signals. Adjust or skip steps based on your "
        "own judgment and circumstances."
    )


# ── Request Schemas ──────────────────────────────────────────


class CreateWorkflowRequest(BaseModel):
    """Create new workflow — from template or custom."""

    template_id: str | None = Field(
        None,
        description="Template ID to create from. Null for custom workflow.",
    )
    name: str | None = Field(
        None, max_length=300,
        description="Custom name. Auto-generated from template if null.",
    )
    trigger_type: str = Field(
        "manual",
        description="vitals_threshold | engine_change | scheduled | manual",
    )
    trigger_config: dict[str, object] | None = Field(
        None,
        description="Trigger-specific configuration (thresholds, schedules).",
    )
    auto_activate: bool = Field(
        False,
        description="Activate immediately after creation.",
    )


class UpdateWorkflowStatusRequest(BaseModel):
    """Update workflow lifecycle status."""

    workflow_status: str = Field(
        ...,
        description="active | paused | archived",
    )


class UpdateStepStatusRequest(BaseModel):
    """Mark workflow step as completed or skipped."""

    action: str = Field(
        ...,
        description="complete | skip",
    )
    notes: str | None = Field(
        None, max_length=1000,
        description="Optional notes about the action.",
    )


class WorkflowPreferenceUpdate(BaseModel):
    """Update workflow automation preferences."""

    automation_enabled: bool | None = Field(
        None,
        description="Enable/disable workflow automation.",
    )
    max_concurrent_workflows: int | None = Field(
        None, ge=1, le=20,
        description="Max concurrent active workflows (1-20).",
    )
    auto_activate_templates: bool | None = Field(
        None,
        description="Auto-activate workflows from templates.",
    )
    trigger_sensitivity: str | None = Field(
        None,
        description="low | medium | high — trigger sensitivity level.",
    )
    enabled_trigger_types: list[str] | None = Field(
        None,
        description="Trigger types to enable.",
    )
    notifications_enabled: bool | None = Field(
        None,
        description="Enable/disable workflow notifications.",
    )
