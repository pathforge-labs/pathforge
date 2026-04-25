/**
 * PathForge Mobile — Test: Deep Link Router
 * =============================================
 * Unit tests for route validation and resolution.
 * Sprint 33 — WS-2: Suite 4 (5 tests)
 */

import { resolveDeepLink, isValidDeepLink, DEFAULT_ROUTE } from "../../lib/deep-link-router";

// ── Tests ───────────────────────────────────────────────────

describe("resolveDeepLink", () => {
  it("resolves known route /career-dna to tab path", () => {
    const result = resolveDeepLink("/career-dna");
    expect(result).toEqual({
      resolved: true,
      route: "/(tabs)/home/career-dna",
      originalUrl: "/career-dna",
    });
  });

  it("resolves tab route /notifications", () => {
    const result = resolveDeepLink("/notifications");
    expect(result).toEqual({
      resolved: true,
      route: "/(tabs)/notifications",
      originalUrl: "/notifications",
    });
  });

  it("falls back to DEFAULT_ROUTE for unknown routes", () => {
    const result = resolveDeepLink("/unknown-page");
    expect(result.resolved).toBe(false);
    expect(result.route).toBe(DEFAULT_ROUTE);
    expect(result.originalUrl).toBe("/unknown-page");
  });

  it("falls back for empty string input", () => {
    const result = resolveDeepLink("");
    expect(result.resolved).toBe(false);
    expect(result.route).toBe(DEFAULT_ROUTE);
  });

  it("falls back for malformed URL without crashing", () => {
    const result = resolveDeepLink("https://evil.com/steal-data");
    expect(result.resolved).toBe(false);
    expect(result.route).toBe(DEFAULT_ROUTE);
  });
});

describe("isValidDeepLink", () => {
  it("returns true for known routes", () => {
    expect(isValidDeepLink("/career-dna")).toBe(true);
    expect(isValidDeepLink("/settings")).toBe(true);
  });

  it("returns false for unknown routes", () => {
    expect(isValidDeepLink("/unknown")).toBe(false);
    expect(isValidDeepLink("")).toBe(false);
  });
});
