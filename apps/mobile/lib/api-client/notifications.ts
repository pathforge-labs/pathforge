/**
 * PathForge Mobile — API Client: Notifications
 * ================================================
 * Push token registration and notification management.
 */

import { del, get, post, patch } from "../http";

import type {
  NotificationListResponse,
  NotificationCountResponse,
  NotificationMarkReadRequest,
  NotificationPreferenceResponse,
  NotificationPreferenceUpdateRequest,
} from "@pathforge/shared/types/api/notifications";

// ── Push Token Management ───────────────────────────────────

export interface PushTokenRegistration {
  token: string;
  platform: "ios" | "android";
}

export interface PushStatusResponse {
  registered: boolean;
  token: string | null;
  platform: string | null;
}

export async function registerPushToken(
  data: PushTokenRegistration,
): Promise<void> {
  return post<void>("/api/v1/notifications/push-token", data);
}

export async function deregisterPushToken(
  data: { token: string },
): Promise<void> {
  return del("/api/v1/notifications/push-token", { body: data });
}

export async function getPushStatus(): Promise<PushStatusResponse> {
  return get<PushStatusResponse>("/api/v1/notifications/push-status");
}

// ── Notifications ───────────────────────────────────────────

export async function getNotifications(
  page: number = 1,
  perPage: number = 20,
): Promise<NotificationListResponse> {
  return get<NotificationListResponse>(
    `/api/v1/notifications?page=${page}&per_page=${perPage}`,
  );
}

export async function getUnreadCount(): Promise<NotificationCountResponse> {
  return get<NotificationCountResponse>("/api/v1/notifications/unread-count");
}

export async function markNotificationsRead(
  request: NotificationMarkReadRequest,
): Promise<void> {
  return post<void>("/api/v1/notifications/mark-read", request);
}

// ── Preferences ─────────────────────────────────────────────

export async function getNotificationPreferences(): Promise<NotificationPreferenceResponse> {
  return get<NotificationPreferenceResponse>("/api/v1/notifications/preferences");
}

export async function updateNotificationPreferences(
  request: NotificationPreferenceUpdateRequest,
): Promise<NotificationPreferenceResponse> {
  return patch<NotificationPreferenceResponse>(
    "/api/v1/notifications/preferences",
    request,
  );
}
