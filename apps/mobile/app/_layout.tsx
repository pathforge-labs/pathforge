/**
 * PathForge Mobile — Root Layout
 * =================================
 * App entry point with:
 * - Sentry crash reporting (Sprint 36 WS-1)
 * - Splash screen hold during SecureStore token hydration
 * - Auth guard routing (login vs tabs)
 * - Provider wrappers (Auth + Query)
 * - Error boundary
 */

import React, { useEffect } from "react";
import { Slot, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useColorScheme, View, StyleSheet, ActivityIndicator } from "react-native";

import { AuthProvider, useAuth } from "../providers/auth-provider";
import { QueryProvider } from "../providers/query-provider";
import { BRAND, DARK, LIGHT } from "../constants/theme";
import { initSentry, wrapWithSentry } from "../lib/sentry";

// Initialize Sentry before any rendering (no-op in __DEV__)
initSentry();

// Hold splash screen until auth state resolves
SplashScreen.preventAutoHideAsync();

// ── Auth Guard ──────────────────────────────────────────────

function AuthGate(): React.JSX.Element {
  const { status, isRestoring } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  const colorScheme = useColorScheme();
  const theme = colorScheme === "dark" ? DARK : LIGHT;

  useEffect(() => {
    if (isRestoring) return;

    // Hide splash once auth state is resolved
    void SplashScreen.hideAsync();

    const inAuthGroup = segments[0] === "(auth)";

    if (status === "authenticated" && inAuthGroup) {
      // User is logged in but on an auth screen — redirect to home
      router.replace("/(tabs)/home");
    } else if (status === "unauthenticated" && !inAuthGroup) {
      // User is not logged in — redirect to login
      router.replace("/(auth)/login");
    }
  }, [status, isRestoring, segments, router]);

  // Show loading while restoring session
  if (isRestoring) {
    return (
      <View style={[styles.loading, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={BRAND.primary} />
      </View>
    );
  }

  return <Slot />;
}

// ── Root Layout ─────────────────────────────────────────────

function RootLayout(): React.JSX.Element {
  const colorScheme = useColorScheme();

  return (
    <QueryProvider>
      <AuthProvider>
        <StatusBar style={colorScheme === "dark" ? "light" : "dark"} />
        <AuthGate />
      </AuthProvider>
    </QueryProvider>
  );
}

// Wrap root with Sentry for automatic crash capture
export default wrapWithSentry(RootLayout);

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
});
