/**
 * PathForge — Workflow Drill-Down Modal
 * ========================================
 * Sprint 36 WS-4: Read-only modal for workflow details.
 *
 * Native <dialog> element for:
 * - Built-in focus trap + keyboard handling (Escape)
 * - 97%+ browser support
 * - No extra accessibility libraries needed
 *
 * Uses existing useWorkflowDetail hook — no new API calls.
 */

"use client";

import { useRef, useEffect, useCallback } from "react";
import type { CareerWorkflowResponse } from "@/types/api/workflow-automation";
import styles from "./workflow-modal.module.css";

// ── Props ─────────────────────────────────────────────────────

interface WorkflowModalProps {
  /** The workflow data to display */
  readonly workflow: CareerWorkflowResponse | null;
  /** Whether the modal is open */
  readonly isOpen: boolean;
  /** Callback when modal should close */
  readonly onClose: () => void;
}

// ── Status Badge ──────────────────────────────────────────────

function StatusBadge({ status }: { readonly status: string }): React.JSX.Element {
  const statusClass = status === "completed"
    ? styles.badgeCompleted
    : status === "active"
      ? styles.badgeActive
      : styles.badgeDraft;

  return (
    <span className={`${styles.badge} ${statusClass}`}>
      {status}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────

export function WorkflowModal({
  workflow,
  isOpen,
  onClose,
}: WorkflowModalProps): React.JSX.Element | null {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Open/close via showModal() for proper backdrop + focus trap
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  // Close on backdrop click (native <dialog> fires cancel on ::backdrop)
  const handleCancel = useCallback(
    (event: React.SyntheticEvent<HTMLDialogElement>) => {
      event.preventDefault();
      onClose();
    },
    [onClose],
  );

  // Close on backdrop click
  const handleBackdropClick = useCallback(
    (event: React.MouseEvent<HTMLDialogElement>) => {
      const dialog = dialogRef.current;
      if (dialog && event.target === dialog) {
        onClose();
      }
    },
    [onClose],
  );

  if (!workflow) return null;

  const completionPercent = workflow.total_steps > 0
    ? Math.round((workflow.completed_steps / workflow.total_steps) * 100)
    : 0;

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby="workflow-modal-title"
      aria-modal="true"
      onCancel={handleCancel}
      onClick={handleBackdropClick}
    >
      <div className={styles.content}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <h2 id="workflow-modal-title" className={styles.title}>
              {workflow.name}
            </h2>
            <StatusBadge status={workflow.workflow_status} />
          </div>
          <button
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Close modal"
            type="button"
          >
            ✕
          </button>
        </header>

        {/* Description */}
        <p className={styles.description}>{workflow.description}</p>

        {/* Progress */}
        <div className={styles.progressSection}>
          <div className={styles.progressHeader}>
            <span className={styles.progressLabel}>Progress</span>
            <span className={styles.progressValue}>
              {workflow.completed_steps}/{workflow.total_steps} steps ({completionPercent}%)
            </span>
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${completionPercent}%` }}
            />
          </div>
        </div>

        {/* Metadata */}
        <div className={styles.metadata}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Trigger</span>
            <span className={styles.metaValue}>{workflow.trigger_type}</span>
          </div>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>Created</span>
            <span className={styles.metaValue}>
              {new Date(workflow.created_at).toLocaleDateString()}
            </span>
          </div>
          {workflow.source_engine && (
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Source</span>
              <span className={styles.metaValue}>{workflow.source_engine}</span>
            </div>
          )}
        </div>

        {/* Disclaimer */}
        {workflow.disclaimer && (
          <p className={styles.disclaimer}>{workflow.disclaimer}</p>
        )}
      </div>
    </dialog>
  );
}
