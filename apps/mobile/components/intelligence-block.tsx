/**
 * PathForge Mobile — Component: IntelligenceBlock
 * ==================================================
 * Expandable card component for intelligence engine data.
 *
 * Features:
 *   - Expand/collapse with LayoutAnimation
 *   - Score-based color theming (red/amber/green)
 *   - Full accessibility: role="button", expanded state
 *   - Reusable across Career DNA, Threat Radar, etc.
 */

import React, { useCallback, useState } from "react";
import {
  LayoutAnimation,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

// ── Types ───────────────────────────────────────────────────

interface IntelligenceBlockProps {
  title: string;
  score?: number;
  scoreLabel?: string;
  children: React.ReactNode;
  initiallyExpanded?: boolean;
}

// ── Score Color Helper ──────────────────────────────────────

function getScoreColor(score: number): string {
  if (score >= 70) return "#10B981"; // Emerald
  if (score >= 40) return "#F59E0B"; // Amber
  return "#EF4444"; // Red
}

// ── Component ───────────────────────────────────────────────

export function IntelligenceBlock({
  title,
  score,
  scoreLabel,
  children,
  initiallyExpanded = false,
}: IntelligenceBlockProps): React.JSX.Element {
  const [expanded, setExpanded] = useState(initiallyExpanded);

  const toggle = useCallback(() => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded((previous) => !previous);
  }, []);

  const scoreColor = score !== undefined ? getScoreColor(score) : "#6C5CE7";

  return (
    <View style={styles.container}>
      <Pressable
        onPress={toggle}
        style={styles.header}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        accessibilityLabel={`${title}${score !== undefined ? `, score ${score}` : ""}. Tap to ${expanded ? "collapse" : "expand"}`}
      >
        <View style={styles.headerLeft}>
          <Text style={styles.title}>{title}</Text>
          {scoreLabel ? (
            <Text style={[styles.scoreLabel, { color: scoreColor }]}>
              {scoreLabel}
            </Text>
          ) : null}
        </View>
        <View style={styles.headerRight}>
          {score !== undefined ? (
            <View style={[styles.scoreBadge, { backgroundColor: scoreColor }]}>
              <Text style={styles.scoreText}>{score}</Text>
            </View>
          ) : null}
          <Text style={styles.chevron}>{expanded ? "▲" : "▼"}</Text>
        </View>
      </Pressable>

      {expanded ? <View style={styles.content}>{children}</View> : null}
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#1E1E2E",
    borderRadius: 16,
    marginBottom: 12,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(108, 92, 231, 0.15)",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  headerLeft: {
    flex: 1,
    marginRight: 12,
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  title: {
    color: "#E2E8F0",
    fontSize: 15,
    fontWeight: "600",
  },
  scoreLabel: {
    fontSize: 12,
    fontWeight: "500",
    marginTop: 2,
  },
  scoreBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: "center",
    alignItems: "center",
  },
  scoreText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
  },
  chevron: {
    color: "#64748B",
    fontSize: 12,
  },
  content: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    borderTopWidth: 1,
    borderTopColor: "rgba(108, 92, 231, 0.1)",
  },
});
