/**
 * PathForge Mobile — UI: Card
 * ==============================
 * Themed container with rounded corners, shadow, and optional header.
 */

import React from "react";
import {
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import {
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SHADOW,
  SPACING,
} from "../../constants/theme";
import { useTheme } from "../../hooks/use-theme";

interface CardProps {
  children: React.ReactNode;
  /** Card title (optional header row). */
  title?: string;
  /** Right-aligned badge or action in header. */
  headerRight?: React.ReactNode;
  /** Shadow elevation level. @default "sm" */
  elevation?: keyof typeof SHADOW;
  /** Custom container style. */
  style?: StyleProp<ViewStyle>;
}

export function Card({
  children,
  title,
  headerRight,
  elevation = "sm",
  style,
}: CardProps): React.JSX.Element {
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.surfaceElevated,
          borderColor: colors.border,
        },
        SHADOW[elevation],
        style,
      ]}
    >
      {title && (
        <View style={styles.header}>
          <Text style={[styles.title, { color: colors.text }]}>
            {title}
          </Text>
          {headerRight}
        </View>
      )}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: SPACING.md,
  },
  title: {
    fontSize: FONT_SIZE.lg,
    fontWeight: FONT_WEIGHT.semibold,
  },
});
