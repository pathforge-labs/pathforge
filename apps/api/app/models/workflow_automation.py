"""
PathForge — Career Workflow Automation Engine™ Models
======================================================
Domain models for the Career Workflow Automation Engine — the
industry's first individual-facing system that converts Career
Vitals™ thresholds and engine state changes into automated,
multi-step career workflows.

Models:
    CareerWorkflow            — Multi-step career workflow definition
    WorkflowStep              — Individual step within a workflow
    WorkflowExecution         — Runtime execution of a workflow
    WorkflowPreference        — User workflow automation preferences

Enums:
    WorkflowTriggerType   — vitals_threshold | engine_change | scheduled | manual
    WorkflowStatus        — draft | active | paused | completed | archived
    StepType              — action | notification | check | decision

Proprietary Innovations:
    🔥 Threshold-Triggered Workflows™  — Career Vitals™ driven automation
    🔥 Multi-Step Career Pipeline™     — Sequential + conditional career steps
    🔥 Smart Workflow Templates™       — Pre-built career acceleration workflows
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class WorkflowTriggerType(enum.StrEnum):
    """What triggers a career workflow."""

    VITALS_THRESHOLD = "vitals_threshold"   # Career Vitals™ score crosses threshold
    ENGINE_CHANGE = "engine_change"         # Engine heartbeat state changes
    SCHEDULED = "scheduled"                 # Time-based trigger (e.g., weekly review)
    MANUAL = "manual"                      # User-initiated workflow


class WorkflowStatus(enum.StrEnum):
    """Lifecycle status of a career workflow."""

    DRAFT = "draft"            # Created but not yet activated
    ACTIVE = "active"          # Currently active and monitoring triggers
    PAUSED = "paused"          # Temporarily paused by user
    COMPLETED = "completed"    # All steps completed
    ARCHIVED = "archived"      # No longer relevant


class StepType(enum.StrEnum):
    """Type of step within a career workflow."""

    ACTION = "action"              # User action required
    NOTIFICATION = "notification"  # Send notification to user
    CHECK = "check"                # Automated condition check
    DECISION = "decision"          # User decision point (branch)


# ── CareerWorkflow ────────────────────────────────────────────


class CareerWorkflow(Base, UUIDMixin, TimestampMixin):
    """Career Workflow Automation Engine™ — Workflow Definition.

    Defines a multi-step career workflow that can be triggered
    automatically by Career Vitals™ thresholds, engine state
    changes, or user-initiated actions.

    Each workflow contains ordered steps that execute sequentially,
    with optional conditional branching at decision points.
    """

    __tablename__ = "wf_workflows"
    __table_args__ = (
        CheckConstraint(
            "total_steps >= 0",
            name="ck_wf_workflow_total_steps_positive",
        ),
    )

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    name: Mapped[str] = mapped_column(
        String(300), nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )
    workflow_status: Mapped[str] = mapped_column(
        String(20), default=WorkflowStatus.DRAFT.value,
        server_default="draft", nullable=False, index=True,
    )

    # ── Trigger configuration ──
    trigger_type: Mapped[str] = mapped_column(
        String(30), default=WorkflowTriggerType.MANUAL.value,
        server_default="manual", nullable=False, index=True,
    )
    trigger_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Workflow metadata ──
    total_steps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    completed_steps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    is_template: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )
    template_category: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )

    # ── Source context ──
    source_engine: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    source_recommendation_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="Career Workflow Automation Engine™ — automated career pipeline",
        server_default="Career Workflow Automation Engine™ — automated career pipeline",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "This workflow is AI-generated based on career intelligence "
            "signals. Steps are suggestions, not mandates. Adjust or "
            "skip steps based on your own judgment and circumstances."
        ),
        server_default=(
            "This workflow is AI-generated based on career intelligence "
            "signals. Steps are suggestions, not mandates. Adjust or "
            "skip steps based on your own judgment and circumstances."
        ),
        nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    steps: Mapped[list[WorkflowStep]] = relationship(
        "WorkflowStep",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
    )

    def __repr__(self) -> str:
        return (
            f"<CareerWorkflow(name={self.name}, "
            f"status={self.workflow_status}, "
            f"trigger={self.trigger_type}, "
            f"steps={self.completed_steps}/{self.total_steps})>"
        )


# ── WorkflowStep ─────────────────────────────────────────────


class WorkflowStep(Base, UUIDMixin, TimestampMixin):
    """Multi-Step Career Pipeline™ — Individual Workflow Step.

    Each step has a type (action, notification, check, decision),
    an order within the workflow, and completion tracking. Steps
    execute sequentially with optional conditional branching.
    """

    __tablename__ = "wf_steps"
    __table_args__ = (
        CheckConstraint(
            "step_order >= 0",
            name="ck_wf_step_order_positive",
        ),
    )

    # ── Foreign keys ──
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("wf_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    step_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    step_type: Mapped[str] = mapped_column(
        String(20), default=StepType.ACTION.value,
        server_default="action", nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
    )

    # ── Completion tracking ──
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )
    is_skipped: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )

    # ── Step configuration ──
    action_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    condition_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )

    # ── Relationships ──
    workflow: Mapped[CareerWorkflow] = relationship(
        "CareerWorkflow",
        back_populates="steps",
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowStep(order={self.step_order}, "
            f"type={self.step_type}, "
            f"completed={self.is_completed})>"
        )


# ── WorkflowExecution ────────────────────────────────────────


class WorkflowExecution(Base, UUIDMixin, TimestampMixin):
    """Career Workflow Automation Engine™ — Execution Record.

    Tracks individual execution runs of a workflow, including
    trigger context, execution state, and completion metrics.
    """

    __tablename__ = "wf_executions"

    # ── Foreign keys ──
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("wf_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Execution context ──
    trigger_context: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    career_vitals_at_trigger: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    execution_status: Mapped[str] = mapped_column(
        String(20), default="running",
        server_default="running", nullable=False,
    )
    steps_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    steps_total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )

    # ── Relationships ──
    workflow: Mapped[CareerWorkflow] = relationship("CareerWorkflow")
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<WorkflowExecution(status={self.execution_status}, "
            f"progress={self.steps_completed}/{self.steps_total})>"
        )


# ── WorkflowPreference ──────────────────────────────────────


class WorkflowPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Career Workflow Automation Engine™.

    Controls automation behavior, trigger sensitivity, and
    maximum concurrent workflows.
    """

    __tablename__ = "wf_preferences"

    # ── Foreign keys ──
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Preference fields ──
    automation_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    max_concurrent_workflows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5,
    )
    auto_activate_templates: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )
    trigger_sensitivity: Mapped[str] = mapped_column(
        String(20), default="medium",
        server_default="medium", nullable=False,
    )
    enabled_trigger_types: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<WorkflowPreference(user_id={self.user_id}, "
            f"automation={self.automation_enabled}, "
            f"max_concurrent={self.max_concurrent_workflows})>"
        )
