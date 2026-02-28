/**
 * PathForge Mobile — UI: ScoreBar
 * ==================================
 * Animated horizontal progress bar for career intelligence scores.
 * Color shifts with score value (red → amber → blue → green).
 */

import React, { useEffect } from "react";
import { StyleSheet, Text, View } from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  Easing,
} from "react-native-reanimated";

import {
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SPACING,
  getScoreColor,
} from "../../constants/theme";
import { useTheme } from "../../hooks/use-theme";
import { ANIMATION } from "../../constants/theme";

// ── Types ───────────────────────────────────────────────────

interface ScoreBarProps {
  /** Label displayed above the bar. */
  label: string;
  /** Score value (0–100). */
  score: number;
  /** Show numeric value to the right of the bar. @default true */
  showValue?: boolean;
  /** Maximum score value. @default 100 */
  maxScore?: number;
}

// ── Component ───────────────────────────────────────────────

export function ScoreBar({
  label,
  score,
  showValue = true,
  maxScore = 100,
}: ScoreBarProps): React.JSX.Element {
  const { colors } = useTheme();
  const clampedScore = Math.max(0, Math.min(score, maxScore));
  const percentage = (clampedScore / maxScore) * 100;
  const scoreColor = getScoreColor(clampedScore);

  // Animate width from 0 to percentage
  const widthProgress = useSharedValue(0);

  useEffect(() => {
    widthProgress.value = withTiming(percentage, {
      duration: ANIMATION.slow,
      easing: Easing.out(Easing.cubic),
    });
  }, [percentage, widthProgress]);

  const animatedStyle = useAnimatedStyle(() => ({
    width: `${widthProgress.value}%`,
  }));

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={[styles.label, { color: colors.textSecondary }]}>
          {label}
        </Text>
        {showValue && (
          <Text style={[styles.value, { color: scoreColor }]}>
            {clampedScore}
          </Text>
        )}
      </View>
      <View style={[styles.track, { backgroundColor: colors.borderSubtle }]}>
        <Animated.View
          style={[
            styles.fill,
            { backgroundColor: scoreColor },
            animatedStyle,
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: SPACING.xs,
  },
  labelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.medium,
  },
  value: {
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.bold,
  },
  track: {
    height: 6,
    borderRadius: RADIUS.round,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    borderRadius: RADIUS.round,
  },
});
