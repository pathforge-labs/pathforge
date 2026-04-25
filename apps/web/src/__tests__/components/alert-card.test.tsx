/**
 * PathForge — AlertCard Component Tests
 * ========================================
 * Validates threat alert card rendering: severity badges, expandable
 * descriptions, action buttons, status callbacks, and disabled states.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AlertCard, type AlertCardAlert, type AlertCardProps } from "@/components/dashboard/alert-card";

// ── Test Data ──────────────────────────────────────────────

function createMockAlert(overrides: Partial<AlertCardAlert> = {}): AlertCardAlert {
  return {
    id: "alert-test-1",
    title: "AI Automation Risk Detected",
    description: "Your primary skill area shows increasing automation potential. Consider upskilling in areas with higher AI resistance.",
    severity: "high",
    status: "active",
    recommendation: "Focus on creative problem-solving and leadership skills",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderAlertCard(overrides: Partial<AlertCardProps> = {}) {
  const defaultProps: AlertCardProps = {
    alert: createMockAlert(),
    onStatusChange: vi.fn(),
    isUpdating: false,
    ...overrides,
  };

  return {
    ...render(<AlertCard {...defaultProps} />),
    props: defaultProps,
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("AlertCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render alert title and severity badge", () => {
    renderAlertCard();

    expect(screen.getByText("AI Automation Risk Detected")).toBeDefined();
    expect(screen.getByText("High")).toBeDefined();
  });

  it("should render recommendation section when present", () => {
    renderAlertCard();

    expect(screen.getByText("Recommendation")).toBeDefined();
    expect(screen.getByText("Focus on creative problem-solving and leadership skills")).toBeDefined();
  });

  it("should not render recommendation section when null", () => {
    const alert = createMockAlert({ recommendation: null });
    renderAlertCard({ alert });

    expect(screen.queryByText("Recommendation")).toBeNull();
  });

  it("should render action buttons for active alerts", () => {
    renderAlertCard();

    expect(screen.getByText("✓ Mark Read")).toBeDefined();
    expect(screen.getByText("⏰ Snooze")).toBeDefined();
    expect(screen.getByText("✕ Dismiss")).toBeDefined();
  });

  it("should not render action buttons for non-active alerts", () => {
    const alert = createMockAlert({ status: "read" });
    renderAlertCard({ alert });

    expect(screen.queryByText("✓ Mark Read")).toBeNull();
    expect(screen.queryByText("⏰ Snooze")).toBeNull();
    expect(screen.queryByText("✕ Dismiss")).toBeNull();
  });

  it("should call onStatusChange with 'read' when Mark Read clicked", () => {
    const onStatusChange = vi.fn();
    renderAlertCard({ onStatusChange });

    fireEvent.click(screen.getByText("✓ Mark Read"));

    expect(onStatusChange).toHaveBeenCalledWith("alert-test-1", "read");
  });

  it("should call onStatusChange with 'snoozed' when Snooze clicked", () => {
    const onStatusChange = vi.fn();
    renderAlertCard({ onStatusChange });

    fireEvent.click(screen.getByText("⏰ Snooze"));

    expect(onStatusChange).toHaveBeenCalledWith("alert-test-1", "snoozed");
  });

  it("should call onStatusChange with 'dismissed' when Dismiss clicked", () => {
    const onStatusChange = vi.fn();
    renderAlertCard({ onStatusChange });

    fireEvent.click(screen.getByText("✕ Dismiss"));

    expect(onStatusChange).toHaveBeenCalledWith("alert-test-1", "dismissed");
  });

  it("should disable action buttons when isUpdating is true", () => {
    renderAlertCard({ isUpdating: true });

    const markReadButton = screen.getByText("✓ Mark Read").closest("button");
    const snoozeButton = screen.getByText("⏰ Snooze").closest("button");
    const dismissButton = screen.getByText("✕ Dismiss").closest("button");

    expect(markReadButton?.disabled).toBe(true);
    expect(snoozeButton?.disabled).toBe(true);
    expect(dismissButton?.disabled).toBe(true);
  });

  it("should render correct severity badge variant for each level", () => {
    const severities = ["critical", "high", "medium", "low"] as const;
    const expectedLabels = ["Critical", "High", "Medium", "Low"];

    for (let index = 0; index < severities.length; index++) {
      const alert = createMockAlert({ severity: severities[index], id: `alert-${index}` });
      const { unmount } = render(
        <AlertCard alert={alert} onStatusChange={vi.fn()} />,
      );

      expect(screen.getByText(expectedLabels[index])).toBeDefined();
      unmount();
    }
  });

  it("should show expandable description toggle for long text", () => {
    const longDescription = "A".repeat(200);
    const alert = createMockAlert({ description: longDescription });
    renderAlertCard({ alert });

    // Should show "Show more" button for descriptions > 120 chars
    expect(screen.getByText("Show more")).toBeDefined();

    // Click to expand
    fireEvent.click(screen.getByText("Show more"));
    expect(screen.getByText("Show less")).toBeDefined();

    // Click to collapse
    fireEvent.click(screen.getByText("Show less"));
    expect(screen.getByText("Show more")).toBeDefined();
  });
});
