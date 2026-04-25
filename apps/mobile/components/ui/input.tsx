/**
 * PathForge Mobile — UI: Input
 * ===============================
 * Themed text input with label, error state, and accessibility.
 * Follows Apple/Material touch target guidelines (44pt minimum).
 */

import React, { forwardRef } from "react";
import {
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
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

interface InputProps extends TextInputProps {
  /** Label displayed above the input. */
  label?: string;
  /** Error message — highlights input border red. */
  error?: string;
  /** Helper text below input. */
  helperText?: string;
}

// ── Component ───────────────────────────────────────────────

export const Input = forwardRef<TextInput, InputProps>(
  function Input(
    { label, error, helperText, style, ...textInputProps }: InputProps,
    ref,
  ): React.JSX.Element {
    const { colors } = useTheme();

    const borderColor = error
      ? BRAND.error
      : colors.border;

    return (
      <View style={styles.container}>
        {label && (
          <Text style={[styles.label, { color: colors.textSecondary }]}>
            {label}
          </Text>
        )}

        <TextInput
          ref={ref}
          {...textInputProps}
          placeholderTextColor={colors.textTertiary}
          accessibilityLabel={label ?? textInputProps.accessibilityLabel}
          accessibilityState={{ disabled: !textInputProps.editable }}
          style={[
            styles.input,
            {
              backgroundColor: colors.surface,
              color: colors.text,
              borderColor,
            },
            style,
          ]}
        />

        {error && (
          <Text
            style={[styles.error, { color: BRAND.error }]}
            accessibilityRole="alert"
          >
            {error}
          </Text>
        )}

        {helperText && !error && (
          <Text style={[styles.helper, { color: colors.textTertiary }]}>
            {helperText}
          </Text>
        )}
      </View>
    );
  },
);

const styles = StyleSheet.create({
  container: {
    gap: SPACING.xs,
  },
  label: {
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.medium,
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.lg,
    fontSize: FONT_SIZE.md,
  },
  error: {
    fontSize: FONT_SIZE.xs,
    fontWeight: FONT_WEIGHT.medium,
  },
  helper: {
    fontSize: FONT_SIZE.xs,
  },
});
