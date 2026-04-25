/**
 * PathForge — API Client: Career Workflow Automation Engine™
 * ==========================================================
 * Workflows, steps, templates, executions, and preferences.
 */

import { get, patch, post, put } from "@/lib/http";
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

const BASE = "/api/v1/workflows";

export const workflowApi = {
  getDashboard: (): Promise<WorkflowDashboardResponse> =>
    get<WorkflowDashboardResponse>(`${BASE}/dashboard`),

  createWorkflow: (data: CreateWorkflowRequest): Promise<CareerWorkflowResponse> =>
    post<CareerWorkflowResponse>(BASE, data),

  listWorkflows: (
    status?: string,
    limit: number = 20,
    offset: number = 0,
  ): Promise<WorkflowListResponse> => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (status) params.set("status", status);
    return get<WorkflowListResponse>(`${BASE}?${params.toString()}`);
  },

  listTemplates: (): Promise<WorkflowTemplateInfo[]> =>
    get<WorkflowTemplateInfo[]>(`${BASE}/templates`),

  getWorkflowDetail: (workflowId: string): Promise<CareerWorkflowResponse> =>
    get<CareerWorkflowResponse>(`${BASE}/${workflowId}`),

  updateWorkflowStatus: (
    workflowId: string,
    data: UpdateWorkflowStatusRequest,
  ): Promise<CareerWorkflowResponse> =>
    patch<CareerWorkflowResponse>(`${BASE}/${workflowId}/status`, data),

  updateStepStatus: (
    workflowId: string,
    stepId: string,
    data: UpdateStepStatusRequest,
  ): Promise<CareerWorkflowResponse> =>
    patch<CareerWorkflowResponse>(`${BASE}/${workflowId}/steps/${stepId}`, data),

  getExecutions: (workflowId: string, limit: number = 10): Promise<WorkflowExecutionResponse[]> =>
    get<WorkflowExecutionResponse[]>(`${BASE}/${workflowId}/executions?limit=${limit}`),

  getPreferences: (): Promise<WorkflowPreferenceResponse> =>
    get<WorkflowPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: WorkflowPreferenceUpdate): Promise<WorkflowPreferenceResponse> =>
    put<WorkflowPreferenceResponse>(`${BASE}/preferences`, data),
};
