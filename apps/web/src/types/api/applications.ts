/**
 * PathForge — Application Types
 * ==============================
 * TypeScript interfaces for application tracking endpoints.
 */

export interface ApplicationResponse {
  id: string;
  job_listing_id: string;
  status: string;
  notes: string | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
  job_title: string | null;
  job_company: string | null;
}

export interface ApplicationListResponse {
  items: ApplicationResponse[];
  total: number;
  page: number;
  per_page: number;
}
