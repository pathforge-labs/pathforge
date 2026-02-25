/**
 * PathForge — Auth Provider
 * ==========================
 * Centralized authentication state via React Context + useReducer.
 *
 * Provides: user, isAuthenticated, isLoading, login(), logout(), register()
 * Handles: session restoration on mount, token storage, API calls.
 */

"use client";

import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";

import { fetchPublic, fetchWithAuth, type ApiError } from "@/lib/http";
import { clearTokens, hasTokens, onTokenChange, setTokens } from "@/lib/token-manager";

// ── Types ───────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
  isActive: boolean;
  isVerified: boolean;
  authProvider: string;
  avatarUrl: string | null;
  createdAt: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  fullName: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface UserApiResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  auth_provider: string;
  avatar_url: string | null;
  created_at: string;
}

export interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

// ── State Machine ───────────────────────────────────────────

export type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

export interface AuthState {
  status: AuthStatus;
  user: AuthUser | null;
  error: string | null;
}

export type AuthAction =
  | { type: "START_LOADING" }
  | { type: "SET_AUTHENTICATED"; user: AuthUser }
  | { type: "SET_UNAUTHENTICATED"; error?: string }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" };

export const initialState: AuthState = {
  status: "idle",
  user: null,
  error: null,
};

export function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "START_LOADING":
      return { ...state, status: "loading", error: null };
    case "SET_AUTHENTICATED":
      return { status: "authenticated", user: action.user, error: null };
    case "SET_UNAUTHENTICATED":
      return {
        status: "unauthenticated",
        user: null,
        error: action.error ?? null,
      };
    case "SET_ERROR":
      return { ...state, error: action.error };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

// ── Helpers ─────────────────────────────────────────────────

function mapUserResponse(response: UserApiResponse): AuthUser {
  return {
    id: response.id,
    email: response.email,
    fullName: response.full_name,
    isActive: response.is_active,
    isVerified: response.is_verified,
    authProvider: response.auth_provider,
    avatarUrl: response.avatar_url,
    createdAt: response.created_at,
  };
}

// ── Context ─────────────────────────────────────────────────

export const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ────────────────────────────────────────────────

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps): React.JSX.Element {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // ── Session Restoration ─────────────────────────────────
  useEffect(() => {
    async function restoreSession(): Promise<void> {
      if (!hasTokens()) {
        dispatch({ type: "SET_UNAUTHENTICATED" });
        return;
      }

      dispatch({ type: "START_LOADING" });

      try {
        const userData = await fetchWithAuth<UserApiResponse>("/api/v1/users/me");
        dispatch({ type: "SET_AUTHENTICATED", user: mapUserResponse(userData) });
      } catch {
        clearTokens();
        dispatch({ type: "SET_UNAUTHENTICATED" });
      }
    }

    restoreSession();
  }, []);

  // ── Multi-tab Sync ──────────────────────────────────────
  useEffect(() => {
    const unsubscribe = onTokenChange((tokensPresent) => {
      if (!tokensPresent) {
        dispatch({ type: "SET_UNAUTHENTICATED" });
      }
    });
    return unsubscribe;
  }, []);

  // ── Login ───────────────────────────────────────────────
  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    dispatch({ type: "START_LOADING" });

    try {
      const tokens = await fetchPublic<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: credentials,
      });

      setTokens(tokens.access_token, tokens.refresh_token);

      const userData = await fetchWithAuth<UserApiResponse>("/api/v1/users/me");
      dispatch({ type: "SET_AUTHENTICATED", user: mapUserResponse(userData) });
    } catch (error) {
      const message = (error as ApiError)?.message ?? "Login failed";
      dispatch({ type: "SET_UNAUTHENTICATED", error: message });
      throw error;
    }
  }, []);

  // ── Register ────────────────────────────────────────────
  const register = useCallback(async (credentials: RegisterCredentials): Promise<void> => {
    dispatch({ type: "START_LOADING" });

    try {
      // Register the account
      await fetchPublic<UserApiResponse>("/api/v1/auth/register", {
        method: "POST",
        body: {
          email: credentials.email,
          password: credentials.password,
          full_name: credentials.fullName,
        },
      });

      // Auto-login after successful registration
      const tokens = await fetchPublic<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: { email: credentials.email, password: credentials.password },
      });

      setTokens(tokens.access_token, tokens.refresh_token);

      const userData = await fetchWithAuth<UserApiResponse>("/api/v1/users/me");
      dispatch({ type: "SET_AUTHENTICATED", user: mapUserResponse(userData) });
    } catch (error) {
      const message = (error as ApiError)?.message ?? "Registration failed";
      dispatch({ type: "SET_UNAUTHENTICATED", error: message });
      throw error;
    }
  }, []);

  // ── Logout ──────────────────────────────────────────────
  const logout = useCallback(async (): Promise<void> => {
    try {
      // Best-effort server-side token revocation
      await fetchWithAuth("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Server-side logout failure is non-critical — clear local state regardless
    } finally {
      clearTokens();
      dispatch({ type: "SET_UNAUTHENTICATED" });
    }
  }, []);

  // ── Context Value ───────────────────────────────────────
  const value = useMemo<AuthContextValue>(
    () => ({
      user: state.user,
      isAuthenticated: state.status === "authenticated",
      isLoading: state.status === "idle" || state.status === "loading",
      error: state.error,
      login,
      register,
      logout,
    }),
    [state.user, state.status, state.error, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
