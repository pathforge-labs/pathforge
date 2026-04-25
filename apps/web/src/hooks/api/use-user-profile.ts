/**
 * PathForge — Hook: useUserProfile
 * ==================================
 * Data-fetching hooks for user profile and onboarding status.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { userProfileApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  UserProfileResponse,
  UserProfileUpdateRequest,
  OnboardingStatusResponse,
  DataExportRequestCreate,
  DataExportRequestResponse,
} from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useUserProfile() {
  const { isAuthenticated } = useAuth();

  return useQuery<UserProfileResponse, ApiError>({
    queryKey: queryKeys.userProfile.profile(),
    queryFn: () => userProfileApi.getProfile(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useOnboardingStatus() {
  const { isAuthenticated } = useAuth();

  return useQuery<OnboardingStatusResponse, ApiError>({
    queryKey: queryKeys.userProfile.onboarding(),
    queryFn: () => userProfileApi.getOnboardingStatus(),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation<UserProfileResponse, ApiError, UserProfileUpdateRequest>({
    mutationFn: (data) => userProfileApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userProfile.all });
    },
  });
}

export function useRequestDataExport() {
  const queryClient = useQueryClient();

  return useMutation<DataExportRequestResponse, ApiError, DataExportRequestCreate>({
    mutationFn: (data) => userProfileApi.requestExport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userProfile.all });
    },
  });
}
