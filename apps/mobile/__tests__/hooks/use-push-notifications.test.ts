/**
 * PathForge Mobile — Test: usePushNotifications
 * =================================================
 * Hook lifecycle tests with full mocking for determinism.
 * Sprint 33 — WS-2: Suite 3 (6 tests)
 */

import { renderHook, act } from "@testing-library/react-native";
import { Platform } from "react-native";

// ── Mocks (inline in factory to avoid jest.mock hoisting issues) ──

jest.mock("expo-notifications", () => ({
  getPermissionsAsync: jest.fn(),
  requestPermissionsAsync: jest.fn(),
  getExpoPushTokenAsync: jest.fn(),
  setNotificationHandler: jest.fn(),
  setNotificationChannelAsync: jest.fn(),
  addNotificationResponseReceivedListener: jest.fn(() => ({
    remove: jest.fn(),
  })),
  removeNotificationSubscription: jest.fn(),
  AndroidImportance: { HIGH: 4 },
}));

jest.mock("expo-constants", () => ({
  expoConfig: {
    extra: {
      eas: { projectId: "test-project-id" },
    },
  },
}));

const mockRouterPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

jest.mock("../../lib/api-client/notifications", () => ({
  registerPushToken: jest.fn(),
  deregisterPushToken: jest.fn(),
}));

jest.mock("../../lib/deep-link-router", () => ({
  resolveDeepLink: (url: string) => ({
    resolved: true,
    route: "/(tabs)/home/career-dna",
    originalUrl: url,
  }),
}));

// Import AFTER mocks
import * as Notifications from "expo-notifications";
import { registerPushToken, deregisterPushToken } from "../../lib/api-client/notifications";
import { usePushNotifications } from "../../hooks/use-push-notifications";

// Cast for Jest mock API access
const mockGetPermissionsAsync = Notifications.getPermissionsAsync as jest.Mock;
const mockRequestPermissionsAsync = Notifications.requestPermissionsAsync as jest.Mock;
const mockGetExpoPushTokenAsync = Notifications.getExpoPushTokenAsync as jest.Mock;
const mockRegisterPushToken = registerPushToken as jest.Mock;
const mockDeregisterPushToken = deregisterPushToken as jest.Mock;

// ── Tests ───────────────────────────────────────────────────

describe("usePushNotifications", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetPermissionsAsync.mockResolvedValue({ status: "undetermined" });
    mockRequestPermissionsAsync.mockResolvedValue({ status: "granted" });
    mockGetExpoPushTokenAsync.mockResolvedValue({ data: "ExponentPushToken[test123]" });
    mockRegisterPushToken.mockResolvedValue(undefined);
    mockDeregisterPushToken.mockResolvedValue(undefined);
  });

  it("initialises with null token and false permission", () => {
    const { result } = renderHook(() => usePushNotifications());
    expect(result.current.expoPushToken).toBeNull();
    expect(result.current.permissionGranted).toBe(false);
  });

  it("returns false on web platform", async () => {
    const originalOS = Platform.OS;
    Object.defineProperty(Platform, "OS", { value: "web", writable: true });

    const { result } = renderHook(() => usePushNotifications());

    let granted = false;
    await act(async () => {
      granted = await result.current.requestPermission();
    });

    expect(granted).toBe(false);
    expect(mockGetExpoPushTokenAsync).not.toHaveBeenCalled();

    Object.defineProperty(Platform, "OS", { value: originalOS, writable: true });
  });

  it("grants permission and registers token on native", async () => {
    Object.defineProperty(Platform, "OS", { value: "ios", writable: true });

    const { result } = renderHook(() => usePushNotifications());

    let granted = false;
    await act(async () => {
      granted = await result.current.requestPermission();
    });

    expect(granted).toBe(true);
    expect(result.current.permissionGranted).toBe(true);
    expect(result.current.expoPushToken).toBe("ExponentPushToken[test123]");
    expect(mockRegisterPushToken).toHaveBeenCalledWith({
      token: "ExponentPushToken[test123]",
      platform: "ios",
    });
  });

  it("calls backend registration with correct platform", async () => {
    Object.defineProperty(Platform, "OS", { value: "android", writable: true });

    const { result } = renderHook(() => usePushNotifications());

    await act(async () => {
      await result.current.requestPermission();
    });

    expect(mockRegisterPushToken).toHaveBeenCalledWith(
      expect.objectContaining({ platform: "android" }),
    );
  });

  it("deregisters with token on logout", async () => {
    Object.defineProperty(Platform, "OS", { value: "ios", writable: true });

    const { result } = renderHook(() => usePushNotifications());

    // First register to set the token
    await act(async () => {
      await result.current.requestPermission();
    });

    await act(async () => {
      await result.current.handleDeregister();
    });

    expect(mockDeregisterPushToken).toHaveBeenCalledWith({
      token: "ExponentPushToken[test123]",
    });
    expect(result.current.expoPushToken).toBeNull();
  });

  it("handles registration error gracefully", async () => {
    Object.defineProperty(Platform, "OS", { value: "ios", writable: true });
    mockRegisterPushToken.mockRejectedValue(new Error("Network error"));

    const consoleError = jest.spyOn(console, "error").mockImplementation();

    const { result } = renderHook(() => usePushNotifications());

    await act(async () => {
      await result.current.requestPermission();
    });

    // Token should still be set locally
    expect(result.current.expoPushToken).toBe("ExponentPushToken[test123]");
    expect(consoleError).toHaveBeenCalledWith(
      "[Push] Failed to register token:",
      expect.any(Error),
    );

    consoleError.mockRestore();
  });
});
