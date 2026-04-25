/**
 * PathForge Mobile — Login Screen
 * ==================================
 * Email + password login using shared UI components.
 */

import React, { useCallback, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";

import { Button, Input } from "../../components/ui";
import { useAuth } from "../../providers/auth-provider";
import { useTheme } from "../../hooks/use-theme";
import { ApiError } from "../../lib/http";
import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  SPACING,
} from "../../constants/theme";

export default function LoginScreen(): React.JSX.Element {
  const { login } = useAuth();
  const router = useRouter();
  const { colors } = useTheme();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  const validate = useCallback((): boolean => {
    const next: { email?: string; password?: string } = {};

    if (!email.trim()) {
      next.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      next.email = "Enter a valid email address";
    }

    if (!password.trim()) {
      next.password = "Password is required";
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  }, [email, password]);

  const handleLogin = useCallback(async (): Promise<void> => {
    if (!validate()) return;

    setIsLoading(true);
    try {
      await login(email.trim(), password);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "An unexpected error occurred. Please try again.";
      setErrors({ password: message });
    } finally {
      setIsLoading(false);
    }
  }, [email, password, login, validate]);

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.logo, { color: BRAND.primary }]}>PathForge</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Career Intelligence in Your Pocket
          </Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          <Input
            label="Email"
            value={email}
            onChangeText={(text) => {
              setEmail(text);
              setErrors((prev) => ({ ...prev, email: undefined }));
            }}
            error={errors.email}
            placeholder="you@example.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            editable={!isLoading}
            returnKeyType="next"
          />

          <Input
            label="Password"
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              setErrors((prev) => ({ ...prev, password: undefined }));
            }}
            error={errors.password}
            placeholder="Enter your password"
            secureTextEntry
            editable={!isLoading}
            returnKeyType="done"
            onSubmitEditing={handleLogin}
          />

          <Button
            label="Sign In"
            onPress={handleLogin}
            isLoading={isLoading}
            size="lg"
          />
        </View>

        {/* Footer */}
        <Pressable
          style={styles.footer}
          onPress={() => router.push("/(auth)/register")}
          accessibilityRole="link"
        >
          <Text style={[styles.footerText, { color: colors.textSecondary }]}>
            Don't have an account?{" "}
            <Text style={{ color: BRAND.primary, fontWeight: FONT_WEIGHT.semibold }}>
              Create one
            </Text>
          </Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: SPACING.xl,
  },
  header: {
    alignItems: "center",
    marginBottom: SPACING.xxxl,
  },
  logo: {
    fontSize: FONT_SIZE.hero,
    fontWeight: FONT_WEIGHT.bold,
    marginBottom: SPACING.sm,
  },
  subtitle: {
    fontSize: FONT_SIZE.md,
  },
  form: {
    gap: SPACING.lg,
  },
  footer: {
    alignItems: "center",
    marginTop: SPACING.xxl,
    padding: SPACING.md,
  },
  footerText: {
    fontSize: FONT_SIZE.sm,
  },
});
