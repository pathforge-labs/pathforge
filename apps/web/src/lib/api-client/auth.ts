/**
 * PathForge — API Client: Auth
 * ==============================
 * Authentication endpoints (register, login, refresh, logout).
 */

import { fetchPublic, fetchWithAuth } from "@/lib/http";
import type { TokenResponse, UserResponse } from "@/types/api";

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
};
