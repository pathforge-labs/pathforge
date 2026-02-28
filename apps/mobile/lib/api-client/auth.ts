/**
 * PathForge Mobile — API Client: Auth
 * ======================================
 * Authentication endpoints.
 */

import { fetchPublic, fetchWithAuth, post } from "../http";

import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
  RefreshTokenRequest,
} from "@pathforge/shared/types/api/auth";

export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  return fetchPublic<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: credentials,
  });
}

export async function register(data: RegisterRequest): Promise<TokenResponse> {
  return fetchPublic<TokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: data,
  });
}

export async function refreshToken(
  request: RefreshTokenRequest,
): Promise<TokenResponse> {
  return fetchPublic<TokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: request,
  });
}

export async function getCurrentUser(): Promise<UserResponse> {
  return fetchWithAuth<UserResponse>("/api/v1/auth/me");
}

export async function logout(): Promise<void> {
  return post<void>("/api/v1/auth/logout");
}
