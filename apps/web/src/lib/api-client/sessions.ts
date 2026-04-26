/**
 * PathForge — API Client: Sessions (T1-extension / ADR-0011)
 * =============================================================
 *
 * Three endpoints under `/api/v1/users/me/sessions`:
 *
 *   - `GET    /`                — list active sessions
 *   - `DELETE /{jti}`           — revoke one
 *   - `POST   /revoke-others`   — keep current, revoke the rest
 *
 * Mutating routes carry double-submit CSRF (ADR-0006); the
 * `fetchWithAuth` helper already attaches `X-CSRF-Token` from the
 * `pathforge_csrf` cookie on every mutating request, so callers
 * don't need to touch the header by hand.
 */

import { del, get, post } from "@/lib/http";

export interface SessionItem {
  jti: string;
  device_label: string;
  user_agent: string;
  ip: string;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
}

export interface SessionListResponse {
  sessions: SessionItem[];
}

export interface RevokeOthersResponse {
  revoked_count: number;
}

export const sessionsApi = {
  /** List the authenticated user's active sessions. */
  list: (): Promise<SessionListResponse> =>
    get<SessionListResponse>("/api/v1/users/me/sessions"),

  /** Revoke a single session by its refresh JTI. 204 No Content on success. */
  revoke: (jti: string): Promise<void> =>
    del<void>(`/api/v1/users/me/sessions/${encodeURIComponent(jti)}`),

  /** "Sign out of all other devices" — keeps the current session. */
  revokeOthers: (): Promise<RevokeOthersResponse> =>
    post<RevokeOthersResponse>("/api/v1/users/me/sessions/revoke-others"),
};
