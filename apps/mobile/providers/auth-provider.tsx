/**
 * PathForge Mobile — Auth Provider
 * ===================================
 * 4-state authentication machine using React Context + useReducer.
 *
 * State machine: idle → loading → authenticated | unauthenticated
 *
 * Uses SecureStore for token persistence. Session restore happens
 * on mount and on foreground return (AppState listener).
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
} from "react";
import { AppState } from "react-native";

import type { UserResponse } from "@pathforge/shared/types/api/auth";

import * as authApi from "../lib/api-client/auth";
import {
  clearTokens,
  hasTokens,
  hydrateTokens,
  isHydrated,
  setTokens,
} from "../lib/token-manager";

// ── State ───────────────────────────────────────────────────

type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  status: AuthStatus;
  user: UserResponse | null;
  isRestoring: boolean;
}

// ── Actions ─────────────────────────────────────────────────

type AuthAction =
  | { type: "RESTORE_START" }
  | { type: "RESTORE_SUCCESS"; user: UserResponse }
  | { type: "RESTORE_FAILURE" }
  | { type: "LOGIN_START" }
  | { type: "LOGIN_SUCCESS"; user: UserResponse }
  | { type: "LOGIN_FAILURE" }
  | { type: "LOGOUT" };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "RESTORE_START":
      return { ...state, status: "loading", isRestoring: true };
    case "RESTORE_SUCCESS":
      return {
        status: "authenticated",
        user: action.user,
        isRestoring: false,
      };
    case "RESTORE_FAILURE":
      return {
        status: "unauthenticated",
        user: null,
        isRestoring: false,
      };
    case "LOGIN_START":
      return { ...state, status: "loading" };
    case "LOGIN_SUCCESS":
      return {
        status: "authenticated",
        user: action.user,
        isRestoring: false,
      };
    case "LOGIN_FAILURE":
      return { ...state, status: "unauthenticated" };
    case "LOGOUT":
      return {
        status: "unauthenticated",
        user: null,
        isRestoring: false,
      };
    default:
      return state;
  }
}

const INITIAL_STATE: AuthState = {
  status: "idle",
  user: null,
  isRestoring: true,
};

// ── Context ─────────────────────────────────────────────────

interface AuthContextValue {
  status: AuthStatus;
  user: UserResponse | null;
  isRestoring: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ────────────────────────────────────────────────

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps): React.JSX.Element {
  const [state, dispatch] = useReducer(authReducer, INITIAL_STATE);

  // ── Session Restore ──────────────────────────────────────

  const restoreSession = useCallback(async (): Promise<void> => {
    dispatch({ type: "RESTORE_START" });

    try {
      // Hydrate tokens from SecureStore if not done yet
      if (!isHydrated()) {
        await hydrateTokens();
      }

      if (!hasTokens()) {
        dispatch({ type: "RESTORE_FAILURE" });
        return;
      }

      // Validate token by fetching current user
      const user = await authApi.getCurrentUser();
      dispatch({ type: "RESTORE_SUCCESS", user });
    } catch {
      // Token invalid or expired — clear and redirect to login
      await clearTokens();
      dispatch({ type: "RESTORE_FAILURE" });
    }
  }, []);

  // ── Initial Restore ──────────────────────────────────────

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  // ── Foreground Restore ───────────────────────────────────

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState === "active" && state.status === "authenticated") {
        // Silently validate token on foreground return
        authApi.getCurrentUser().catch(() => {
          // Token expired while in background
          void clearTokens().then(() => {
            dispatch({ type: "LOGOUT" });
          });
        });
      }
    });

    return () => subscription.remove();
  }, [state.status]);

  // ── Auth Actions ─────────────────────────────────────────

  const login = useCallback(
    async (email: string, password: string): Promise<void> => {
      dispatch({ type: "LOGIN_START" });
      try {
        const tokens = await authApi.login({ email, password });
        await setTokens(tokens.access_token, tokens.refresh_token);

        const user = await authApi.getCurrentUser();
        dispatch({ type: "LOGIN_SUCCESS", user });
      } catch (error) {
        dispatch({ type: "LOGIN_FAILURE" });
        throw error; // Re-throw for the calling component to handle
      }
    },
    [],
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      fullName: string,
    ): Promise<void> => {
      dispatch({ type: "LOGIN_START" });
      try {
        const tokens = await authApi.register({
          email,
          password,
          full_name: fullName,
        });
        await setTokens(tokens.access_token, tokens.refresh_token);

        const user = await authApi.getCurrentUser();
        dispatch({ type: "LOGIN_SUCCESS", user });
      } catch (error) {
        dispatch({ type: "LOGIN_FAILURE" });
        throw error;
      }
    },
    [],
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authApi.logout();
    } catch {
      // Logout API call is best-effort
    }
    // Push-token deregistration happens inside ``usePushNotifications``
    // because that hook owns the Expo push-token state — the
    // auth-provider has no direct access to it. The previous
    // ``notificationsApi.deregisterPushToken()`` call here was a
    // placeholder that compiled before the API was made
    // token-required (it now needs ``{ token: string }``). The hook
    // observes the LOGOUT dispatch via auth state and tears down its
    // registration there. Server-side, the JWT is already blacklisted
    // by the logout call above, so any straggling push delivery to
    // this device fails fast even if cleanup is interrupted.
    await clearTokens();
    dispatch({ type: "LOGOUT" });
  }, []);

  // ── Memoized Value ───────────────────────────────────────

  const value = useMemo<AuthContextValue>(
    () => ({
      status: state.status,
      user: state.user,
      isRestoring: state.isRestoring,
      isAuthenticated: state.status === "authenticated",
      login,
      register,
      logout,
    }),
    [state.status, state.user, state.isRestoring, login, register, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
