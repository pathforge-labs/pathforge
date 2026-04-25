/**
 * PathForge — API Client: Career Simulation Engine™
 * ===================================================
 * Dashboard, 5 scenario types, compare, detail, delete, and preference endpoints.
 */

import { del, get, post, put } from "@/lib/http";
import type {
  SimulationDashboardResponse,
  CareerSimulationResponse,
  SimulationComparisonResponse,
  SimulationPreferenceResponse,
  SimulationPreferenceUpdateRequest,
  RoleTransitionSimRequest,
  GeoMoveSimRequest,
  SkillInvestmentSimRequest,
  IndustryPivotSimRequest,
  SeniorityJumpSimRequest,
  SimulationCompareRequest,
} from "@/types/api";

const BASE = "/api/v1/career-simulation";

export const careerSimulationApi = {
  // ── Dashboard ──────────────────────────────────────────────
  getDashboard: (page: number = 1, pageSize: number = 20): Promise<SimulationDashboardResponse> => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    return get<SimulationDashboardResponse>(`${BASE}?${params.toString()}`);
  },

  // ── Run Simulations ────────────────────────────────────────
  simulateRole: (data: RoleTransitionSimRequest): Promise<CareerSimulationResponse> =>
    post<CareerSimulationResponse>(`${BASE}/simulate/role`, data),

  simulateGeo: (data: GeoMoveSimRequest): Promise<CareerSimulationResponse> =>
    post<CareerSimulationResponse>(`${BASE}/simulate/geo`, data),

  simulateSkill: (data: SkillInvestmentSimRequest): Promise<CareerSimulationResponse> =>
    post<CareerSimulationResponse>(`${BASE}/simulate/skill`, data),

  simulateIndustry: (data: IndustryPivotSimRequest): Promise<CareerSimulationResponse> =>
    post<CareerSimulationResponse>(`${BASE}/simulate/industry`, data),

  simulateSeniority: (data: SeniorityJumpSimRequest): Promise<CareerSimulationResponse> =>
    post<CareerSimulationResponse>(`${BASE}/simulate/seniority`, data),

  // ── Compare ────────────────────────────────────────────────
  compare: (data: SimulationCompareRequest): Promise<SimulationComparisonResponse> =>
    post<SimulationComparisonResponse>(`${BASE}/compare`, data),

  // ── Detail / Delete ────────────────────────────────────────
  getSimulation: (simulationId: string): Promise<CareerSimulationResponse> =>
    get<CareerSimulationResponse>(`${BASE}/${simulationId}`),

  deleteSimulation: (simulationId: string): Promise<void> =>
    del<void>(`${BASE}/${simulationId}`),

  // ── Preferences ────────────────────────────────────────────
  getPreferences: (): Promise<SimulationPreferenceResponse> =>
    get<SimulationPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: SimulationPreferenceUpdateRequest): Promise<SimulationPreferenceResponse> =>
    put<SimulationPreferenceResponse>(`${BASE}/preferences`, data),
};
