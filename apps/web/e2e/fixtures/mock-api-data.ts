/**
 * PathForge — Visual Regression Mock API Data
 * =============================================
 * Sprint 36 WS-7: Deterministic, seeded API responses for visual regression tests.
 *
 * All `/api/v1/*` calls from the frontend hit `localhost:8000` (Python backend).
 * These mocks are intercepted at the Playwright network level so the frontend
 * renders real UI components with stable, repeatable data.
 */

/* ── Auth ─────────────────────────────────────────────────── */

export const MOCK_USER = {
  id: "vr-user-001",
  email: "visual-tester@pathforge.ai",
  full_name: "Visual Tester",
  is_active: true,
  is_verified: true,
  auth_provider: "email",
  avatar_url: null,
  created_at: "2025-12-01T00:00:00Z",
} as const;

/* ── Health ───────────────────────────────────────────────── */

export const MOCK_HEALTH = {
  status: "healthy",
  app: "PathForge API",
  version: "1.0.0",
  database: "connected",
  timestamp: "2026-01-15T10:00:00Z",
} as const;

/* ── Onboarding Status ───────────────────────────────────── */

export const MOCK_ONBOARDING_STATUS = {
  profile_complete: true,
  resume_uploaded: true,
  career_dna_generated: true,
  steps_completed: 4,
  total_steps: 4,
} as const;

/* ── Career DNA ──────────────────────────────────────────── */

export const MOCK_CAREER_DNA_SUMMARY = {
  completeness_score: 87,
  dimensions_count: 6,
  last_updated: "2026-01-14T08:00:00Z",
  top_skills: ["TypeScript", "System Design", "API Architecture"],
} as const;

export const MOCK_CAREER_DNA_PROFILE = {
  id: "cdna-001",
  user_id: "vr-user-001",
  completeness_score: 87,
  dimensions_count: 6,
  created_at: "2025-12-15T00:00:00Z",
  updated_at: "2026-01-14T08:00:00Z",
} as const;

export const MOCK_SKILL_GENOME = [
  { skill_name: "TypeScript", proficiency_level: 92, category: "Programming", confidence: 0.95 },
  { skill_name: "React", proficiency_level: 88, category: "Frontend", confidence: 0.90 },
  { skill_name: "Node.js", proficiency_level: 85, category: "Backend", confidence: 0.88 },
  { skill_name: "PostgreSQL", proficiency_level: 78, category: "Database", confidence: 0.85 },
  { skill_name: "Docker", proficiency_level: 72, category: "DevOps", confidence: 0.80 },
  { skill_name: "System Design", proficiency_level: 80, category: "Architecture", confidence: 0.82 },
] as const;

export const MOCK_EXPERIENCE_BLUEPRINT = {
  total_years: 8,
  roles: [
    { title: "Senior Software Engineer", company: "TechCorp", years: 3 },
    { title: "Software Engineer", company: "StartupAI", years: 5 },
  ],
} as const;

export const MOCK_GROWTH_VECTOR = {
  target_role: "Staff Engineer",
  readiness_score: 72,
  gap_areas: ["distributed systems", "team leadership"],
} as const;

export const MOCK_VALUES_PROFILE = {
  top_values: ["innovation", "autonomy", "impact"],
  alignment_score: 85,
} as const;

export const MOCK_MARKET_POSITION = {
  market_demand: "high",
  salary_percentile: 78,
  competitive_index: 0.82,
} as const;

/* ── Threat Radar ────────────────────────────────────────── */

export const MOCK_THREAT_RADAR_OVERVIEW = {
  automation_risk: {
    risk_level: "Low",
    risk_score: 0.18,
    probability: 0.15,
  },
  alerts_summary: {
    total: 5,
    unread: 2,
    critical: 0,
    high: 1,
    medium: 3,
    low: 1,
  },
  resilience_score: 78,
  last_scan: "2026-01-14T12:00:00Z",
} as const;

export const MOCK_RESILIENCE = {
  overall_score: 78,
  adaptability: 82,
  skill_diversity: 75,
  market_readiness: 80,
  learning_velocity: 73,
} as const;

export const MOCK_SKILLS_SHIELD = {
  protected_skills: 12,
  at_risk_skills: 3,
  emerging_skills: 5,
  matrix: [
    { skill: "TypeScript", status: "protected", shield_level: 0.95 },
    { skill: "React", status: "protected", shield_level: 0.90 },
    { skill: "jQuery", status: "at_risk", shield_level: 0.30 },
  ],
} as const;

