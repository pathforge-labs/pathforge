/**
 * PathForge — Blacklist API Client
 * ==================================
 * Domain-split API client for company blacklist endpoints.
 * Replaces the `blacklist` namespace from the legacy `lib/api.ts` monolith.
 */

import { fetchWithAuth } from "@/lib/http";
import type {
  BlacklistResponse,
  BlacklistListResponse,
} from "@/types/api/blacklist";

/** Add a company to the blacklist. */
export function addBlacklist(
  companyName: string,
  reason?: string,
  isCurrentEmployer?: boolean,
): Promise<BlacklistResponse> {
  return fetchWithAuth<BlacklistResponse>("/api/v1/blacklist", {
    method: "POST",
    body: JSON.stringify({
      company_name: companyName,
      reason,
      is_current_employer: isCurrentEmployer ?? false,
    }),
  });
}

/** List all blacklisted companies. */
export function listBlacklist(): Promise<BlacklistListResponse> {
  return fetchWithAuth<BlacklistListResponse>("/api/v1/blacklist");
}

/** Remove a company from the blacklist. */
export function removeBlacklist(id: string): Promise<void> {
  return fetchWithAuth<void>(`/api/v1/blacklist/${id}`, { method: "DELETE" });
}
