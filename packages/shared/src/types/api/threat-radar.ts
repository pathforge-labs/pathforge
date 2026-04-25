/**
 * PathForge — API Types: Career Threat Radar™
 * =============================================
 * Types for threat analysis, automation risk, and alerts.
 */

// ── Overview ────────────────────────────────────────────────

export interface ThreatRadarOverviewResponse {
  automation_risk: AutomationRiskResponse | null;
  industry_trends: IndustryTrendResponse[];
  skills_shield: SkillShieldMatrixResponse | null;
  resilience: CareerResilienceResponse | null;
  alerts_summary: { total: number; unread: number };
  scan_status: string | null;
  last_scan_at: string | null;
}

export interface ThreatRadarScanResponse {
  scan_id: string;
  status: string;
  automation_risk: AutomationRiskResponse;
  industry_trends: IndustryTrendResponse[];
  skills_shield: SkillShieldMatrixResponse;
  resilience: CareerResilienceResponse;
  alerts_generated: number;
  scanned_at: string;
}

// ── Automation Risk ─────────────────────────────────────────

export interface AutomationRiskResponse {
  id: string;
  overall_risk_score: number;
  onet_probability: number;
  llm_assessment_score: number;
  risk_level: string;
  soc_code: string;
  occupation_title: string;
  key_factors: string[];
  mitigation_strategies: string[];
  assessed_at: string;
}

// ── Industry Trends ─────────────────────────────────────────

export interface IndustryTrendResponse {
  id: string;
  trend_name: string;
  category: string;
  impact_level: string;
  description: string;
  relevance_score: number;
  time_horizon: string;
}

// ── Skills Shield ───────────────────────────────────────────

export interface SkillShieldEntryResponse {
  skill_name: string;
  classification: "shield" | "exposure" | "neutral";
  automation_resistance: number;
  market_demand: number;
  recommendation: string;
}

export interface SkillShieldMatrixResponse {
  shields: SkillShieldEntryResponse[];
  exposures: SkillShieldEntryResponse[];
  neutrals: SkillShieldEntryResponse[];
  overall_protection_score: number;
}

// ── Resilience ──────────────────────────────────────────────

export interface CareerResilienceResponse {
  overall_score: number;
  adaptability: number;
  skill_diversity: number;
  market_alignment: number;
  learning_velocity: number;
  network_strength: number;
  career_moat_score: number;
  assessed_at: string;
}

// ── Alerts ──────────────────────────────────────────────────

export type AlertStatus = "unread" | "read" | "dismissed" | "snoozed";

export interface ThreatAlertResponse {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  status: AlertStatus;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

export interface ThreatAlertListResponse {
  items: ThreatAlertResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface ThreatAlertUpdateRequest {
  status: AlertStatus;
}

// ── Preferences ─────────────────────────────────────────────

export interface AlertPreferenceResponse {
  id: string;
  email_alerts: boolean;
  push_alerts: boolean;
  alert_frequency: string;
  minimum_severity: string;
}

export interface AlertPreferenceUpdateRequest {
  email_alerts?: boolean;
  push_alerts?: boolean;
  alert_frequency?: string;
  minimum_severity?: string;
}
