/**
 * PathForge Mobile — Test: ThreatSummary Helpers
 * ==================================================
 * Unit tests for exported risk color/label utility functions.
 * Sprint 33 — WS-2: Suite 2 (5 tests)
 */

import { getRiskColor, getRiskLabel } from "../../components/threat-summary";

// ── Tests ───────────────────────────────────────────────────

describe("getRiskColor", () => {
  it("returns red for high risk (score >= 70)", () => {
    expect(getRiskColor(70)).toBe("#EF4444");
    expect(getRiskColor(100)).toBe("#EF4444");
  });

  it("returns amber for moderate risk (40 <= score < 70)", () => {
    expect(getRiskColor(40)).toBe("#F59E0B");
    expect(getRiskColor(69)).toBe("#F59E0B");
  });

  it("returns green for low risk (score < 40)", () => {
    expect(getRiskColor(39)).toBe("#10B981");
    expect(getRiskColor(0)).toBe("#10B981");
  });
});

describe("getRiskLabel", () => {
  it("returns correct labels for each threshold", () => {
    expect(getRiskLabel(70)).toBe("High Risk");
    expect(getRiskLabel(40)).toBe("Moderate Risk");
    expect(getRiskLabel(39)).toBe("Low Risk");
  });

  it("returns Low Risk for zero score", () => {
    expect(getRiskLabel(0)).toBe("Low Risk");
  });
});
