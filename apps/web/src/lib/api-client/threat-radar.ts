/**
 * PathForge — API Client: Career Threat Radar™
 * ===============================================
 * Overview, scan, alerts, and preference endpoints.
 */

import { get, patch, post, put } from "@/lib/http";
import type {
  AlertPreferenceResponse,
  AlertPreferenceUpdateRequest,
  AutomationRiskResponse,
  CareerResilienceResponse,
  SkillShieldMatrixResponse,
  ThreatAlertListResponse,
  ThreatAlertResponse,
  ThreatAlertUpdateRequest,
  ThreatRadarOverviewResponse,
  ThreatRadarScanResponse,
} from "@/types/api";

const BASE = "/api/v1/threat-radar";

export const threatRadarApi = {
  // ── Overview ────────────────────────────────────────────
  getOverview: (): Promise<ThreatRadarOverviewResponse> =>
    get<ThreatRadarOverviewResponse>(BASE),

  // ── Scan ────────────────────────────────────────────────
  triggerScan: (socCode: string, industryName: string): Promise<ThreatRadarScanResponse> =>
    post<ThreatRadarScanResponse>(`${BASE}/scan?soc_code=${encodeURIComponent(socCode)}&industry_name=${encodeURIComponent(industryName)}`),

  // ── Components ──────────────────────────────────────────
  getAutomationRisk: (): Promise<AutomationRiskResponse> =>
    get<AutomationRiskResponse>(`${BASE}/automation-risk`),

  getSkillsShield: (): Promise<SkillShieldMatrixResponse> =>
    get<SkillShieldMatrixResponse>(`${BASE}/skills-shield`),

  getResilience: (): Promise<CareerResilienceResponse> =>
    get<CareerResilienceResponse>(`${BASE}/resilience`),

  // ── Alerts ──────────────────────────────────────────────
  getAlerts: (
    page: number = 1,
    pageSize: number = 20,
    alertStatus?: string,
  ): Promise<ThreatAlertListResponse> => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (alertStatus) params.set("alert_status", alertStatus);
    return get<ThreatAlertListResponse>(`${BASE}/alerts?${params.toString()}`);
  },

  updateAlert: (alertId: string, data: ThreatAlertUpdateRequest): Promise<ThreatAlertResponse> =>
    patch<ThreatAlertResponse>(`${BASE}/alerts/${alertId}`, data),

  // ── Preferences ─────────────────────────────────────────
  getPreferences: (): Promise<AlertPreferenceResponse> =>
    get<AlertPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: AlertPreferenceUpdateRequest): Promise<AlertPreferenceResponse> =>
    put<AlertPreferenceResponse>(`${BASE}/preferences`, data),
};
