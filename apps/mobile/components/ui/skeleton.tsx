/**
 * PathForge Mobile — UI: Skeleton
 * ==================================
 * Shimmer loading placeholder using react-native-reanimated.
 * Replaces content blocks during data fetching.
 */

import React, { useEffect } from "react";
import { StyleSheet, type StyleProp, type ViewStyle } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from "react-native-reanimated";

import { RADIUS } from "../../constants/theme";
import { useTheme } from "../../hooks/use-theme";

// ── Types ───────────────────────────────────────────────────

interface SkeletonProps {
  /** Width of the skeleton block. @default "100%" */
  width?: number | `${number}%`;
  /** Height of the skeleton block. @default 16 */
  height?: number;
  /** Border radius. @default RADIUS.md */
  borderRadius?: number;
  /** Custom style override. */
  style?: StyleProp<ViewStyle>;
}

// ── Component ───────────────────────────────────────────────

export function Skeleton({
  width = "100%",
  height = 16,
  borderRadius = RADIUS.md,
  style,
}: SkeletonProps): React.JSX.Element {
  const { colors, isDark } = useTheme();
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    opacity.value = withRepeat(
      withTiming(0.7, {
        duration: 1000,
        easing: Easing.inOut(Easing.ease),
      }),
      -1, // Infinite repeats
      true, // Reverse
    );
  }, [opacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  const baseColor = isDark ? "#334155" : "#E2E8F0";

  return (
    <Animated.View
      accessibilityRole="progressbar"
      accessibilityLabel="Loading content"
      style={[
        {
          width,
          height,
          borderRadius,
          backgroundColor: baseColor,
        },
        animatedStyle,
        style,
      ]}
    />
  );
}

// ── Presets ──────────────────────────────────────────────────

/** Full-width text line skeleton. */
export function SkeletonLine({
  width = "100%",
}: { width?: number | `${number}%` }): React.JSX.Element {
  return <Skeleton width={width} height={14} />;
}

/** Circular avatar skeleton. */
export function SkeletonCircle({
  size = 40,
}: { size?: number }): React.JSX.Element {
  return <Skeleton width={size} height={size} borderRadius={size / 2} />;
}

/** Card-sized skeleton block. */
export function SkeletonCard(): React.JSX.Element {
  return <Skeleton width="100%" height={120} borderRadius={RADIUS.lg} />;
}
