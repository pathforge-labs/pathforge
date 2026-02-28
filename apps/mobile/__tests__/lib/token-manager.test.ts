/**
 * Token Manager — Unit Tests
 * ============================
 * Tests async hydration, in-memory caching, setTokens/clearTokens,
 * listener notifications, and SecureStore failure handling.
 */

import * as SecureStore from "expo-secure-store";
import {
  hydrateTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  hasTokens,
  isHydrated,
  onTokenChange,
} from "../../lib/token-manager";

// ── Mocks ───────────────────────────────────────────────────

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

const mockGetItem = SecureStore.getItemAsync as jest.MockedFunction<
  typeof SecureStore.getItemAsync
>;
const mockSetItem = SecureStore.setItemAsync as jest.MockedFunction<
  typeof SecureStore.setItemAsync
>;
const mockDeleteItem = SecureStore.deleteItemAsync as jest.MockedFunction<
  typeof SecureStore.deleteItemAsync
>;

// ── Setup ───────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  // Reset module state between tests by clearing tokens
  // (we can't reset module-level variables, so we use clearTokens)
});

// ── Tests ───────────────────────────────────────────────────

describe("token-manager", () => {
  describe("hydrateTokens", () => {
    it("should hydrate tokens from SecureStore", async () => {
      mockGetItem
        .mockResolvedValueOnce("test-access-token")
        .mockResolvedValueOnce("test-refresh-token");

      await hydrateTokens();

      expect(getAccessToken()).toBe("test-access-token");
      expect(getRefreshToken()).toBe("test-refresh-token");
      expect(isHydrated()).toBe(true);
    });

    it("should set null tokens when SecureStore is empty", async () => {
      mockGetItem.mockResolvedValue(null);

      await hydrateTokens();

      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(isHydrated()).toBe(true);
    });

    it("should handle SecureStore read failures gracefully", async () => {
      mockGetItem.mockRejectedValue(new Error("Keychain unavailable"));

      await hydrateTokens();

      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(isHydrated()).toBe(true);
    });
  });

  describe("setTokens", () => {
    it("should update cache and persist to SecureStore", async () => {
      await setTokens("new-access", "new-refresh");

      expect(getAccessToken()).toBe("new-access");
      expect(getRefreshToken()).toBe("new-refresh");
      expect(mockSetItem).toHaveBeenCalledWith(
        "pathforge_access_token",
        "new-access",
      );
      expect(mockSetItem).toHaveBeenCalledWith(
        "pathforge_refresh_token",
        "new-refresh",
      );
    });

    it("should still update cache when SecureStore write fails", async () => {
      mockSetItem.mockRejectedValue(new Error("Disk full"));

      await setTokens("cached-access", "cached-refresh");

      // Cache should still be updated
      expect(getAccessToken()).toBe("cached-access");
      expect(getRefreshToken()).toBe("cached-refresh");
    });

    it("should notify listeners with hasTokens=true", async () => {
      const listener = jest.fn();
      onTokenChange(listener);

      await setTokens("a", "r");

      expect(listener).toHaveBeenCalledWith(true);
    });
  });

  describe("clearTokens", () => {
    it("should clear cache and delete from SecureStore", async () => {
      await setTokens("token", "refresh");
      await clearTokens();

      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(hasTokens()).toBe(false);
      expect(mockDeleteItem).toHaveBeenCalledTimes(2);
    });

    it("should notify listeners with hasTokens=false", async () => {
      const listener = jest.fn();
      onTokenChange(listener);

      await clearTokens();

      expect(listener).toHaveBeenCalledWith(false);
    });

    it("should handle SecureStore delete failures gracefully", async () => {
      mockDeleteItem.mockRejectedValue(new Error("Keychain error"));

      await clearTokens();

      expect(getAccessToken()).toBeNull();
    });
  });

  describe("hasTokens", () => {
    it("should return true when access token exists", async () => {
      await setTokens("present", "refresh");
      expect(hasTokens()).toBe(true);
    });

    it("should return false when tokens are cleared", async () => {
      await clearTokens();
      expect(hasTokens()).toBe(false);
    });
  });

  describe("onTokenChange", () => {
    it("should return an unsubscribe function", async () => {
      const listener = jest.fn();
      const unsubscribe = onTokenChange(listener);

      await setTokens("a", "r");
      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
      await setTokens("b", "s");
      expect(listener).toHaveBeenCalledTimes(1); // Not called again
    });

    it("should not break when a listener throws", async () => {
      const badListener = jest.fn(() => {
        throw new Error("Listener crash");
      });
      const goodListener = jest.fn();

      onTokenChange(badListener);
      onTokenChange(goodListener);

      await setTokens("a", "r");

      expect(badListener).toHaveBeenCalled();
      expect(goodListener).toHaveBeenCalled();
    });
  });
});
