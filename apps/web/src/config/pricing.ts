/**
 * PathForge — Pricing Configuration
 * ====================================
 * Config-driven pricing tiers mirroring backend `feature_gate.py`.
 *
 * IMPORTANT: This is the SSOT for frontend pricing display.
 * Actual enforcement is server-side — this config is informational only.
 *
 * @see apps/api/app/core/feature_gate.py for backend definitions.
 */

import type { SubscriptionTier } from "@/types/api";

// ── Feature Display Names ──────────────────────────────────

const ENGINE_DISPLAY_NAMES: Record<string, string> = {
  career_dna: "Career DNA™ Analysis",
  threat_radar: "Threat Radar™",
  skill_decay: "Skill Decay & Growth Tracker",
  salary_intelligence: "Salary Intelligence Engine™",
  career_simulation: "Career Simulation Engine™",
  interview_intelligence: "Interview Intelligence™",
  hidden_job_market: "Hidden Job Market Detector™",
  collective_intelligence: "Collective Intelligence",
  recommendation_intelligence: "Cross-Engine Recommendations™",
  career_action_planner: "Career Action Planner™",
  career_passport: "Cross-Border Career Passport™",
  predictive_career: "Predictive Career Analytics™",
} as const;

// ── Tier Definitions ───────────────────────────────────────

export interface PricingTier {
  /** Internal tier ID matching backend enum. */
  readonly id: SubscriptionTier;
  /** Display name. */
  readonly name: string;
  /** Monthly price in EUR (0 for free tier). */
  readonly monthlyPrice: number;
  /** Annual price in EUR (0 for free tier). */
  readonly annualPrice: number;
  /** Monthly scan limit. null = unlimited. */
  readonly scanLimit: number | null;
  /** Engine keys accessible in this tier. */
  readonly engines: ReadonlyArray<string>;
  /** Human-readable feature descriptions for the pricing card. */
  readonly features: ReadonlyArray<string>;
  /** Whether this tier should be visually highlighted (recommended). */
  readonly highlighted: boolean;
  /** CTA button text. */
  readonly ctaText: string;
}

export const PRICING_TIERS: ReadonlyArray<PricingTier> = [
  {
    id: "free",
    name: "Free",
    monthlyPrice: 0,
    annualPrice: 0,
    scanLimit: 3,
    engines: ["career_dna", "threat_radar"],
    features: [
      "Career DNA™ Analysis",
      "Threat Radar™ Monitoring",
      "3 scans per month",
      "Basic skill genome mapping",
      "Email support",
    ],
    highlighted: false,
    ctaText: "Get Started",
  },
  {
    id: "pro",
    name: "Pro",
    monthlyPrice: 19,
    annualPrice: 149,
    scanLimit: 30,
    engines: [
      "career_dna",
      "threat_radar",
      "skill_decay",
      "salary_intelligence",
      "career_simulation",
      "interview_intelligence",
      "hidden_job_market",
      "collective_intelligence",
      "recommendation_intelligence",
      "career_action_planner",
    ],
    features: [
      "Everything in Free, plus:",
      "10 Intelligence Engines",
      "30 scans per month",
      "Salary Intelligence Engine™",
      "Career Simulation Engine™",
      "Interview Intelligence™",
      "Hidden Job Market Detector™",
      "Cross-Engine Recommendations™",
      "Priority support",
    ],
    highlighted: true,
    ctaText: "Upgrade to Pro",
  },
  {
    id: "premium",
    name: "Premium",
    monthlyPrice: 39,
    annualPrice: 299,
    scanLimit: null,
    engines: [
      "career_dna",
      "threat_radar",
      "skill_decay",
      "salary_intelligence",
      "career_simulation",
      "interview_intelligence",
      "hidden_job_market",
      "collective_intelligence",
      "recommendation_intelligence",
      "career_action_planner",
      "career_passport",
      "predictive_career",
    ],
    features: [
      "Everything in Pro, plus:",
      "All 12 Intelligence Engines",
      "Unlimited scans",
      "Cross-Border Career Passport™",
      "Predictive Career Analytics™",
      "Advanced workflow automation",
      "Dedicated support",
    ],
    highlighted: false,
    ctaText: "Upgrade to Premium",
  },
] as const;

// ── Helpers ────────────────────────────────────────────────

/**
 * Format a price for display.
 * Returns "Free" for 0, formatted EUR amount otherwise.
 */
export function formatPrice(amount: number): string {
  if (amount === 0) return "Free";
  return new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Calculate annual savings percentage relative to monthly billing.
 */
export function getAnnualSavingsPercent(tier: PricingTier): number {
  if (tier.monthlyPrice === 0) return 0;
  const monthlyTotal = tier.monthlyPrice * 12;
  return Math.round(((monthlyTotal - tier.annualPrice) / monthlyTotal) * 100);
}

/**
 * Get human-readable display name for an engine key.
 */
export function getEngineDisplayName(engineKey: string): string {
  return ENGINE_DISPLAY_NAMES[engineKey] ?? engineKey;
}
