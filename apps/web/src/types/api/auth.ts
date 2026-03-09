/**
 * PathForge — API Types: Auth
 * =============================
 * Types mirroring `app.schemas.user` Pydantic models.
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  auth_provider: string;
  avatar_url: string | null;
  created_at: string;
}

export interface UserUpdateRequest {
  full_name?: string;
  avatar_url?: string | null;
}

// ── Sprint 39: Password Reset & Email Verification ──────────

export interface ForgotPasswordRequest {
  readonly email: string;
}

export interface ResetPasswordRequest {
  readonly token: string;
  readonly new_password: string;
}

export interface VerifyEmailRequest {
  readonly token: string;
}

export interface OAuthTokenRequest {
  readonly id_token: string;
}

