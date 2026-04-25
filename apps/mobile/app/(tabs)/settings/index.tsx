/**
 * PathForge Mobile — Settings Screen
 * =====================================
 * Profile info, notification preferences, and logout.
 */

import React, { useCallback, useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useColorScheme,
} from "react-native";

import { useAuth } from "../../../providers/auth-provider";
import {
  BRAND,
  DARK,
  FONT_SIZE,
  FONT_WEIGHT,
  LIGHT,
  RADIUS,
  SHADOW,
  SPACING,
} from "../../../constants/theme";
import { usePushNotifications } from "../../../hooks/use-push-notifications";

export default function SettingsScreen(): React.JSX.Element {
  const { user, logout } = useAuth();
  const colorScheme = useColorScheme();
  const theme = colorScheme === "dark" ? DARK : LIGHT;

  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const pushState = usePushNotifications();

  const handleEnablePush = useCallback(async (): Promise<void> => {
    await pushState.requestPermission();
  }, [pushState]);

  const handleLogout = useCallback(async (): Promise<void> => {
    Alert.alert(
      "Sign Out",
      "Are you sure you want to sign out?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Sign Out",
          style: "destructive",
          onPress: async () => {
            setIsLoggingOut(true);
            // Deregister the Expo push token before clearing auth.
            // The hook owns the token and the API call is best-effort
            // (it must still happen with a valid session, hence pre-logout).
            await pushState.handleDeregister();
            await logout();
          },
        },
      ],
    );
  }, [logout, pushState]);

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Profile Card */}
      <View
        style={[
          styles.card,
          { backgroundColor: theme.surfaceElevated, borderColor: theme.border },
          SHADOW.sm,
        ]}
      >
        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          Profile
        </Text>
        <View style={styles.infoRow}>
          <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>
            Name
          </Text>
          <Text style={[styles.infoValue, { color: theme.text }]}>
            {user?.full_name ?? "—"}
          </Text>
        </View>
        <View style={[styles.divider, { backgroundColor: theme.border }]} />
        <View style={styles.infoRow}>
          <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>
            Email
          </Text>
          <Text style={[styles.infoValue, { color: theme.text }]}>
            {user?.email ?? "—"}
          </Text>
        </View>
      </View>

      {/* Notification Preferences */}
      <View
        style={[
          styles.card,
          { backgroundColor: theme.surfaceElevated, borderColor: theme.border },
          SHADOW.sm,
        ]}
      >
        <Text style={[styles.sectionTitle, { color: theme.text }]}>
          Notifications
        </Text>
        <View style={styles.infoRow}>
          <Text style={[styles.infoLabel, { color: theme.textSecondary }]}>
            Push Notifications
          </Text>
          {pushState.permissionGranted ? (
            <View
              style={[styles.badge, { backgroundColor: "#10B981" + "20" }]}
            >
              <Text style={[styles.badgeText, { color: "#10B981" }]}>
                Enabled
              </Text>
            </View>
          ) : (
            <Pressable
              onPress={handleEnablePush}
              style={[styles.badge, { backgroundColor: BRAND.primary + "20" }]}
              accessibilityRole="button"
              accessibilityLabel="Enable push notifications"
            >
              <Text style={[styles.badgeText, { color: BRAND.primary }]}>
                Enable
              </Text>
            </Pressable>
          )}
        </View>
        {pushState.expoPushToken ? (
          <Text
            style={[styles.tokenText, { color: theme.textTertiary }]}
            numberOfLines={1}
          >
            Token: {pushState.expoPushToken.slice(0, 20)}…
          </Text>
        ) : null}
      </View>

      {/* Account Actions */}
      <View style={styles.actions}>
        <Pressable
          style={({ pressed }) => [
            styles.logoutButton,
            {
              backgroundColor: pressed ? BRAND.error + "30" : BRAND.error + "15",
            },
          ]}
          onPress={handleLogout}
          disabled={isLoggingOut}
          accessibilityRole="button"
          accessibilityLabel="Sign out"
        >
          <Text
            style={[
              styles.logoutText,
              { color: BRAND.error, opacity: isLoggingOut ? 0.5 : 1 },
            ]}
          >
            {isLoggingOut ? "Signing out…" : "Sign Out"}
          </Text>
        </Pressable>
      </View>

      {/* App Info */}
      <View style={styles.appInfo}>
        <Text style={[styles.appVersion, { color: theme.textTertiary }]}>
          PathForge Mobile v0.1.0
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: SPACING.lg,
    gap: SPACING.lg,
    paddingBottom: SPACING.xxxl,
  },
  card: {
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: SPACING.sm,
  },
  sectionTitle: {
    fontSize: FONT_SIZE.lg,
    fontWeight: FONT_WEIGHT.semibold,
    marginBottom: SPACING.md,
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: SPACING.sm,
  },
  infoLabel: {
    fontSize: FONT_SIZE.md,
  },
  infoValue: {
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.medium,
  },
  divider: {
    height: 1,
    marginVertical: SPACING.xs,
  },
  badge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.round,
  },
  badgeText: {
    fontSize: FONT_SIZE.xs,
    fontWeight: FONT_WEIGHT.medium,
  },
  comingSoon: {
    fontSize: FONT_SIZE.sm,
  },
  tokenText: {
    fontSize: FONT_SIZE.xs,
    marginTop: SPACING.xs,
  },
  actions: {
    gap: SPACING.md,
  },
  logoutButton: {
    height: 48,
    borderRadius: RADIUS.md,
    justifyContent: "center",
    alignItems: "center",
  },
  logoutText: {
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.semibold,
  },
  appInfo: {
    alignItems: "center",
    paddingTop: SPACING.lg,
  },
  appVersion: {
    fontSize: FONT_SIZE.xs,
  },
});
