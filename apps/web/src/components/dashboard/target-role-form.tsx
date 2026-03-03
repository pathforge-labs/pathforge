/**
 * PathForge — Target Role Form
 * ================================
 * Sprint 36 WS-6: User-editable target role with confirm→save flow.
 *
 * Key UX decisions:
 * - Inline edit mode (click-to-edit) — minimal UI disruption
 * - Confirmation step before save — prevents accidental changes
 * - Success/error toast feedback
 * - Debounced save (not autosave — explicit submit)
 */

"use client";

import { useState, useCallback, type JSX, type FormEvent } from "react";
import { useTargetRole } from "@/hooks/api/use-target-role";
import styles from "./target-role-form.module.css";

// ── Props ─────────────────────────────────────────────────────

interface TargetRoleFormProps {
  /** Current target role value (may be null) */
  readonly currentRole: string | null;
}

// ── Component ─────────────────────────────────────────────────

export function TargetRoleForm({ currentRole }: TargetRoleFormProps): JSX.Element {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(currentRole ?? "");
  const [showConfirm, setShowConfirm] = useState(false);

  const mutation = useTargetRole();

  const handleSubmit = useCallback(
    (event: FormEvent) => {
      event.preventDefault();
      const trimmed = value.trim();
      if (!trimmed || trimmed === currentRole) {
        setIsEditing(false);
        return;
      }
      setShowConfirm(true);
    },
    [value, currentRole],
  );

  const handleConfirm = useCallback(() => {
    mutation.mutate(
      { target_role: value.trim() },
      {
        onSuccess: () => {
          setIsEditing(false);
          setShowConfirm(false);
        },
        onError: () => {
          setShowConfirm(false);
        },
      },
    );
  }, [mutation, value]);

  const handleCancel = useCallback(() => {
    setValue(currentRole ?? "");
    setIsEditing(false);
    setShowConfirm(false);
  }, [currentRole]);

  // Display mode
  if (!isEditing) {
    return (
      <div className={styles.displayContainer}>
        <div className={styles.labelRow}>
          <span className={styles.label}>Target Role</span>
          <button
            className={styles.editButton}
            onClick={() => setIsEditing(true)}
            type="button"
          >
            Edit
          </button>
        </div>
        <p className={styles.currentValue}>
          {currentRole || "Not set — click edit to set your career target"}
        </p>
      </div>
    );
  }

  // Confirmation dialog
  if (showConfirm) {
    return (
      <div className={styles.confirmContainer}>
        <p className={styles.confirmText}>
          Update target role to <strong>{value.trim()}</strong>?
        </p>
        <p className={styles.confirmNote}>
          This will recalculate your growth trajectory.
        </p>
        <div className={styles.confirmActions}>
          <button
            className={styles.confirmButton}
            onClick={handleConfirm}
            disabled={mutation.isPending}
            type="button"
          >
            {mutation.isPending ? "Saving…" : "Confirm"}
          </button>
          <button
            className={styles.cancelButton}
            onClick={handleCancel}
            disabled={mutation.isPending}
            type="button"
          >
            Cancel
          </button>
        </div>
        {mutation.isError && (
          <p className={styles.errorText}>
            Failed to update. Please try again.
          </p>
        )}
      </div>
    );
  }

  // Edit mode
  return (
    <form className={styles.editContainer} onSubmit={handleSubmit}>
      <label htmlFor="target-role-input" className={styles.label}>
        Target Role
      </label>
      <input
        id="target-role-input"
        className={styles.input}
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="e.g., Senior Staff Engineer"
        maxLength={255}
        autoFocus
      />
      <div className={styles.editActions}>
        <button
          className={styles.saveButton}
          type="submit"
          disabled={!value.trim() || value.trim() === currentRole}
        >
          Save
        </button>
        <button
          className={styles.cancelButton}
          onClick={handleCancel}
          type="button"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
