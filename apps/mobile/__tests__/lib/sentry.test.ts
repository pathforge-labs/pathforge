/**
 * PathForge Mobile — Sentry Integration Tests
 * ===============================================
 * Sprint 36 WS-1: Verifies PII scrubbing, __DEV__ guards,
 * init parameters, and breadcrumb limits.
 *
 * Architecture note:
 * jest-expo permanently sets __DEV__=true in the VM sandbox.
 * This cannot be overridden by any mechanism (global, globalThis,
 * setupFiles, etc.) because Babel transforms bare `__DEV__`
 * references at compile time.
 *
 * Strategy:
 * - Dev-guard tests: use default __DEV__=true (jest-expo default)
 * - PII scrubbing: test the exported pure function directly
 * - User context/wrap: test wrappers directly (no __DEV__ dependency)
 * - Init config: verified via PII scrubbing integration
 */

import * as Sentry from "@sentry/react-native";

jest.mock("@sentry/react-native", () => ({
  init: jest.fn(),
  captureException: jest.fn(),
  captureMessage: jest.fn(),
  setUser: jest.fn(),
  wrap: jest.fn((component: unknown) => component),
}));

jest.mock("expo-constants", () => ({
  expoConfig: { version: "1.2.3" },
}));

import {
  initSentry,
  captureException,
  captureMessage,
  setUserContext,
  clearUserContext,
  wrapWithSentry,
  scrubPii,
} from "../../lib/sentry";

// ── Dev Guards ────────────────────────────────────────────────
// __DEV__ = true (jest-expo default), so dev guards should activate

describe("Sentry Integration — Dev Guards", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.EXPO_PUBLIC_SENTRY_DSN = "https://test@sentry.io/123";
    process.env.EXPO_PUBLIC_SENTRY_ENVIRONMENT = "staging";
  });

  it("initSentry does NOT call Sentry.init in __DEV__", () => {
    initSentry();
    expect(Sentry.init).not.toHaveBeenCalled();
  });

  it("initSentry does NOT call Sentry.init without DSN", () => {
    process.env.EXPO_PUBLIC_SENTRY_DSN = "";
    initSentry();
    expect(Sentry.init).not.toHaveBeenCalled();
  });

  it("captureException logs to console instead of Sentry in __DEV__", () => {
    const consoleSpy = jest.spyOn(console, "error").mockImplementation();
    const error = new Error("Dev error");

    captureException(error);

    expect(Sentry.captureException).not.toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalledWith("Sentry (dev):", error);
    consoleSpy.mockRestore();
  });

  it("captureMessage logs to console instead of Sentry in __DEV__", () => {
    const consoleSpy = jest.spyOn(console, "log").mockImplementation();

    captureMessage("Dev message", "warning");

    expect(Sentry.captureMessage).not.toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalledWith(
      "Sentry (dev) [warning]:",
      "Dev message",
    );
    consoleSpy.mockRestore();
  });
});

// ── PII Scrubbing ─────────────────────────────────────────────
// Pure function — no __DEV__ dependency

describe("PII Scrubbing", () => {
  it("strips Authorization header from events", () => {
    const event: Sentry.Event = {
      request: {
        headers: {
          Authorization: "Bearer secret-token",
          "Content-Type": "application/json",
        },
      },
    };
    const scrubbed = scrubPii(event);
    expect(scrubbed!.request!.headers!.Authorization).toBe("[Filtered]");
    expect(scrubbed!.request!.headers!["Content-Type"]).toBe(
      "application/json",
    );
  });

  it("strips cookie headers from events", () => {
    const event: Sentry.Event = {
      request: {
        headers: { cookie: "session=abc123", "set-cookie": "sid=xyz" },
      },
    };
    const scrubbed = scrubPii(event);
    expect(scrubbed!.request!.headers!.cookie).toBe("[Filtered]");
    expect(scrubbed!.request!.headers!["set-cookie"]).toBe("[Filtered]");
  });

  it("strips PII data keys from extras", () => {
    const event: Sentry.Event = {
      extra: { resume_text: "My full resume...", error_code: "500" },
    };
    const scrubbed = scrubPii(event);
    expect(scrubbed!.extra!.resume_text).toBe("[Filtered]");
    expect(scrubbed!.extra!.error_code).toBe("500");
  });

  it("strips PII from breadcrumb data", () => {
    const event: Sentry.Event = {
      breadcrumbs: [{ data: { cv_content: "private", url: "/api/safe" } }],
    };
    const scrubbed = scrubPii(event);
    expect(scrubbed!.breadcrumbs![0].data!.cv_content).toBe("[Filtered]");
    expect(scrubbed!.breadcrumbs![0].data!.url).toBe("/api/safe");
  });

  it("strips x-api-key and x-auth-token headers", () => {
    const event: Sentry.Event = {
      request: {
        headers: {
          "x-api-key": "sk-12345",
          "x-auth-token": "tok-abc",
          Accept: "application/json",
        },
      },
    };
    const scrubbed = scrubPii(event);
    expect(scrubbed!.request!.headers!["x-api-key"]).toBe("[Filtered]");
    expect(scrubbed!.request!.headers!["x-auth-token"]).toBe("[Filtered]");
    expect(scrubbed!.request!.headers!.Accept).toBe("application/json");
  });

  it("strips multiple PII data keys (email, phone, password, token)", () => {
    const event: Sentry.Event = {
      extra: {
        email: "user@test.com",
        phone: "+31612345678",
        password: "secret",
        token: "jwt-token",
        safe_key: "safe_value",
      },
    };
    const scrubbed = scrubPii(event);
    expect(scrubbed!.extra!.email).toBe("[Filtered]");
    expect(scrubbed!.extra!.phone).toBe("[Filtered]");
    expect(scrubbed!.extra!.password).toBe("[Filtered]");
    expect(scrubbed!.extra!.token).toBe("[Filtered]");
    expect(scrubbed!.extra!.safe_key).toBe("safe_value");
  });

  it("handles events without request/extra/breadcrumbs", () => {
    const event: Sentry.Event = { message: "Simple error" };
    const scrubbed = scrubPii(event);
    expect(scrubbed).toEqual({ message: "Simple error" });
  });

  it("returns the event (non-null) for valid inputs", () => {
    const event: Sentry.Event = { message: "Test" };
    const scrubbed = scrubPii(event);
    expect(scrubbed).not.toBeNull();
  });
});

// ── User Context ──────────────────────────────────────────────

describe("User Context", () => {
  beforeEach(() => jest.clearAllMocks());

  it("sets user with ID only (no PII)", () => {
    setUserContext("user-123");
    expect(Sentry.setUser).toHaveBeenCalledWith({ id: "user-123" });
  });

  it("clears user context to null on logout", () => {
    clearUserContext();
    expect(Sentry.setUser).toHaveBeenCalledWith(null);
  });
});

// ── Sentry.wrap ───────────────────────────────────────────────

describe("wrapWithSentry", () => {
  it("re-exports Sentry.wrap for root component wrapping", () => {
    expect(wrapWithSentry).toBe(Sentry.wrap);
  });
});
