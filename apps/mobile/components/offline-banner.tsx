/**
 * PathForge Mobile — Offline Banner
 * ====================================
 * Persistent banner showing network status when offline.
 */

import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { useNetworkStatus } from "../lib/network";
import { BRAND, FONT_SIZE, FONT_WEIGHT, SPACING } from "../constants/theme";

export function OfflineBanner(): React.JSX.Element | null {
  const { isConnected, isChecking } = useNetworkStatus();

  // Don't show during initial check or when online
  if (isChecking || isConnected) {
    return null;
  }

  return (
    <View style={styles.banner}>
      <Text style={styles.text}>
        📡 No internet connection — showing cached data
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: BRAND.warning,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.lg,
    alignItems: "center",
  },
  text: {
    color: "#000000",
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.medium,
  },
});
