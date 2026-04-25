/**
 * PathForge — API Types: Common
 * ===============================
 * Shared types used across multiple API domains.
 * Includes generic API response wrappers merged from packages/shared/types/api.ts.
 */

// ── Generic Wrappers ────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiErrorResponse {
  detail: string;
  status_code: number;
}

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
