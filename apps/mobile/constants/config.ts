/**
 * PathForge Mobile — Constants: Config
 * =======================================
 * Application-level configuration constants.
 */

// ── API Timeouts ─────────────────────────────────────────────

/** Default request timeout in milliseconds. */
export const DEFAULT_REQUEST_TIMEOUT_MS = 15_000;

/** Upload request timeout in milliseconds. */
export const UPLOAD_REQUEST_TIMEOUT_MS = 30_000;

// ── Retry Configuration ─────────────────────────────────────

/** Maximum retry attempts for 5xx errors. */
export const MAX_RETRY_ATTEMPTS = 1;

/** Base delay for exponential backoff in milliseconds. */
export const RETRY_BASE_DELAY_MS = 1_000;

// ── File Upload Limits ──────────────────────────────────────

/** Maximum file size for resume upload in bytes (10MB). */
export const MAX_UPLOAD_FILE_SIZE_BYTES = 10 * 1024 * 1024;

/** Allowed MIME types for resume upload. */
export const ALLOWED_RESUME_MIME_TYPES: readonly string[] = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "image/jpeg",
  "image/png",
] as const;

/** Human-readable file extensions for error messages. */
export const ALLOWED_RESUME_EXTENSIONS: readonly string[] = [
  "PDF",
  "DOC",
  "DOCX",
  "TXT",
  "JPG",
  "PNG",
] as const;

// ── Notification Limits ─────────────────────────────────────

/** Maximum push notifications per day (server-enforced). */
export const MAX_PUSH_NOTIFICATIONS_PER_DAY = 3;

// ── Query Configuration ─────────────────────────────────────

/** Default stale time for TanStack Query in milliseconds (5 min). */
export const QUERY_STALE_TIME_MS = 5 * 60 * 1_000;

/** Maximum number of retries for failed queries. */
export const QUERY_MAX_RETRIES = 2;

// ── Network ─────────────────────────────────────────────────

/** Network polling interval in milliseconds. */
export const NETWORK_POLL_INTERVAL_MS = 10_000;
