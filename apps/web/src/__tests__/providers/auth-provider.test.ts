/**
 * PathForge — Auth Provider Tests
 * =================================
 * Tests the authReducer state machine (pure function) and
 * AuthProvider component behavior (login, register, logout, session restore).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";

// ── Mock modules (before imports) ──────────────────────────

vi.mock("@/lib/http", () => ({
  fetchPublic: vi.fn(),
  fetchWithAuth: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status = 500) {
      super(message);
      this.status = status;
    }
  },
}));

vi.mock("@/lib/token-manager", () => ({
  hasTokens: vi.fn(),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
  onTokenChange: vi.fn().mockReturnValue(() => undefined),
}));

import { fetchPublic, fetchWithAuth } from "@/lib/http";
import { hasTokens, setTokens, clearTokens, onTokenChange } from "@/lib/token-manager";
import {
  AuthProvider,
  AuthContext,
  authReducer,
  initialState,
  type AuthContextValue,
  type AuthState,
  type AuthUser,
} from "@/providers/auth-provider";
import { useAuth } from "@/hooks/use-auth";

// ── Helpers ────────────────────────────────────────────────

const MOCK_USER_API = {
  id: "user-1",
  email: "emre@pathforge.eu",
  full_name: "Emre Dursun",
  is_active: true,
  is_verified: true,
  auth_provider: "local",
  avatar_url: null,
  created_at: "2026-01-01T00:00:00Z",
};

const MOCK_TOKENS = {
  access_token: "access-123",
  refresh_token: "refresh-456",
  token_type: "bearer",
};

function useAuthContext(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

function createAuthWrapper(): ({ children }: { children: ReactNode }) => React.JSX.Element {
  return function TestWrapper({ children }: { children: ReactNode }): React.JSX.Element {
    return React.createElement(AuthProvider, null, children);
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (hasTokens as ReturnType<typeof vi.fn>).mockReturnValue(false);
    (onTokenChange as ReturnType<typeof vi.fn>).mockReturnValue(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Session Restore ──────────────────────────────────

  describe("session restore", () => {
    it("should set unauthenticated when no tokens exist", async () => {
      (hasTokens as ReturnType<typeof vi.fn>).mockReturnValue(false);

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it("should restore session when tokens exist", async () => {
      (hasTokens as ReturnType<typeof vi.fn>).mockReturnValue(true);
      (fetchWithAuth as ReturnType<typeof vi.fn>).mockResolvedValue(MOCK_USER_API);

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      expect(result.current.user).toEqual({
        id: "user-1",
        email: "emre@pathforge.eu",
        fullName: "Emre Dursun",
        isActive: true,
        isVerified: true,
        authProvider: "local",
        avatarUrl: null,
        createdAt: "2026-01-01T00:00:00Z",
      });
    });

    it("should clear tokens and set unauthenticated if session restore fails", async () => {
      (hasTokens as ReturnType<typeof vi.fn>).mockReturnValue(true);
      (fetchWithAuth as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("Expired"));

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(clearTokens).toHaveBeenCalledOnce();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  // ── Login ────────────────────────────────────────────

  describe("login", () => {
    it("should authenticate after successful login", async () => {
      (fetchPublic as ReturnType<typeof vi.fn>).mockResolvedValue(MOCK_TOKENS);
      (fetchWithAuth as ReturnType<typeof vi.fn>).mockResolvedValue(MOCK_USER_API);

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      // Wait for initial session restore (no tokens)
      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.login({ email: "emre@pathforge.eu", password: "secret" });
      });

      expect(setTokens).toHaveBeenCalledWith("access-123", "refresh-456");
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user?.email).toBe("emre@pathforge.eu");
    });

    it("should set error and rethrow on login failure", async () => {
      const loginError = new Error("Invalid credentials");
      (fetchPublic as ReturnType<typeof vi.fn>).mockRejectedValue(loginError);

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      let thrownError: Error | undefined;
      await act(async () => {
        try {
          await result.current.login({ email: "bad@test.com", password: "wrong" });
        } catch (error) {
          thrownError = error as Error;
        }
      });

      expect(thrownError?.message).toBe("Invalid credentials");
      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.error).toBe("Invalid credentials");
      });
    });
  });

  // ── Register ─────────────────────────────────────────

  describe("register", () => {
    it("should register and auto-login", async () => {
      // First call: register, second call: login
      (fetchPublic as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(MOCK_USER_API) // register
        .mockResolvedValueOnce(MOCK_TOKENS); // auto-login
      (fetchWithAuth as ReturnType<typeof vi.fn>).mockResolvedValue(MOCK_USER_API);

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.register({
          email: "emre@pathforge.eu",
          password: "secure123",
          fullName: "Emre Dursun",
        });
      });

      expect(setTokens).toHaveBeenCalledWith("access-123", "refresh-456");
      expect(result.current.isAuthenticated).toBe(true);
    });

    it("should set error and rethrow on register failure", async () => {
      (fetchPublic as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("Email taken"));

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      let thrownError: Error | undefined;
      await act(async () => {
        try {
          await result.current.register({
            email: "taken@test.com",
            password: "pwd",
            fullName: "Test",
          });
        } catch (error) {
          thrownError = error as Error;
        }
      });

      expect(thrownError?.message).toBe("Email taken");
      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(false);
        expect(result.current.error).toBe("Email taken");
      });
    });
  });

  // ── Logout ───────────────────────────────────────────

  describe("logout", () => {
    it("should clear tokens and set unauthenticated", async () => {
      // Start authenticated
      (hasTokens as ReturnType<typeof vi.fn>).mockReturnValue(true);
      (fetchWithAuth as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(MOCK_USER_API)   // session restore
        .mockResolvedValueOnce(undefined);        // logout POST

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

      await act(async () => {
        await result.current.logout();
      });

      expect(clearTokens).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it("should still clear local state even if server logout fails", async () => {
      (hasTokens as ReturnType<typeof vi.fn>).mockReturnValue(true);
      (fetchWithAuth as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(MOCK_USER_API)       // session restore
        .mockRejectedValueOnce(new Error("Network")); // logout POST fails

      const { result } = renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

      await act(async () => {
        await result.current.logout();
      });

      // Should still clear — server-side failure is non-critical
      expect(clearTokens).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  // ── Multi-tab Sync ───────────────────────────────────

  describe("multi-tab sync", () => {
    it("should subscribe to token changes on mount", () => {
      renderHook(() => useAuthContext(), {
        wrapper: createAuthWrapper(),
      });

      expect(onTokenChange).toHaveBeenCalledOnce();
      expect(onTokenChange).toHaveBeenCalledWith(expect.any(Function));
    });
  });
});

// ── authReducer (Pure Function Tests) ─────────────────────

describe("authReducer", () => {
  const MOCK_AUTH_USER: AuthUser = {
    id: "user-1",
    email: "emre@pathforge.eu",
    fullName: "Emre Dursun",
    isActive: true,
    isVerified: true,
    authProvider: "local",
    avatarUrl: null,
    createdAt: "2026-01-01T00:00:00Z",
  };

  it("START_LOADING — sets loading status and clears error", () => {
    const stateWithError: AuthState = {
      status: "unauthenticated",
      user: null,
      error: "Previous error",
    };

    const result = authReducer(stateWithError, { type: "START_LOADING" });

    expect(result.status).toBe("loading");
    expect(result.error).toBeNull();
    expect(result.user).toBeNull(); // user preserved from spread
  });

  it("SET_AUTHENTICATED — sets user and authenticated status", () => {
    const result = authReducer(initialState, {
      type: "SET_AUTHENTICATED",
      user: MOCK_AUTH_USER,
    });

    expect(result.status).toBe("authenticated");
    expect(result.user).toEqual(MOCK_AUTH_USER);
    expect(result.error).toBeNull();
  });

  it("SET_UNAUTHENTICATED — clears user without error", () => {
    const authenticatedState: AuthState = {
      status: "authenticated",
      user: MOCK_AUTH_USER,
      error: null,
    };

    const result = authReducer(authenticatedState, { type: "SET_UNAUTHENTICATED" });

    expect(result.status).toBe("unauthenticated");
    expect(result.user).toBeNull();
    expect(result.error).toBeNull();
  });

  it("SET_UNAUTHENTICATED — clears user with error message", () => {
    const authenticatedState: AuthState = {
      status: "authenticated",
      user: MOCK_AUTH_USER,
      error: null,
    };

    const result = authReducer(authenticatedState, {
      type: "SET_UNAUTHENTICATED",
      error: "Session expired",
    });

    expect(result.status).toBe("unauthenticated");
    expect(result.user).toBeNull();
    expect(result.error).toBe("Session expired");
  });

  it("SET_ERROR — sets error while preserving other state", () => {
    const authenticatedState: AuthState = {
      status: "authenticated",
      user: MOCK_AUTH_USER,
      error: null,
    };

    const result = authReducer(authenticatedState, {
      type: "SET_ERROR",
      error: "Something went wrong",
    });

    expect(result.error).toBe("Something went wrong");
    expect(result.status).toBe("authenticated"); // preserved
    expect(result.user).toEqual(MOCK_AUTH_USER); // preserved
  });

  it("CLEAR_ERROR — clears error while preserving other state", () => {
    const stateWithError: AuthState = {
      status: "authenticated",
      user: MOCK_AUTH_USER,
      error: "Previous error",
    };

    const result = authReducer(stateWithError, { type: "CLEAR_ERROR" });

    expect(result.error).toBeNull();
    expect(result.status).toBe("authenticated"); // preserved
    expect(result.user).toEqual(MOCK_AUTH_USER); // preserved
  });

  it("default — returns unchanged state for unknown action", () => {
    const currentState: AuthState = {
      status: "authenticated",
      user: MOCK_AUTH_USER,
      error: null,
    };

    // Force an unknown action type to test the default branch
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = authReducer(currentState, { type: "UNKNOWN_ACTION" } as any);

    expect(result).toBe(currentState); // exact same reference
  });
});

// ── useAuth Guard ─────────────────────────────────────────

describe("useAuth", () => {
  it("should throw descriptive error when used outside AuthProvider", () => {
    // Suppress React console.error for the expected error boundary
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within an AuthProvider");

    consoleSpy.mockRestore();
  });
});
