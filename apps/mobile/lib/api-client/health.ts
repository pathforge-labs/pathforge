/**
 * PathForge Mobile — API Client: Health
 * ========================================
 * Backend health check endpoint.
 */

import { fetchPublic } from "../http";

import type {
  HealthCheckResponse,
  ReadinessCheckResponse,
} from "@pathforge/shared/types/api/health";

export async function getHealthCheck(): Promise<HealthCheckResponse> {
  return fetchPublic<HealthCheckResponse>("/api/v1/health");
}

export async function getReadinessCheck(): Promise<ReadinessCheckResponse> {
  return fetchPublic<ReadinessCheckResponse>("/api/v1/health/ready");
}
