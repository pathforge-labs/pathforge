/**
 * PathForge Mobile — API Client: Career DNA
 * ============================================
 * Career DNA profile, dimensions, and summary endpoints.
 */

import { get, post } from "../http";

import type {
  CareerDnaProfileResponse,
  CareerDnaSummaryResponse,
  CareerDnaGenerateRequest,
} from "@pathforge/shared/types/api/career-dna";

export async function getCareerDnaProfile(): Promise<CareerDnaProfileResponse> {
  return get<CareerDnaProfileResponse>("/api/v1/career-dna/profile");
}

export async function getCareerDnaSummary(): Promise<CareerDnaSummaryResponse> {
  return get<CareerDnaSummaryResponse>("/api/v1/career-dna/summary");
}

export async function generateCareerDna(
  request?: CareerDnaGenerateRequest,
): Promise<CareerDnaProfileResponse> {
  return post<CareerDnaProfileResponse>("/api/v1/career-dna/generate", request);
}
