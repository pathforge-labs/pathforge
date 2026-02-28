/**
 * PathForge — AI Engine Types
 * ============================
 * TypeScript interfaces for AI pipeline endpoints.
 */

// ── Resume Parsing ─────────────────────────────────────────

export interface ParseResumeResponse {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  skills: Array<{ name: string; category?: string; level?: string }>;
  experience: Array<{
    title: string;
    company: string;
    description?: string;
    start_date?: string;
    end_date?: string;
  }>;
  education: Array<{ degree: string; institution: string; year?: string }>;
  certifications: Array<{ name: string; issuer?: string; year?: string }>;
  languages: Array<{ name: string; proficiency?: string }>;
}

// ── Resume Embedding ───────────────────────────────────────

export interface EmbedResumeResponse {
  resume_id: string;
  dimensions: number;
  message: string;
}

// ── Job Matching ───────────────────────────────────────────

export interface MatchCandidate {
  job_id: string;
  score: number;
  title: string;
  company: string;
}

export interface MatchResponse {
  resume_id: string;
  matches: MatchCandidate[];
  total: number;
}

// ── CV Tailoring ───────────────────────────────────────────

export interface TailorCVResponse {
  tailored_summary: string;
  tailored_skills: string[];
  tailored_experience: string[];
  diffs: Array<{
    field: string;
    original: string;
    modified: string;
    reason: string;
  }>;
  ats_score: number;
  ats_suggestions: string[];
}

// ── Job Ingestion ──────────────────────────────────────────

export interface IngestJobsParams {
  keywords: string;
  location?: string;
  country?: string;
  pages?: number;
  results_per_page?: number;
  embed?: boolean;
}

export interface IngestJobsResponse {
  total_fetched: number;
  total_new: number;
  total_duplicates: number;
  providers: Array<{
    provider: string;
    fetched: number;
    new: number;
    duplicates: number;
    errors: number;
  }>;
  embedded: number;
}
