/**
 * PathForge — Sprint 28: Hidden Job Market API Client Tests
 * ==========================================================
 * Tests for signal scanning, outreach generation, and opportunity surfacing.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockFetch,
  mockFetchResponse,
} from "../test-helpers";

vi.mock("@/lib/token-manager", () => ({
  getAccessToken: vi.fn(() => "mock-access-token"),
}));

vi.mock("@/lib/refresh-queue", () => ({
  refreshAccessToken: vi.fn(),
}));

import { hiddenJobMarketApi } from "@/lib/api-client/hidden-job-market";
import type { HiddenJobMarketDashboardResponse } from "@/types/api";

describe("Hidden Job Market — API Client", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetch();
  });

  describe("Dashboard", () => {
    it("should fetch dashboard with signal counts", async () => {
      const mockDashboard: HiddenJobMarketDashboardResponse = {
        signals: [],
        preferences: null,
        total_signals: 8,
        active_signals: 5,
        average_match_score: 0.72,
        data_source: "ai_analysis",
        disclaimer: "AI-generated signals",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockDashboard));

      const result = await hiddenJobMarketApi.getDashboard();

      expect(result.total_signals).toBe(8);
      expect(result.active_signals).toBe(5);
      expect(result.average_match_score).toBe(0.72);
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/hidden-job-market/dashboard"),
        expect.any(Object),
      );
    });
  });

  describe("Company scanning", () => {
    it("should scan a company with signal type focus", async () => {
      const mockSignal = {
        id: "sig-1",
        career_dna_id: "dna-1",
        user_id: "user-1",
        company_name: "Acme Corp",
        industry: "Technology",
        signal_type: "hiring_surge",
        title: "Engineering team growth signal",
        description: null,
        strength: 0.85,
        status: "active",
        confidence_score: 0.78,
        evidence: null,
        detected_at: "2026-02-26T12:00:00Z",
        data_source: "ai_analysis",
        disclaimer: "AI-generated",
        match_results: [],
        outreach_templates: [],
        hidden_opportunities: [],
        created_at: "2026-02-26T12:00:00Z",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockSignal));

      const result = await hiddenJobMarketApi.scanCompany({
        company_name: "Acme Corp",
        industry: "Technology",
        focus_signal_types: ["hiring_surge"],
      });

      expect(result.company_name).toBe("Acme Corp");
      expect(result.signal_type).toBe("hiring_surge");
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/scan-company"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  describe("Outreach generation", () => {
    it("should generate outreach template for a signal", async () => {
      const mockOutreach = {
        id: "out-1",
        signal_id: "sig-1",
        template_type: "cold_email",
        tone: "professional",
        subject_line: "Exploring opportunities at Acme Corp",
        body: "Dear hiring manager...",
        personalization_points: null,
        confidence: 0.82,
        created_at: "2026-02-26T12:00:00Z",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockOutreach));

      const result = await hiddenJobMarketApi.generateOutreach("sig-1", {
        template_type: "cold_email",
        tone: "professional",
      });

      expect(result.template_type).toBe("cold_email");
      expect(result.tone).toBe("professional");
      expect(result.subject_line).toBeTruthy();
    });
  });

  describe("Opportunities", () => {
    it("should surface opportunity radar data", async () => {
      const mockOpportunities = {
        opportunities: [
          {
            id: "opp-1",
            signal_id: "sig-1",
            predicted_role: "Senior Engineer",
            predicted_department: "Engineering",
            time_horizon: "3-6 months",
            probability: 0.75,
            reasoning: "Team growth combined with new product launch",
            required_skills: null,
            salary_range_min: 80000,
            salary_range_max: 120000,
            currency: "EUR",
            created_at: "2026-02-26T12:00:00Z",
          },
        ],
        total_opportunities: 1,
        top_industries: ["Technology"],
        data_source: "ai_analysis",
        disclaimer: "AI prediction",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockOpportunities));

      const result = await hiddenJobMarketApi.getOpportunities();

      expect(result.total_opportunities).toBe(1);
      expect(result.opportunities[0].probability).toBe(0.75);
      expect(result.opportunities[0].predicted_role).toBe("Senior Engineer");
    });
  });
});
