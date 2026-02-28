/**
 * PathForge Mobile — Constants: Theme
 * =====================================
 * Design tokens for the mobile application.
 * Light + dark mode support, matching PathForge brand.
 */

// ── Brand Colors ────────────────────────────────────────────

export const BRAND = {
  primary: "#3B82F6",      // Blue-500
  primaryDark: "#2563EB",  // Blue-600
  primaryLight: "#60A5FA", // Blue-400
  secondary: "#8B5CF6",    // Violet-500
  accent: "#06B6D4",       // Cyan-500
  success: "#10B981",      // Emerald-500
  warning: "#F59E0B",      // Amber-500
  error: "#EF4444",        // Red-500
  info: "#3B82F6",         // Blue-500
} as const;

// ── Severity Colors ─────────────────────────────────────────

export const SEVERITY = {
  critical: "#EF4444",
  warning: "#F59E0B",
  info: "#3B82F6",
  success: "#10B981",
} as const;

// ── Score Colors ────────────────────────────────────────────

export function getScoreColor(score: number): string {
  if (score >= 80) return BRAND.success;
  if (score >= 60) return BRAND.primary;
  if (score >= 40) return BRAND.warning;
  return BRAND.error;
}

// ── Light Theme ─────────────────────────────────────────────

export const LIGHT = {
  background: "#FFFFFF",
  surface: "#F8FAFC",
  surfaceElevated: "#FFFFFF",
  border: "#E2E8F0",
  borderSubtle: "#F1F5F9",
  text: "#0F172A",
  textSecondary: "#475569",
  textTertiary: "#94A3B8",
  textInverse: "#FFFFFF",
  tabBar: "#FFFFFF",
  tabBarInactive: "#94A3B8",
  statusBar: "dark" as const,
} as const;

// ── Dark Theme ──────────────────────────────────────────────

export const DARK = {
  background: "#0F172A",
  surface: "#1E293B",
  surfaceElevated: "#334155",
  border: "#334155",
  borderSubtle: "#1E293B",
  text: "#F8FAFC",
  textSecondary: "#CBD5E1",
  textTertiary: "#64748B",
  textInverse: "#0F172A",
  tabBar: "#1E293B",
  tabBarInactive: "#64748B",
  statusBar: "light" as const,
} as const;

// ── Spacing ─────────────────────────────────────────────────

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

// ── Border Radius ───────────────────────────────────────────

export const RADIUS = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  round: 9999,
} as const;

// ── Typography ──────────────────────────────────────────────

export const FONT_SIZE = {
  xs: 11,
  sm: 13,
  md: 15,
  lg: 17,
  xl: 20,
  xxl: 24,
  xxxl: 30,
  hero: 36,
} as const;

export const FONT_WEIGHT = {
  regular: "400" as const,
  medium: "500" as const,
  semibold: "600" as const,
  bold: "700" as const,
};

// ── Shadows ─────────────────────────────────────────────────

export const SHADOW = {
  sm: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  lg: {
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
  },
} as const;

// ── Animation ───────────────────────────────────────────────

export const ANIMATION = {
  fast: 150,
  normal: 250,
  slow: 400,
} as const;
