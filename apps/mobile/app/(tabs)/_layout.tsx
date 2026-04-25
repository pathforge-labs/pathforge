/**
 * PathForge Mobile — Tabs Layout
 * =================================
 * Bottom tab navigator: Home, Upload, Settings.
 *
 * Uses Ionicons via the centralized Icon system — no emoji,
 * no inline requires. Platform-adaptive styling.
 */

import React from "react";
import { StyleSheet, Platform } from "react-native";
import { Tabs } from "expo-router";

import { TabBarIcon } from "../../components/ui/icon";
import { BRAND, FONT_SIZE } from "../../constants/theme";
import { useTheme } from "../../hooks/use-theme";

export default function TabsLayout(): React.JSX.Element {
  const { colors } = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerStyle: {
          backgroundColor: colors.background,
          ...Platform.select({
            android: { elevation: 0 },
            ios: { shadowOpacity: 0 },
          }),
        },
        headerTintColor: colors.text,
        headerTitleStyle: {
          fontSize: FONT_SIZE.lg,
          fontWeight: "600",
        },
        tabBarStyle: {
          backgroundColor: colors.tabBar,
          borderTopColor: colors.border,
          borderTopWidth: StyleSheet.hairlineWidth,
          ...Platform.select({
            android: { elevation: 8, height: 60, paddingBottom: 8 },
            ios: {},
          }),
        },
        tabBarActiveTintColor: BRAND.primary,
        tabBarInactiveTintColor: colors.tabBarInactive,
        tabBarLabelStyle: {
          fontSize: FONT_SIZE.xs,
          fontWeight: "500",
        },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: "Home",
          tabBarLabel: "Home",
          tabBarIcon: ({ color, focused }: { color: string; focused: boolean }) => (
            <TabBarIcon name="home" color={color} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="upload"
        options={{
          title: "Upload",
          tabBarLabel: "Upload",
          tabBarIcon: ({ color, focused }: { color: string; focused: boolean }) => (
            <TabBarIcon name="upload" color={color} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarLabel: "Settings",
          tabBarIcon: ({ color, focused }: { color: string; focused: boolean }) => (
            <TabBarIcon name="settings" color={color} focused={focused} />
          ),
        }}
      />
    </Tabs>
  );
}
