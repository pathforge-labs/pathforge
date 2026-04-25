/**
 * PathForge — API Client: Salary Intelligence Engine™
 * =====================================================
 * Dashboard, scan, estimate, impacts, trajectory, scenarios, and preference endpoints.
 */

import { get, post, put } from "@/lib/http";
import type {
  SalaryDashboardResponse,
  SalaryScanResponse,
  SalaryEstimateResponse,
  SalaryImpactAnalysisResponse,
  SalaryHistoryEntryResponse,
  SalaryScenarioResponse,
  SalaryScenarioRequest,
  SkillWhatIfRequest,
  LocationWhatIfRequest,
  SalaryPreferenceResponse,
  SalaryPreferenceUpdateRequest,
} from "@/types/api";

const BASE = "/api/v1/salary-intelligence";

export const salaryIntelligenceApi = {
  // ── Dashboard ──────────────────────────────────────────────
  getDashboard: (): Promise<SalaryDashboardResponse> =>
    get<SalaryDashboardResponse>(BASE),

  // ── Full Scan ──────────────────────────────────────────────
  triggerScan: (): Promise<SalaryScanResponse> =>
    post<SalaryScanResponse>(`${BASE}/scan`),

  // ── Components ─────────────────────────────────────────────
  getEstimate: (): Promise<SalaryEstimateResponse> =>
    get<SalaryEstimateResponse>(`${BASE}/estimate`),

  getSkillImpacts: (): Promise<SalaryImpactAnalysisResponse> =>
    get<SalaryImpactAnalysisResponse>(`${BASE}/skill-impacts`),

  getTrajectory: (): Promise<SalaryHistoryEntryResponse[]> =>
    get<SalaryHistoryEntryResponse[]>(`${BASE}/trajectory`),

  // ── Scenarios ──────────────────────────────────────────────
  listScenarios: (): Promise<SalaryScenarioResponse[]> =>
    get<SalaryScenarioResponse[]>(`${BASE}/scenarios`),

  runScenario: (data: SalaryScenarioRequest): Promise<SalaryScenarioResponse> =>
    post<SalaryScenarioResponse>(`${BASE}/scenarios`, data),

  getScenario: (scenarioId: string): Promise<SalaryScenarioResponse> =>
    get<SalaryScenarioResponse>(`${BASE}/scenarios/${scenarioId}`),

  // ── What-If Shortcuts ──────────────────────────────────────
  whatIfSkill: (data: SkillWhatIfRequest): Promise<SalaryScenarioResponse> =>
    post<SalaryScenarioResponse>(`${BASE}/what-if/skill`, data),

  whatIfLocation: (data: LocationWhatIfRequest): Promise<SalaryScenarioResponse> =>
    post<SalaryScenarioResponse>(`${BASE}/what-if/location`, data),

  // ── Preferences ────────────────────────────────────────────
  getPreferences: (): Promise<SalaryPreferenceResponse> =>
    get<SalaryPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: SalaryPreferenceUpdateRequest): Promise<SalaryPreferenceResponse> =>
    put<SalaryPreferenceResponse>(`${BASE}/preferences`, data),
};
