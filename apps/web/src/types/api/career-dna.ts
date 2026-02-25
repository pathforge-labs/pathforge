/**
 * PathForge — API Types: Career DNA™
 * =====================================
 * Types for Career DNA profile, dimensions, and hidden skills.
 */

// ── Profile ─────────────────────────────────────────────────

export interface CareerDnaProfileResponse {
  id: string;
  user_id: string;
  completeness_score: number;
  generated_at: string;
  created_at: string;
  updated_at: string;
  skill_genome: SkillGenomeEntryResponse[];
  experience_blueprint: ExperienceBlueprintResponse | null;
  growth_vector: GrowthVectorResponse | null;
  values_profile: ValuesProfileResponse | null;
  market_position: MarketPositionResponse | null;
  hidden_skills: HiddenSkillResponse[];
}

export interface CareerDnaSummaryResponse {
  has_profile: boolean;
  completeness_score: number;
  generated_at: string | null;
  dimension_status: Record<string, boolean>;
}

export interface CareerDnaGenerateRequest {
  dimensions?: string[];
}

// ── Skill Genome ────────────────────────────────────────────

export interface SkillGenomeEntryResponse {
  id: string;
  skill_name: string;
  category: string;
  proficiency_level: number;
  years_experience: number;
  last_used: string | null;
  growth_velocity: number;
  market_demand_score: number;
  is_ai_discovered: boolean;
  confidence_score: number;
}

// ── Experience Blueprint ────────────────────────────────────

export interface ExperienceBlueprintResponse {
  career_pattern: string;
  total_years: number;
  industry_diversity: number;
  role_progression: string;
  notable_transitions: string[];
  analysis: string;
}

// ── Growth Vector ───────────────────────────────────────────

export interface GrowthVectorResponse {
  trajectory_direction: string;
  momentum_score: number;
  projected_roles: string[];
  growth_catalysts: string[];
  risk_factors: string[];
  reasoning: string;
}

// ── Values Profile ──────────────────────────────────────────

export interface ValuesProfileResponse {
  top_values: string[];
  work_style: string;
  culture_fit_indicators: string[];
  deal_breakers: string[];
  analysis: string;
}

// ── Market Position ─────────────────────────────────────────

export interface MarketPositionResponse {
  competitiveness_score: number;
  demand_level: string;
  salary_percentile: number;
  geographic_advantage: string[];
  positioning_advice: string;
}

// ── Hidden Skills ───────────────────────────────────────────

export interface HiddenSkillResponse {
  id: string;
  skill_name: string;
  evidence: string;
  confidence: number;
  source_dimension: string;
  user_confirmed: boolean | null;
}

export interface HiddenSkillConfirmRequest {
  confirmed: boolean;
}
