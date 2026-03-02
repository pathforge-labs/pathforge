/**
 * PathForge — API Client Index
 * ==============================
 * Re-exports all domain API modules for convenient access.
 *
 * Usage:
 *   import { careerDnaApi, healthApi } from "@/lib/api-client";
 *   import * as aiApi from "@/lib/api-client/ai";
 */

export { authApi } from "./auth";
export { usersApi } from "./users";
export { healthApi } from "./health";
export { careerDnaApi } from "./career-dna";
export { threatRadarApi } from "./threat-radar";
export { commandCenterApi } from "./career-command-center";
export { notificationsApi } from "./notifications";
export { userProfileApi } from "./user-profile";

// ── Phase A–D Legacy Domains ───────────────────────────────
// Individual function exports (no namespace wrapper needed)
export * as aiApi from "./ai";
export * as applicationsApi from "./applications";
export * as blacklistApi from "./blacklist";
export * as analyticsApi from "./analytics";

// ── Sprint 27: Intelligence Hub ────────────────────────────────
export { skillDecayApi } from "./skill-decay";
export { salaryIntelligenceApi } from "./salary-intelligence";
export { careerSimulationApi } from "./career-simulation";
export { transitionPathwaysApi } from "./transition-pathways";

// ── Sprint 28: Network Intelligence & Command Center ───────────
export { hiddenJobMarketApi } from "./hidden-job-market";
export { careerPassportApi } from "./career-passport";
export { interviewIntelligenceApi } from "./interview-intelligence";
export { recommendationApi } from "./recommendation-intelligence";
export { workflowApi } from "./workflow-automation";

// ── Sprint 35: Billing & Monetization ──────────────────────
export { billingApi } from "./billing";
