/**
 * PathForge — API Client: AI Usage (T4 / Sprint 56, ADR-0008)
 * =============================================================
 *
 * Single endpoint surface — `/api/v1/ai-usage/summary` — returns the
 * authenticated user's per-engine AI consumption for the requested
 * period.  See ADR-0008 for the dual-display rationale (the same
 * response carries both call counts and EUR cost).
 */

import { fetchWithAuth } from "@/lib/http";
import type { UsageSummaryAiResponse } from "@/types/api";

export const aiUsageApi = {
  /**
   * Get the authenticated user's AI usage summary for the period.
   *
   * `period` defaults to `"current_month"` server-side; future
   * tokens (`"last_month"`, `"current_quarter"`) extend the
   * server enum without changing this signature.
   */
  getSummary: (
    period: "current_month" = "current_month",
  ): Promise<UsageSummaryAiResponse> =>
    fetchWithAuth<UsageSummaryAiResponse>(
      `/api/v1/ai-usage/summary?period=${encodeURIComponent(period)}`,
    ),
};