export const MOCK_THREAT_ALERTS = {
  items: [
    {
      id: "alert-001",
      type: "skill_decay",
      severity: "medium",
      title: "jQuery proficiency declining",
      description: "Market demand for jQuery has decreased 40% year-over-year.",
      status: "unread",
      created_at: "2026-01-10T00:00:00Z",
    },
    {
      id: "alert-002",
      type: "market_shift",
      severity: "high",
      title: "AI/ML skills demand surge",
      description: "AI engineering roles grew 65% in your region.",
      status: "unread",
      created_at: "2026-01-12T00:00:00Z",
    },
  ],
  total: 5,
  page: 1,
  page_size: 20,
} as const;

export const MOCK_RESILIENCE_HISTORY = {
  data: [
    { date: "2025-12-15", score: 70, delta: 0 },
    { date: "2025-12-22", score: 72, delta: 2 },
    { date: "2025-12-29", score: 74, delta: 2 },
    { date: "2026-01-05", score: 76, delta: 2 },
    { date: "2026-01-12", score: 78, delta: 2 },
  ],
  period_days: 30,
} as const;

/* ── Recommendations ─────────────────────────────────────── */

export const MOCK_RECOMMENDATIONS = {
  recommendations: [
    {
      id: "rec-001",
      title: "Complete TypeScript Advanced Patterns Course",
      description: "Strengthen your TypeScript expertise with advanced type-level programming.",
      priority: "high",
      category: "skill_development",
      estimated_impact: 0.85,
      status: "pending",
    },
    {
      id: "rec-002",
      title: "Publish Technical Blog Post",
      description: "Increase visibility by sharing your system design knowledge.",
      priority: "medium",
      category: "visibility",
      estimated_impact: 0.60,
      status: "pending",
    },
    {
      id: "rec-003",
      title: "Contribute to Open Source Project",
      description: "Build your public portfolio with meaningful contributions.",
      priority: "medium",
      category: "portfolio",
      estimated_impact: 0.70,
      status: "in_progress",
    },
  ],
  total: 3,
  generated_at: "2026-01-14T08:00:00Z",
} as const;

/* ── Workflows ───────────────────────────────────────────── */

export const MOCK_WORKFLOWS = {
  workflows: [
    {
      id: "wf-001",
      name: "Resume Optimization",
      description: "AI-powered resume enhancement for target roles.",
      status: "available",
      steps_count: 4,
      estimated_duration: "15 min",
    },
    {
      id: "wf-002",
      name: "Interview Preparation",
      description: "Personalized interview prep based on your Career DNA.",
      status: "available",
      steps_count: 6,
      estimated_duration: "30 min",
    },
  ],
  total: 2,
} as const;

/* ── Career Passport ─────────────────────────────────────── */

export const MOCK_CAREER_PASSPORT = {
  total_mappings: 3,
  total_comparisons: 2,
  credential_mappings: [
    {
      id: "cm-001",
      source_qualification: "BSc Computer Science",
      source_country: "Netherlands",
      target_country: "United States",
      equivalent_level: "Bachelor's Degree",
      eqf_level: 6,
    },
    {
      id: "cm-002",
      source_qualification: "ISTQB Foundation",
      source_country: "International",
      target_country: "Germany",
      equivalent_level: "ISTQB Certified Tester",
      eqf_level: 5,
    },
  ],
  country_comparisons: [
    {
      id: "cc-001",
      source_country: "Netherlands",
      target_country: "Germany",
      salary_delta_pct: -5,
      cost_of_living_index: 95,
      market_demand_level: "high",
      purchasing_power_delta: 3,
    },
  ],
  visa_assessments: [
    {
      id: "va-001",
      target_country: "Germany",
      visa_type: "Blue Card",
      nationality: "Turkish",
      eligibility_score: 0.85,
      processing_time_weeks: 8,
    },
  ],
  disclaimer: "Data is indicative only. Consult official sources for authoritative information.",
} as const;

/* ── Salary Intelligence ─────────────────────────────────── */

export const MOCK_SALARY_INTELLIGENCE = {
  current_estimate: {
    currency: "EUR",
    median: 85000,
    p25: 72000,
    p75: 98000,
  },
  market_trend: "growing",
  last_updated: "2026-01-14T00:00:00Z",
} as const;

