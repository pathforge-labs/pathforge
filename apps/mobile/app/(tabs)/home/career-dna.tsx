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

import type { CareerDnaProfileResponse } from "@pathforge/shared/types/api/career-dna";

// ── Dimension Card Data ─────────────────────────────────────

interface DimensionCard {
  id: string;
  title: string;
  score: number;
  scoreLabel: string;
  content: string[];
}

function buildDimensions(profile: CareerDnaProfileResponse): DimensionCard[] {
  const dimensions: DimensionCard[] = [];

  // 1. Skill Genome
  if (profile.skill_genome.length > 0) {
    const avgProficiency = Math.round(
      profile.skill_genome.reduce((sum, skill) => sum + skill.proficiency_level, 0) /
        profile.skill_genome.length,
    );
    dimensions.push({
      id: "skill_genome",
      title: "🧬 Skill Genome",
      score: avgProficiency,
      scoreLabel: `${profile.skill_genome.length} skills mapped`,
      content: profile.skill_genome
        .slice(0, 5)
        .map((skill) => `${skill.skill_name} — Level ${skill.proficiency_level}`),
    });
  }

  // 2. Experience Blueprint
  if (profile.experience_blueprint) {
    const blueprint = profile.experience_blueprint;
    dimensions.push({
      id: "experience_blueprint",
      title: "📋 Experience Blueprint",
      score: Math.round(blueprint.industry_diversity * 100),
      scoreLabel: `${blueprint.total_years} years · ${blueprint.career_pattern}`,
      content: [
        `Pattern: ${blueprint.career_pattern}`,
        `Progression: ${blueprint.role_progression}`,
        ...(blueprint.notable_transitions || []),
      ],
    });
  }

  // 3. Growth Vector
  if (profile.growth_vector) {
    const growth = profile.growth_vector;
    dimensions.push({
      id: "growth_vector",
      title: "📈 Growth Vector",
      score: growth.momentum_score,
      scoreLabel: `Trajectory: ${growth.trajectory_direction}`,
      content: [
        `Direction: ${growth.trajectory_direction}`,
        ...(growth.projected_roles || []).map((role) => `→ ${role}`),
        ...(growth.growth_catalysts || []).map((catalyst) => `✦ ${catalyst}`),
      ],
    });
  }

  // 4. Values Profile
  if (profile.values_profile) {
    const values = profile.values_profile;
    dimensions.push({
      id: "values_profile",
      title: "💎 Values Profile",
      score: 0,
      scoreLabel: values.work_style,
      content: [
        `Work style: ${values.work_style}`,
        ...(values.top_values || []).map((value) => `• ${value}`),
      ],
    });
  }

  // 5. Market Position
  if (profile.market_position) {
    const market = profile.market_position;
    dimensions.push({
      id: "market_position",
      title: "🎯 Market Position",
      score: market.competitiveness_score,
      scoreLabel: `P${market.salary_percentile} · ${market.demand_level} demand`,
      content: [
        `Demand: ${market.demand_level}`,
        `Salary percentile: P${market.salary_percentile}`,
        market.positioning_advice,
      ],
    });
  }

  // 6. Hidden Skills
  if (profile.hidden_skills.length > 0) {
    const avgConfidence = Math.round(
      profile.hidden_skills.reduce((sum, skill) => sum + skill.confidence, 0) /
        profile.hidden_skills.length,
    );
    dimensions.push({
      id: "hidden_skills",
      title: "🔍 Hidden Skills",
      score: avgConfidence,
      scoreLabel: `${profile.hidden_skills.length} discovered`,
      content: profile.hidden_skills.map(
        (skill) => `${skill.skill_name} (${Math.round(skill.confidence * 100)}%)`,
      ),
    });
  }

  return dimensions;
}

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
