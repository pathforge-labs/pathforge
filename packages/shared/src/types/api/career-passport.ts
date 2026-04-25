/**
 * PathForge — API Types: Cross-Border Career Passport™
 * ======================================================
 * Types for credential mapping, country comparison, visa assessment, and market demand.
 * Mirrors: apps/api/app/schemas/career_passport.py
 */

// ── Credential Mapping ────────────────────────────────────────

export interface CredentialMappingResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly user_id: string;
  readonly source_qualification: string;
  readonly source_country: string;
  readonly target_country: string;
  readonly equivalent_level: string;
  readonly eqf_level: string;
  readonly recognition_notes: string | null;
  readonly framework_reference: string | null;
  readonly confidence_score: number;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly created_at: string;
}

// ── Country Comparison ────────────────────────────────────────

export interface CountryComparisonResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly user_id: string;
  readonly source_country: string;
  readonly target_country: string;
  readonly cost_of_living_index: number;
  readonly salary_delta_pct: number;
  readonly purchasing_power_delta: number;
  readonly tax_impact_notes: string | null;
  readonly market_demand_level: string;
  readonly detailed_breakdown: Record<string, unknown> | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly created_at: string;
}

// ── Visa Assessment ───────────────────────────────────────────

export interface VisaAssessmentResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly user_id: string;
  readonly nationality: string;
  readonly target_country: string;
  readonly visa_type: string;
  readonly eligibility_score: number;
  readonly requirements: Record<string, unknown> | null;
  readonly processing_time_weeks: number | null;
  readonly estimated_cost: string | null;
  readonly notes: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly created_at: string;
}

// ── Market Demand ─────────────────────────────────────────────

export interface MarketDemandResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly user_id: string;
  readonly country: string;
  readonly role: string;
  readonly demand_level: string;
  readonly openings_estimate: number;
  readonly yoy_growth_pct: number | null;
  readonly top_employers: Record<string, unknown> | null;
  readonly salary_range_min: number | null;
  readonly salary_range_max: number | null;
  readonly currency: string;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly created_at: string;
}

// ── Preferences ───────────────────────────────────────────────

export interface CareerPassportPreferenceResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly preferred_countries: Record<string, unknown> | null;
  readonly nationality: string | null;
  readonly include_visa_info: boolean;
  readonly include_col_comparison: boolean;
  readonly include_market_demand: boolean;
  readonly created_at: string;
}

// ── Passport Score ────────────────────────────────────────────

export interface PassportScoreResponse {
  readonly credential_score: number;
  readonly visa_feasibility_score: number;
  readonly market_readiness_score: number;
  readonly cost_of_living_score: number;
  readonly composite_score: number;
  readonly target_country: string;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Dashboard ─────────────────────────────────────────────────

export interface CareerPassportDashboardResponse {
  readonly credential_mappings: CredentialMappingResponse[];
  readonly country_comparisons: CountryComparisonResponse[];
  readonly visa_assessments: VisaAssessmentResponse[];
  readonly preferences: CareerPassportPreferenceResponse | null;
  readonly total_mappings: number;
  readonly total_comparisons: number;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Full Passport Scan ────────────────────────────────────────

export interface PassportScanResponse {
  readonly credential_mapping: CredentialMappingResponse | null;
  readonly country_comparison: CountryComparisonResponse | null;
  readonly visa_assessment: VisaAssessmentResponse | null;
  readonly passport_score: PassportScoreResponse | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Multi-Country Comparison ──────────────────────────────────

export interface MultiCountryComparisonResponse {
  readonly comparisons: CountryComparisonResponse[];
  readonly passport_scores: PassportScoreResponse[];
  readonly recommended_country: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Request Schemas ───────────────────────────────────────────

export interface CredentialMappingRequest {
  readonly source_qualification: string;
  readonly source_country: string;
  readonly target_country: string;
}

export interface CountryComparisonRequest {
  readonly source_country: string;
  readonly target_country: string;
}

export interface MultiCountryComparisonRequest {
  readonly source_country: string;
  readonly target_countries: string[];
}

export interface VisaAssessmentRequest {
  readonly nationality: string;
  readonly target_country: string;
  readonly visa_type?: string;
}

export interface CareerPassportPreferenceUpdate {
  readonly preferred_countries?: Record<string, unknown> | null;
  readonly nationality?: string | null;
  readonly include_visa_info?: boolean;
  readonly include_col_comparison?: boolean;
  readonly include_market_demand?: boolean;
}
