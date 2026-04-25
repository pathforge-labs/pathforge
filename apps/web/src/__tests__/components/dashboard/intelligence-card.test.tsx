/**
 * PathForge — IntelligenceCard Component Tests
 * ================================================
 * Tests for the shared Intelligence Hub card wrapper:
 * rendering, slots, empty state, skeleton loading, and accessibility.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { IntelligenceCard } from "@/components/dashboard/intelligence-card";

describe("IntelligenceCard", () => {
  // ── Basic Rendering ─────────────────────────────────────

  it("should render title and icon", () => {
    render(
      <IntelligenceCard title="Skills Health" icon="🔋">
        <p>Body content</p>
      </IntelligenceCard>,
    );

    expect(screen.getByText("Skills Health")).toBeDefined();
    expect(screen.getByText("🔋")).toBeDefined();
  });

  it("should render children in body when hasData is true", () => {
    render(
      <IntelligenceCard title="Test Card" icon="📊" hasData={true}>
        <p>Dashboard data here</p>
      </IntelligenceCard>,
    );

    expect(screen.getByText("Dashboard data here")).toBeDefined();
  });

  // ── Empty State ─────────────────────────────────────────

  it("should render default empty state when hasData is false", () => {
    render(
      <IntelligenceCard title="Test Card" icon="📊" hasData={false}>
        <p>This should not show</p>
      </IntelligenceCard>,
    );

    expect(screen.getByText(/No data yet/)).toBeDefined();
    expect(screen.queryByText("This should not show")).toBeNull();
  });

  it("should render custom empty state when provided", () => {
    render(
      <IntelligenceCard
        title="Test Card"
        icon="📊"
        hasData={false}
        emptyState={<p>Custom empty message</p>}
      >
        <p>Body</p>
      </IntelligenceCard>,
    );

    expect(screen.getByText("Custom empty message")).toBeDefined();
  });

  // ── Headline ────────────────────────────────────────────

  it("should render headline when provided and has data", () => {
    render(
      <IntelligenceCard title="Test" icon="📊" hasData={true} headline={<span>Important insight</span>}>
        <p>Body</p>
      </IntelligenceCard>,
    );

    expect(screen.getByText("Important insight")).toBeDefined();
  });

  it("should not render headline when hasData is false", () => {
    render(
      <IntelligenceCard title="Test" icon="📊" hasData={false} headline={<span>Hidden insight</span>}>
        <p>Body</p>
      </IntelligenceCard>,
    );

    expect(screen.queryByText("Hidden insight")).toBeNull();
  });

  // ── Skeleton Loading ────────────────────────────────────

  it("should render skeleton when isLoading is true", () => {
    render(
      <IntelligenceCard title="Test" icon="📊" isLoading={true}>
        <p>Body should not show</p>
      </IntelligenceCard>,
    );

    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.queryByText("Body should not show")).toBeNull();
  });

  // ── Accessibility ───────────────────────────────────────

  it("should have accessible section with aria-label matching title", () => {
    render(
      <IntelligenceCard title="Salary Intelligence" icon="💰">
        <p>Content</p>
      </IntelligenceCard>,
    );

    const section = screen.getByRole("region", { name: "Salary Intelligence" });
    expect(section).toBeDefined();
  });
});
