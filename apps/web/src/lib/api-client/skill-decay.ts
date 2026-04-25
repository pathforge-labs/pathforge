/**
 * PathForge — API Client: Skill Decay & Growth Tracker
 * ======================================================
 * Dashboard, scan, freshness, velocity, reskilling, and preference endpoints.
 */

import { get, post, put } from "@/lib/http";
import type {
  SkillDecayDashboardResponse,
  SkillDecayScanResponse,
  SkillFreshnessResponse,
  MarketDemandSnapshotResponse,
  SkillVelocityEntryResponse,
  ReskillingPathwayResponse,
  SkillRefreshRequest,
  SkillDecayPreferenceResponse,
  SkillDecayPreferenceUpdateRequest,
} from "@/types/api";

const BASE = "/api/v1/skill-decay";

export const skillDecayApi = {
  // ── Dashboard ──────────────────────────────────────────────
  getDashboard: (): Promise<SkillDecayDashboardResponse> =>
    get<SkillDecayDashboardResponse>(BASE),

  // ── Full Scan ──────────────────────────────────────────────
  triggerScan: (): Promise<SkillDecayScanResponse> =>
    post<SkillDecayScanResponse>(`${BASE}/scan`),

  // ── Individual Components ──────────────────────────────────
  getFreshness: (): Promise<SkillFreshnessResponse[]> =>
    get<SkillFreshnessResponse[]>(`${BASE}/freshness`),

  getMarketDemand: (): Promise<MarketDemandSnapshotResponse[]> =>
    get<MarketDemandSnapshotResponse[]>(`${BASE}/market-demand`),

  getVelocityMap: (): Promise<SkillVelocityEntryResponse[]> =>
    get<SkillVelocityEntryResponse[]>(`${BASE}/velocity`),

  getReskillingPathways: (): Promise<ReskillingPathwayResponse[]> =>
    get<ReskillingPathwayResponse[]>(`${BASE}/reskilling`),

  // ── Skill Refresh ──────────────────────────────────────────
  refreshSkill: (data: SkillRefreshRequest): Promise<SkillFreshnessResponse> =>
    post<SkillFreshnessResponse>(`${BASE}/refresh`, data),

  // ── Preferences ────────────────────────────────────────────
  getPreferences: (): Promise<SkillDecayPreferenceResponse> =>
    get<SkillDecayPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: SkillDecayPreferenceUpdateRequest): Promise<SkillDecayPreferenceResponse> =>
    put<SkillDecayPreferenceResponse>(`${BASE}/preferences`, data),
};
