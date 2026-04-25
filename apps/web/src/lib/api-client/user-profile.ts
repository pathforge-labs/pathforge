/**
 * PathForge — API Client: User Profile
 * =======================================
 * Profile CRUD, onboarding status, and GDPR export endpoints.
 */

import { del, get, post, put } from "@/lib/http";
import type {
  DataExportListResponse,
  DataExportRequestCreate,
  DataExportRequestResponse,
  OnboardingStatusResponse,
  UserDataSummaryResponse,
  UserProfileCreateRequest,
  UserProfileResponse,
  UserProfileUpdateRequest,
} from "@/types/api";

const BASE = "/api/v1/user-profile";

export const userProfileApi = {
  // ── Profile CRUD ────────────────────────────────────────
  getProfile: (): Promise<UserProfileResponse> =>
    get<UserProfileResponse>(`${BASE}/profile`),

  createProfile: (data: UserProfileCreateRequest): Promise<UserProfileResponse> =>
    post<UserProfileResponse>(`${BASE}/profile`, data),

  updateProfile: (data: UserProfileUpdateRequest): Promise<UserProfileResponse> =>
    put<UserProfileResponse>(`${BASE}/profile`, data),

  deleteProfile: (): Promise<void> =>
    del(`${BASE}/profile`),

  // ── Onboarding ──────────────────────────────────────────
  getOnboardingStatus: (): Promise<OnboardingStatusResponse> =>
    get<OnboardingStatusResponse>(`${BASE}/onboarding`),

  // ── Data Summary ────────────────────────────────────────
  getDataSummary: (): Promise<UserDataSummaryResponse> =>
    get<UserDataSummaryResponse>(`${BASE}/data-summary`),

  // ── GDPR Exports ────────────────────────────────────────
  requestExport: (data: DataExportRequestCreate): Promise<DataExportRequestResponse> =>
    post<DataExportRequestResponse>(`${BASE}/exports`, data),

  listExports: (page: number = 1, pageSize: number = 20): Promise<DataExportListResponse> => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    return get<DataExportListResponse>(`${BASE}/exports?${params.toString()}`);
  },

  getExportStatus: (exportId: string): Promise<DataExportRequestResponse> =>
    get<DataExportRequestResponse>(`${BASE}/exports/${exportId}`),
};
