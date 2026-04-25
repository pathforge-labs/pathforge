/**
 * PathForge Mobile — Career DNA Helpers
 * ========================================
 * Pure utility functions for Career DNA dimension building.
 * Extracted for testability (Sprint 33 — WS-2).
 */

import type { CareerDnaProfileResponse } from "@pathforge/shared/types/api/career-dna";

// ── Types ───────────────────────────────────────────────────

export interface DimensionCard {
  readonly id: string;
  readonly title: string;
  readonly score: number;
  readonly scoreLabel: string;
  readonly content: string[];
}

// ── Builder ─────────────────────────────────────────────────

/**
 * Transform a Career DNA profile response into displayable dimension cards.
 *
 * - Produces 0–6 cards depending on profile completeness.
 * - Skill Genome + Hidden Skills: average proficiency/confidence scores.
 * - Values Profile: explicit score=0 (no numeric score available).
 * - All arrays are capped at 5 items for display.
 */
export function buildDimensions(profile: CareerDnaProfileResponse): DimensionCard[] {
  const dimensions: DimensionCard[] = [];

  // 1. Skill Genome
  if (profile.skill_genome.length > 0) {
    const avgProficiency = Math.round(
      profile.skill_genome.reduce((sum, skill) => sum + skill.proficiency_level, 0) /
        profile.skill_genome.length,
    );
    dimensions.push({
      id: "skill_genome",
      title: "🧬 Skill Genome",
      score: avgProficiency,
      scoreLabel: `${profile.skill_genome.length} skills mapped`,
      content: profile.skill_genome
        .slice(0, 5)
        .map((skill) => `${skill.skill_name} — Level ${skill.proficiency_level}`),
    });
  }

  // 2. Experience Blueprint
  if (profile.experience_blueprint) {
    const blueprint = profile.experience_blueprint;
    dimensions.push({
      id: "experience_blueprint",
      title: "📋 Experience Blueprint",
      score: Math.round(blueprint.industry_diversity * 100),
      scoreLabel: `${blueprint.total_years} years · ${blueprint.career_pattern}`,
      content: [
        `Pattern: ${blueprint.career_pattern}`,
        `Progression: ${blueprint.role_progression}`,
        ...(blueprint.notable_transitions || []),
      ],
    });
  }

  // 3. Growth Vector
  if (profile.growth_vector) {
    const growth = profile.growth_vector;
    dimensions.push({
      id: "growth_vector",
      title: "📈 Growth Vector",
      score: growth.momentum_score,
      scoreLabel: `Trajectory: ${growth.trajectory_direction}`,
      content: [
        `Direction: ${growth.trajectory_direction}`,
        ...(growth.projected_roles || []).map((role) => `→ ${role}`),
        ...(growth.growth_catalysts || []).map((catalyst) => `✦ ${catalyst}`),
      ],
    });
  }

  // 4. Values Profile
  if (profile.values_profile) {
    const values = profile.values_profile;
    dimensions.push({
      id: "values_profile",
      title: "💎 Values Profile",
      score: 0,
      scoreLabel: values.work_style,
      content: [
        `Work style: ${values.work_style}`,
        ...(values.top_values || []).map((value) => `• ${value}`),
      ],
    });
  }

  // 5. Market Position
  if (profile.market_position) {
    const market = profile.market_position;
    dimensions.push({
      id: "market_position",
      title: "🎯 Market Position",
      score: market.competitiveness_score,
      scoreLabel: `P${market.salary_percentile} · ${market.demand_level} demand`,
      content: [
        `Demand: ${market.demand_level}`,
        `Salary percentile: P${market.salary_percentile}`,
        market.positioning_advice,
      ],
    });
  }

  // 6. Hidden Skills
  if (profile.hidden_skills.length > 0) {
    const avgConfidence = Math.round(
      profile.hidden_skills.reduce((sum, skill) => sum + skill.confidence, 0) /
        profile.hidden_skills.length,
    );
    dimensions.push({
      id: "hidden_skills",
      title: "🔍 Hidden Skills",
      score: avgConfidence,
      scoreLabel: `${profile.hidden_skills.length} discovered`,
      content: profile.hidden_skills.map(
        (skill) => `${skill.skill_name} (${Math.round(skill.confidence * 100)}%)`,
      ),
    });
  }

  return dimensions;
}
