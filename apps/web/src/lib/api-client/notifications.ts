/**
 * PathForge — API Client: Notifications
 * ========================================
 * Notification list, count, digests, and preferences.
 */

import { get, patch, post, put } from "@/lib/http";
import type {
  NotificationCountResponse,
  NotificationDigestListResponse,
  NotificationDigestResponse,
  NotificationListResponse,
  NotificationMarkReadRequest,
  NotificationPreferenceResponse,
  NotificationPreferenceUpdateRequest,
} from "@/types/api";
import type { MessageResponse } from "@/types/api/common";

const BASE = "/api/v1/notifications";

export const notificationsApi = {
  list: (
    page: number = 1,
    pageSize: number = 20,
    category?: string,
    severity?: string,
    isRead?: boolean,
  ): Promise<NotificationListResponse> => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    if (category) params.set("category", category);
    if (severity) params.set("severity", severity);
    if (isRead !== undefined) params.set("is_read", String(isRead));
    return get<NotificationListResponse>(`${BASE}?${params.toString()}`);
  },

  getUnreadCount: (): Promise<NotificationCountResponse> =>
    get<NotificationCountResponse>(`${BASE}/unread-count`),

  markRead: (data: NotificationMarkReadRequest): Promise<MessageResponse> =>
    patch<MessageResponse>(`${BASE}/mark-read`, data),

  markAllRead: (): Promise<MessageResponse> =>
    post<MessageResponse>(`${BASE}/mark-all-read`),

  // ── Digests ───────────────────────────────────────────
  listDigests: (page: number = 1, pageSize: number = 20): Promise<NotificationDigestListResponse> => {
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    return get<NotificationDigestListResponse>(`${BASE}/digests?${params.toString()}`);
  },

  generateDigest: (digestType: string = "weekly"): Promise<NotificationDigestResponse> =>
    post<NotificationDigestResponse>(`${BASE}/digests/generate?digest_type=${encodeURIComponent(digestType)}`),

  // ── Preferences ─────────────────────────────────────────
  getPreferences: (): Promise<NotificationPreferenceResponse> =>
    get<NotificationPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: NotificationPreferenceUpdateRequest): Promise<NotificationPreferenceResponse> =>
    put<NotificationPreferenceResponse>(`${BASE}/preferences`, data),
};
