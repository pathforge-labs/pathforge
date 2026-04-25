/**
 * PathForge Mobile — API Client: Resume
 * ========================================
 * Resume upload with progress tracking via XMLHttpRequest.
 *
 * Uses XMLHttpRequest instead of fetch for upload progress events.
 */

import { API_BASE_URL, UPLOAD_TIMEOUT_MS, ApiError } from "../http";
import { getAccessToken } from "../token-manager";

export interface UploadProgressEvent {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadOptions {
  /** Progress callback (0-100). */
  onProgress?: (event: UploadProgressEvent) => void;
  /** AbortController signal for cancellation. */
  signal?: AbortSignal;
}

export interface UploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

/**
 * Upload a resume file with progress tracking.
 *
 * Uses XMLHttpRequest for upload progress events (fetch API
 * doesn't support upload progress monitoring).
 */
export function uploadResume(
  fileUri: string,
  fileName: string,
  mimeType: string,
  options: UploadOptions = {},
): Promise<UploadResponse> {
  return new Promise<UploadResponse>((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", {
      uri: fileUri,
      name: fileName,
      type: mimeType,
    } as unknown as Blob);

    const xhr = new XMLHttpRequest();
    const url = `${API_BASE_URL}/api/v1/resume/upload`;

    // Set up progress handler
    if (options.onProgress) {
      xhr.upload.onprogress = (event: ProgressEvent) => {
        if (event.lengthComputable) {
          options.onProgress!({
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100),
          });
        }
      };
    }

    // Set up completion handler
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText) as UploadResponse;
          resolve(response);
        } catch {
          reject(new ApiError(xhr.status, "Invalid response from server"));
        }
      } else {
        try {
          const error = JSON.parse(xhr.responseText) as { detail?: string };
          reject(
            new ApiError(
              xhr.status,
              error.detail ?? "Upload failed",
            ),
          );
        } catch {
          reject(new ApiError(xhr.status, "Upload failed"));
        }
      }
    };

    xhr.onerror = () => {
      reject(new ApiError(0, "Network error during upload"));
    };

    xhr.ontimeout = () => {
      reject(new ApiError(0, "Upload timed out", "TIMEOUT"));
    };

    // Handle cancellation via AbortSignal
    if (options.signal) {
      options.signal.addEventListener("abort", () => {
        xhr.abort();
        reject(new ApiError(0, "Upload cancelled", "REQUEST_CANCELLED"));
      });
    }

    // Configure and send
    xhr.open("POST", url);
    xhr.timeout = UPLOAD_TIMEOUT_MS;

    const accessToken = getAccessToken();
    if (accessToken) {
      xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
    }

    xhr.send(formData);
  });
}
