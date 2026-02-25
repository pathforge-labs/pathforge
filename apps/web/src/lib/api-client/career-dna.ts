/**
 * PathForge — API Client: Career DNA™
 * ======================================
 * CRUD, dimension, and hidden skill endpoints.
 */

import { del, get, patch, post } from "@/lib/http";
import type {
  CareerDnaGenerateRequest,
  CareerDnaProfileResponse,
  CareerDnaSummaryResponse,
  ExperienceBlueprintResponse,
  GrowthVectorResponse,
  HiddenSkillConfirmRequest,
  HiddenSkillResponse,
  MarketPositionResponse,
  SkillGenomeEntryResponse,
  ValuesProfileResponse,
} from "@/types/api";

const BASE = "/api/v1/career-dna";

export const careerDnaApi = {
  // ── Profile ─────────────────────────────────────────────
  getProfile: (): Promise<CareerDnaProfileResponse> =>
    get<CareerDnaProfileResponse>(BASE),

  getSummary: (): Promise<CareerDnaSummaryResponse> =>
    get<CareerDnaSummaryResponse>(`${BASE}/summary`),

  generate: (params?: CareerDnaGenerateRequest): Promise<CareerDnaProfileResponse> =>
    post<CareerDnaProfileResponse>(`${BASE}/generate`, params),

  deleteProfile: (): Promise<void> =>
    del(`${BASE}`),

  // ── Dimensions ──────────────────────────────────────────
  getSkillGenome: (): Promise<SkillGenomeEntryResponse[]> =>
    get<SkillGenomeEntryResponse[]>(`${BASE}/skill-genome`),

  getExperienceBlueprint: (): Promise<ExperienceBlueprintResponse> =>
    get<ExperienceBlueprintResponse>(`${BASE}/experience-blueprint`),

  getGrowthVector: (): Promise<GrowthVectorResponse> =>
    get<GrowthVectorResponse>(`${BASE}/growth-vector`),

  getValuesProfile: (): Promise<ValuesProfileResponse> =>
    get<ValuesProfileResponse>(`${BASE}/values-profile`),

  getMarketPosition: (): Promise<MarketPositionResponse> =>
    get<MarketPositionResponse>(`${BASE}/market-position`),

  // ── Hidden Skills ───────────────────────────────────────
  confirmHiddenSkill: (skillId: string, data: HiddenSkillConfirmRequest): Promise<HiddenSkillResponse> =>
    patch<HiddenSkillResponse>(`${BASE}/hidden-skills/${skillId}`, data),
};
