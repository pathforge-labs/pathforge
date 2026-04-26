/**
 * PathForge — Hook: useSessions (T1-extension / ADR-0011)
 * =========================================================
 *
 * React Query hooks for the active-session list + revoke surface.
 *
 * Pattern: a single `queryKey` for the list, and mutations that
 * invalidate it on success so the UI auto-refreshes after revoke.
 * Auth-gated via the `enabled` option (Style Guide §92) so the
 * query never fires for an unauthenticated user.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { sessionsApi } from "@/lib/api-client/sessions";
import type {
  RevokeOthersResponse,
  SessionListResponse,
} from "@/lib/api-client/sessions";

const SESSIONS_QUERY_KEY = ["sessions", "list"] as const;

export function useSessions() {
  const { isAuthenticated } = useAuth();
  return useQuery<SessionListResponse>({
    queryKey: SESSIONS_QUERY_KEY,
    queryFn: () => sessionsApi.list(),
    // Sessions are short-lived; 30 s stale lets the user refresh
    // the page and see new logins from another device quickly,
    // without polling the API on every render.
    staleTime: 30 * 1000,
    enabled: isAuthenticated,
  });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (jti: string) => sessionsApi.revoke(jti),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    },
  });
}

export function useRevokeOtherSessions() {
  const queryClient = useQueryClient();
  return useMutation<RevokeOthersResponse, Error>({
    mutationFn: () => sessionsApi.revokeOthers(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    },
  });
}
