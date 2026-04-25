/**
 * PathForge — Hook: useNotifications
 * =====================================
 * Data-fetching hooks for the Notification Engine.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationsApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  NotificationCountResponse,
  NotificationListResponse,
  NotificationPreferenceResponse,
  NotificationDigestListResponse,
  NotificationPreferenceUpdateRequest,
} from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useUnreadNotificationCount() {
  const { isAuthenticated } = useAuth();

  return useQuery<NotificationCountResponse, ApiError>({
    queryKey: queryKeys.notifications.unreadCount(),
    queryFn: () => notificationsApi.getUnreadCount(),
    enabled: isAuthenticated,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useNotifications(page?: number, filters?: Record<string, unknown>) {
  const { isAuthenticated } = useAuth();
  const category = filters?.category as string | undefined;
  const severity = filters?.severity as string | undefined;
  const isRead = filters?.isRead as boolean | undefined;

  return useQuery<NotificationListResponse, ApiError>({
    queryKey: queryKeys.notifications.list(page, filters),
    queryFn: () => notificationsApi.list(page, 20, category, severity, isRead),
    enabled: isAuthenticated,
    staleTime: 30_000,
  });
}

export function useNotificationPreferences() {
  const { isAuthenticated } = useAuth();

  return useQuery<NotificationPreferenceResponse, ApiError>({
    queryKey: queryKeys.notifications.preferences(),
    queryFn: () => notificationsApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useNotificationDigests(page?: number) {
  const { isAuthenticated } = useAuth();

  return useQuery<NotificationDigestListResponse, ApiError>({
    queryKey: queryKeys.notifications.digests(page),
    queryFn: () => notificationsApi.listDigests(page),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useGenerateDigest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (format?: string) => notificationsApi.generateDigest(format),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: NotificationPreferenceUpdateRequest) => notificationsApi.updatePreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.preferences() });
    },
  });
}
