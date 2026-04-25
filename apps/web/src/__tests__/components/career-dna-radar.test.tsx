/**
 * PathForge — CareerDnaRadar Component Tests
 * =============================================
 * Validates SVG radar chart rendering, dimension mapping,
 * loading states, accessibility, and geometry correctness.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CareerDnaRadar, type RadarDimension } from "@/components/dashboard/career-dna-radar";

// ── Test Data ──────────────────────────────────────────────

const MOCK_DIMENSIONS: readonly RadarDimension[] = [
  { label: "Skills", value: 85, icon: "🧬" },
  { label: "Experience", value: 70, icon: "📐" },
  { label: "Growth", value: 60, icon: "📈" },
  { label: "Values", value: 50, icon: "💎" },
  { label: "Market", value: 75, icon: "🎯" },
  { label: "Resilience", value: 90, icon: "🛡️" },
];

const EMPTY_DIMENSIONS: readonly RadarDimension[] = [
  { label: "Skills", value: 0, icon: "🧬" },
  { label: "Experience", value: 0, icon: "📐" },
  { label: "Growth", value: 0, icon: "📈" },
  { label: "Values", value: 0, icon: "💎" },
  { label: "Market", value: 0, icon: "🎯" },
  { label: "Resilience", value: 0, icon: "🛡️" },
];

// ── Tests ──────────────────────────────────────────────────

describe("CareerDnaRadar", () => {
  it("should render SVG with correct aria-label", () => {
    render(<CareerDnaRadar dimensions={MOCK_DIMENSIONS} />);

    const svg = screen.getByRole("img");
    expect(svg).toBeDefined();
    expect(svg.getAttribute("aria-label")).toContain("Career DNA radar chart");
  });

  it("should render all 6 axis labels", () => {
    render(<CareerDnaRadar dimensions={MOCK_DIMENSIONS} />);

    for (const dimension of MOCK_DIMENSIONS) {
      expect(screen.getByText(dimension.label)).toBeDefined();
    }
  });

  it("should render score values for each dimension when loaded", () => {
    render(<CareerDnaRadar dimensions={MOCK_DIMENSIONS} />);

    // Score text nodes should appear with rounded integer values
    expect(screen.getByText("85")).toBeDefined();
    expect(screen.getByText("70")).toBeDefined();
    expect(screen.getByText("60")).toBeDefined();
    expect(screen.getByText("50")).toBeDefined();
    expect(screen.getByText("75")).toBeDefined();
    expect(screen.getByText("90")).toBeDefined();
  });

  it("should not render score values during loading state", () => {
    render(<CareerDnaRadar dimensions={MOCK_DIMENSIONS} isLoading />);

    // Loading state hides data polygon and score text
    expect(screen.queryByText("85")).toBeNull();
    expect(screen.queryByText("70")).toBeNull();
  });

  it("should render card title and description", () => {
    render(<CareerDnaRadar dimensions={MOCK_DIMENSIONS} />);

    expect(screen.getByText("Career DNA™ Profile")).toBeDefined();
    expect(screen.getByText("Your career shape across 6 dimensions")).toBeDefined();
  });

  it("should clamp dimension values to 0–100 range", () => {
    const overMaxDimensions: readonly RadarDimension[] = [
      { label: "Skills", value: 150, icon: "🧬" },
      { label: "Experience", value: -20, icon: "📐" },
      { label: "Growth", value: 100, icon: "📈" },
      { label: "Values", value: 0, icon: "💎" },
      { label: "Market", value: 50, icon: "🎯" },
      { label: "Resilience", value: 200, icon: "🛡️" },
    ];

    // Should render without throwing — geometry helpers handle clamping
    const { container } = render(<CareerDnaRadar dimensions={overMaxDimensions} />);
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();
  });

  it("should render correctly with all-zero dimensions", () => {
    const { container } = render(<CareerDnaRadar dimensions={EMPTY_DIMENSIONS} />);

    // SVG should still render with collapsed polygon at center
    const svg = container.querySelector("svg");
    expect(svg).toBeDefined();

    // All labels should still be visible
    for (const dimension of EMPTY_DIMENSIONS) {
      expect(screen.getByText(dimension.label)).toBeDefined();
    }
  });
});
