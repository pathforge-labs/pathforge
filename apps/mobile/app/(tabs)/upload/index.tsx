/**
 * PathForge Mobile — Upload Screen
 * ===================================
 * Resume upload with camera, gallery, and file picker.
 *
 * Business logic delegated to useResumeUpload hook.
 * This screen is a thin presentation layer using shared UI components.
 */

import React from "react";
import {
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Button, Card } from "../../../components/ui";
import { useTheme } from "../../../hooks/use-theme";
import { useResumeUpload } from "../../../hooks/use-resume-upload";
import {
  BRAND,
  FONT_SIZE,
  FONT_WEIGHT,
  RADIUS,
  SHADOW,
  SPACING,
} from "../../../constants/theme";

export default function UploadScreen(): React.JSX.Element {
  const { colors } = useTheme();
  const {
    status,
    progress,
    errorMessage,
    pickFromCamera,
    pickFromGallery,
    pickFromFiles,
    reset,
    cancel,
  } = useResumeUpload();

  const isUploading = status === "uploading";

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.title, { color: colors.text }]}>
            Upload Resume
          </Text>
          <Text style={[styles.description, { color: colors.textSecondary }]}>
            Upload your resume to generate Career DNA intelligence. Supports
            PDF, DOC, DOCX, TXT, and images.
          </Text>
        </View>

        {/* Upload Options */}
        {status !== "success" && status !== "error" && (
          <View style={styles.options}>
            <UploadOption
              icon="📷"
              label="Camera"
              description="Capture a photo of your resume"
              onPress={pickFromCamera}
              disabled={isUploading}
            />
            <UploadOption
              icon="🖼️"
              label="Photo Library"
              description="Select from your photos"
              onPress={pickFromGallery}
              disabled={isUploading}
            />
            <UploadOption
              icon="📁"
              label="Files"
              description="Browse documents on your device"
              onPress={pickFromFiles}
              disabled={isUploading}
            />
          </View>
        )}

        {/* Progress */}
        {isUploading && (
          <Card title={`Uploading… ${progress}%`}>
            <View
              style={[styles.progressTrack, { backgroundColor: colors.border }]}
            >
              <View
                style={[
                  styles.progressFill,
                  {
                    backgroundColor: BRAND.primary,
                    width: `${progress}%`,
                  },
                ]}
              />
            </View>
            <Button
              label="Cancel"
              variant="ghost"
              size="sm"
              onPress={cancel}
              style={styles.cancelButton}
            />
          </Card>
        )}

        {/* Success */}
        {status === "success" && (
          <View
            style={[
              styles.resultCard,
              { backgroundColor: BRAND.success + "15" },
            ]}
          >
            <Text style={styles.resultIcon}>✅</Text>
            <Text style={[styles.resultTitle, { color: BRAND.success }]}>
              Upload Complete!
            </Text>
            <Text style={[styles.resultMessage, { color: colors.textSecondary }]}>
              Your resume is being processed. Career DNA intelligence will be
              generated shortly.
            </Text>
            <Button label="Upload Another" onPress={reset} style={styles.actionButton} />
          </View>
        )}

        {/* Error */}
        {status === "error" && (
          <View
            style={[
              styles.resultCard,
              { backgroundColor: BRAND.error + "15" },
            ]}
          >
            <Text style={styles.resultIcon}>❌</Text>
            <Text style={[styles.resultTitle, { color: BRAND.error }]}>
              Upload Failed
            </Text>
            <Text style={[styles.resultMessage, { color: colors.textSecondary }]}>
              {errorMessage ?? "An unexpected error occurred."}
            </Text>
            <Button label="Try Again" onPress={reset} style={styles.actionButton} />
          </View>
        )}
      </View>
    </View>
  );
}

// ── Upload Option Card ──────────────────────────────────────

interface UploadOptionProps {
  icon: string;
  label: string;
  description: string;
  onPress: () => void;
  disabled: boolean;
}

function UploadOption({
  icon,
  label,
  description,
  onPress,
  disabled,
}: UploadOptionProps): React.JSX.Element {
  const { colors } = useTheme();

  return (
    <Pressable
      style={({ pressed }) => [
        styles.optionCard,
        {
          backgroundColor: colors.surfaceElevated,
          borderColor: pressed ? BRAND.primary : colors.border,
          opacity: disabled ? 0.5 : 1,
        },
        SHADOW.sm,
      ]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Text style={styles.optionIcon}>{icon}</Text>
      <View>
        <Text style={[styles.optionLabel, { color: colors.text }]}>
          {label}
        </Text>
        <Text style={[styles.optionDescription, { color: colors.textSecondary }]}>
          {description}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: SPACING.lg,
    gap: SPACING.xl,
  },
  header: {
    gap: SPACING.sm,
  },
  title: {
    fontSize: FONT_SIZE.xl,
    fontWeight: FONT_WEIGHT.bold,
  },
  description: {
    fontSize: FONT_SIZE.sm,
    lineHeight: 20,
  },
  options: {
    gap: SPACING.md,
  },
  optionCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.lg,
    padding: SPACING.lg,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
  },
  optionIcon: {
    fontSize: 28,
  },
  optionLabel: {
    fontSize: FONT_SIZE.md,
    fontWeight: FONT_WEIGHT.semibold,
  },
  optionDescription: {
    fontSize: FONT_SIZE.sm,
    marginTop: 2,
  },
  progressTrack: {
    height: 8,
    borderRadius: RADIUS.round,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: RADIUS.round,
  },
  cancelButton: {
    alignSelf: "center",
    marginTop: SPACING.md,
  },
  resultCard: {
    padding: SPACING.xl,
    borderRadius: RADIUS.lg,
    alignItems: "center",
    gap: SPACING.md,
  },
  resultIcon: {
    fontSize: 48,
  },
  resultTitle: {
    fontSize: FONT_SIZE.lg,
    fontWeight: FONT_WEIGHT.bold,
  },
  resultMessage: {
    fontSize: FONT_SIZE.sm,
    textAlign: "center",
    lineHeight: 20,
  },
  actionButton: {
    marginTop: SPACING.sm,
    minWidth: 160,
  },
});
