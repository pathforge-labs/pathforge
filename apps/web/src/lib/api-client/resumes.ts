/**
 * PathForge — Resumes API Client
 * ================================
 * API client for resume management endpoints.
 */

import { fetchWithAuth } from "@/lib/http";
import type { ResumeSummary } from "@/types/api";

export const resumesApi = {
  list(): Promise<ResumeSummary[]> {
    return fetchWithAuth<ResumeSummary[]>("/api/v1/resumes/");
  },
};
