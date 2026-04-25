/**
 * PathForge Mobile — UI: Badge
 * ===============================
 * Compact status indicator with color variant support.
 * Used for sprint labels, score ranges, and status tags.
 */

import React from "react";
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from "react-native";

import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SPACING,
} from "../../constants/theme";

// ── Types ───────────────────────────────────────────────────

type BadgeVariant = "primary" | "success" | "warning" | "error" | "neutral";

interface BadgeProps {
  /** Text content. */
  label: string;
  /** Color variant. @default "primary" */
  variant?: BadgeVariant;
  /** Custom container style. */
  style?: StyleProp<ViewStyle>;
}

// ── Variant Colors ──────────────────────────────────────────

const VARIANT_MAP: Record<BadgeVariant, { background: string; text: string }> = {
  primary: { background: BRAND.primary + "20", text: BRAND.primary },
  success: { background: BRAND.success + "20", text: BRAND.success },
  warning: { background: BRAND.warning + "20", text: BRAND.warning },
  error: { background: BRAND.error + "20", text: BRAND.error },
  neutral: { background: "#94A3B820", text: "#94A3B8" },
};

// ── Component ───────────────────────────────────────────────

export function Badge({
  label,
  variant = "primary",
  style,
}: BadgeProps): React.JSX.Element {
  const colors = VARIANT_MAP[variant];

  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: colors.background },
        style,
      ]}
    >
      <Text style={[styles.label, { color: colors.text }]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.round,
    alignSelf: "flex-start",
  },
  label: {
    fontSize: FONT_SIZE.xs,
    fontWeight: FONT_WEIGHT.semibold,
  },
});
