/**
 * PathForge — Hook: useNotifications
 * =====================================
 * Data-fetching hooks for the Notification Engine.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationsApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { NotificationCountResponse } from "@/types/api";
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

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}
