/**
 * PathForge Mobile — Auth Group Layout
 * =======================================
 * Stack navigator for authentication screens (login, register).
 */

import React from "react";
import { Stack } from "expo-router";
import { useColorScheme } from "react-native";

import { DARK, LIGHT } from "../../constants/theme";

export default function AuthLayout(): React.JSX.Element {
  const colorScheme = useColorScheme();
  const theme = colorScheme === "dark" ? DARK : LIGHT;

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: theme.background },
        animation: "slide_from_right",
      }}
    />
  );
}
