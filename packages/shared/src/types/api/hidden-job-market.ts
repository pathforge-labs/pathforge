/**
 * PathForge — API Types: Hidden Job Market Detector™
 * =====================================================
 * Types for company signal detection, outreach, and opportunity surfacing.
 * Mirrors: apps/api/app/schemas/hidden_job_market.py
 */

// ── Signal Match ──────────────────────────────────────────────

export interface SignalMatchResultResponse {
  readonly id: string;
  readonly signal_id: string;
  readonly match_score: number;
  readonly skill_overlap: number;
  readonly role_relevance: number;
  readonly explanation: string | null;
  readonly matched_skills: Record<string, unknown> | null;
  readonly relevance_reasoning: string | null;
  readonly created_at: string;
}

// ── Outreach Template ─────────────────────────────────────────

export interface OutreachTemplateResponse {
  readonly id: string;
  readonly signal_id: string;
  readonly template_type: string;
  readonly tone: string;
  readonly subject_line: string;
  readonly body: string;
  readonly personalization_points: Record<string, unknown> | null;
  readonly confidence: number;
  readonly created_at: string;
}

// ── Hidden Opportunity ────────────────────────────────────────

export interface HiddenOpportunityResponse {
  readonly id: string;
  readonly signal_id: string;
  readonly predicted_role: string;
  readonly predicted_department: string;
  readonly time_horizon: string;
  readonly probability: number;
  readonly reasoning: string | null;
  readonly required_skills: Record<string, unknown> | null;
  readonly salary_range_min: number | null;
  readonly salary_range_max: number | null;
  readonly currency: string;
  readonly created_at: string;
}

// ── Company Signal ────────────────────────────────────────────

export interface CompanySignalResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly user_id: string;
  readonly company_name: string;
  readonly industry: string | null;
  readonly signal_type: string;
  readonly title: string;
  readonly description: string | null;
  readonly strength: number;
  readonly status: string;
  readonly confidence_score: number;
  readonly evidence: Record<string, unknown> | null;
  readonly detected_at: string;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly match_results: SignalMatchResultResponse[];
  readonly outreach_templates: OutreachTemplateResponse[];
  readonly hidden_opportunities: HiddenOpportunityResponse[];
  readonly created_at: string;
}

export interface CompanySignalSummaryResponse {
  readonly id: string;
  readonly company_name: string;
  readonly signal_type: string;
  readonly title: string;
  readonly strength: number;
  readonly status: string;
  readonly confidence_score: number;
  readonly detected_at: string;
  readonly match_score: number | null;
}

// ── Preferences ───────────────────────────────────────────────

export interface HiddenJobMarketPreferenceResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly min_signal_strength: number;
  readonly enabled_signal_types: Record<string, unknown> | null;
  readonly max_outreach_per_week: number;
  readonly auto_generate_outreach: boolean;
  readonly notification_enabled: boolean;
  readonly created_at: string;
}

// ── Dashboard ─────────────────────────────────────────────────

export interface HiddenJobMarketDashboardResponse {
  readonly signals: CompanySignalSummaryResponse[];
  readonly preferences: HiddenJobMarketPreferenceResponse | null;
  readonly total_signals: number;
  readonly active_signals: number;
  readonly average_match_score: number;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Comparison ────────────────────────────────────────────────

export interface SignalComparisonResponse {
  readonly signals: CompanySignalResponse[];
  readonly comparison_summary: string | null;
  readonly recommended_signal_id: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Opportunity Radar ─────────────────────────────────────────

export interface OpportunityRadarResponse {
  readonly opportunities: HiddenOpportunityResponse[];
  readonly total_opportunities: number;
  readonly top_industries: string[];
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Request Schemas ───────────────────────────────────────────

export interface ScanCompanyRequest {
  readonly company_name: string;
  readonly industry?: string | null;
  readonly focus_signal_types?: string[] | null;
}

export interface ScanIndustryRequest {
  readonly industry: string;
  readonly region?: string | null;
  readonly max_companies?: number;
}

export interface SignalCompareRequest {
  readonly signal_ids: string[];
}

export interface GenerateOutreachRequest {
  readonly template_type?: string;
  readonly tone?: string;
}

export interface DismissSignalRequest {
  readonly reason?: string;
}

export interface HiddenJobMarketPreferenceUpdateRequest {
  readonly min_signal_strength?: number;
  readonly enabled_signal_types?: Record<string, unknown> | null;
  readonly max_outreach_per_week?: number;
  readonly auto_generate_outreach?: boolean;
  readonly notification_enabled?: boolean;
}
