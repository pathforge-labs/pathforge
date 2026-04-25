/**
 * PathForge Mobile — Home Tab Stack Navigator
 * =============================================
 * Enables navigation from home screen to Career DNA detail view
 * within the home tab without leaving the bottom tabs.
 */

import { Stack } from "expo-router";
import React from "react";

export default function HomeLayout(): React.JSX.Element {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        animation: "slide_from_right",
      }}
    />
  );
}
