/**
 * PathForge — API Types: Transition Pathways
 * ============================================
 * Types for career transitions, skill bridges, milestones, and comparisons.
 * Mirrors: apps/api/app/schemas/transition_pathways.py
 */

// ── Skill Bridge ───────────────────────────────────────────────

export interface SkillBridgeEntryResponse {
  readonly id: string;
  readonly skill_name: string;
  readonly category: string;
  readonly is_already_held: boolean;
  readonly current_level: string | null;
  readonly required_level: string | null;
  readonly acquisition_method: string | null;
  readonly estimated_weeks: number | null;
  readonly recommended_resources: Record<string, unknown> | null;
  readonly priority: string;
  readonly impact_on_confidence: number | null;
}

// ── Milestones ─────────────────────────────────────────────────

export interface TransitionMilestoneResponse {
  readonly id: string;
  readonly phase: string;
  readonly title: string;
  readonly description: string | null;
  readonly target_week: number;
  readonly order_index: number;
  readonly is_completed: boolean;
  readonly completed_at: string | null;
}

// ── Comparison ─────────────────────────────────────────────────

export interface TransitionComparisonResponse {
  readonly id: string;
  readonly dimension: string;
  readonly source_value: number;
  readonly target_value: number;
  readonly delta: number;
  readonly unit: string | null;
  readonly reasoning: string | null;
}

// ── Transition Path ────────────────────────────────────────────

export interface TransitionPathResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly from_role: string;
  readonly to_role: string;
  readonly confidence_score: number;
  readonly difficulty: string;
  readonly status: string;
  readonly skill_overlap_percent: number;
  readonly skills_to_acquire_count: number;
  readonly estimated_duration_months: number | null;
  readonly optimistic_months: number | null;
  readonly realistic_months: number | null;
  readonly conservative_months: number | null;
  readonly salary_impact_percent: number | null;
  readonly success_probability: number;
  readonly reasoning: string | null;
  readonly factors: Record<string, unknown> | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly computed_at: string;
}

// ── Summary (for lists/dashboard) ──────────────────────────────

export interface TransitionSummaryResponse {
  readonly id: string;
  readonly from_role: string;
  readonly to_role: string;
  readonly confidence_score: number;
  readonly difficulty: string;
  readonly status: string;
  readonly skill_overlap_percent: number;
  readonly estimated_duration_months: number | null;
  readonly computed_at: string;
}

// ── Preferences ────────────────────────────────────────────────

export interface TransitionPreferenceResponse {
  readonly id: string;
  readonly preferred_industries: string[] | null;
  readonly excluded_roles: string[] | null;
  readonly min_confidence: number;
  readonly max_timeline_months: number;
  readonly notification_enabled: boolean;
}

export interface TransitionPreferenceUpdateRequest {
  readonly preferred_industries?: string[] | null;
  readonly excluded_roles?: string[] | null;
  readonly min_confidence?: number;
  readonly max_timeline_months?: number;
  readonly notification_enabled?: boolean;
}

// ── Request Schemas ────────────────────────────────────────────

export interface TransitionExploreRequest {
  readonly target_role: string;
  readonly target_industry?: string | null;
  readonly target_location?: string | null;
}

export interface TransitionCompareRequest {
  readonly target_roles: string[];
}

export interface RoleWhatIfRequest {
  readonly target_role: string;
}

// ── Composite Responses ────────────────────────────────────────

export interface TransitionScanResponse {
  readonly transition_path: TransitionPathResponse;
  readonly skill_bridge: SkillBridgeEntryResponse[];
  readonly milestones: TransitionMilestoneResponse[];
  readonly comparisons: TransitionComparisonResponse[];
}

export interface TransitionDashboardResponse {
  readonly transitions: TransitionSummaryResponse[];
  readonly preferences: TransitionPreferenceResponse | null;
  readonly total_explored: number;
}
