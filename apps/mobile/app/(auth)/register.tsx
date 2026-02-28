/**
 * PathForge Mobile — Register Screen
 * =====================================
 * Registration with shared UI components and inline validation.
 */

import React, { useCallback, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
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

interface FormErrors {
  fullName?: string;
  email?: string;
  password?: string;
}

export default function RegisterScreen(): React.JSX.Element {
  const { register } = useAuth();
  const router = useRouter();
  const { colors } = useTheme();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});

  const validate = useCallback((): boolean => {
    const next: FormErrors = {};

    if (!fullName.trim()) {
      next.fullName = "Full name is required";
    } else if (fullName.trim().length < 2) {
      next.fullName = "Name must be at least 2 characters";
    }

    if (!email.trim()) {
      next.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      next.email = "Enter a valid email address";
    }

    if (!password.trim()) {
      next.password = "Password is required";
    } else if (password.length < 8) {
      next.password = "Password must be at least 8 characters";
    }

    setErrors(next);
    return Object.keys(next).length === 0;
  }, [fullName, email, password]);

  const handleRegister = useCallback(async (): Promise<void> => {
    if (!validate()) return;

    setIsLoading(true);
    try {
      await register(email.trim(), password, fullName.trim());
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "An unexpected error occurred. Please try again.";
      setErrors({ email: message });
    } finally {
      setIsLoading(false);
    }
  }, [fullName, email, password, register, validate]);

  const clearFieldError = useCallback(
    (field: keyof FormErrors) =>
      (text: string): void => {
        const setters: Record<keyof FormErrors, (val: string) => void> = {
          fullName: setFullName,
          email: setEmail,
          password: setPassword,
        };
        setters[field](text);
        setErrors((prev) => ({ ...prev, [field]: undefined }));
      },
    [],
  );

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={[styles.logo, { color: BRAND.primary }]}>
              PathForge
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Create your career intelligence account
            </Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <Input
              label="Full Name"
              value={fullName}
              onChangeText={clearFieldError("fullName")}
              error={errors.fullName}
              placeholder="Your full name"
              autoCorrect={false}
              editable={!isLoading}
              returnKeyType="next"
            />

            <Input
              label="Email"
              value={email}
              onChangeText={clearFieldError("email")}
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
              onChangeText={clearFieldError("password")}
              error={errors.password}
              placeholder="Minimum 8 characters"
              helperText="Must be at least 8 characters"
              secureTextEntry
              editable={!isLoading}
              returnKeyType="done"
              onSubmitEditing={handleRegister}
            />

            <Button
              label="Create Account"
              onPress={handleRegister}
              isLoading={isLoading}
              size="lg"
            />
          </View>

          {/* Footer */}
          <Pressable
            style={styles.footer}
            onPress={() => router.back()}
            accessibilityRole="link"
          >
            <Text style={[styles.footerText, { color: colors.textSecondary }]}>
              Already have an account?{" "}
              <Text
                style={{
                  color: BRAND.primary,
                  fontWeight: FONT_WEIGHT.semibold,
                }}
              >
                Sign in
              </Text>
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
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
    textAlign: "center",
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
