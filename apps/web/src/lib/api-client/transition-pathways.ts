/**
 * PathForge — API Client: Transition Pathways
 * ==============================================
 * Dashboard, explore, what-if, skill bridge, milestones, and preference endpoints.
 */

import { del, get, post, put } from "@/lib/http";
import type {
  TransitionDashboardResponse,
  TransitionScanResponse,
  TransitionPathResponse,
  TransitionSummaryResponse,
  SkillBridgeEntryResponse,
  TransitionMilestoneResponse,
  TransitionComparisonResponse,
  TransitionExploreRequest,
  RoleWhatIfRequest,
  TransitionCompareRequest,
  TransitionPreferenceResponse,
  TransitionPreferenceUpdateRequest,
} from "@/types/api";

const BASE = "/api/v1/transition-pathways";

export const transitionPathwaysApi = {
  // ── Dashboard ──────────────────────────────────────────────
  getDashboard: (): Promise<TransitionDashboardResponse> =>
    get<TransitionDashboardResponse>(BASE),

  // ── Explore & What-If ──────────────────────────────────────
  explore: (data: TransitionExploreRequest): Promise<TransitionScanResponse> =>
    post<TransitionScanResponse>(`${BASE}/explore`, data),

  whatIf: (data: RoleWhatIfRequest): Promise<TransitionPathResponse> =>
    post<TransitionPathResponse>(`${BASE}/what-if`, data),

  // ── Compare ────────────────────────────────────────────────
  compare: (data: TransitionCompareRequest): Promise<TransitionComparisonResponse[]> =>
    post<TransitionComparisonResponse[]>(`${BASE}/compare`, data),

  // ── List / Detail / Delete ─────────────────────────────────
  list: (): Promise<TransitionSummaryResponse[]> =>
    get<TransitionSummaryResponse[]>(`${BASE}/list`),

  getTransition: (transitionId: string): Promise<TransitionPathResponse> =>
    get<TransitionPathResponse>(`${BASE}/${transitionId}`),

  deleteTransition: (transitionId: string): Promise<void> =>
    del<void>(`${BASE}/${transitionId}`),

  // ── Sub-Resources ──────────────────────────────────────────
  getSkillBridge: (transitionId: string): Promise<SkillBridgeEntryResponse[]> =>
    get<SkillBridgeEntryResponse[]>(`${BASE}/${transitionId}/skill-bridge`),

  getMilestones: (transitionId: string): Promise<TransitionMilestoneResponse[]> =>
    get<TransitionMilestoneResponse[]>(`${BASE}/${transitionId}/milestones`),

  // ── Preferences ────────────────────────────────────────────
  getPreferences: (): Promise<TransitionPreferenceResponse> =>
    get<TransitionPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: TransitionPreferenceUpdateRequest): Promise<TransitionPreferenceResponse> =>
    put<TransitionPreferenceResponse>(`${BASE}/preferences`, data),
};
