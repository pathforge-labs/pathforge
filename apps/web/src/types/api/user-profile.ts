/**
 * PathForge — API Types: User Profile & GDPR
 * =============================================
 * Types for user profile management and data exports.
 */

export interface UserProfileResponse {
  id: string;
  user_id: string;
  headline: string | null;
  bio: string | null;
  location: string | null;
  phone: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  website_url: string | null;
  preferred_job_titles: string[];
  preferred_locations: string[];
  preferred_industries: string[];
  salary_expectation_min: number | null;
  salary_expectation_max: number | null;
  salary_currency: string;
  remote_preference: string;
  created_at: string;
  updated_at: string;
}

export interface UserProfileCreateRequest {
  headline?: string;
  bio?: string;
  location?: string;
  phone?: string;
  linkedin_url?: string;
  github_url?: string;
  website_url?: string;
  preferred_job_titles?: string[];
  preferred_locations?: string[];
  preferred_industries?: string[];
  salary_expectation_min?: number;
  salary_expectation_max?: number;
  salary_currency?: string;
  remote_preference?: string;
}

export interface UserProfileUpdateRequest {
  headline?: string;
  bio?: string;
  location?: string;
  phone?: string;
  linkedin_url?: string;
  github_url?: string;
  website_url?: string;
  preferred_job_titles?: string[];
  preferred_locations?: string[];
  preferred_industries?: string[];
  salary_expectation_min?: number | null;
  salary_expectation_max?: number | null;
  salary_currency?: string;
  remote_preference?: string;
}

export interface OnboardingStatusResponse {
  profile_complete: boolean;
  resume_uploaded: boolean;
  career_dna_generated: boolean;
  steps_completed: number;
  total_steps: number;
}

export interface UserDataSummaryResponse {
  engines: Record<string, number>;
  total_records: number;
  last_activity: string | null;
}

// ── GDPR Exports ────────────────────────────────────────────

export interface DataExportRequestCreate {
  export_format: "json" | "csv";
  include_engines?: string[];
}

export interface DataExportRequestResponse {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
  export_format: string;
  include_engines: string[];
  download_url: string | null;
  expires_at: string | null;
  requested_at: string;
  completed_at: string | null;
}

export interface DataExportListResponse {
  items: DataExportRequestResponse[];
  total: number;
  page: number;
  per_page: number;
}
