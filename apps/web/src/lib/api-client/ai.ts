/**
 * PathForge — AI Engine API Client
 * ==================================
 * Domain-split API client for AI pipeline endpoints.
 * Replaces the `ai` namespace from the legacy `lib/api.ts` monolith.
 */

import { fetchWithAuth } from "@/lib/http";
import type {
  ParseResumeResponse,
  EmbedResumeResponse,
  MatchResponse,
  TailorCVResponse,
  IngestJobsParams,
  IngestJobsResponse,
} from "@/types/api/ai";

/** Parse raw resume text into structured data. */
export function parseResume(rawText: string): Promise<ParseResumeResponse> {
  return fetchWithAuth<ParseResumeResponse>("/api/v1/ai/parse-resume", {
    method: "POST",
    body: JSON.stringify({ raw_text: rawText }),
  });
}

/** Generate vector embedding for a parsed resume. */
export function embedResume(resumeId: string): Promise<EmbedResumeResponse> {
  return fetchWithAuth<EmbedResumeResponse>(
    `/api/v1/ai/embed-resume/${resumeId}`,
    { method: "POST" },
  );
}

/** Find semantic job matches for a resume. */
export function matchResume(
  resumeId: string,
  topK: number = 20,
): Promise<MatchResponse> {
  return fetchWithAuth<MatchResponse>(
    `/api/v1/ai/match-resume/${resumeId}`,
    {
      method: "POST",
      body: JSON.stringify({ top_k: topK }),
    },
  );
}

/** Tailor a CV for a specific job listing. */
export function tailorCV(
  resumeId: string,
  jobId: string,
): Promise<TailorCVResponse> {
  return fetchWithAuth<TailorCVResponse>("/api/v1/ai/tailor-cv", {
    method: "POST",
    body: JSON.stringify({ resume_id: resumeId, job_id: jobId }),
  });
}

/** Ingest jobs from external providers. */
export function ingestJobs(
  params: IngestJobsParams,
): Promise<IngestJobsResponse> {
  return fetchWithAuth<IngestJobsResponse>("/api/v1/ai/ingest-jobs", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
