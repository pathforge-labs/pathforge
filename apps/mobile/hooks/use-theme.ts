/**
 * PathForge Mobile — useTheme Hook
 * ===================================
 * Centralized theme resolution for light/dark mode.
 *
 * Replaces the repeated `useColorScheme() → ternary` pattern
 * scattered across every component with a single, memoized call.
 */

import { useMemo } from "react";
import { useColorScheme } from "react-native";

import { DARK, LIGHT } from "../constants/theme";

/** Structural theme contract — compatible with both LIGHT and DARK. */
export interface ThemeColors {
  background: string;
  surface: string;
  surfaceElevated: string;
  border: string;
  borderSubtle: string;
  text: string;
  textSecondary: string;
  textTertiary: string;
  textInverse: string;
  tabBar: string;
  tabBarInactive: string;
  statusBar: "dark" | "light";
}

export interface ThemeResult {
  /** Resolved theme colors for current color scheme. */
  colors: ThemeColors;
  /** Whether dark mode is active. */
  isDark: boolean;
  /** Raw color scheme value ("light" | "dark" | null). */
  colorScheme: ReturnType<typeof useColorScheme>;
}

/**
 * Resolve the current theme based on system color scheme.
 *
 * @example
 * ```tsx
 * const { colors, isDark } = useTheme();
 * <View style={{ backgroundColor: colors.background }} />
 * ```
 */
export function useTheme(): ThemeResult {
  const colorScheme = useColorScheme();

  return useMemo<ThemeResult>(
    () => ({
      colors: colorScheme === "dark" ? DARK : LIGHT,
      isDark: colorScheme === "dark",
      colorScheme,
    }),
    [colorScheme],
  );
}

