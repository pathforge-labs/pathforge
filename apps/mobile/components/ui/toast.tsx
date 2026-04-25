/**
 * PathForge Mobile — UI: Toast
 * ===============================
 * Non-intrusive feedback banner with auto-dismiss,
 * multiple severity levels, and swipe-to-dismiss.
 *
 * Usage:
 * ```tsx
 * const { showToast } = useToast();
 * showToast({ message: "Resume uploaded!", severity: "success" });
 * ```
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Animated as RNAnimated,
  Pressable,
  StyleSheet,
  Text,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SHADOW,
  SPACING,
} from "../../constants/theme";
import { useTheme } from "../../hooks/use-theme";

// ── Types ───────────────────────────────────────────────────

type ToastSeverity = "success" | "error" | "warning" | "info";

interface ToastConfig {
  message: string;
  severity?: ToastSeverity;
  durationMs?: number;
  action?: {
    label: string;
    onPress: () => void;
  };
}

interface ToastContextValue {
  showToast: (config: ToastConfig) => void;
}

// ── Severity Config ─────────────────────────────────────────

const SEVERITY_MAP: Record<ToastSeverity, { icon: string; color: string }> = {
  success: { icon: "✓", color: BRAND.success },
  error: { icon: "✕", color: BRAND.error },
  warning: { icon: "⚠", color: BRAND.warning },
  info: { icon: "ℹ", color: BRAND.info },
};

const DEFAULT_DURATION_MS = 3_000;

// ── Context ─────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue | null>(null);

// ── Provider ────────────────────────────────────────────────

interface ToastProviderProps {
  children: React.ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps): React.JSX.Element {
  const [toast, setToast] = useState<ToastConfig | null>(null);
  const insets = useSafeAreaInsets();
  const { colors, isDark } = useTheme();
  const translateY = useRef(new RNAnimated.Value(-100)).current;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismiss = useCallback((): void => {
    RNAnimated.timing(translateY, {
      toValue: -100,
      duration: 200,
      useNativeDriver: true,
    }).start(() => setToast(null));
  }, [translateY]);

  const showToast = useCallback(
    (config: ToastConfig): void => {
      // Clear existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      setToast(config);

      // Slide in
      RNAnimated.spring(translateY, {
        toValue: 0,
        useNativeDriver: true,
        tension: 80,
        friction: 10,
      }).start();

      // Auto dismiss
      const duration = config.durationMs ?? DEFAULT_DURATION_MS;
      timeoutRef.current = setTimeout(dismiss, duration);
    },
    [translateY, dismiss],
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const contextValue = useMemo<ToastContextValue>(
    () => ({ showToast }),
    [showToast],
  );

  const severity = toast?.severity ?? "info";
  const severityConfig = SEVERITY_MAP[severity];

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {toast && (
        <RNAnimated.View
          style={[
            styles.toastContainer,
            { top: insets.top + SPACING.sm, transform: [{ translateY }] },
          ]}
        >
          <Pressable
            onPress={dismiss}
            style={[
              styles.toast,
              {
                backgroundColor: isDark ? "#1E293B" : "#FFFFFF",
                borderLeftColor: severityConfig.color,
              },
              SHADOW.lg,
            ]}
          >
            <Text style={[styles.icon, { color: severityConfig.color }]}>
              {severityConfig.icon}
            </Text>
            <Text
              style={[styles.message, { color: colors.text }]}
              numberOfLines={2}
            >
              {toast.message}
            </Text>
            {toast.action && (
              <Pressable
                onPress={() => {
                  toast.action?.onPress();
                  dismiss();
                }}
                hitSlop={8}
              >
                <Text style={[styles.actionLabel, { color: BRAND.primary }]}>
                  {toast.action.label}
                </Text>
              </Pressable>
            )}
          </Pressable>
        </RNAnimated.View>
      )}
    </ToastContext.Provider>
  );
}

// ── Hook ────────────────────────────────────────────────────

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

const styles = StyleSheet.create({
  toastContainer: {
    position: "absolute",
    left: SPACING.lg,
    right: SPACING.lg,
    zIndex: 9999,
  },
  toast: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.md,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.lg,
    borderRadius: RADIUS.lg,
    borderLeftWidth: 4,
  },
  icon: {
    fontSize: 18,
    fontWeight: FONT_WEIGHT.bold,
  },
  message: {
    flex: 1,
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.medium,
    lineHeight: 20,
  },
  actionLabel: {
    fontSize: FONT_SIZE.sm,
    fontWeight: FONT_WEIGHT.bold,
  },
});
