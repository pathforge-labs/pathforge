/**
 * PathForge — API Types: Career Workflow Automation Engine™
 * ==========================================================
 * Types for workflows, steps, executions, templates, and preferences.
 * Mirrors: apps/api/app/schemas/workflow_automation.py
 */

// ── Workflow Step ─────────────────────────────────────────────

export interface WorkflowStepResponse {
  readonly id: string;
  readonly workflow_id: string;
  readonly step_order: number;
  readonly step_type: string;
  readonly title: string;
  readonly description: string;
  readonly is_completed: boolean;
  readonly is_skipped: boolean;
  readonly action_config: Record<string, unknown> | null;
  readonly condition_config: Record<string, unknown> | null;
  readonly created_at: string;
  readonly updated_at: string;
}

// ── Workflow ──────────────────────────────────────────────────

export interface CareerWorkflowResponse {
  readonly id: string;
  readonly user_id: string;
  readonly name: string;
  readonly description: string;
  readonly workflow_status: string;
  readonly trigger_type: string;
  readonly trigger_config: Record<string, unknown> | null;
  readonly total_steps: number;
  readonly completed_steps: number;
  readonly is_template: boolean;
  readonly template_category: string | null;
  readonly source_engine: string | null;
  readonly source_recommendation_id: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface WorkflowSummary {
  readonly id: string;
  readonly name: string;
  readonly workflow_status: string;
  readonly trigger_type: string;
  readonly total_steps: number;
  readonly completed_steps: number;
  readonly is_template: boolean;
  readonly created_at: string;
}

// ── Workflow Execution ────────────────────────────────────────

export interface WorkflowExecutionResponse {
  readonly id: string;
  readonly workflow_id: string;
  readonly user_id: string;
  readonly trigger_context: Record<string, unknown> | null;
  readonly career_vitals_at_trigger: number | null;
  readonly execution_status: string;
  readonly steps_completed: number;
  readonly steps_total: number;
  readonly created_at: string;
  readonly updated_at: string;
}

// ── Preferences ───────────────────────────────────────────────

export interface WorkflowPreferenceResponse {
  readonly id: string;
  readonly user_id: string;
  readonly automation_enabled: boolean;
  readonly max_concurrent_workflows: number;
  readonly auto_activate_templates: boolean;
  readonly trigger_sensitivity: string;
  readonly enabled_trigger_types: string[] | null;
  readonly notifications_enabled: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

// ── Template ──────────────────────────────────────────────────

export interface WorkflowTemplateInfo {
  readonly template_id: string;
  readonly name: string;
  readonly description: string;
  readonly category: string;
  readonly trigger_type: string;
  readonly total_steps: number;
  readonly estimated_duration: string;
  readonly difficulty: string;
}

// ── Dashboard ─────────────────────────────────────────────────

export interface WorkflowDashboardResponse {
  readonly active_workflows: WorkflowSummary[];
  readonly available_templates: WorkflowTemplateInfo[];
  readonly total_active: number;
  readonly total_completed: number;
  readonly total_draft: number;
  readonly preferences: WorkflowPreferenceResponse | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Workflow List ─────────────────────────────────────────────

export interface WorkflowListResponse {
  readonly items: CareerWorkflowResponse[];
  readonly total: number;
  readonly limit: number;
  readonly offset: number;
}

// ── Request Schemas ───────────────────────────────────────────

export interface CreateWorkflowRequest {
  readonly template_id?: string | null;
  readonly name?: string | null;
  readonly trigger_type?: string;
  readonly trigger_config?: Record<string, unknown> | null;
  readonly auto_activate?: boolean;
}

export interface UpdateWorkflowStatusRequest {
  readonly workflow_status: string;
}

export interface UpdateStepStatusRequest {
  readonly action: string;
  readonly notes?: string | null;
}

export interface WorkflowPreferenceUpdate {
  readonly automation_enabled?: boolean | null;
  readonly max_concurrent_workflows?: number | null;
  readonly auto_activate_templates?: boolean | null;
  readonly trigger_sensitivity?: string | null;
  readonly enabled_trigger_types?: string[] | null;
  readonly notifications_enabled?: boolean | null;
}
