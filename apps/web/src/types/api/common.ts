/**
 * PathForge — API Types: Common
 * ===============================
 * Shared types used across multiple API domains.
 */

// ── Pagination ──────────────────────────────────────────────

export interface PaginatedResponse<TItem> {
  items: TItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

// ── Timestamps ──────────────────────────────────────────────

export interface Timestamped {
  created_at: string;
  updated_at?: string;
}

// ── Generic API Response ────────────────────────────────────

export interface MessageResponse {
  message: string;
}

export interface CountResponse {
  count: number;
}
