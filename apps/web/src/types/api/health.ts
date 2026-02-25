/**
 * PathForge — API Types: Health
 * ===============================
 * Types for health check endpoints.
 */

export interface HealthCheckResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export interface ReadinessCheckResponse {
  status: "ok" | "degraded";
  database: string;
  app: string;
  version: string;
}
