/**
 * PathForge — API Types: Skill Decay & Growth Tracker
 * =====================================================
 * Types for skill freshness, market demand, velocity, and reskilling.
 * Mirrors: apps/api/app/schemas/skill_decay.py
 */

// ── Skill Freshness ────────────────────────────────────────────

export interface SkillFreshnessResponse {
  readonly id: string;
  readonly skill_name: string;
  readonly category: string;
  readonly last_active_date: string | null;
  readonly freshness_score: number;
  readonly half_life_days: number;
  readonly decay_rate: string;
  readonly days_since_active: number;
  readonly refresh_urgency: number;
  readonly analysis_reasoning: string | null;
  readonly computed_at: string;
}

// ── Market Demand ──────────────────────────────────────────────

export interface MarketDemandSnapshotResponse {
  readonly id: string;
  readonly skill_name: string;
  readonly demand_score: number;
  readonly demand_trend: string;
  readonly trend_confidence: number;
  readonly job_posting_signal: Record<string, unknown> | null;
  readonly industry_relevance: Record<string, unknown> | null;
  readonly growth_projection_6m: number | null;
  readonly growth_projection_12m: number | null;
  readonly data_sources: Record<string, unknown> | null;
  readonly snapshot_date: string;
}

// ── Skill Velocity ─────────────────────────────────────────────

export interface SkillVelocityEntryResponse {
  readonly id: string;
  readonly skill_name: string;
  readonly velocity_score: number;
  readonly velocity_direction: string;
  readonly freshness_component: number | null;
  readonly demand_component: number | null;
  readonly composite_health: number;
  readonly acceleration: number | null;
  readonly reasoning: string | null;
  readonly computed_at: string;
}

// ── Reskilling Pathways ────────────────────────────────────────

export interface ReskillingPathwayResponse {
  readonly id: string;
  readonly target_skill: string;
  readonly current_level: string;
  readonly target_level: string;
  readonly priority: string;
  readonly rationale: string | null;
  readonly estimated_effort_hours: number | null;
  readonly prerequisite_skills: Record<string, unknown> | null;
  readonly learning_resources: Record<string, unknown> | null;
  readonly career_impact: string | null;
  readonly freshness_gain: number | null;
  readonly demand_alignment: number | null;
  readonly created_at: string;
}

// ── Preferences ────────────────────────────────────────────────

export interface SkillDecayPreferenceResponse {
  readonly id: string;
  readonly tracking_enabled: boolean;
  readonly notification_frequency: string;
  readonly decay_alert_threshold: number;
  readonly focus_categories: Record<string, unknown> | null;
  readonly excluded_skills: Record<string, unknown> | null;
}

export interface SkillDecayPreferenceUpdateRequest {
  readonly tracking_enabled?: boolean;
  readonly notification_frequency?: string;
  readonly decay_alert_threshold?: number;
  readonly focus_categories?: Record<string, unknown> | null;
  readonly excluded_skills?: Record<string, unknown> | null;
}

// ── Request Schemas ────────────────────────────────────────────

export interface SkillRefreshRequest {
  readonly skill_name: string;
}

// ── Composite Responses ────────────────────────────────────────

export interface SkillDecayScanResponse {
  readonly status: string;
  readonly skills_analyzed: number;
  readonly freshness: SkillFreshnessResponse[];
  readonly market_demand: MarketDemandSnapshotResponse[];
  readonly velocity: SkillVelocityEntryResponse[];
  readonly reskilling_pathways: ReskillingPathwayResponse[];
}

export interface SkillDecayDashboardResponse {
  readonly freshness: SkillFreshnessResponse[];
  readonly freshness_summary: Record<string, unknown>;
  readonly market_demand: MarketDemandSnapshotResponse[];
  readonly velocity: SkillVelocityEntryResponse[];
  readonly reskilling_pathways: ReskillingPathwayResponse[];
  readonly preference: SkillDecayPreferenceResponse | null;
  readonly last_scan_at: string | null;
}
