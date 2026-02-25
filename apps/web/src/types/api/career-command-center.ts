/**
 * PathForge — API Types: Career Command Center™
 * ================================================
 * Types for the unified dashboard and engine status.
 */

// ── Dashboard ───────────────────────────────────────────────

export interface CommandCenterDashboardResponse {
  career_health_score: number;
  engines: EngineStatusResponse[];
  vitals_snapshot: VitalsSnapshotResponse | null;
  last_updated: string;
}

export interface EngineStatusResponse {
  engine_name: string;
  display_name: string;
  status: "active" | "inactive" | "error" | "pending";
  last_run_at: string | null;
  summary: string | null;
  health_score: number | null;
}

export interface EngineDetailResponse {
  engine_name: string;
  display_name: string;
  status: string;
  last_run_at: string | null;
  data_summary: Record<string, unknown>;
  recommendations: string[];
}

export interface VitalsSnapshotResponse {
  career_health_score: number;
  threat_level: string;
  skill_coverage: number;
  market_alignment: number;
  growth_momentum: number;
  calculated_at: string;
}

// ── Health Summary ──────────────────────────────────────────

export interface CareerHealthSummaryResponse {
  career_health_score: number;
  trend: "improving" | "stable" | "declining";
  key_insights: string[];
  action_items: string[];
}

// ── Preferences ─────────────────────────────────────────────

export interface CommandCenterPreferenceResponse {
  id: string;
  pinned_engines: string[];
  collapsed_engines: string[];
  refresh_interval: number;
}

export interface CommandCenterPreferenceUpdateRequest {
  pinned_engines?: string[];
  collapsed_engines?: string[];
  refresh_interval?: number;
}
