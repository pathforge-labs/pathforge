/**
 * PathForge — Blacklist Types
 * =============================
 * TypeScript interfaces for company blacklist endpoints.
 */

export interface BlacklistResponse {
  id: string;
  company_name: string;
  reason: string | null;
  is_current_employer: boolean;
  created_at: string;
}

export interface BlacklistListResponse {
  items: BlacklistResponse[];
  total: number;
}
