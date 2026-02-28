/**
 * Theme & Config — Unit Tests
 * ==============================
 * Tests design token consistency, score color mapping,
 * and config constant validation.
 */

import {
  BRAND,
  LIGHT,
  DARK,
  SPACING,
  SHADOW,
  ANIMATION,
  getScoreColor,
} from "../../constants/theme";

import {
  DEFAULT_REQUEST_TIMEOUT_MS,
  UPLOAD_REQUEST_TIMEOUT_MS,
  MAX_UPLOAD_FILE_SIZE_BYTES,
  ALLOWED_RESUME_MIME_TYPES,
  ALLOWED_RESUME_EXTENSIONS,
  QUERY_STALE_TIME_MS,
  QUERY_MAX_RETRIES,
} from "../../constants/config";

// ── Theme Tests ─────────────────────────────────────────────

describe("theme constants", () => {
  describe("BRAND colors", () => {
    it("should define all required brand colors", () => {
      expect(BRAND.primary).toBeDefined();
      expect(BRAND.primaryDark).toBeDefined();
      expect(BRAND.primaryLight).toBeDefined();
      expect(BRAND.secondary).toBeDefined();
      expect(BRAND.accent).toBeDefined();
      expect(BRAND.success).toBeDefined();
      expect(BRAND.warning).toBeDefined();
      expect(BRAND.error).toBeDefined();
      expect(BRAND.info).toBeDefined();
    });

    it("should use valid hex color format", () => {
      const hexRegex = /^#[0-9A-Fa-f]{6}$/;
      Object.values(BRAND).forEach((color) => {
        expect(color).toMatch(hexRegex);
      });
    });
  });

  describe("LIGHT and DARK themes", () => {
    it("should have the same keys", () => {
      const lightKeys = Object.keys(LIGHT).sort();
      const darkKeys = Object.keys(DARK).sort();
      expect(lightKeys).toEqual(darkKeys);
    });

    it("should define all required semantic colors", () => {
      const requiredKeys = [
        "background",
        "surface",
        "surfaceElevated",
        "border",
        "borderSubtle",
        "text",
        "textSecondary",
        "textTertiary",
        "textInverse",
        "tabBar",
        "tabBarInactive",
        "statusBar",
      ];

      requiredKeys.forEach((key) => {
        expect(LIGHT).toHaveProperty(key);
        expect(DARK).toHaveProperty(key);
      });
    });

    it("LIGHT should have dark statusBar", () => {
      expect(LIGHT.statusBar).toBe("dark");
    });

    it("DARK should have light statusBar", () => {
      expect(DARK.statusBar).toBe("light");
    });
  });

  describe("getScoreColor", () => {
    it("should return success for scores >= 80", () => {
      expect(getScoreColor(80)).toBe(BRAND.success);
      expect(getScoreColor(100)).toBe(BRAND.success);
    });

    it("should return primary for scores 60-79", () => {
      expect(getScoreColor(60)).toBe(BRAND.primary);
      expect(getScoreColor(79)).toBe(BRAND.primary);
    });

    it("should return warning for scores 40-59", () => {
      expect(getScoreColor(40)).toBe(BRAND.warning);
      expect(getScoreColor(59)).toBe(BRAND.warning);
    });

    it("should return error for scores < 40", () => {
      expect(getScoreColor(39)).toBe(BRAND.error);
      expect(getScoreColor(0)).toBe(BRAND.error);
    });
  });

  describe("spacing scale", () => {
    it("should follow an increasing scale", () => {
      expect(SPACING.xs).toBeLessThan(SPACING.sm);
      expect(SPACING.sm).toBeLessThan(SPACING.md);
      expect(SPACING.md).toBeLessThan(SPACING.lg);
      expect(SPACING.lg).toBeLessThan(SPACING.xl);
      expect(SPACING.xl).toBeLessThan(SPACING.xxl);
      expect(SPACING.xxl).toBeLessThan(SPACING.xxxl);
    });
  });

  describe("shadows", () => {
    it("should define sm, md, lg with increasing elevation", () => {
      expect(SHADOW.sm.elevation).toBeLessThan(SHADOW.md.elevation);
      expect(SHADOW.md.elevation).toBeLessThan(SHADOW.lg.elevation);
    });
  });

  describe("animations", () => {
    it("should define fast < normal < slow durations", () => {
      expect(ANIMATION.fast).toBeLessThan(ANIMATION.normal);
      expect(ANIMATION.normal).toBeLessThan(ANIMATION.slow);
    });
  });
});

// ── Config Tests ────────────────────────────────────────────

describe("config constants", () => {
  it("should define reasonable timeout defaults", () => {
    expect(DEFAULT_REQUEST_TIMEOUT_MS).toBe(15_000);
    expect(UPLOAD_REQUEST_TIMEOUT_MS).toBe(30_000);
    expect(UPLOAD_REQUEST_TIMEOUT_MS).toBeGreaterThan(DEFAULT_REQUEST_TIMEOUT_MS);
  });

  it("should define 10MB max upload size", () => {
    expect(MAX_UPLOAD_FILE_SIZE_BYTES).toBe(10 * 1024 * 1024);
  });

  it("should include PDF in allowed MIME types", () => {
    expect(ALLOWED_RESUME_MIME_TYPES).toContain("application/pdf");
  });

  it("should include PDF in allowed extensions", () => {
    expect(ALLOWED_RESUME_EXTENSIONS).toContain("PDF");
  });

  it("should define query defaults with stale time and retry", () => {
    expect(QUERY_STALE_TIME_MS).toBeGreaterThan(0);
    expect(QUERY_MAX_RETRIES).toBeGreaterThanOrEqual(1);
  });
});
