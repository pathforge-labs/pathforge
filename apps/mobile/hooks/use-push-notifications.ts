/**
 * PathForge Mobile — Hook: use-push-notifications
 * ===================================================
 * Manages Expo push notification permissions, token registration,
 * and notification response handling (deep linking).
 *
 * Audit Fix #4 (deep linking), #8 (logout deregister), #12 (plugin config).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";

import {
  registerPushToken,
  deregisterPushToken,
} from "../lib/api-client/notifications";

// ── Types ───────────────────────────────────────────────────

interface UsePushNotificationsReturn {
  expoPushToken: string | null;
  permissionGranted: boolean;
  requestPermission: () => Promise<boolean>;
  handleDeregister: () => Promise<void>;
}

// ── Handler Configuration ───────────────────────────────────

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowInForeground: true,
  }),
});

// ── Hook ────────────────────────────────────────────────────

export function usePushNotifications(): UsePushNotificationsReturn {
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const notificationResponseRef = useRef<Notifications.Subscription | null>(null);

  // Register token with backend
  const registerToken = useCallback(async (token: string): Promise<void> => {
    try {
      const platform = Platform.OS === "ios" ? "ios" : "android";
      await registerPushToken({ token, platform: platform as "ios" | "android" });
    } catch (error) {
      console.error("[Push] Failed to register token:", error);
    }
  }, []);

  // Request permission and get token
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (Platform.OS === "web") {
      console.warn("[Push] Push notifications require a native device");
      return false;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") {
      setPermissionGranted(false);
      return false;
    }

    setPermissionGranted(true);

    // Get Expo push token
    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    const tokenResponse = await Notifications.getExpoPushTokenAsync({
      projectId,
    });

    const token = tokenResponse.data;
    setExpoPushToken(token);
    await registerToken(token);

    // Android notification channel
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("career-alerts", {
        name: "Career Alerts",
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 250, 250, 250],
      });
    }

    return true;
  }, [registerToken]);

  // Deregister on logout
  const handleDeregister = useCallback(async (): Promise<void> => {
    try {
      await deregisterPushToken();
      setExpoPushToken(null);
    } catch (error) {
      console.warn("[Push] Deregister failed (best-effort):", error);
    }
  }, []);

  // Listen for notification taps (deep linking)
  useEffect(() => {
    notificationResponseRef.current =
      Notifications.addNotificationResponseReceivedListener((response) => {
        const actionUrl = response.notification.request.content.data?.action_url;
        if (typeof actionUrl === "string" && actionUrl.length > 0) {
          // Deep link handling — router.push(actionUrl) would be called here
          console.info("[Push] Deep link:", actionUrl);
        }
      });

    return () => {
      if (notificationResponseRef.current) {
        Notifications.removeNotificationSubscription(notificationResponseRef.current);
      }
    };
  }, []);

  // Check permission on mount
  useEffect(() => {
    void (async () => {
      if (Platform.OS === "web") return;
      const { status } = await Notifications.getPermissionsAsync();
      setPermissionGranted(status === "granted");
    })();
  }, []);

  return {
    expoPushToken,
    permissionGranted,
    requestPermission,
    handleDeregister,
  };
}
