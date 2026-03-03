/**
 * PathForge — Target Role Hook
 * ================================
 * Sprint 36 WS-6: Mutation hook for target role updates.
 *
 * Uses TanStack Query useMutation with query invalidation.
 * Uses careerDnaApi domain object following existing codebase pattern.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { careerDnaApi } from "@/lib/api-client";
import type { GrowthVectorResponse } from "@/types/api";
import type { TargetRoleUpdatePayload } from "@/lib/api-client/career-dna";
import type { ApiError } from "@/lib/http";

// Re-export for consumer convenience
export type { TargetRoleUpdatePayload } from "@/lib/api-client/career-dna";

// ── Hook ──────────────────────────────────────────────────────

export function useTargetRole() {
  const queryClient = useQueryClient();

  return useMutation<GrowthVectorResponse, ApiError, TargetRoleUpdatePayload>({
    mutationFn: (payload) => careerDnaApi.updateTargetRole(payload),
    onSuccess: () => {
      // Invalidate all career DNA queries — target role affects
      // growth vector, career simulation, and transition pathways
      queryClient.invalidateQueries({ queryKey: queryKeys.careerDna.all });
    },
  });
}
