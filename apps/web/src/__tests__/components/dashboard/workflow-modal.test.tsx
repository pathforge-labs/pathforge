/**
 * PathForge — Workflow Modal Tests
 * ====================================
 * Sprint 36 WS-4: Tests for WorkflowModal component.
 *
 * Tests rendering, open/close behavior, and data display.
 * Uses native <dialog> element — no mocking of external modal libraries.
 */

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
  source_engine: "career_dna",
  disclaimer: "AI-assisted optimization.",
  created_at: "2026-01-15T10:00:00Z",
  updated_at: "2026-02-15T10:00:00Z",
};

// ── Tests ─────────────────────────────────────────────────────

describe("WorkflowModal", () => {
  // Mock showModal/close since JSDOM doesn't support <dialog> natively
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = jest.fn();
    HTMLDialogElement.prototype.close = jest.fn();
  });

  it("renders null when workflow is null", () => {
    const { container } = render(
      <WorkflowModal workflow={null} isOpen={false} onClose={jest.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders workflow details when provided", () => {
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={jest.fn()} />,
    );

    expect(screen.getByText("Resume Optimization Pipeline")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText(/3\/5 steps/)).toBeInTheDocument();
    expect(screen.getByText("manual")).toBeInTheDocument();
    expect(screen.getByText("career_dna")).toBeInTheDocument();
    expect(screen.getByText("AI-assisted optimization.")).toBeInTheDocument();
  });

  it("calculates completion percentage correctly", () => {
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={jest.fn()} />,
    );

    // 3/5 = 60%
    expect(screen.getByText(/60%/)).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = jest.fn();
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={onClose} />,
    );

    fireEvent.click(screen.getByLabelText("Close modal"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls showModal when isOpen becomes true", () => {
    render(
      <WorkflowModal workflow={MOCK_WORKFLOW} isOpen={true} onClose={jest.fn()} />,
    );

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
  });
});
