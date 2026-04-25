/**
 * PathForge — API Client: Auth
 * ==============================
 * Authentication endpoints (register, login, refresh, logout, password reset).
 */

import { fetchPublic, fetchWithAuth } from "@/lib/http";
import type {
  ForgotPasswordRequest,
  MessageResponse,
  OAuthTokenRequest,
  ResetPasswordRequest,
  TokenResponse,
  UserResponse,
  VerifyEmailRequest,
} from "@/types/api";

export const authApi = {
  register: (data: { email: string; password: string; full_name: string }): Promise<UserResponse> =>
    fetchPublic<UserResponse>("/api/v1/auth/register", {
      method: "POST",
      body: data,
    }),

  login: (data: { email: string; password: string }): Promise<TokenResponse> =>
    fetchPublic<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: data,
    }),

  refresh: (refreshToken: string): Promise<TokenResponse> =>
    fetchPublic<TokenResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),

  logout: (): Promise<void> =>
    fetchWithAuth<void>("/api/v1/auth/logout", { method: "POST" }),

  // ── Sprint 39: Password Reset ──────────────────────────────

  forgotPassword: (data: ForgotPasswordRequest): Promise<MessageResponse> =>
    fetchPublic<MessageResponse>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: data,
    }),

  resetPassword: (data: ResetPasswordRequest): Promise<MessageResponse> =>
    fetchPublic<MessageResponse>("/api/v1/auth/reset-password", {
      method: "POST",
      body: data,
    }),

  // ── Sprint 39: Email Verification ─────────────────────────

  verifyEmail: (data: VerifyEmailRequest): Promise<MessageResponse> =>
    fetchPublic<MessageResponse>("/api/v1/auth/verify-email", {
      method: "POST",
      body: data,
    }),

  resendVerification: (data: ForgotPasswordRequest): Promise<MessageResponse> =>
    fetchPublic<MessageResponse>("/api/v1/auth/resend-verification", {
      method: "POST",
      body: data,
    }),

  // ── Sprint 39: OAuth / Social Login ───────────────────────

  oauthLogin: (provider: "google" | "microsoft", data: OAuthTokenRequest): Promise<TokenResponse> =>
    fetchPublic<TokenResponse>(`/api/v1/auth/oauth/${provider}`, {
      method: "POST",
      body: data,
    }),
};
