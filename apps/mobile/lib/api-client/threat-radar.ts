/**
 * PathForge Mobile — API Client: Threat Radar
 * ===============================================
 * Career Threat Radar™ overview endpoint.
 * Audit Fix #1: Missing mobile API client for threat radar data.
 */

import { get } from "../http";

import type { ThreatRadarOverviewResponse } from "@pathforge/shared/types/api/threat-radar";

export async function getThreatRadarOverview(): Promise<ThreatRadarOverviewResponse> {
  return get<ThreatRadarOverviewResponse>("/api/v1/threat-radar/overview");
}
