/**
 * PathForge Mobile — Error Boundary
 * ====================================
 * Root error boundary with fallback UI and Sentry integration.
 */

import React, { Component } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SPACING,
} from "../constants/theme";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error.message || "An unexpected error occurred",
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // TODO: Integrate sentry-expo when Sentry DSN is configured
    // Sentry.Native.captureException(error, { extra: errorInfo });
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, errorMessage: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <Text style={styles.icon}>⚠️</Text>
          <Text style={styles.title}>Something Went Wrong</Text>
          <Text style={styles.message}>
            {this.state.errorMessage}
          </Text>
          <Pressable
            style={({ pressed }) => [
              styles.button,
              {
                backgroundColor: pressed
                  ? BRAND.primaryDark
                  : BRAND.primary,
              },
            ]}
            onPress={this.handleRetry}
            accessibilityRole="button"
          >
            <Text style={styles.buttonText}>Try Again</Text>
          </Pressable>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: SPACING.xl,
    backgroundColor: "#0F172A",
  },
  icon: {
    fontSize: 64,
    marginBottom: SPACING.lg,
  },
  title: {
    fontSize: FONT_SIZE.xl,
    fontWeight: FONT_WEIGHT.bold,
    color: "#F8FAFC",
    marginBottom: SPACING.sm,
  },
  message: {
    fontSize: FONT_SIZE.md,
    color: "#CBD5E1",
    textAlign: "center",
    marginBottom: SPACING.xl,
    lineHeight: 22,
  },
  button: {
    paddingHorizontal: SPACING.xl,
    paddingVertical: SPACING.md,
    borderRadius: RADIUS.md,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.semibold,
  },
});
