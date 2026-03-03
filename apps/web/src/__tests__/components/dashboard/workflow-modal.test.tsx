/**
 * PathForge — Workflow Modal Tests
 * ====================================
 * Sprint 36 WS-4: Tests for WorkflowModal component.
 *
 * Tests rendering, open/close behavior, and data display.
 * Uses native <dialog> element — no mocking of external modal libraries.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WorkflowModal } from "@/components/dashboard/workflow-modal";
import type { CareerWorkflowResponse } from "@/types/api/workflow-automation";

// ── Fixtures ──────────────────────────────────────────────────

const MOCK_WORKFLOW: CareerWorkflowResponse = {
  id: "wf-001",
  user_id: "user-001",
  name: "Resume Optimization Pipeline",
  description: "Automated resume refinement based on career DNA analysis.",
  workflow_status: "active",
  trigger_type: "manual",
  trigger_config: {},
  template_category: "resume",
  completed_steps: 3,
  total_steps: 5,
  is_template: false,
  source_engine: "career_dna",
  source_recommendation_id: null,
  data_source: "ai_analysis",
  disclaimer: "AI-assisted optimization.",
  created_at: "2026-01-15T10:00:00Z",
  updated_at: "2026-02-15T10:00:00Z",
};

// ── Tests ─────────────────────────────────────────────────────

describe("WorkflowModal", () => {
  // Mock showModal/close since JSDOM doesn't support <dialog> natively
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  it("renders null when workflow is null", () => {
    const { container } = render(
      <WorkflowModal workflow={null} isOpen={false} onClose={vi.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders workflow details when provided", () => {
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={vi.fn()} />,
    );

    expect(screen.getByText("Resume Optimization Pipeline")).toBeDefined();
    expect(screen.getByText("active")).toBeDefined();
    expect(screen.getByText(/3\/5 steps/)).toBeDefined();
    expect(screen.getByText("manual")).toBeDefined();
    expect(screen.getByText("career_dna")).toBeDefined();
    expect(screen.getByText("AI-assisted optimization.")).toBeDefined();
  });

  it("calculates completion percentage correctly", () => {
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={vi.fn()} />,
    );

    // 3/5 = 60%
    expect(screen.getByText(/60%/)).toBeDefined();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={onClose} />,
    );

    fireEvent.click(screen.getByLabelText("Close modal"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls showModal when isOpen becomes true", () => {
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={vi.fn()} />,
    );

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
  });
});
