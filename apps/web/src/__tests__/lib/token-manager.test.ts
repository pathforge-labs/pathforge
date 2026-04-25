/**
 * PathForge — Token Manager Tests
 * ==================================
 * Unit tests for token storage, caching, listener notifications,
 * and SSR safety.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mockLocalStorage } from "../test-helpers";

describe("Token Manager", () => {
  let storage: Storage;

  beforeEach(async () => {
    // Set up a fresh localStorage mock before each test
    storage = mockLocalStorage();
    vi.stubGlobal("localStorage", storage);

    // Re-import the module to reset internal state
    vi.resetModules();
  });

  async function importTokenManager() {
    return await import("@/lib/token-manager");
  }

  // ── Storage Operations ────────────────────────────────────

  describe("setTokens / getTokens", () => {
    it("should store tokens in cache and localStorage", async () => {
      const tm = await importTokenManager();

      tm.setTokens("access-123", "refresh-456");

      expect(tm.getAccessToken()).toBe("access-123");
      expect(tm.getRefreshToken()).toBe("refresh-456");
      expect(storage.getItem("pathforge_access_token")).toBe("access-123");
      expect(storage.getItem("pathforge_refresh_token")).toBe("refresh-456");
    });
  });

  describe("clearTokens", () => {
    it("should remove tokens from cache and localStorage", async () => {
      const tm = await importTokenManager();
      tm.setTokens("access-123", "refresh-456");

      tm.clearTokens();

      expect(tm.getAccessToken()).toBeNull();
      expect(tm.getRefreshToken()).toBeNull();
      expect(storage.getItem("pathforge_access_token")).toBeNull();
      expect(storage.getItem("pathforge_refresh_token")).toBeNull();
    });
  });

  // ── State Queries ─────────────────────────────────────────

  describe("hasTokens", () => {
    it("should return true when access token is present", async () => {
      const tm = await importTokenManager();
      tm.setTokens("access-123", "refresh-456");

      expect(tm.hasTokens()).toBe(true);
    });

    it("should return false when no tokens are set", async () => {
      const tm = await importTokenManager();

      expect(tm.hasTokens()).toBe(false);
    });

    it("should return false after clearTokens", async () => {
      const tm = await importTokenManager();
      tm.setTokens("access-123", "refresh-456");
      tm.clearTokens();

      expect(tm.hasTokens()).toBe(false);
    });
  });

  // ── Listener Notifications ────────────────────────────────

  describe("onTokenChange", () => {
    it("should notify listener with true on setTokens", async () => {
      const tm = await importTokenManager();
      const listener = vi.fn();
      tm.onTokenChange(listener);

      tm.setTokens("access-123", "refresh-456");

      expect(listener).toHaveBeenCalledWith(true);
    });

    it("should notify listener with false on clearTokens", async () => {
      const tm = await importTokenManager();
      const listener = vi.fn();
      tm.setTokens("access-123", "refresh-456");
      tm.onTokenChange(listener);

      tm.clearTokens();

      expect(listener).toHaveBeenCalledWith(false);
    });

    it("should not notify after unsubscribe", async () => {
      const tm = await importTokenManager();
      const listener = vi.fn();
      const unsubscribe = tm.onTokenChange(listener);

      unsubscribe();
      tm.setTokens("new-access", "new-refresh");

      expect(listener).not.toHaveBeenCalled();
    });

    it("should handle listener errors without breaking token operations", async () => {
      const tm = await importTokenManager();
      const badListener = vi.fn(() => { throw new Error("Listener crash"); });
      const goodListener = vi.fn();
      tm.onTokenChange(badListener);
      tm.onTokenChange(goodListener);

      // Should not throw despite bad listener
      tm.setTokens("access-123", "refresh-456");

      expect(goodListener).toHaveBeenCalledWith(true);
      expect(tm.getAccessToken()).toBe("access-123");
    });
  });
});
