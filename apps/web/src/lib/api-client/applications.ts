/**
 * PathForge — Applications API Client
 * =====================================
 * Domain-split API client for application tracking endpoints.
 * Replaces the `applications` namespace from the legacy `lib/api.ts` monolith.
 */

import { fetchWithAuth } from "@/lib/http";
import type {
  ApplicationResponse,
  ApplicationListResponse,
} from "@/types/api/applications";

/** Create a new application for a job listing. */
export function createApplication(
  jobListingId: string,
  status?: string,
  notes?: string,
): Promise<ApplicationResponse> {
  return fetchWithAuth<ApplicationResponse>("/api/v1/applications", {
    method: "POST",
    body: JSON.stringify({ job_listing_id: jobListingId, status, notes }),
  });
}

/** List applications with optional status filter and pagination. */
export function listApplications(
  status?: string,
  page: number = 1,
  perPage: number = 20,
): Promise<ApplicationListResponse> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("page", String(page));
  params.set("per_page", String(perPage));
  return fetchWithAuth<ApplicationListResponse>(
    `/api/v1/applications?${params.toString()}`,
  );
}

/** Get a single application by ID. */
export function getApplication(id: string): Promise<ApplicationResponse> {
  return fetchWithAuth<ApplicationResponse>(`/api/v1/applications/${id}`);
}

/** Update an application's status. */
export function updateApplicationStatus(
  id: string,
  status: string,
): Promise<ApplicationResponse> {
  return fetchWithAuth<ApplicationResponse>(
    `/api/v1/applications/${id}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    },
  );
}

/** Delete an application. */
export function deleteApplication(id: string): Promise<void> {
  return fetchWithAuth<void>(`/api/v1/applications/${id}`, {
    method: "DELETE",
  });
}
