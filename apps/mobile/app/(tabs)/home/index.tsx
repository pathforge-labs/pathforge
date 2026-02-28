/**
 * PathForge Mobile — Home Screen
 * =================================
 * Career DNA summary view — Sprint 31 placeholder, wired in Sprint 32.
 */

import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useAuth } from "../../../providers/auth-provider";
import { useTheme, type ThemeColors } from "../../../hooks/use-theme";
import { Icon } from "../../../components/ui/icon";
import { Card, Badge } from "../../../components/ui";
import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SHADOW,
  SPACING,
} from "../../../constants/theme";

export default function HomeScreen(): React.JSX.Element {
  const { user } = useAuth();
  const { colors: theme } = useTheme();

  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Welcome */}
      <View style={styles.welcomeSection}>
        <Text style={[styles.greeting, { color: theme.textSecondary }]}>
          Welcome back,
        </Text>
        <Text style={[styles.name, { color: theme.text }]}>
          {firstName} 👋
        </Text>
      </View>

      {/* Career DNA Placeholder */}
      <View
        style={[
          styles.card,
          {
            backgroundColor: theme.surfaceElevated,
            borderColor: theme.border,
          },
          SHADOW.md,
        ]}
      >
        <View style={styles.cardHeader}>
          <Text style={[styles.cardTitle, { color: theme.text }]}>
            🧬 Career DNA
          </Text>
          <View
            style={[
              styles.badge,
              { backgroundColor: BRAND.primary + "20" },
            ]}
          >
            <Text style={[styles.badgeText, { color: BRAND.primary }]}>
              Coming in Sprint 32
            </Text>
          </View>
        </View>
        <Text style={[styles.cardDescription, { color: theme.textSecondary }]}>
          Upload your resume to generate your Career DNA profile with
          personalized intelligence scores.
        </Text>
      </View>

      {/* Quick Actions */}
      <View
        style={[
          styles.card,
          {
            backgroundColor: theme.surfaceElevated,
            borderColor: theme.border,
          },
          SHADOW.sm,
        ]}
      >
        <Text style={[styles.cardTitle, { color: theme.text }]}>
          📋 Quick Start
        </Text>
        <View style={styles.actionList}>
          <ActionItem
            icon="📄"
            label="Upload your resume"
            description="Start your career intelligence analysis"
            theme={theme}
          />
          <ActionItem
            icon="🔔"
            label="Enable career alerts"
            description="Get proactive career threat notifications"
            theme={theme}
          />
        </View>
      </View>
    </ScrollView>
  );
}

// ── Action Item ─────────────────────────────────────────────

interface ActionItemProps {
  icon: string;
  label: string;
  description: string;
  theme: ThemeColors;
}

function ActionItem({
  icon,
  label,
  description,
  theme,
}: ActionItemProps): React.JSX.Element {
  return (
    <View style={styles.actionItem}>
      <Text style={styles.actionIcon}>{icon}</Text>
      <View style={styles.actionContent}>
        <Text style={[styles.actionLabel, { color: theme.text }]}>
          {label}
        </Text>
        <Text style={[styles.actionDescription, { color: theme.textSecondary }]}>
          {description}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: SPACING.lg,
    gap: SPACING.lg,
  },
  welcomeSection: {
    paddingTop: SPACING.sm,
  },
  greeting: {
    fontSize: FONT_SIZE.md,
  },
  name: {
    fontSize: FONT_SIZE.xxl,
    fontWeight: FONT_WEIGHT.bold,
  },
  card: {
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: SPACING.sm,
  },
  cardTitle: {
    fontSize: FONT_SIZE.lg,
    fontWeight: FONT_WEIGHT.semibold,
  },
  cardDescription: {
    fontSize: FONT_SIZE.sm,
    lineHeight: 20,
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
  actionList: {
    marginTop: SPACING.md,
    gap: SPACING.md,
  },
  actionItem: {
    flexDirection: "row",
    gap: SPACING.md,
  },
  actionIcon: {
    fontSize: 24,
    marginTop: 2,
  },
  actionContent: {
    flex: 1,
  },
  actionLabel: {
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.medium,
  },
  actionDescription: {
    fontSize: FONT_SIZE.sm,
    marginTop: 2,
  },
});
