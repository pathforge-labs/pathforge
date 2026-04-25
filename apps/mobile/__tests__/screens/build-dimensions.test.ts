/**
 * PathForge Mobile — Test: buildDimensions
 * ============================================
 * Pure-function tests for Career DNA dimension card builder.
 * Sprint 33 — WS-2: Suite 1 (6 tests)
 */

import { buildDimensions } from "../../lib/career-dna-helpers";
import type { CareerDnaProfileResponse } from "@pathforge/shared/types/api/career-dna";

// ── Test Fixtures ───────────────────────────────────────────

const EMPTY_PROFILE: CareerDnaProfileResponse = {
  completeness_score: 0,
  generated_at: "2026-01-01T00:00:00Z",
  skill_genome: [],
  experience_blueprint: null,
  growth_vector: null,
  values_profile: null,
  market_position: null,
  hidden_skills: [],
};

const FULL_PROFILE: CareerDnaProfileResponse = {
  completeness_score: 100,
  generated_at: "2026-03-01T12:00:00Z",
  skill_genome: [
    { skill_name: "TypeScript", proficiency_level: 9, category: "technical" },
    { skill_name: "React", proficiency_level: 8, category: "technical" },
    { skill_name: "Node.js", proficiency_level: 7, category: "technical" },
    { skill_name: "Python", proficiency_level: 6, category: "technical" },
    { skill_name: "Docker", proficiency_level: 5, category: "devops" },
    { skill_name: "Kubernetes", proficiency_level: 4, category: "devops" },
  ],
  experience_blueprint: {
    total_years: 8,
    career_pattern: "T-Shaped",
    role_progression: "IC → Senior → Staff",
    industry_diversity: 0.75,
    notable_transitions: ["Backend → Full-Stack"],
  },
  growth_vector: {
    momentum_score: 82,
    trajectory_direction: "upward",
    projected_roles: ["Staff Engineer", "Principal Engineer"],
    growth_catalysts: ["Open source", "Conference talks"],
  },
  values_profile: {
    work_style: "Async-first remote",
    top_values: ["Autonomy", "Impact", "Craft"],
  },
  market_position: {
    competitiveness_score: 88,
    salary_percentile: 90,
    demand_level: "high",
    positioning_advice: "Strong position in cloud-native engineering.",
  },
  hidden_skills: [
    { skill_name: "Technical Writing", confidence: 0.85 },
    { skill_name: "Mentoring", confidence: 0.72 },
  ],
};

// ── Tests ───────────────────────────────────────────────────

describe("buildDimensions", () => {
  it("returns empty array for empty profile", () => {
    const result = buildDimensions(EMPTY_PROFILE);
    expect(result).toEqual([]);
  });

  it("returns 6 cards for complete profile", () => {
    const result = buildDimensions(FULL_PROFILE);
    expect(result).toHaveLength(6);
    expect(result.map((card) => card.id)).toEqual([
      "skill_genome",
      "experience_blueprint",
      "growth_vector",
      "values_profile",
      "market_position",
      "hidden_skills",
    ]);
  });

  it("calculates average proficiency correctly", () => {
    const result = buildDimensions(FULL_PROFILE);
    const skillGenome = result.find((card) => card.id === "skill_genome");
    // (9+8+7+6+5+4) / 6 = 6.5 → Math.round = 7
    expect(skillGenome?.score).toBe(7);
  });

  it("calculates industry diversity as percentage", () => {
    const result = buildDimensions(FULL_PROFILE);
    const blueprint = result.find((card) => card.id === "experience_blueprint");
    // 0.75 * 100 = 75
    expect(blueprint?.score).toBe(75);
  });

  it("truncates skill genome content to 5 items", () => {
    const result = buildDimensions(FULL_PROFILE);
    const skillGenome = result.find((card) => card.id === "skill_genome");
    // Profile has 6 skills, content should show only 5
    expect(skillGenome?.content).toHaveLength(5);
    expect(skillGenome?.scoreLabel).toBe("6 skills mapped");
  });

  it("uses explicit zero score for values profile", () => {
    const result = buildDimensions(FULL_PROFILE);
    const valuesProfile = result.find((card) => card.id === "values_profile");
    expect(valuesProfile?.score).toBe(0);
    expect(valuesProfile?.scoreLabel).toBe("Async-first remote");
  });
});
