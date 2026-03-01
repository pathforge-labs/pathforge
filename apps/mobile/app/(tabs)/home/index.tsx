/**
 * PathForge Mobile — Home Screen
 * =================================
 * Career DNA summary + Threat Summary — live intelligence dashboard.
 * Sprint 32: Replaces Sprint 31 placeholder with real data.
 */

import React from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";

import { useAuth } from "../../../providers/auth-provider";
import { useTheme, type ThemeColors } from "../../../hooks/use-theme";
import { useCareerDnaSummary } from "../../../hooks/use-career-dna";
import { ThreatSummary } from "../../../components/threat-summary";
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
  const router = useRouter();

  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useCareerDnaSummary();

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

      {/* Career DNA Summary */}
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
        </View>

        {summaryLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator color={BRAND.primary} size="small" />
            <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
              Analyzing your career profile…
            </Text>
          </View>
        ) : summaryError ? (
          <Text style={[styles.errorText, { color: "#EF4444" }]}>
            Unable to load Career DNA. Pull down to retry.
          </Text>
        ) : summary?.has_profile ? (
          <Pressable
            onPress={() => router.push("/(tabs)/home/career-dna")}
            accessibilityRole="button"
            accessibilityLabel="View full Career DNA profile"
          >
            <View style={styles.heroMetric}>
              <Text style={[styles.heroScore, { color: BRAND.primary }]}>
                {summary.completeness_score}%
              </Text>
              <Text
                style={[styles.heroLabel, { color: theme.textSecondary }]}
              >
                Profile Completeness
              </Text>
            </View>
            <View style={styles.dimensionGrid}>
              {Object.entries(summary.dimension_status).slice(0, 3).map(
                ([dimension, available]) => (
                  <DimensionChip
                    key={dimension}
                    label={formatDimension(dimension)}
                    available={available}
                    theme={theme}
                  />
                ),
              )}
            </View>
            <Text style={[styles.viewAll, { color: BRAND.primary }]}>
              View full profile →
            </Text>
          </Pressable>
        ) : (
          <View>
            <Text
              style={[styles.cardDescription, { color: theme.textSecondary }]}
            >
              Upload your resume to generate a personalized Career DNA profile
              with AI-powered intelligence scores.
            </Text>
          </View>
        )}
      </View>

      {/* Threat Summary */}
      <ThreatSummary />

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

// ── Dimension Chip ──────────────────────────────────────────

interface DimensionChipProps {
  label: string;
  available: boolean;
  theme: ThemeColors;
}

function DimensionChip({
  label,
  available,
  theme,
}: DimensionChipProps): React.JSX.Element {
  return (
    <View
      style={[
        styles.chip,
        {
          backgroundColor: available
            ? BRAND.primary + "15"
            : theme.border + "30",
        },
      ]}
    >
      <Text
        style={[
          styles.chipText,
          { color: available ? BRAND.primary : theme.textSecondary },
        ]}
      >
        {available ? "✓" : "○"} {label}
      </Text>
    </View>
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
        <Text
          style={[styles.actionDescription, { color: theme.textSecondary }]}
        >
          {description}
        </Text>
      </View>
    </View>
  );
}

// ── Helpers ─────────────────────────────────────────────────

function formatDimension(dimension: string): string {
  return dimension
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// ── Styles ──────────────────────────────────────────────────

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
  heroMetric: {
    alignItems: "center",
    paddingVertical: SPACING.md,
  },
  heroScore: {
    fontSize: 48,
    fontWeight: FONT_WEIGHT.bold,
  },
  heroLabel: {
    fontSize: FONT_SIZE.sm,
    marginTop: SPACING.xs,
  },
  dimensionGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: SPACING.xs,
    marginTop: SPACING.sm,
  },
  chip: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.round,
  },
  chipText: {
    fontSize: FONT_SIZE.xs,
    fontWeight: FONT_WEIGHT.medium,
  },
  viewAll: {
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.medium,
    textAlign: "right",
    marginTop: SPACING.md,
  },
  loadingContainer: {
    alignItems: "center",
    paddingVertical: SPACING.xl,
    gap: SPACING.sm,
  },
  loadingText: {
    fontSize: FONT_SIZE.sm,
  },
  errorText: {
    fontSize: FONT_SIZE.sm,
    textAlign: "center",
    paddingVertical: SPACING.md,
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
