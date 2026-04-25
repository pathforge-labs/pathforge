/**
 * PathForge — Sprint 28: Notification Digest Tests
 * ===================================================
 * Time-based unit tests for notification digest scheduling.
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

import { notificationsApi } from "@/lib/api-client/notifications";
import type {
  NotificationDigestResponse,
  NotificationDigestListResponse,
  NotificationPreferenceResponse,
} from "@/types/api";

describe("Notification Digests — Time-Based Tests", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetch();
  });

  // ── Digest Generation ─────────────────────────────────────

  describe("Digest generation", () => {
    it("should generate a daily digest", async () => {
      const mockDigest: NotificationDigestResponse = {
        id: "digest-1",
        digest_type: "daily",
        summary: "3 new alerts from Threat Radar, 2 skill decay warnings",
        notification_count: 5,
        highlights: [
          "Threat level increased for AI automation",
          "TypeScript freshness dropped below 60%",
        ],
        generated_at: "2026-02-26T08:00:00Z",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockDigest));

      const result = await notificationsApi.generateDigest("daily");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("digest_type=daily"),
        expect.any(Object),
      );
      expect(result.digest_type).toBe("daily");
      expect(result.notification_count).toBeGreaterThan(0);
      expect(result.highlights).toHaveLength(2);
    });

    it("should generate a weekly digest", async () => {
      const mockDigest: NotificationDigestResponse = {
        id: "digest-2",
        digest_type: "weekly",
        summary: "12 notifications this week across 4 engines",
        notification_count: 12,
        highlights: [
          "Career health improved by 5 points",
          "2 new hidden market signals detected",
          "Salary Intelligence updated for Netherlands",
        ],
        generated_at: "2026-02-23T08:00:00Z",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockDigest));

      const result = await notificationsApi.generateDigest("weekly");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("digest_type=weekly"),
        expect.any(Object),
      );
      expect(result.digest_type).toBe("weekly");
      expect(result.notification_count).toBe(12);
    });
  });

  // ── Digest Listing ────────────────────────────────────────

  describe("Digest listing", () => {
    it("should list past digests with pagination", async () => {
      const mockList: NotificationDigestListResponse = {
        items: [
          {
            id: "digest-1",
            digest_type: "weekly",
            summary: "Week of Feb 17",
            notification_count: 8,
            highlights: ["skill decay scan completed"],
            generated_at: "2026-02-17T08:00:00Z",
          },
          {
            id: "digest-2",
            digest_type: "weekly",
            summary: "Week of Feb 10",
            notification_count: 15,
            highlights: ["career pivot detected"],
            generated_at: "2026-02-10T08:00:00Z",
          },
        ],
        total: 10,
        page: 1,
        per_page: 20,
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockList));

      const result = await notificationsApi.listDigests(1, 20);

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(10);

      // Verify digests are time-ordered (most recent first)
      const dates = result.items.map((d) => new Date(d.generated_at).getTime());
      expect(dates[0]).toBeGreaterThan(dates[1]);
    });
  });

  // ── Preference Scheduling ─────────────────────────────────

  describe("Digest scheduling preferences", () => {
    it("should fetch digest frequency preference", async () => {
      const mockPrefs: NotificationPreferenceResponse = {
        id: "pref-1",
        email_enabled: true,
        push_enabled: false,
        digest_frequency: "weekly",
        quiet_hours_start: "22:00",
        quiet_hours_end: "08:00",
        muted_engines: [],
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockPrefs));

      const result = await notificationsApi.getPreferences();

      expect(result.digest_frequency).toBe("weekly");
      expect(result.quiet_hours_start).toBe("22:00");
      expect(result.quiet_hours_end).toBe("08:00");
    });

    it("should update digest frequency", async () => {
      const mockUpdated: NotificationPreferenceResponse = {
        id: "pref-1",
        email_enabled: true,
        push_enabled: true,
        digest_frequency: "daily",
        quiet_hours_start: null,
        quiet_hours_end: null,
        muted_engines: ["analytics"],
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockUpdated));

      const result = await notificationsApi.updatePreferences({
        digest_frequency: "daily",
        push_enabled: true,
      });

      expect(result.digest_frequency).toBe("daily");
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/preferences"),
        expect.objectContaining({ method: "PUT" }),
      );
    });
  });
});