/* ── Billing Features ────────────────────────────────────── */

/**
 * Sprint 37 WS-2: Mock billing features matching FeatureAccessResponse.
 * Without this, VR pricing screenshots show all cards as "Coming Soon"
 * because billingEnabled defaults to false.
 */
export const MOCK_BILLING_FEATURES = {
  tier: "pro" as const,
  engines: [
    "career_dna",
    "threat_radar",
    "skill_decay",
    "salary_intelligence",
    "career_simulation",
    "interview_intelligence",
    "hidden_job_market",
    "collective_intelligence",
    "recommendation_intelligence",
    "career_action_planner",
  ],
  scan_limit: 30,
  billing_enabled: true,
} as const;

/* ── Auth Token Response (defensive mock) ────────────────── */

/**
 * Sprint 37 WS-2: Defensive auth mock.
 * JWT exp=2286 prevents 401 in normal VR flow, but these provide
 * a safety net if refresh is triggered by race conditions.
 */
export const MOCK_TOKEN_RESPONSE = {
  access_token: "vr-mock-access-token-001",
  refresh_token: "vr-mock-refresh-token-001",
  token_type: "bearer",
} as const;

/* ── Route Map ───────────────────────────────────────────── */

/**
 * Maps URL path patterns to their mock responses.
 * Used by the visual fixtures route handler.
 */
export const API_ROUTE_MAP: Record<string, unknown> = {
  // Auth
  "/api/v1/users/me": MOCK_USER,
  "/api/v1/auth/refresh": MOCK_TOKEN_RESPONSE,
  "/api/v1/auth/login": MOCK_TOKEN_RESPONSE,
  "/api/v1/auth/logout": { status: "ok" },

  // OAuth (Sprint Pre-40 H7)
  "/api/v1/auth/oauth/google": MOCK_TOKEN_RESPONSE,
  "/api/v1/auth/oauth/microsoft": MOCK_TOKEN_RESPONSE,

  // Health
  "/api/v1/health/ready": MOCK_HEALTH,

  // Onboarding
  "/api/v1/users/onboarding-status": MOCK_ONBOARDING_STATUS,
  "/api/v1/user-profile/onboarding": MOCK_ONBOARDING_STATUS,

  // Billing (Sprint 37 WS-2)
  "/api/v1/billing/features": MOCK_BILLING_FEATURES,

  // Career DNA
  "/api/v1/career-dna": MOCK_CAREER_DNA_PROFILE,
  "/api/v1/career-dna/summary": MOCK_CAREER_DNA_SUMMARY,
  "/api/v1/career-dna/skill-genome": MOCK_SKILL_GENOME,
  "/api/v1/career-dna/experience-blueprint": MOCK_EXPERIENCE_BLUEPRINT,
  "/api/v1/career-dna/growth-vector": MOCK_GROWTH_VECTOR,
  "/api/v1/career-dna/values-profile": MOCK_VALUES_PROFILE,
  "/api/v1/career-dna/market-position": MOCK_MARKET_POSITION,

  // Threat Radar
  "/api/v1/threat-radar": MOCK_THREAT_RADAR_OVERVIEW,
  "/api/v1/threat-radar/resilience": MOCK_RESILIENCE,
  "/api/v1/threat-radar/skill-shield": MOCK_SKILLS_SHIELD,
  "/api/v1/threat-radar/alerts": MOCK_THREAT_ALERTS,
  "/api/v1/threat-radar/resilience/history": MOCK_RESILIENCE_HISTORY,

  // Recommendations
  "/api/v1/recommendations": MOCK_RECOMMENDATIONS,
  "/api/v1/recommendations/dashboard": MOCK_RECOMMENDATIONS,

  // Workflows
  "/api/v1/workflows": MOCK_WORKFLOWS,
  "/api/v1/workflows/dashboard": MOCK_WORKFLOWS,

  // Career Passport
  "/api/v1/career-passport/dashboard": MOCK_CAREER_PASSPORT,

  // Salary Intelligence
  "/api/v1/salary-intelligence": MOCK_SALARY_INTELLIGENCE,
  "/api/v1/salary-intelligence/dashboard": MOCK_SALARY_INTELLIGENCE,
};
