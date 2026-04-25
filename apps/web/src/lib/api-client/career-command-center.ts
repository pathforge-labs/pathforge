/**
 * PathForge — API Client: Career Command Center™
 * =================================================
 * Dashboard, health summary, and engine-level endpoints.
 */

import { get, post, put } from "@/lib/http";
import type {
  CareerHealthSummaryResponse,
  CommandCenterDashboardResponse,
  CommandCenterPreferenceResponse,
  CommandCenterPreferenceUpdateRequest,
  EngineDetailResponse,
  VitalsSnapshotResponse,
} from "@/types/api";

const BASE = "/api/v1/command-center";

export const commandCenterApi = {
  getDashboard: (): Promise<CommandCenterDashboardResponse> =>
    get<CommandCenterDashboardResponse>(`${BASE}/dashboard`),

  getHealthSummary: (): Promise<CareerHealthSummaryResponse> =>
    get<CareerHealthSummaryResponse>(`${BASE}/health-summary`),

  refreshSnapshot: (): Promise<VitalsSnapshotResponse> =>
    post<VitalsSnapshotResponse>(`${BASE}/refresh-snapshot`),

  getEngineDetail: (engineName: string): Promise<EngineDetailResponse> =>
    get<EngineDetailResponse>(`${BASE}/engines/${engineName}`),

  getPreferences: (): Promise<CommandCenterPreferenceResponse> =>
    get<CommandCenterPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: CommandCenterPreferenceUpdateRequest): Promise<CommandCenterPreferenceResponse> =>
    put<CommandCenterPreferenceResponse>(`${BASE}/preferences`, data),
};
