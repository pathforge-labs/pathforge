/**
 * PathForge Mobile — Component: ThreatSummary
 * ===============================================
 * Compact threat overview card for the home screen.
 * Shows automation risk score + top threat with mitigation guidance.
 */

import React from "react";
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useThreatRadarOverview } from "../hooks/use-threat-radar";
import { IntelligenceBlock } from "./intelligence-block";
import { BRAND, FONT_SIZE, FONT_WEIGHT, SPACING } from "../constants/theme";

// ── Risk Level Badge ────────────────────────────────────────

export function getRiskColor(score: number): string {
  if (score >= 70) return "#EF4444"; // High risk = red
  if (score >= 40) return "#F59E0B"; // Medium risk = amber
  return "#10B981"; // Low risk = green
}

export function getRiskLabel(score: number): string {
  if (score >= 70) return "High Risk";
  if (score >= 40) return "Moderate Risk";
  return "Low Risk";
}

// ── Component ───────────────────────────────────────────────

export function ThreatSummary(): React.JSX.Element | null {
  const { data, isLoading, error } = useThreatRadarOverview();

  if (isLoading) {
    return (
      <IntelligenceBlock title="⚡ Career Threat Radar">
        <View style={styles.loadingContainer}>
          <ActivityIndicator color={BRAND.primary} size="small" />
          <Text style={styles.loadingText}>Scanning threats…</Text>
        </View>
      </IntelligenceBlock>
    );
  }

  if (error || !data) {
    return null; // Graceful degradation — don't show if unavailable
  }

  const riskScore = data.automation_risk?.overall_risk_score ?? 0;
  const riskColor = getRiskColor(riskScore);
  const riskLabel = getRiskLabel(riskScore);

  return (
    <IntelligenceBlock
      title="⚡ Career Threat Radar"
      score={Math.round(riskScore)}
      scoreLabel={riskLabel}
    >
      {/* Risk Summary */}
      <View style={styles.riskRow}>
        <View style={[styles.riskBadge, { backgroundColor: riskColor + "20" }]}>
          <Text style={[styles.riskBadgeText, { color: riskColor }]}>
            {riskLabel}
          </Text>
        </View>
      </View>

      {/* Key factors */}
      {data.automation_risk?.key_factors && data.automation_risk.key_factors.length > 0 ? (
        <Text style={styles.analysisText}>
          {data.automation_risk.key_factors[0]}
        </Text>
      ) : null}

      {/* Skills Shield Summary */}
      {data.skills_shield?.shields && data.skills_shield.shields.length > 0 ? (
        <View style={styles.shieldContainer}>
          <Text style={styles.sectionLabel}>🛡️ Protective Skills</Text>
          {data.skills_shield.shields.slice(0, 3).map((skill, index) => (
            <Text key={`shield-${index}`} style={styles.shieldItem}>
              • {skill.skill_name}
            </Text>
          ))}
        </View>
      ) : null}
    </IntelligenceBlock>
  );
}

// ── Styles ──────────────────────────────────────────────────

const styles = StyleSheet.create({
  loadingContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.sm,
    paddingVertical: SPACING.sm,
  },
  loadingText: {
    color: "#94A3B8",
    fontSize: FONT_SIZE.sm,
  },
  riskRow: {
    flexDirection: "row",
    marginTop: SPACING.sm,
  },
  riskBadge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    borderRadius: 8,
  },
  riskBadgeText: {
    fontSize: FONT_SIZE.xs,
    fontWeight: FONT_WEIGHT.semibold,
  },
  analysisText: {
    color: "#94A3B8",
    fontSize: FONT_SIZE.sm,
    lineHeight: 20,
    marginTop: SPACING.sm,
  },
  shieldContainer: {
    marginTop: SPACING.md,
  },
  sectionLabel: {
    color: "#E2E8F0",
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.semibold,
    marginBottom: SPACING.xs,
  },
  shieldItem: {
    color: "#94A3B8",
    fontSize: FONT_SIZE.sm,
    lineHeight: 22,
  },
});
