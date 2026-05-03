/**
 * PathForge — AI Usage API Types (T4 / Sprint 56, ADR-0008)
 * ===========================================================
 *
 * Mirrors `app/schemas/ai_usage.py`. Dual-display: every response
 * carries both call counts (free-tier signal) and EUR cost in cents
 * (premium-tier signal). The web layer chooses which to surface.
 */

export interface EngineUsageResponse {
  /** Engine principal name (e.g. "career_dna"). */
  engine: string;
  /** Number of completed AI calls in the period. */
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  /**
   * Estimated EUR cost in cents (integer to avoid float drift).
   * 0 when the model is not in the price table — see
   * `has_unpriced_models` on the parent summary.
   */
  cost_eur_cents: number;
  avg_latency_ms: number;
  /** UTC timestamp of the most recent call (ISO 8601). */
  last_call_at: string | null;
}

export interface UsageSummaryAiResponse {
  user_id: string;
  /** e.g. "current_month". */
  period_label: string;
  /** ISO 8601 UTC. */
  period_start: string;
  /** ISO 8601 UTC. */
  period_end: string;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  /**
   * Estimated EUR cost in cents across all engines. Free tier should
   * display the call counts; premium tier should display this. The
   * same response carries both per the dual-display decision.
   */
  total_cost_eur_cents: number;
  /**
   * True when at least one record's model isn't in the server-side
   * price table. UI should append "cost estimate excludes some
   * calls" messaging.
   */
  has_unpriced_models: boolean;
  engines: EngineUsageResponse[];
}
