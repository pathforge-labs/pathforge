/**
 * PathForge Mobile — Hook: use-career-dna
 * ==========================================
 * TanStack Query hooks for Career DNA summary and full profile.
 * Uses QUERY_STALE_TIME_MS from config (Audit Fix #17).
 */

import { useQuery } from "@tanstack/react-query";

import { getCareerDnaSummary, getCareerDnaProfile } from "../lib/api-client/career-dna";
import { QUERY_STALE_TIME_MS } from "../constants/config";

import type { CareerDnaSummaryResponse, CareerDnaProfileResponse } from "@pathforge/shared/types/api/career-dna";

// ── Query Keys ──────────────────────────────────────────────

export const CAREER_DNA_KEYS = {
  all: ["career-dna"] as const,
  summary: () => [...CAREER_DNA_KEYS.all, "summary"] as const,
  profile: () => [...CAREER_DNA_KEYS.all, "profile"] as const,
} as const;

// ── Summary Hook ────────────────────────────────────────────

export function useCareerDnaSummary(): ReturnType<typeof useQuery<CareerDnaSummaryResponse>> {
  return useQuery<CareerDnaSummaryResponse>({
    queryKey: CAREER_DNA_KEYS.summary(),
    queryFn: getCareerDnaSummary,
    staleTime: QUERY_STALE_TIME_MS,
  });
}

// ── Profile Hook ────────────────────────────────────────────

export function useCareerDnaProfile(): ReturnType<typeof useQuery<CareerDnaProfileResponse>> {
  return useQuery<CareerDnaProfileResponse>({
    queryKey: CAREER_DNA_KEYS.profile(),
    queryFn: getCareerDnaProfile,
    staleTime: QUERY_STALE_TIME_MS,
  });
}
