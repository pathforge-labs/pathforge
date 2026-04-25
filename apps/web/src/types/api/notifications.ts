/**
 * PathForge — API Types: Notifications
 * =======================================
 * Types for the Notification Engine.
 */

export interface NotificationResponse {
  id: string;
  notification_type: string;
  severity: "info" | "warning" | "critical" | "success";
  title: string;
  message: string;
  source_engine: string;
  is_read: boolean;
  action_url: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface NotificationCountResponse {
  total_unread: number;
  by_severity: Record<string, number>;
}

export interface NotificationMarkReadRequest {
  notification_ids: string[];
}

export interface NotificationDigestResponse {
  id: string;
  digest_type: "daily" | "weekly";
  summary: string;
  notification_count: number;
  highlights: string[];
  generated_at: string;
}

export interface NotificationDigestListResponse {
  items: NotificationDigestResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface NotificationPreferenceResponse {
  id: string;
  email_enabled: boolean;
  push_enabled: boolean;
  digest_frequency: string;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  muted_engines: string[];
}

export interface NotificationPreferenceUpdateRequest {
  email_enabled?: boolean;
  push_enabled?: boolean;
  digest_frequency?: string;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  muted_engines?: string[];
}
