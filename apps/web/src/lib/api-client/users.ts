/**
 * PathForge — API Client: Users
 * ================================
 * User management endpoints.
 */

import { get, patch } from "@/lib/http";
import type { UserResponse, UserUpdateRequest } from "@/types/api";

export const usersApi = {
  me: (): Promise<UserResponse> =>
    get<UserResponse>("/api/v1/users/me"),

  update: (data: UserUpdateRequest): Promise<UserResponse> =>
    patch<UserResponse>("/api/v1/users/me", data),
};
