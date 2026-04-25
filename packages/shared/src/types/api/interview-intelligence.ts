/**
 * PathForge — API Types: Interview Intelligence™
 * ================================================
 * Types for interview preparation, questions, STAR examples, and negotiation.
 * Mirrors: apps/api/app/schemas/interview_intelligence.py
 */

// ── Company Insight ───────────────────────────────────────────

export interface CompanyInsightResponse {
  readonly id: string;
  readonly insight_type: string;
  readonly title: string;
  readonly content: Record<string, unknown> | null;
  readonly summary: string | null;
  readonly source: string | null;
  readonly confidence: number;
}

// ── Interview Question ────────────────────────────────────────

export interface InterviewQuestionResponse {
  readonly id: string;
  readonly category: string;
  readonly question_text: string;
  readonly suggested_answer: string | null;
  readonly answer_strategy: string | null;
  readonly frequency_weight: number;
  readonly difficulty_level: string | null;
  readonly order_index: number;
}

// ── STAR Example ──────────────────────────────────────────────

export interface STARExampleResponse {
  readonly id: string;
  readonly question_id: string | null;
  readonly situation: string;
  readonly task: string;
  readonly action: string;
  readonly result: string;
  readonly career_dna_dimension: string | null;
  readonly source_experience: string | null;
  readonly relevance_score: number;
  readonly order_index: number;
}

// ── Interview Prep ────────────────────────────────────────────

export interface InterviewPrepResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly company_name: string;
  readonly target_role: string;
  readonly status: string;
  readonly prep_depth: string;
  readonly confidence_score: number;
  readonly culture_alignment_score: number | null;
  readonly interview_format: string | null;
  readonly company_brief: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly computed_at: string;
  readonly insights: CompanyInsightResponse[];
  readonly questions: InterviewQuestionResponse[];
  readonly star_examples: STARExampleResponse[];
}

export interface InterviewPrepSummaryResponse {
  readonly id: string;
  readonly company_name: string;
  readonly target_role: string;
  readonly status: string;
  readonly confidence_score: number;
  readonly culture_alignment_score: number | null;
  readonly prep_depth: string;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly computed_at: string;
}

// ── Negotiation Script ────────────────────────────────────────

export interface NegotiationScriptResponse {
  readonly interview_prep_id: string;
  readonly company_name: string;
  readonly target_role: string;
  readonly salary_range_min: number | null;
  readonly salary_range_max: number | null;
  readonly salary_range_median: number | null;
  readonly currency: string;
  readonly opening_script: string;
  readonly counteroffer_script: string;
  readonly fallback_script: string;
  readonly key_arguments: string[];
  readonly skill_premiums: Record<string, number>;
  readonly market_position_summary: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Preferences ───────────────────────────────────────────────

export interface InterviewPreferenceResponse {
  readonly id: string;
  readonly career_dna_id: string;
  readonly default_prep_depth: string | null;
  readonly max_saved_preps: number;
  readonly include_salary_negotiation: boolean;
  readonly notification_enabled: boolean;
}

// ── Dashboard ─────────────────────────────────────────────────

export interface InterviewDashboardResponse {
  readonly preps: InterviewPrepSummaryResponse[];
  readonly preferences: InterviewPreferenceResponse | null;
  readonly total_preps: number;
  readonly company_counts: Record<string, number>;
}

// ── Comparison ────────────────────────────────────────────────

export interface InterviewPrepComparisonResponse {
  readonly preps: InterviewPrepResponse[];
  readonly ranking: string[];
  readonly comparison_summary: string | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Request Schemas ───────────────────────────────────────────

export interface InterviewPrepRequest {
  readonly company_name: string;
  readonly target_role: string;
  readonly prep_depth?: "quick" | "standard" | "comprehensive" | null;
}

export interface GenerateQuestionsRequest {
  readonly category_filter?: string | null;
  readonly max_questions?: number;
}

export interface GenerateSTARExamplesRequest {
  readonly question_ids?: string[] | null;
  readonly max_examples?: number;
}

export interface GenerateNegotiationScriptRequest {
  readonly target_salary?: number | null;
  readonly currency?: string;
}

export interface InterviewPreferenceUpdateRequest {
  readonly default_prep_depth?: string | null;
  readonly max_saved_preps?: number | null;
  readonly include_salary_negotiation?: boolean | null;
  readonly notification_enabled?: boolean | null;
}

export interface InterviewPrepCompareRequest {
  readonly prep_ids: string[];
}
