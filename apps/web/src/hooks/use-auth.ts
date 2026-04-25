/**
 * PathForge — useAuth Hook
 * =========================
 * Thin wrapper around AuthContext for convenient access to auth state.
 */

"use client";

import { useContext } from "react";

import { AuthContext, type AuthContextValue } from "@/providers/auth-provider";

/**
 * Access authentication state and actions.
 *
 * @returns Auth context value with user, status, and action methods.
 * @throws {Error} If used outside of `AuthProvider`.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error(
      "useAuth must be used within an AuthProvider. " +
      "Ensure your component tree is wrapped with <AuthProvider>.",
    );
  }

  return context;
}
