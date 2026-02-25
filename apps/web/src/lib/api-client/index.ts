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
