/**
 * PathForge — Domain API Client Tests
 * ======================================
 * Unit tests for AI, Applications, Analytics, Blacklist,
 * Health, and Users API client modules.
 *
 * Strategy: Mock fetchWithAuth/fetchPublic and verify each function
 * calls the correct endpoint with proper method and body.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/http", () => ({
  fetchWithAuth: vi.fn(),
  fetchPublic: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}));

import { fetchWithAuth, fetchPublic, get, patch } from "@/lib/http";

// Domain imports
import { parseResume, embedResume, matchResume, tailorCV, ingestJobs } from "@/lib/api-client/ai";
import { listApplications, createApplication, updateApplicationStatus, deleteApplication } from "@/lib/api-client/applications";
import { getFunnelMetrics, getMarketInsights, generateInsight, listExperiments } from "@/lib/api-client/analytics";
import { addBlacklist, listBlacklist, removeBlacklist } from "@/lib/api-client/blacklist";
import { healthApi } from "@/lib/api-client/health";
import { usersApi } from "@/lib/api-client/users";

const mockedFetchWithAuth = vi.mocked(fetchWithAuth);
const mockedFetchPublic = vi.mocked(fetchPublic);
const mockedGet = vi.mocked(get);
const mockedPatch = vi.mocked(patch);

describe("Domain API Clients", () => {
  beforeEach(() => {
    mockedFetchWithAuth.mockResolvedValue({});
    mockedFetchPublic.mockResolvedValue({});
    mockedGet.mockResolvedValue({});
    mockedPatch.mockResolvedValue({});
  });

  // ── AI Engine ─────────────────────────────────────────────

  describe("AI API Client", () => {
    it("parseResume should POST to /api/v1/ai/parse-resume", async () => {
      await parseResume("Raw resume text here");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/ai/parse-resume",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ raw_text: "Raw resume text here" }),
        }),
      );
    });

    it("embedResume should POST to /api/v1/ai/embed-resume/:id", async () => {
      await embedResume("resume-123");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/ai/embed-resume/resume-123",
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("matchResume should POST with top_k parameter", async () => {
      await matchResume("resume-123", 10);

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/ai/match-resume/resume-123",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ top_k: 10 }),
        }),
      );
    });

    it("tailorCV should POST with resume and job IDs", async () => {
      await tailorCV("resume-123", "job-456");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/ai/tailor-cv",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ resume_id: "resume-123", job_id: "job-456" }),
        }),
      );
    });

    it("ingestJobs should POST with ingestion params", async () => {
      await ingestJobs({ keywords: "software engineer", location: "Netherlands", pages: 3 });

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/ai/ingest-jobs",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ keywords: "software engineer", location: "Netherlands", pages: 3 }),
        }),
      );
    });
  });

  // ── Applications ──────────────────────────────────────────

  describe("Applications API Client", () => {
    it("listApplications should include query parameters", async () => {
      await listApplications("applied", 2, 50);

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/v1\/applications\?.*status=applied/),
      );
      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        expect.stringMatching(/page=2/),
      );
    });

    it("createApplication should POST with job listing data", async () => {
      await createApplication("job-789", "applied", "Great opportunity");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/applications",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            job_listing_id: "job-789",
            status: "applied",
            notes: "Great opportunity",
          }),
        }),
      );
    });

    it("updateApplicationStatus should PATCH correct endpoint", async () => {
      await updateApplicationStatus("app-123", "interviewing");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/applications/app-123/status",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ status: "interviewing" }),
        }),
      );
    });

    it("deleteApplication should DELETE correct endpoint", async () => {
      await deleteApplication("app-123");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/applications/app-123",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  // ── Analytics ─────────────────────────────────────────────

  describe("Analytics API Client", () => {
    it("getFunnelMetrics should pass period parameter", async () => {
      await getFunnelMetrics("7d");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/analytics/funnel/metrics?period=7d",
      );
    });

    it("getMarketInsights should GET insights endpoint", async () => {
      await getMarketInsights();

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/analytics/market/insights",
      );
    });

    it("generateInsight should POST with type and period", async () => {
      await generateInsight("salary_trends" as never, "30d");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/analytics/market/insights/generate",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ insight_type: "salary_trends", period: "30d" }),
        }),
      );
    });

    it("listExperiments should GET experiments endpoint", async () => {
      await listExperiments();

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/analytics/experiments",
      );
    });
  });

  // ── Blacklist ─────────────────────────────────────────────

  describe("Blacklist API Client", () => {
    it("addBlacklist should POST with company data", async () => {
      await addBlacklist("BadCorp", "Toxic culture", false);

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/blacklist",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            company_name: "BadCorp",
            reason: "Toxic culture",
            is_current_employer: false,
          }),
        }),
      );
    });

    it("listBlacklist should GET blacklist endpoint", async () => {
      await listBlacklist();

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/blacklist",
      );
    });

    it("removeBlacklist should DELETE by ID", async () => {
      await removeBlacklist("bl-123");

      expect(mockedFetchWithAuth).toHaveBeenCalledWith(
        "/api/v1/blacklist/bl-123",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  // ── Health ────────────────────────────────────────────────

  describe("Health API Client", () => {
    it("healthApi.check should GET /api/v1/health", async () => {
      await healthApi.check();

      expect(mockedFetchPublic).toHaveBeenCalledWith(
        "/api/v1/health",
      );
    });

    it("healthApi.ready should GET /api/v1/health/ready", async () => {
      await healthApi.ready();

      expect(mockedFetchPublic).toHaveBeenCalledWith(
        "/api/v1/health/ready",
      );
    });
  });

  // ── Users ─────────────────────────────────────────────────

  describe("Users API Client", () => {
    it("usersApi.me should GET /api/v1/users/me", async () => {
      await usersApi.me();

      expect(mockedGet).toHaveBeenCalledWith("/api/v1/users/me");
    });

    it("usersApi.update should PATCH /api/v1/users/me with data", async () => {
      await usersApi.update({ full_name: "Updated Name" });

      expect(mockedPatch).toHaveBeenCalledWith(
        "/api/v1/users/me",
        { full_name: "Updated Name" },
      );
    });
  });
});
