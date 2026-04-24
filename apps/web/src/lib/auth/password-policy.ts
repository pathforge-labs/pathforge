/**
 * PathForge — Shared Password Policy
 * ====================================
 * Single source of truth for password complexity validation on the
 * client. Mirrors ``apps/api/app/core/password_policy.py`` on the
 * backend — keep the two in sync whenever the ruleset changes.
 *
 * OWASP-aligned requirements (ASVS V2.1 — Password Security):
 * - Minimum 8 characters
 * - At least one uppercase letter
 * - At least one digit
 * - At least one special character from a wide, printable set
 *
 * Sprint 39 audit finding: the register and reset-password pages had
 * subtly different regexes (escape drift), so a password accepted by
 * one form could be rejected by the other. Extracting this module
 * fixes that drift; every form imports the same validator.
 */

// Keep this pattern in sync with
// ``apps/api/app/core/password_policy.py::PASSWORD_SPECIAL_CHARS_PATTERN``.
//
// Character class: !@#$%^&*(),.?":{}|<>-_=+[]\/'`~;
// Excludes whitespace and control characters; includes the full set of
// printable ASCII punctuation common to US-ASCII keyboards.
export const PASSWORD_SPECIAL_CHARS_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\/'`~;]/;
export const PASSWORD_UPPERCASE_REGEX = /[A-Z]/;
export const PASSWORD_DIGIT_REGEX = /\d/;

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

/**
 * Validate that a password satisfies PathForge's complexity rules.
 *
 * Returns ``null`` on success, or a user-facing error message on
 * failure. The message format is deliberately identical to the
 * backend's validator so that errors look the same regardless of
 * which layer catches them.
 */
export function validatePasswordComplexity(value: string): string | null {
  if (value.length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters`;
  }
  if (value.length > PASSWORD_MAX_LENGTH) {
    return `Password must be at most ${PASSWORD_MAX_LENGTH} characters`;
  }

  const missing: string[] = [];
  if (!PASSWORD_UPPERCASE_REGEX.test(value)) missing.push("one uppercase letter");
  if (!PASSWORD_DIGIT_REGEX.test(value)) missing.push("one digit");
  if (!PASSWORD_SPECIAL_CHARS_REGEX.test(value)) missing.push("one special character");

  if (missing.length > 0) {
    return `Password must contain at least ${missing.join(", ")}`;
  }

  return null;
}
