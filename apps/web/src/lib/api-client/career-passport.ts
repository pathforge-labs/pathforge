/**
 * PathForge — API Client: Cross-Border Career Passport™
 * ======================================================
 * Credential mapping, country comparison, visa assessment, and market demand.
 */

import { del, get, post, put } from "@/lib/http";
import type {
  CareerPassportDashboardResponse,
  CareerPassportPreferenceResponse,
  CareerPassportPreferenceUpdate,
  CountryComparisonRequest,
  CountryComparisonResponse,
  CredentialMappingRequest,
  CredentialMappingResponse,
  MarketDemandResponse,
  MultiCountryComparisonRequest,
  MultiCountryComparisonResponse,
  PassportScanResponse,
  VisaAssessmentRequest,
  VisaAssessmentResponse,
} from "@/types/api";

const BASE = "/api/v1/career-passport";

export const careerPassportApi = {
  getDashboard: (): Promise<CareerPassportDashboardResponse> =>
    get<CareerPassportDashboardResponse>(`${BASE}/dashboard`),

  fullScan: (data: CredentialMappingRequest, nationality?: string): Promise<PassportScanResponse> => {
    const params = nationality ? `?nationality=${encodeURIComponent(nationality)}` : "";
    return post<PassportScanResponse>(`${BASE}/scan${params}`, data);
  },

  createCredentialMapping: (data: CredentialMappingRequest): Promise<CredentialMappingResponse> =>
    post<CredentialMappingResponse>(`${BASE}/credentials`, data),

  getCredentialMapping: (mappingId: string): Promise<CredentialMappingResponse> =>
    get<CredentialMappingResponse>(`${BASE}/credentials/${mappingId}`),

  deleteCredentialMapping: (mappingId: string): Promise<void> =>
    del<void>(`${BASE}/credentials/${mappingId}`),

  createCountryComparison: (data: CountryComparisonRequest): Promise<CountryComparisonResponse> =>
    post<CountryComparisonResponse>(`${BASE}/comparison`, data),

  multiCountryComparison: (data: MultiCountryComparisonRequest): Promise<MultiCountryComparisonResponse> =>
    post<MultiCountryComparisonResponse>(`${BASE}/comparison/multi`, data),

  createVisaAssessment: (data: VisaAssessmentRequest): Promise<VisaAssessmentResponse> =>
    post<VisaAssessmentResponse>(`${BASE}/visa`, data),

  getMarketDemand: (country: string): Promise<MarketDemandResponse[]> =>
    get<MarketDemandResponse[]>(`${BASE}/demand/${encodeURIComponent(country)}`),

  getPreferences: (): Promise<CareerPassportPreferenceResponse> =>
    get<CareerPassportPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: CareerPassportPreferenceUpdate): Promise<CareerPassportPreferenceResponse> =>
    put<CareerPassportPreferenceResponse>(`${BASE}/preferences`, data),
};
