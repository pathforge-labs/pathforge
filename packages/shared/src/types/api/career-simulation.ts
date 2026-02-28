/**
 * PathForge — API Types: Career Simulation Engine™
 * ==================================================
 * Types for what-if career scenarios, projections, and comparisons.
 * Mirrors: apps/api/app/schemas/career_simulation.py
 */

// ── Simulation Sub-Components ──────────────────────────────────

export interface SimulationInputResponse {
  readonly id: string;
  readonly parameter_name: string;
  readonly parameter_value: string;
  readonly parameter_type: string;
}

export interface SimulationOutcomeResponse {
  readonly id: string;
  readonly dimension: string;
  readonly current_value: number;
  readonly projected_value: number;
  readonly delta: number;
  readonly unit: string | null;
  readonly reasoning: string | null;
}

export interface SimulationRecommendationResponse {
  readonly id: string;
  readonly priority: string;
  readonly title: string;
  readonly description: string | null;
  readonly estimated_weeks: number | null;
  readonly order_index: number;
}

// ── Full Simulation ────────────────────────────────────────────

export interface CareerSimulationResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly scenario_type: string;
  readonly status: string;
  readonly confidence_score: number;
  readonly feasibility_rating: number;
  readonly roi_score: number | null;
  readonly salary_impact_percent: number | null;
  readonly estimated_months: number | null;
  readonly reasoning: string | null;
  readonly factors: Record<string, unknown> | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly computed_at: string;
  readonly inputs: SimulationInputResponse[];
  readonly outcomes: SimulationOutcomeResponse[];
  readonly recommendations: SimulationRecommendationResponse[];
}

// ── Summary (for lists/dashboard) ──────────────────────────────

export interface SimulationSummaryResponse {
  readonly id: string;
  readonly scenario_type: string;
  readonly status: string;
  readonly confidence_score: number;
  readonly salary_impact_percent: number | null;
  readonly estimated_months: number | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly computed_at: string;
}

// ── Preferences ────────────────────────────────────────────────

export interface SimulationPreferenceResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly default_scenario_type: string | null;
  readonly max_scenarios: number;
  readonly notification_enabled: boolean;
}

export interface SimulationPreferenceUpdateRequest {
  readonly default_scenario_type?: string | null;
  readonly max_scenarios?: number;
  readonly notification_enabled?: boolean;
}

// ── Comparison ─────────────────────────────────────────────────

export interface SimulationComparisonResponse {
  readonly simulations: CareerSimulationResponse[];
  readonly ranking: string[];
  readonly trade_off_analysis: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Dashboard ──────────────────────────────────────────────────

export interface SimulationDashboardResponse {
  readonly simulations: SimulationSummaryResponse[];
  readonly preferences: SimulationPreferenceResponse | null;
  readonly total_simulations: number;
  readonly scenario_type_counts: Record<string, number>;
}

// ── Request Schemas ────────────────────────────────────────────

export interface RoleTransitionSimRequest {
  readonly target_role: string;
  readonly target_industry?: string | null;
  readonly target_location?: string | null;
}

export interface GeoMoveSimRequest {
  readonly target_location: string;
  readonly keep_role?: boolean;
  readonly target_role?: string | null;
}

export interface SkillInvestmentSimRequest {
  readonly skills: string[];
  readonly target_role?: string | null;
}

export interface IndustryPivotSimRequest {
  readonly target_industry: string;
  readonly target_role?: string | null;
}

export interface SeniorityJumpSimRequest {
  readonly target_seniority: string;
  readonly target_role?: string | null;
}

export interface SimulationCompareRequest {
  readonly simulation_ids: string[];
}
