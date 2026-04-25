/**
 * PathForge — API Client: Health
 * =================================
 * System health check endpoints.
 */

import { fetchPublic } from "@/lib/http";
import type { HealthCheckResponse, ReadinessCheckResponse } from "@/types/api";

export const healthApi = {
  check: (): Promise<HealthCheckResponse> =>
    fetchPublic<HealthCheckResponse>("/api/v1/health"),

  ready: (): Promise<ReadinessCheckResponse> =>
    fetchPublic<ReadinessCheckResponse>("/api/v1/health/ready"),
};
