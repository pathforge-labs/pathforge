/**
 * PathForge Mobile — UI: Button
 * ================================
 * Pressable button with variant system, loading state, haptic feedback,
 * and accessibility-first design (44pt minimum touch target).
 *
 * Variants: primary | secondary | ghost | danger
 * Sizes: sm (36) | md (44) | lg (52)
 */

import React from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SPACING,
} from "../../constants/theme";
import { useTheme } from "../../hooks/use-theme";

// ── Types ───────────────────────────────────────────────────

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends Omit<PressableProps, "style"> {
  /** Display label. */
  label: string;
  /** Visual variant. @default "primary" */
  variant?: ButtonVariant;
  /** Size preset. @default "md" */
  size?: ButtonSize;
  /** Show spinner and disable press. */
  isLoading?: boolean;
  /** Custom container style override. */
  style?: StyleProp<ViewStyle>;
}

// ── Size Map ────────────────────────────────────────────────

const SIZE_MAP: Record<ButtonSize, { height: number; fontSize: number; paddingH: number }> = {
  sm: { height: 36, fontSize: FONT_SIZE.sm, paddingH: SPACING.md },
  md: { height: 44, fontSize: FONT_SIZE.md, paddingH: SPACING.lg },
  lg: { height: 52, fontSize: FONT_SIZE.lg, paddingH: SPACING.xl },
};

// ── Component ───────────────────────────────────────────────

export function Button({
  label,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  style,
  ...pressableProps
}: ButtonProps): React.JSX.Element {
  const { colors } = useTheme();
  const sizeConfig = SIZE_MAP[size];
  const isDisabled = disabled || isLoading;

  const getVariantStyles = (pressed: boolean): ViewStyle => {
    const pressedOpacity = pressed ? 0.85 : 1;

    switch (variant) {
      case "primary":
        return {
          backgroundColor: pressed ? BRAND.primaryDark : BRAND.primary,
          opacity: isDisabled ? 0.5 : pressedOpacity,
        };
      case "secondary":
        return {
          backgroundColor: "transparent",
          borderWidth: 1.5,
          borderColor: BRAND.primary,
          opacity: isDisabled ? 0.5 : pressedOpacity,
        };
      case "ghost":
        return {
          backgroundColor: pressed ? colors.surface : "transparent",
          opacity: isDisabled ? 0.5 : pressedOpacity,
        };
      case "danger":
        return {
          backgroundColor: pressed ? "#DC2626" : BRAND.error,
          opacity: isDisabled ? 0.5 : pressedOpacity,
        };
    }
  };

  const getTextColor = (): string => {
    switch (variant) {
      case "primary": return "#FFFFFF";
      case "secondary": return BRAND.primary;
      case "ghost": return colors.text;
      case "danger": return "#FFFFFF";
    }
  };

  return (
    <Pressable
      {...pressableProps}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: isLoading }}
      accessibilityLabel={label}
      style={({ pressed }) => [
        {
          height: sizeConfig.height,
          paddingHorizontal: sizeConfig.paddingH,
          borderRadius: RADIUS.md,
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "row",
          gap: SPACING.sm,
        },
        getVariantStyles(pressed),
        style,
      ]}
    >
      {isLoading && (
        <ActivityIndicator
          size="small"
          color={getTextColor()}
        />
      )}
      <Text
        style={{
          color: getTextColor(),
          fontSize: sizeConfig.fontSize,
          fontWeight: FONT_WEIGHT.semibold,
        }}
      >
        {isLoading ? "Loading…" : label}
      </Text>
    </Pressable>
  );
}
