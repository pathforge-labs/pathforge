/**
 * PathForge — API Types: Salary Intelligence Engine™
 * ====================================================
 * Types for salary estimates, skill impacts, trajectory, and scenarios.
 * Mirrors: apps/api/app/schemas/salary_intelligence.py
 */

// ── Salary Estimate ────────────────────────────────────────────

export interface SalaryEstimateResponse {
  readonly id: string;
  readonly role_title: string;
  readonly location: string;
  readonly seniority_level: string;
  readonly industry: string;
  readonly estimated_min: number;
  readonly estimated_max: number;
  readonly estimated_median: number;
  readonly currency: string;
  readonly confidence: number;
  readonly market_percentile: number | null;
  readonly factors: Record<string, unknown> | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly computed_at: string;
}

// ── Skill Salary Impact ────────────────────────────────────────

export interface SkillSalaryImpactResponse {
  readonly id: string;
  readonly skill_name: string;
  readonly category: string;
  readonly salary_impact_amount: number;
  readonly salary_impact_percent: number;
  readonly demand_premium: number;
  readonly scarcity_factor: number;
  readonly impact_direction: string;
  readonly reasoning: string | null;
  readonly computed_at: string;
}

// ── Salary History ─────────────────────────────────────────────

export interface SalaryHistoryEntryResponse {
  readonly id: string;
  readonly estimated_min: number;
  readonly estimated_max: number;
  readonly estimated_median: number;
  readonly currency: string;
  readonly confidence: number;
  readonly market_percentile: number | null;
  readonly role_title: string;
  readonly location: string;
  readonly seniority_level: string;
  readonly skills_count: number;
  readonly factors_snapshot: Record<string, unknown> | null;
  readonly snapshot_date: string;
}

// ── Salary Scenario ────────────────────────────────────────────

export interface SalaryScenarioResponse {
  readonly id: string;
  readonly scenario_type: string;
  readonly scenario_label: string;
  readonly scenario_input: Record<string, unknown>;
  readonly projected_min: number;
  readonly projected_max: number;
  readonly projected_median: number;
  readonly currency: string;
  readonly delta_amount: number;
  readonly delta_percent: number;
  readonly confidence: number;
  readonly reasoning: string | null;
  readonly impact_breakdown: Record<string, unknown> | null;
  readonly computed_at: string;
}

// ── Preferences ────────────────────────────────────────────────

export interface SalaryPreferenceResponse {
  readonly id: string;
  readonly preferred_currency: string;
  readonly include_benefits: boolean;
  readonly target_salary: number | null;
  readonly target_currency: string;
  readonly notification_enabled: boolean;
  readonly notification_frequency: string;
  readonly comparison_market: string;
  readonly comparison_industries: Record<string, unknown> | null;
}

export interface SalaryPreferenceUpdateRequest {
  readonly preferred_currency?: string;
  readonly include_benefits?: boolean;
  readonly target_salary?: number | null;
  readonly target_currency?: string;
  readonly notification_enabled?: boolean;
  readonly notification_frequency?: string;
  readonly comparison_market?: string;
  readonly comparison_industries?: Record<string, unknown> | null;
}

// ── Request Schemas ────────────────────────────────────────────

export interface SalaryScenarioRequest {
  readonly scenario_type: string;
  readonly scenario_label: string;
  readonly scenario_input: Record<string, unknown>;
}

export interface SkillWhatIfRequest {
  readonly skill_name: string;
}

export interface LocationWhatIfRequest {
  readonly location: string;
}

// ── Composite Responses ────────────────────────────────────────

export interface SalaryImpactAnalysisResponse {
  readonly impacts: SkillSalaryImpactResponse[];
  readonly total_positive_impact: number;
  readonly total_negative_impact: number;
  readonly top_skill: string | null;
}

export interface SalaryScanResponse {
  readonly status: string;
  readonly estimate: SalaryEstimateResponse;
  readonly skill_impacts: SkillSalaryImpactResponse[];
  readonly history_entry: SalaryHistoryEntryResponse;
}

export interface SalaryDashboardResponse {
  readonly estimate: SalaryEstimateResponse | null;
  readonly skill_impacts: SkillSalaryImpactResponse[];
  readonly trajectory: SalaryHistoryEntryResponse[];
  readonly scenarios: SalaryScenarioResponse[];
  readonly preference: SalaryPreferenceResponse | null;
  readonly last_scan_at: string | null;
}
