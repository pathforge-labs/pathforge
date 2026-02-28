/**
 * PathForge — Shared Types Package
 * ==================================
 * Central export point for all shared TypeScript types.
 * Domain-specific API types are exported via `./types/api`.
 */

export type {
  User,
  AuthTokens,
  UserRegisterPayload,
  UserLoginPayload,
} from "./types/user";

export type {
  Resume,
  Skill,
} from "./types/resume";

export type {
  JobListing,
  MatchResult,
} from "./types/job";

// Generic API wrappers (formerly in types/api.ts, now in types/api/common.ts)
export type {
  ApiResponse,
  ApiErrorResponse,
  PaginatedResponse,
  PaginationParams,
  MessageResponse,
  CountResponse,
} from "./types/api/common";

// Full API type re-exports
export type * from "./types/api";
