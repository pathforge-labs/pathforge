/**
 * PathForge — API Client: Hidden Job Market Detector™
 * =====================================================
 * Signal feed, outreach, opportunities, and company scanning.
 */

import { get, patch, post, put } from "@/lib/http";
import type {
  CompanySignalResponse,
  HiddenJobMarketDashboardResponse,
  HiddenJobMarketPreferenceResponse,
  HiddenJobMarketPreferenceUpdateRequest,
  OpportunityRadarResponse,
  SignalComparisonResponse,
  ScanCompanyRequest,
  ScanIndustryRequest,
  SignalCompareRequest,
  GenerateOutreachRequest,
  DismissSignalRequest,
  OutreachTemplateResponse,
} from "@/types/api";
import type { MessageResponse } from "@/types/api/common";

const BASE = "/api/v1/hidden-job-market";

export const hiddenJobMarketApi = {
  getDashboard: (): Promise<HiddenJobMarketDashboardResponse> =>
    get<HiddenJobMarketDashboardResponse>(`${BASE}/dashboard`),

  scanCompany: (data: ScanCompanyRequest): Promise<CompanySignalResponse> =>
    post<CompanySignalResponse>(`${BASE}/scan-company`, data),

  scanIndustry: (data: ScanIndustryRequest): Promise<CompanySignalResponse[]> =>
    post<CompanySignalResponse[]>(`${BASE}/scan-industry`, data),

  getPreferences: (): Promise<HiddenJobMarketPreferenceResponse> =>
    get<HiddenJobMarketPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: HiddenJobMarketPreferenceUpdateRequest): Promise<HiddenJobMarketPreferenceResponse> =>
    put<HiddenJobMarketPreferenceResponse>(`${BASE}/preferences`, data),

  compareSignals: (data: SignalCompareRequest): Promise<SignalComparisonResponse> =>
    post<SignalComparisonResponse>(`${BASE}/compare`, data),

  getOpportunities: (): Promise<OpportunityRadarResponse> =>
    get<OpportunityRadarResponse>(`${BASE}/opportunities`),

  surfaceOpportunities: (): Promise<OpportunityRadarResponse> =>
    post<OpportunityRadarResponse>(`${BASE}/opportunities/surface`),

  getSignal: (signalId: string): Promise<CompanySignalResponse> =>
    get<CompanySignalResponse>(`${BASE}/${signalId}`),

  generateOutreach: (signalId: string, data: GenerateOutreachRequest): Promise<OutreachTemplateResponse> =>
    post<OutreachTemplateResponse>(`${BASE}/${signalId}/outreach`, data),

  dismissSignal: (signalId: string, data: DismissSignalRequest): Promise<MessageResponse> =>
    patch<MessageResponse>(`${BASE}/${signalId}/dismiss`, data),
};
