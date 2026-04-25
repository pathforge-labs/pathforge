/**
 * PathForge Mobile — Career DNA Detail Screen
 * ===============================================
 * All 6 Career DNA dimensions displayed via IntelligenceBlock.
 * Navigated to from home screen "View full profile →" link.
 */

import React, { useCallback } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useTheme } from "../../../hooks/use-theme";
import { useCareerDnaProfile } from "../../../hooks/use-career-dna";
import { IntelligenceBlock } from "../../../components/intelligence-block";
import { BRAND, FONT_SIZE, FONT_WEIGHT, SPACING } from "../../../constants/theme";

import { buildDimensions } from "../../../lib/career-dna-helpers";

// ── Screen ──────────────────────────────────────────────────

export default function CareerDnaDetailScreen(): React.JSX.Element {
  const { colors: theme } = useTheme();
  const { data: profile, isLoading, error, refetch, isRefetching } = useCareerDnaProfile();

  const onRefresh = useCallback((): void => {
    void refetch();
  }, [refetch]);

  if (isLoading) {
    return (
      <View style={[styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator color={BRAND.primary} size="large" />
        <Text style={[styles.loadingText, { color: theme.textSecondary }]}>
          Loading Career DNA…
        </Text>
      </View>
    );
  }

  if (error || !profile) {
    return (
      <View style={[styles.centered, { backgroundColor: theme.background }]}>
        <Text style={styles.errorText}>
          Unable to load Career DNA profile.
        </Text>
      </View>
    );
  }

  const dimensions = buildDimensions(profile);

  return (
    <FlatList
      style={{ backgroundColor: theme.background }}
      contentContainerStyle={styles.listContent}
      data={dimensions}
      keyExtractor={(item) => item.id}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={onRefresh}
          tintColor={BRAND.primary}
        />
      }
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={[styles.title, { color: theme.text }]}>
            🧬 Career DNA Profile
          </Text>
          <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
            {profile.completeness_score}% complete · Generated{" "}
            {new Date(profile.generated_at).toLocaleDateString()}
          </Text>
        </View>
      }
      renderItem={({ item }) => (
        <IntelligenceBlock
          title={item.title}
          score={item.score > 0 ? item.score : undefined}
          scoreLabel={item.scoreLabel}
        >
          {item.content.map((line, index) => (
            <Text
              key={`${item.id}-${index}`}
              style={[styles.contentLine, { color: theme.textSecondary }]}
            >
              {line}
            </Text>
          ))}
        </IntelligenceBlock>
      )}
    />
  );
}

// ── Styles ──────────────────────────────────────────────────

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    gap: SPACING.md,
  },
  listContent: {
    padding: SPACING.lg,
  },
  header: {
    marginBottom: SPACING.lg,
  },
  title: {
    fontSize: FONT_SIZE.xxl,
    fontWeight: FONT_WEIGHT.bold,
  },
  subtitle: {
    fontSize: FONT_SIZE.sm,
    marginTop: SPACING.xs,
  },
  contentLine: {
    fontSize: FONT_SIZE.sm,
    lineHeight: 22,
    marginTop: SPACING.xs,
  },
  loadingText: {
    fontSize: FONT_SIZE.sm,
  },
  errorText: {
    fontSize: FONT_SIZE.md,
    color: "#EF4444",
    textAlign: "center",
  },
});
