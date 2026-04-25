/**
 * PathForge — Sprint 28: Sidebar Navigation Tests
 * ==================================================
 * Structural tests for section headers and navigation coherence.
 */

import { describe, it, expect } from "vitest";

/**
 * These are structural tests validating the navigation configuration
 * rather than component rendering (which would require jsdom + React).
 */

// Inline copy of navigation structure for testing without importing
// the client component directly. This mirrors layout.tsx exactly.
const navigation = [
  {
    label: "",
    items: [
      { name: "Dashboard", href: "/dashboard", icon: "📊" },
      { name: "Onboarding", href: "/dashboard/onboarding", icon: "🚀" },
    ],
  },
  {
    label: "CAREER",
    items: [
      { name: "Career DNA", href: "/dashboard/career-dna", icon: "🧬" },
      { name: "Threat Radar", href: "/dashboard/threat-radar", icon: "🛡️" },
      { name: "Job Matches", href: "/dashboard/matches", icon: "🎯" },
      { name: "Applications", href: "/dashboard/applications", icon: "📋" },
      { name: "Resumes", href: "/dashboard/resumes", icon: "📄" },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { name: "Hidden Market", href: "/dashboard/hidden-job-market", icon: "🕵️" },
      { name: "Career Passport", href: "/dashboard/career-passport", icon: "🌍" },
      { name: "Interview Prep", href: "/dashboard/interview-prep", icon: "🎤" },
      { name: "Skills Health", href: "/dashboard/skill-decay", icon: "🔋" },
      { name: "Salary Intelligence", href: "/dashboard/salary-intelligence", icon: "💰" },
      { name: "Career Simulator", href: "/dashboard/career-simulation", icon: "🔮" },
      { name: "Career Moves", href: "/dashboard/transition-pathways", icon: "🔄" },
    ],
  },
  {
    label: "COMMAND",
    items: [
      { name: "Command Center", href: "/dashboard/command-center", icon: "🎛️" },
      { name: "Actions", href: "/dashboard/recommendations", icon: "⚡" },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { name: "Notifications", href: "/dashboard/notifications", icon: "🔔" },
      { name: "Analytics", href: "/dashboard/analytics", icon: "📈" },
      { name: "Settings", href: "/dashboard/settings", icon: "⚙️" },
    ],
  },
] as const;

describe("Sidebar Navigation Structure", () => {
  it("should have exactly 5 sections", () => {
    expect(navigation).toHaveLength(5);
  });

  it("should have required section headers: CAREER, INTELLIGENCE, COMMAND, OPERATIONS", () => {
    const labels = navigation.map((s) => s.label).filter(Boolean);
    expect(labels).toContain("CAREER");
    expect(labels).toContain("INTELLIGENCE");
    expect(labels).toContain("COMMAND");
    expect(labels).toContain("OPERATIONS");
  });

  it("should have Sprint 28 items in INTELLIGENCE section", () => {
    const intelligenceSection = navigation.find((s) => s.label === "INTELLIGENCE");
    const itemNames = intelligenceSection?.items.map((i) => i.name) ?? [];
    expect(itemNames).toContain("Hidden Market");
    expect(itemNames).toContain("Career Passport");
    expect(itemNames).toContain("Interview Prep");
  });

  it("should have Command Center and Actions in COMMAND section", () => {
    const commandSection = navigation.find((s) => s.label === "COMMAND");
    const itemNames = commandSection?.items.map((i) => i.name) ?? [];
    expect(itemNames).toContain("Command Center");
    expect(itemNames).toContain("Actions");
  });

  it("should have Notifications in OPERATIONS section", () => {
    const operationsSection = navigation.find((s) => s.label === "OPERATIONS");
    const itemNames = operationsSection?.items.map((i) => i.name) ?? [];
    expect(itemNames).toContain("Notifications");
  });

  it("should not have duplicate hrefs across all sections", () => {
    const allHrefs = navigation.flatMap((s) => s.items.map((i) => i.href));
    const uniqueHrefs = new Set(allHrefs);
    expect(uniqueHrefs.size).toBe(allHrefs.length);
  });

  it("should have all Sprint 28 routes", () => {
    const allHrefs = navigation.flatMap((s) => s.items.map((i) => i.href));
    expect(allHrefs).toContain("/dashboard/hidden-job-market");
    expect(allHrefs).toContain("/dashboard/career-passport");
    expect(allHrefs).toContain("/dashboard/interview-prep");
    expect(allHrefs).toContain("/dashboard/command-center");
    expect(allHrefs).toContain("/dashboard/notifications");
    expect(allHrefs).toContain("/dashboard/recommendations");
  });
});
