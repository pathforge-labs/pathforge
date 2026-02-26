/**
 * PathForge — useOnboarding Hook Tests
 * ======================================
 * Validates onboarding state machine: step transitions, file handling,
 * text validation, navigation constraints, and reset behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// ── Mocks ──────────────────────────────────────────────────

vi.mock("@/lib/api-client/ai", () => ({
  parseResume: vi.fn().mockResolvedValue({
    full_name: "Jane Doe",
    email: "jane@example.com",
    phone: "",
    location: "Amsterdam",
    summary: "Experienced engineer",
    skills: [{ name: "TypeScript" }],
    experience: [],
    education: [],
    certifications: [],
    languages: [],
  }),
  embedResume: vi.fn().mockResolvedValue({ embedding_id: "emb-1" }),
  matchResume: vi.fn().mockResolvedValue({ matches: [] }),
}));

vi.mock("@/lib/api-client", () => ({
  careerDnaApi: {
    generate: vi.fn().mockResolvedValue({ id: "dna-1", dimensions: {} }),
  },
}));

import { useOnboarding } from "@/hooks/use-onboarding";

// ── Tests ──────────────────────────────────────────────────

describe("useOnboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should start with upload step and empty state", () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.step).toBe("upload");
    expect(result.current.stepIndex).toBe(0);
    expect(result.current.rawText).toBe("");
    expect(result.current.file).toBeNull();
    expect(result.current.parsedResume).toBeNull();
    expect(result.current.careerDna).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("should have correct 5-step order", () => {
    const { result } = renderHook(() => useOnboarding());

    expect(result.current.steps).toEqual([
      "upload",
      "parse",
      "dna",
      "readiness",
      "dashboard",
    ]);
  });

  it("should update rawText and clear error on setRawText", () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.setRawText("My resume text here");
    });

    expect(result.current.rawText).toBe("My resume text here");
    expect(result.current.error).toBeNull();
  });

  it("should update file on setFile", () => {
    const { result } = renderHook(() => useOnboarding());
    const testFile = new File(["content"], "resume.txt", { type: "text/plain" });

    act(() => {
      result.current.setFile(testFile);
    });

    expect(result.current.file).toBe(testFile);
    expect(result.current.error).toBeNull();
  });

  it("should reject parseResume with text shorter than 50 chars", async () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.setRawText("Too short");
    });

    await act(async () => {
      await result.current.parseResume();
    });

    expect(result.current.error).toBe("Please provide at least 50 characters of resume text.");
    expect(result.current.step).toBe("upload");
  });

  it("should transition to parse step on successful parseResume", async () => {
    const { result } = renderHook(() => useOnboarding());
    const longText = "A".repeat(60);

    act(() => {
      result.current.setRawText(longText);
    });

    await act(async () => {
      await result.current.parseResume();
    });

    expect(result.current.step).toBe("parse");
    expect(result.current.parsedResume).not.toBeNull();
    expect(result.current.parsedResume?.full_name).toBe("Jane Doe");
  });

  it("should allow going backward but not forward via goToStep", async () => {
    const { result } = renderHook(() => useOnboarding());
    const longText = "A".repeat(60);

    // Advance to parse step
    act(() => result.current.setRawText(longText));
    await act(async () => await result.current.parseResume());
    expect(result.current.step).toBe("parse");

    // Go back to upload — should work
    act(() => result.current.goToStep("upload"));
    expect(result.current.step).toBe("upload");

    // Try to jump forward to dna — should NOT work (can't skip steps)
    act(() => result.current.goToStep("dna"));
    expect(result.current.step).toBe("upload");
  });

  it("should reset to initial state on reset()", async () => {
    const { result } = renderHook(() => useOnboarding());
    const longText = "A".repeat(60);

    act(() => result.current.setRawText(longText));
    await act(async () => await result.current.parseResume());

    act(() => result.current.reset());

    expect(result.current.step).toBe("upload");
    expect(result.current.rawText).toBe("");
    expect(result.current.parsedResume).toBeNull();
    expect(result.current.careerDna).toBeNull();
  });
});
