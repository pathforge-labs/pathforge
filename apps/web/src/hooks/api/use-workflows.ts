"use client";

/**
 * PathForge — Hooks: Career Workflow Automation Engine™
 * =====================================================
 * TanStack Query hooks for workflows, steps, templates, and executions.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { workflowApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CareerWorkflowResponse,
  CreateWorkflowRequest,
  UpdateStepStatusRequest,
  UpdateWorkflowStatusRequest,
  WorkflowDashboardResponse,
  WorkflowExecutionResponse,
  WorkflowListResponse,
  WorkflowPreferenceResponse,
  WorkflowPreferenceUpdate,
  WorkflowTemplateInfo,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useWorkflowDashboard(): ReturnType<typeof useQuery<WorkflowDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.workflows.dashboard(),
    queryFn: () => workflowApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useWorkflows(
  status?: string,
  limit?: number,
  offset?: number,
): ReturnType<typeof useQuery<WorkflowListResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.workflows.list({ status, limit, offset }),
    queryFn: () => workflowApi.listWorkflows(status, limit, offset),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useWorkflowDetail(workflowId: string): ReturnType<typeof useQuery<CareerWorkflowResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.workflows.detail(workflowId),
    queryFn: () => workflowApi.getWorkflowDetail(workflowId),
    enabled: isAuthenticated && !!workflowId,
    staleTime: STALE_5M,
  });
}

export function useWorkflowTemplates(): ReturnType<typeof useQuery<WorkflowTemplateInfo[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.workflows.templates(),
    queryFn: () => workflowApi.listTemplates(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useWorkflowExecutions(workflowId: string): ReturnType<typeof useQuery<WorkflowExecutionResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.workflows.executions(workflowId),
    queryFn: () => workflowApi.getExecutions(workflowId),
    enabled: isAuthenticated && !!workflowId,
    staleTime: STALE_5M,
  });
}

export function useWorkflowPreferences(): ReturnType<typeof useQuery<WorkflowPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.workflows.preferences(),
    queryFn: () => workflowApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useCreateWorkflow(): ReturnType<typeof useMutation<CareerWorkflowResponse, Error, CreateWorkflowRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateWorkflowRequest) => workflowApi.createWorkflow(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.workflows.all });
    },
  });
}

interface UpdateWorkflowStatusParams {
  readonly workflowId: string;
  readonly data: UpdateWorkflowStatusRequest;
}

export function useUpdateWorkflowStatus(): ReturnType<typeof useMutation<CareerWorkflowResponse, Error, UpdateWorkflowStatusParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workflowId, data }: UpdateWorkflowStatusParams) => workflowApi.updateWorkflowStatus(workflowId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.workflows.all });
    },
  });
}

interface UpdateStepStatusParams {
  readonly workflowId: string;
  readonly stepId: string;
  readonly data: UpdateStepStatusRequest;
}

export function useUpdateStepStatus(): ReturnType<typeof useMutation<CareerWorkflowResponse, Error, UpdateStepStatusParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workflowId, stepId, data }: UpdateStepStatusParams) => workflowApi.updateStepStatus(workflowId, stepId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.workflows.all });
    },
  });
}

export function useUpdateWorkflowPreferences(): ReturnType<typeof useMutation<WorkflowPreferenceResponse, Error, WorkflowPreferenceUpdate>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowPreferenceUpdate) => workflowApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.workflows.preferences() });
    },
  });
}
