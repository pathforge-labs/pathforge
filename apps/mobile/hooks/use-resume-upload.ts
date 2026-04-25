/**
 * PathForge Mobile — useResumeUpload Hook
 * ==========================================
 * Encapsulates resume upload logic: file selection, validation,
 * XHR upload with progress, and state management.
 *
 * Separates business logic from presentation for testability.
 */

import { useCallback, useRef, useState } from "react";
import { Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";

import { uploadResume, type UploadProgressEvent, type UploadResponse } from "../lib/api-client/resume";
import { ApiError } from "../lib/http";
import {
  ALLOWED_RESUME_EXTENSIONS,
  ALLOWED_RESUME_MIME_TYPES,
  MAX_UPLOAD_FILE_SIZE_BYTES,
} from "../constants/config";

// ── State ───────────────────────────────────────────────────

export type UploadStatus =
  | "idle"
  | "picking"
  | "validating"
  | "uploading"
  | "success"
  | "error";

export interface ResumeUploadState {
  status: UploadStatus;
  progress: number;
  errorMessage: string | null;
  lastResult: UploadResponse | null;
}

export interface ResumeUploadActions {
  pickFromCamera: () => Promise<void>;
  pickFromGallery: () => Promise<void>;
  pickFromFiles: () => Promise<void>;
  reset: () => void;
  cancel: () => void;
}

// ── Hook ────────────────────────────────────────────────────

export function useResumeUpload(): ResumeUploadState & ResumeUploadActions {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<UploadResponse | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // ── Validation ────────────────────────────────────────────

  const validateFile = useCallback(
    (mimeType: string | null, fileSize: number | null): boolean => {
      if (fileSize && fileSize > MAX_UPLOAD_FILE_SIZE_BYTES) {
        const sizeMb = Math.round(fileSize / (1024 * 1024));
        Alert.alert(
          "File Too Large",
          `Maximum file size is 10MB. Your file is ${sizeMb}MB.`,
        );
        return false;
      }

      if (mimeType && !ALLOWED_RESUME_MIME_TYPES.includes(mimeType)) {
        Alert.alert(
          "Unsupported Format",
          `Supported: ${ALLOWED_RESUME_EXTENSIONS.join(", ")}`,
        );
        return false;
      }

      return true;
    },
    [],
  );

  // ── Core Upload ───────────────────────────────────────────

  const handleUpload = useCallback(
    async (uri: string, fileName: string, mimeType: string): Promise<void> => {
      setStatus("uploading");
      setProgress(0);
      setErrorMessage(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const result = await uploadResume(uri, fileName, mimeType, {
          onProgress: (event: UploadProgressEvent) => {
            setProgress(event.percentage);
          },
          signal: controller.signal,
        });
        setLastResult(result);
        setStatus("success");
      } catch (error) {
        if (error instanceof ApiError && error.code === "REQUEST_CANCELLED") {
          setStatus("idle");
          return;
        }
        const message =
          error instanceof ApiError
            ? error.message
            : "Upload failed. Please try again.";
        setStatus("error");
        setErrorMessage(message);
      } finally {
        abortControllerRef.current = null;
      }
    },
    [],
  );

  // ── Camera ────────────────────────────────────────────────

  const pickFromCamera = useCallback(async (): Promise<void> => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        "Permission Required",
        "Camera access is needed to capture resume documents. Please enable it in Settings.",
      );
      return;
    }

    setStatus("picking");
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ["images"],
      quality: 0.8,
    });

    if (result.canceled || !result.assets[0]) {
      setStatus("idle");
      return;
    }

    const asset = result.assets[0];
    const fileName = asset.fileName ?? `resume_${Date.now()}.jpg`;
    const mimeType = asset.mimeType ?? "image/jpeg";

    setStatus("validating");
    if (!validateFile(mimeType, asset.fileSize ?? null)) {
      setStatus("idle");
      return;
    }

    await handleUpload(asset.uri, fileName, mimeType);
  }, [validateFile, handleUpload]);

  // ── Gallery ───────────────────────────────────────────────

  const pickFromGallery = useCallback(async (): Promise<void> => {
    const permission =
      await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        "Permission Required",
        "Photo library access is needed. Please enable it in Settings.",
      );
      return;
    }

    setStatus("picking");
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
    });

    if (result.canceled || !result.assets[0]) {
      setStatus("idle");
      return;
    }

    const asset = result.assets[0];
    const fileName = asset.fileName ?? `resume_${Date.now()}.jpg`;
    const mimeType = asset.mimeType ?? "image/jpeg";

    setStatus("validating");
    if (!validateFile(mimeType, asset.fileSize ?? null)) {
      setStatus("idle");
      return;
    }

    await handleUpload(asset.uri, fileName, mimeType);
  }, [validateFile, handleUpload]);

  // ── Document Files ────────────────────────────────────────

  const pickFromFiles = useCallback(async (): Promise<void> => {
    setStatus("picking");

    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [...ALLOWED_RESUME_MIME_TYPES],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets[0]) {
        setStatus("idle");
        return;
      }

      const asset = result.assets[0];

      setStatus("validating");
      if (!validateFile(asset.mimeType ?? null, asset.size ?? null)) {
        setStatus("idle");
        return;
      }

      await handleUpload(
        asset.uri,
        asset.name,
        asset.mimeType ?? "application/octet-stream",
      );
    } catch {
      setStatus("idle");
    }
  }, [validateFile, handleUpload]);

  // ── Controls ──────────────────────────────────────────────

  const reset = useCallback((): void => {
    setStatus("idle");
    setProgress(0);
    setErrorMessage(null);
    setLastResult(null);
  }, []);

  const cancel = useCallback((): void => {
    abortControllerRef.current?.abort();
    setStatus("idle");
    setProgress(0);
  }, []);

  return {
    status,
    progress,
    errorMessage,
    lastResult,
    pickFromCamera,
    pickFromGallery,
    pickFromFiles,
    reset,
    cancel,
  };
}
