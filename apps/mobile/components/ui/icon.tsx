/**
 * PathForge Mobile — Icon System
 * =================================
 * Centralized icon registry using @expo/vector-icons (Ionicons).
 *
 * WHY Ionicons?
 * - 1300+ icons with consistent visual weight
 * - Outline/filled pairs for active/inactive states
 * - Ships with Expo — zero additional bundle cost
 * - Platform-agnostic (no iOS-only SF Symbols dependency)
 *
 * All icon usage MUST go through this module to ensure:
 * 1. Consistent sizing across the app
 * 2. Type-safe icon name references
 * 3. Single point of change for icon library swaps
 */

import React from "react";
import { Ionicons } from "@expo/vector-icons";

// ── Standard Sizes ──────────────────────────────────────────

export const ICON_SIZE = {
  xs: 16,
  sm: 20,
  md: 24,
  lg: 28,
  xl: 32,
  xxl: 48,
} as const;

// ── Named Icons ─────────────────────────────────────────────

/**
 * Semantic icon registry mapping feature names to Ionicons glyphs.
 * Each entry has an outline (inactive) and a filled (active) variant.
 */
const ICON_REGISTRY = {
  // Navigation
  home: { outline: "home-outline", filled: "home" },
  upload: { outline: "cloud-upload-outline", filled: "cloud-upload" },
  settings: { outline: "settings-outline", filled: "settings" },
  notifications: { outline: "notifications-outline", filled: "notifications" },

  // Actions
  camera: { outline: "camera-outline", filled: "camera" },
  image: { outline: "image-outline", filled: "image" },
  document: { outline: "document-outline", filled: "document" },
  search: { outline: "search-outline", filled: "search" },
  add: { outline: "add-circle-outline", filled: "add-circle" },
  close: { outline: "close-circle-outline", filled: "close-circle" },
  back: { outline: "chevron-back-outline", filled: "chevron-back" },
  forward: { outline: "chevron-forward-outline", filled: "chevron-forward" },

  // Status
  checkmark: { outline: "checkmark-circle-outline", filled: "checkmark-circle" },
  warning: { outline: "warning-outline", filled: "warning" },
  error: { outline: "alert-circle-outline", filled: "alert-circle" },
  info: { outline: "information-circle-outline", filled: "information-circle" },

  // Career Intelligence
  dna: { outline: "analytics-outline", filled: "analytics" },
  shield: { outline: "shield-checkmark-outline", filled: "shield-checkmark" },
  trending: { outline: "trending-up-outline", filled: "trending-up" },
  star: { outline: "star-outline", filled: "star" },
  briefcase: { outline: "briefcase-outline", filled: "briefcase" },
  globe: { outline: "globe-outline", filled: "globe" },

  // User
  person: { outline: "person-outline", filled: "person" },
  logout: { outline: "log-out-outline", filled: "log-out" },
  lock: { outline: "lock-closed-outline", filled: "lock-closed" },
  mail: { outline: "mail-outline", filled: "mail" },

  // Misc
  wifi: { outline: "wifi-outline", filled: "wifi" },
  wifiOff: { outline: "cloud-offline-outline", filled: "cloud-offline" },
  moon: { outline: "moon-outline", filled: "moon" },
  eye: { outline: "eye-outline", filled: "eye" },
  eyeOff: { outline: "eye-off-outline", filled: "eye-off" },
} as const;

export type IconName = keyof typeof ICON_REGISTRY;

// ── Component ───────────────────────────────────────────────

interface IconProps {
  /** Semantic icon name from the registry. */
  name: IconName;
  /** Icon size. @default ICON_SIZE.md (24) */
  size?: number;
  /** Icon color. */
  color: string;
  /** Use filled variant instead of outline. @default false */
  filled?: boolean;
}

export function Icon({
  name,
  size = ICON_SIZE.md,
  color,
  filled = false,
}: IconProps): React.JSX.Element {
  const entry = ICON_REGISTRY[name];
  const ionName = filled ? entry.filled : entry.outline;

  return (
    <Ionicons
      name={ionName as keyof typeof Ionicons.glyphMap}
      size={size}
      color={color}
    />
  );
}

// ── Tab Bar Icon ────────────────────────────────────────────

interface TabBarIconProps {
  name: IconName;
  color: string;
  focused: boolean;
  size?: number;
}

/**
 * Tab bar icon with automatic outline/filled switching.
 * Active tabs show filled icons, inactive show outline.
 */
export function TabBarIcon({
  name,
  color,
  focused,
  size = ICON_SIZE.md,
}: TabBarIconProps): React.JSX.Element {
  return (
    <Icon
      name={name}
      size={size}
      color={color}
      filled={focused}
    />
  );
}
