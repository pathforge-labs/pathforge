/**
 * PathForge Mobile — 404 Not Found
 * ===================================
 * Fallback screen for unmatched routes.
 */

import React from "react";
import { StyleSheet, Text, View, Pressable, useColorScheme } from "react-native";
import { useRouter } from "expo-router";

import { BRAND, DARK, FONT_SIZE, FONT_WEIGHT, LIGHT, RADIUS, SPACING } from "../constants/theme";

export default function NotFoundScreen(): React.JSX.Element {
  const router = useRouter();
  const colorScheme = useColorScheme();
  const theme = colorScheme === "dark" ? DARK : LIGHT;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Text style={styles.icon}>🔍</Text>
      <Text style={[styles.title, { color: theme.text }]}>Page Not Found</Text>
      <Text style={[styles.message, { color: theme.textSecondary }]}>
        The page you're looking for doesn't exist.
      </Text>
      <Pressable
        style={({ pressed }) => [
          styles.button,
          { backgroundColor: pressed ? BRAND.primaryDark : BRAND.primary },
        ]}
        onPress={() => router.replace("/")}
        accessibilityRole="button"
      >
        <Text style={styles.buttonText}>Go Home</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: SPACING.xl,
  },
  icon: {
    fontSize: 64,
    marginBottom: SPACING.lg,
  },
  title: {
    fontSize: FONT_SIZE.xxl,
    fontWeight: FONT_WEIGHT.bold,
    marginBottom: SPACING.sm,
  },
  message: {
    fontSize: FONT_SIZE.md,
    textAlign: "center",
    marginBottom: SPACING.xl,
  },
  button: {
    paddingHorizontal: SPACING.xl,
    paddingVertical: SPACING.md,
    borderRadius: RADIUS.md,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.semibold,
  },
});
